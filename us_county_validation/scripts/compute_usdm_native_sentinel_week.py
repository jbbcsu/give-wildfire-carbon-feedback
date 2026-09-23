#!/usr/bin/env python3
"""Compute one preregistered county-week at native 30 m CDL pixel centers."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import tomllib
from datetime import date
from pathlib import Path

import numpy as np
import pyarrow.compute as pc
import pyarrow.parquet as pq
import rasterio
from pyproj import CRS, Transformer
from rasterio.features import geometry_mask
from rasterio.windows import Window, transform as window_transform
from shapely import make_valid
from shapely.geometry import mapping, shape
from shapely.ops import transform

from build_cdl_2008_agricultural_grid import cdl_path, clipped_window
from build_usdm_agricultural_exposure import CATEGORY_NAMES, classify_points, read_week_geometries


def sha512_file(path: Path) -> str:
    digest = hashlib.sha512()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def selected_pair(selection: dict, geoid: str, map_date: date) -> bool:
    for county in selection["sentinels"]:
        if str(county["county_geoid"]) != geoid:
            continue
        return map_date.isoformat() in {row["map_date"] for row in county["selected_weeks"]}
    return False


def county_geometry(path: Path, geoid: str, target_crs: CRS):
    import shapefile

    reader = shapefile.Reader(str(path))
    fields = [field[0] for field in reader.fields[1:]]
    position = fields.index("GEOID")
    projection = path.with_suffix(".prj")
    source_crs = CRS.from_wkt(projection.read_text(encoding="utf-8"))
    matches = [
        index for index, record in enumerate(reader.iterRecords())
        if str(record[position]).zfill(5) == geoid
    ]
    if len(matches) != 1:
        raise ValueError(f"expected one county geometry for {geoid}, found {len(matches)}")
    geometry = make_valid(shape(reader.shape(matches[0]).__geo_interface__))
    projector = Transformer.from_crs(source_crs, target_crs, always_xy=True)
    return transform(projector.transform, geometry)


def grid_shares(path: Path, geoid: str, geometries: dict[int, object]) -> dict[str, list[float]]:
    table = pq.read_table(
        path,
        columns=["county_geoid", "mask_id", "cell_center_x_m", "cell_center_y_m", "spatial_weight"],
        filters=[("county_geoid", "=", geoid)],
    )
    if table.num_rows == 0:
        raise ValueError(f"grid has no rows for sentinel county {geoid}")
    transformer = Transformer.from_crs("EPSG:5070", "EPSG:4326", always_xy=True)
    longitude, latitude = transformer.transform(
        np.asarray(table["cell_center_x_m"].to_numpy(), dtype=np.float64),
        np.asarray(table["cell_center_y_m"].to_numpy(), dtype=np.float64),
    )
    severity, violations = classify_points(
        geometries, np.asarray(longitude, dtype=np.float64), np.asarray(latitude, dtype=np.float64)
    )
    if sum(violations.values()):
        raise ValueError("exclusive classes overlap at grid centers")
    weights = np.asarray(table["spatial_weight"].to_numpy(), dtype=np.float64)
    masks = np.asarray(table["mask_id"].to_pylist(), dtype="U24")
    result = {}
    for mask in ("cultivated_agriculture", "broad_agriculture"):
        keep = masks == mask
        shares = np.bincount(severity[keep].astype(np.int16) + 1, weights=weights[keep], minlength=6)
        if not np.isclose(shares.sum(), 1, rtol=0, atol=1e-10):
            raise ValueError(f"grid shares do not sum to one for {mask}")
        result[mask] = shares.tolist()
    return result


def native_counts(
    archive: Path,
    member: str,
    geometry,
    mask_codes: dict[str, np.ndarray],
    geometries: dict[int, object],
    block_size: int,
    gdal_cachemax: int,
) -> dict[str, np.ndarray]:
    counts = {mask: np.zeros(6, dtype=np.int64) for mask in mask_codes}
    with rasterio.Env(GDAL_CACHEMAX=gdal_cachemax), rasterio.open(cdl_path(archive, member)) as dataset:
        window = clipped_window(geometry.bounds, dataset)
        row_start, col_start = int(window.row_off), int(window.col_off)
        row_stop = row_start + int(window.height)
        col_stop = col_start + int(window.width)
        to_wgs84 = Transformer.from_crs(dataset.crs, "EPSG:4326", always_xy=True)
        broad_codes = mask_codes["broad_agriculture"]
        cultivated_codes = mask_codes["cultivated_agriculture"]
        for row_off in range(row_start, row_stop, block_size):
            height = min(block_size, row_stop - row_off)
            for col_off in range(col_start, col_stop, block_size):
                width = min(block_size, col_stop - col_off)
                block = Window(col_off, row_off, width, height)
                data = dataset.read(1, window=block)
                inside = geometry_mask(
                    [mapping(geometry)], out_shape=data.shape,
                    transform=window_transform(block, dataset.transform),
                    invert=True, all_touched=False,
                )
                broad = inside & np.isin(data, broad_codes)
                local_row, local_col = np.nonzero(broad)
                if len(local_row) == 0:
                    continue
                global_row = local_row + row_off
                global_col = local_col + col_off
                x, y = dataset.transform * (global_col + 0.5, global_row + 0.5)
                longitude, latitude = to_wgs84.transform(x, y)
                severity, violations = classify_points(
                    geometries,
                    np.asarray(longitude, dtype=np.float64),
                    np.asarray(latitude, dtype=np.float64),
                )
                if sum(violations.values()):
                    raise ValueError("exclusive classes overlap at native pixel centers")
                category = severity.astype(np.int16) + 1
                counts["broad_agriculture"] += np.bincount(category, minlength=6)
                cultivated = np.isin(data[local_row, local_col], cultivated_codes)
                counts["cultivated_agriculture"] += np.bincount(category[cultivated], minlength=6)
    return counts


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sentinel-config", type=Path, required=True)
    parser.add_argument("--cdl-config", type=Path, required=True)
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--county-geoid", required=True)
    parser.add_argument("--map-date", required=True)
    parser.add_argument("--cdl-archive", type=Path, required=True)
    parser.add_argument("--counties", type=Path, required=True)
    parser.add_argument("--shape-dir", type=Path, required=True)
    parser.add_argument("--coarse-grid", type=Path, required=True)
    parser.add_argument("--fine-grid", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    arguments = parser.parse_args()
    geoid = str(arguments.county_geoid).zfill(5)
    map_date = date.fromisoformat(arguments.map_date)
    sentinel = tomllib.loads(arguments.sentinel_config.read_text(encoding="utf-8"))
    cdl = tomllib.loads(arguments.cdl_config.read_text(encoding="utf-8"))
    selection = json.loads(arguments.selection.read_text(encoding="utf-8"))
    if not selected_pair(selection, geoid, map_date):
        raise ValueError("requested county-week is not in the frozen sentinel set")
    if arguments.cdl_archive.stat().st_size != int(cdl["archive_bytes"]):
        raise ValueError("CDL archive byte size differs from contract")
    mask_codes = {
        name: np.asarray(details["codes"], dtype=np.uint8)
        for name, details in cdl["masks"].items()
    }
    shape_path = arguments.shape_dir / f"USDM_{map_date:%Y%m%d}_M.zip"
    geometries = read_week_geometries(shape_path, map_date)
    projected_crs = CRS.from_user_input(cdl["raster_crs"])
    geometry = county_geometry(arguments.counties, geoid, projected_crs)
    counts = native_counts(
        arguments.cdl_archive, str(cdl["archive_member"]), geometry, mask_codes,
        geometries, int(sentinel["native_block_size_pixels"]), int(cdl["gdal_cachemax_bytes"]),
    )
    coarse = grid_shares(arguments.coarse_grid, geoid, geometries)
    fine = grid_shares(arguments.fine_grid, geoid, geometries)
    rows = {}
    for mask in ("cultivated_agriculture", "broad_agriculture"):
        total = int(counts[mask].sum())
        if total <= 0:
            raise ValueError(f"native support is empty for {mask}")
        native = counts[mask].astype(np.float64) / total
        coarse_values = np.asarray(coarse[mask], dtype=np.float64)
        fine_values = np.asarray(fine[mask], dtype=np.float64)
        rows[mask] = {
            "native_pixel_counts": counts[mask].tolist(),
            "native_total_pixels": total,
            "native_shares": native.tolist(),
            "coarse_3960m_shares": coarse_values.tolist(),
            "fine_990m_shares": fine_values.tolist(),
            "coarse_native_tvd": float(0.5 * np.abs(coarse_values - native).sum()),
            "fine_native_tvd": float(0.5 * np.abs(fine_values - native).sum()),
        }
    result = {
        "schema": "usdm_native_30m_sentinel_week_v1",
        "county_geoid": geoid,
        "map_date": map_date.isoformat(),
        "categories": list(CATEGORY_NAMES),
        "masks": rows,
        "sources": {
            "selection_sha512": sha512_file(arguments.selection),
            "coarse_grid_sha512": sha512_file(arguments.coarse_grid),
            "fine_grid_sha512": sha512_file(arguments.fine_grid),
            "usdm_archive_sha512": sha512_file(shape_path),
        },
        "selection_uses_outcomes": False,
        "causal_claim_authorized": False,
        "damage_claim_authorized": False,
        "scc_claim_authorized": False,
    }
    arguments.out.parent.mkdir(parents=True, exist_ok=True)
    arguments.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "county_geoid": geoid,
        "map_date": map_date.isoformat(),
        "coarse_native_tvd": {mask: rows[mask]["coarse_native_tvd"] for mask in rows},
        "fine_native_tvd": {mask: rows[mask]["fine_native_tvd"] for mask in rows},
    }, sort_keys=True))


if __name__ == "__main__":
    main()
