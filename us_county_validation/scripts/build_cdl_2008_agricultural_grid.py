#!/usr/bin/env python3
"""Reduce the 2008 CDL to bounded sparse county/agricultural grid weights."""
from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import json
import math
import tomllib
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import rasterio
from pyproj import CRS, Transformer
from rasterio.features import geometry_mask
from rasterio.windows import Window, from_bounds, transform as window_transform
import shapefile
from shapely import make_valid
from shapely.geometry import mapping, shape
from shapely.ops import transform


CONTIGUOUS_STATE_FIPS = {
    "01", "04", "05", "06", "08", "09", "10", "11", "12", "13",
    "16", "17", "18", "19", "20", "21", "22", "23", "24", "25",
    "26", "27", "28", "29", "30", "31", "32", "33", "34", "35",
    "36", "37", "38", "39", "40", "41", "42", "44", "45", "46",
    "47", "48", "49", "50", "51", "53", "54", "55", "56",
}


def hashes(path: Path) -> tuple[str, str]:
    sha256 = hashlib.sha256()
    sha512 = hashlib.sha512()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            sha256.update(block)
            sha512.update(block)
    return sha256.hexdigest(), sha512.hexdigest()


def cdl_path(archive: Path, member: str) -> str:
    return f"zip://{archive.resolve()}!{member}"


def clipped_window(bounds: tuple[float, float, float, float], dataset) -> Window:
    candidate = from_bounds(*bounds, transform=dataset.transform)
    left = max(0, int(math.floor(candidate.col_off)))
    top = max(0, int(math.floor(candidate.row_off)))
    right = min(dataset.width, int(math.ceil(candidate.col_off + candidate.width)))
    bottom = min(dataset.height, int(math.ceil(candidate.row_off + candidate.height)))
    if right <= left or bottom <= top:
        raise ValueError("county does not overlap the CDL raster")
    return Window(left, top, right - left, bottom - top)


def county_record_index(path: Path, states: set[str], selected: set[str] | None):
    reader = shapefile.Reader(str(path))
    fields = [field[0] for field in reader.fields[1:]]
    required = {"STATEFP", "GEOID", "NAME"}
    if missing := required - set(fields):
        raise ValueError(f"county shapefile lacks {sorted(missing)}")
    positions = {name: fields.index(name) for name in required}
    projection = path.with_suffix(".prj")
    if not projection.is_file():
        raise ValueError("county shapefile lacks .prj")
    crs = CRS.from_wkt(projection.read_text(encoding="utf-8"))
    records = []
    for index, record in enumerate(reader.iterRecords()):
        state = str(record[positions["STATEFP"]]).zfill(2)
        if state not in states:
            continue
        geoid = str(record[positions["GEOID"]]).zfill(5)
        if selected is not None and geoid not in selected:
            continue
        records.append((geoid, state, str(record[positions["NAME"]]), index))
    records.sort(key=lambda row: row[0])
    return reader, crs, records


def inventory_geoids(path: Path, eligible_column: str) -> set[str]:
    with path.open("r", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        fields = set(reader.fieldnames or [])
        required = {"county_geoid", eligible_column}
        if missing := required - fields:
            raise ValueError(f"county inventory lacks {sorted(missing)}")
        selected = {
            str(row["county_geoid"]).zfill(5)
            for row in reader
            if str(row[eligible_column]).strip().lower() in {"true", "1", "yes"}
        }
    if not selected:
        raise ValueError("county inventory selected no counties")
    return selected


def reduce_county(
    dataset,
    geometry,
    masks: dict[str, np.ndarray],
    factor: int,
    block_size: int,
) -> tuple[dict[str, np.ndarray], Window]:
    window = clipped_window(geometry.bounds, dataset)
    coarse_rows = math.ceil(dataset.height / factor)
    coarse_cols = math.ceil(dataset.width / factor)
    accumulator = {
        name: np.zeros(coarse_rows * coarse_cols, dtype=np.int64) for name in masks
    }
    row_start = int(window.row_off)
    row_stop = row_start + int(window.height)
    col_start = int(window.col_off)
    col_stop = col_start + int(window.width)
    for row_off in range(row_start, row_stop, block_size):
        height = min(block_size, row_stop - row_off)
        for col_off in range(col_start, col_stop, block_size):
            width = min(block_size, col_stop - col_off)
            block = Window(col_off, row_off, width, height)
            data = dataset.read(1, window=block)
            inside = geometry_mask(
                [mapping(geometry)],
                out_shape=data.shape,
                transform=window_transform(block, dataset.transform),
                invert=True,
                all_touched=False,
            )
            if not inside.any():
                continue
            for name, codes in masks.items():
                selected = inside & np.isin(data, codes)
                local_rows, local_cols = np.nonzero(selected)
                if len(local_rows) == 0:
                    continue
                keys = (
                    ((local_rows + row_off) // factor) * coarse_cols
                    + ((local_cols + col_off) // factor)
                )
                unique, counts = np.unique(keys, return_counts=True)
                accumulator[name][unique] += counts
    return accumulator, window


def rows_for_county(
    dataset,
    geoid: str,
    state: str,
    county_name: str,
    accumulator: dict[str, np.ndarray],
    factor: int,
) -> tuple[pa.Table | None, list[dict[str, object]]]:
    coarse_cols = math.ceil(dataset.width / factor)
    records: list[dict[str, object]] = []
    audits = []
    pixel_area = abs(dataset.transform.a * dataset.transform.e)
    for mask_name, values in accumulator.items():
        keys = np.flatnonzero(values)
        total_pixels = int(values[keys].sum())
        if total_pixels == 0:
            audits.append({
                "county_geoid": geoid, "state_fips": state,
                "county_name": county_name, "mask_id": mask_name,
                "agricultural_pixels": 0, "positive_coarse_cells": 0,
            })
            continue
        coarse_row = keys // coarse_cols
        coarse_col = keys % coarse_cols
        row0 = coarse_row * factor
        col0 = coarse_col * factor
        row_span = np.minimum(factor, dataset.height - row0)
        col_span = np.minimum(factor, dataset.width - col0)
        x = dataset.transform.c + (col0 + col_span / 2) * dataset.transform.a
        y = dataset.transform.f + (row0 + row_span / 2) * dataset.transform.e
        counts = values[keys]
        area = counts.astype(float) * pixel_area
        total_area = total_pixels * pixel_area
        for index in range(len(keys)):
            records.append({
                "county_geoid": geoid,
                "state_fips": state,
                "county_name": county_name,
                "mask_id": mask_name,
                "coarse_row": int(coarse_row[index]),
                "coarse_col": int(coarse_col[index]),
                "cell_center_x_m": float(x[index]),
                "cell_center_y_m": float(y[index]),
                "agricultural_pixel_count": int(counts[index]),
                "agricultural_area_m2": float(area[index]),
                "county_agricultural_area_m2": float(total_area),
                "spatial_weight": float(area[index] / total_area),
                "source_raster_crs": "EPSG:5070",
                "source_pixel_area_m2": float(pixel_area),
                "coarse_factor_pixels": factor,
                "coarse_cell_nominal_size_m": float(factor * abs(dataset.transform.a)),
                "spatial_approximation": "agricultural-pixel counts by county and coarse cell; USDM category assigned at coarse-cell center",
                "analysis_role": "historical_agricultural_area_validation_only",
                "scc_authorized": False,
            })
        weight_sum = float(area.sum() / total_area)
        if not np.isclose(weight_sum, 1, rtol=0, atol=1e-12):
            raise ValueError(f"weights do not sum to one for {geoid} {mask_name}")
        audits.append({
            "county_geoid": geoid, "state_fips": state,
            "county_name": county_name, "mask_id": mask_name,
            "agricultural_pixels": total_pixels,
            "agricultural_area_m2": total_area,
            "positive_coarse_cells": int(len(keys)),
            "spatial_weight_sum": weight_sum,
        })
    if not records:
        return None, audits
    return pa.Table.from_pylist(records), audits


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--cdl-archive", type=Path, required=True)
    parser.add_argument("--counties", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--audit-out", type=Path, required=True)
    parser.add_argument("--state-fips", action="append")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--county-inventory", type=Path)
    parser.add_argument("--inventory-eligible-column", default="classifier_eligible")
    arguments = parser.parse_args()
    contract = tomllib.loads(arguments.config.read_text(encoding="utf-8"))
    if arguments.cdl_archive.stat().st_size != int(contract["archive_bytes"]):
        raise ValueError("CDL archive byte size differs from contract")
    sha256, sha512 = hashes(arguments.cdl_archive)
    if sha256 != contract["archive_sha256"] or sha512 != contract["archive_sha512"]:
        raise ValueError("CDL archive checksum differs from contract")
    masks = {
        name: np.asarray(details["codes"], dtype=np.uint8)
        for name, details in contract["masks"].items()
    }
    if not set(masks["cultivated_agriculture"]) < set(masks["broad_agriculture"]):
        raise ValueError("broad mask must strictly contain cultivated mask")
    factor = int(contract["coarse_factor_pixels"])
    block_size = int(contract["block_size_pixels"])
    states = set(arguments.state_fips or CONTIGUOUS_STATE_FIPS)
    if not states <= CONTIGUOUS_STATE_FIPS:
        raise ValueError("requested state is outside the contiguous-state contract")
    selected_geoids = None
    eligible_inventory_geoids = None
    if arguments.county_inventory is not None:
        eligible_inventory_geoids = inventory_geoids(
            arguments.county_inventory, arguments.inventory_eligible_column
        )
        selected_geoids = {
            geoid for geoid in eligible_inventory_geoids if geoid[:2] in states
        }
    county_reader, source_crs, inventory = county_record_index(
        arguments.counties, states, selected_geoids
    )
    expected_count = len(inventory)
    if selected_geoids is not None:
        absent = selected_geoids - {row[0] for row in inventory}
        if absent:
            raise ValueError(
                f"{len(absent)} selected inventory counties absent from requested county geometry/state scope"
            )
    if arguments.limit is not None:
        if arguments.limit <= 0:
            raise ValueError("--limit must be positive")
        inventory = list(itertools.islice(inventory, arguments.limit))
        expected_count = len(inventory)

    arguments.out.parent.mkdir(parents=True, exist_ok=True)
    writer: pq.ParquetWriter | None = None
    county_audits: list[dict[str, object]] = []
    processed_geoids: set[str] = set()
    rows_written = 0
    projected_crs = CRS.from_user_input(contract["raster_crs"])
    gdal_cachemax_bytes = int(contract["gdal_cachemax_bytes"])
    if gdal_cachemax_bytes <= 0 or gdal_cachemax_bytes > 128 * 1024 * 1024:
        raise ValueError("GDAL cache contract must be within (0, 128 MiB]")
    try:
        with rasterio.Env(GDAL_CACHEMAX=gdal_cachemax_bytes), rasterio.open(
            cdl_path(arguments.cdl_archive, contract["archive_member"])
        ) as dataset:
            if (
                dataset.crs != projected_crs
                or dataset.width != int(contract["raster_width"])
                or dataset.height != int(contract["raster_height"])
                or dataset.dtypes != ("uint8",)
            ):
                raise ValueError("CDL raster profile differs from contract")
            for number, (geoid, state, name, shape_index) in enumerate(inventory, start=1):
                if geoid in processed_geoids:
                    raise ValueError(f"duplicate county geometry {geoid}")
                processed_geoids.add(geoid)
                source_geometry = make_valid(
                    shape(county_reader.shape(shape_index).__geo_interface__)
                )
                if source_geometry.is_empty:
                    raise ValueError(f"empty county geometry {geoid}")
                projector = Transformer.from_crs(source_crs, projected_crs, always_xy=True)
                geometry = transform(projector.transform, source_geometry)
                accumulator, _ = reduce_county(dataset, geometry, masks, factor, block_size)
                table, audits = rows_for_county(
                    dataset, geoid, state, name, accumulator, factor
                )
                county_audits.extend(audits)
                if table is not None:
                    if writer is None:
                        writer = pq.ParquetWriter(
                            arguments.out, table.schema, compression="zstd", use_dictionary=True
                        )
                    elif table.schema != writer.schema:
                        raise ValueError(f"output schema drift at county {geoid}")
                    writer.write_table(table)
                    rows_written += table.num_rows
                denominator = "?" if expected_count is None else str(expected_count)
                print(f"{number}/{denominator} {geoid} rows={0 if table is None else table.num_rows}", flush=True)
                del accumulator, table, geometry, source_geometry
    finally:
        if writer is not None:
            writer.close()
    if writer is None:
        raise RuntimeError("no agricultural support rows written")
    if expected_count is not None and len(processed_geoids) != expected_count:
        missing = (selected_geoids or set()) - processed_geoids
        raise ValueError(
            f"processed {len(processed_geoids)} counties but expected {expected_count}; missing {len(missing)}"
        )
    metadata = pq.ParquetFile(arguments.out).metadata
    if metadata.num_rows != rows_written:
        raise RuntimeError("Parquet row count differs from streamed count")
    summaries = {}
    for mask_name in masks:
        rows = [row for row in county_audits if row["mask_id"] == mask_name]
        summaries[mask_name] = {
            "counties_examined": len(rows),
            "counties_with_positive_support": sum(int(row["agricultural_pixels"]) > 0 for row in rows),
            "agricultural_pixels": sum(int(row["agricultural_pixels"]) for row in rows),
            "positive_coarse_cells": sum(int(row["positive_coarse_cells"]) for row in rows),
        }
    output_sha256, output_sha512 = hashes(arguments.out)
    audit = {
        "schema": "cdl_2008_county_agricultural_grid_audit_v1",
        "config": str(arguments.config),
        "cdl_archive": {
            "path": str(arguments.cdl_archive), "bytes": arguments.cdl_archive.stat().st_size,
            "sha256": sha256, "sha512": sha512,
        },
        "county_source": str(arguments.counties),
        "county_inventory": None if arguments.county_inventory is None else {
            "path": str(arguments.county_inventory),
            "eligible_column": arguments.inventory_eligible_column,
            "eligible_counties_all_states": len(eligible_inventory_geoids or []),
            "selected_counties": len(selected_geoids or []),
        },
        "states": sorted(states),
        "counties_examined": len(processed_geoids),
        "output_rows": rows_written,
        "output_sha256": output_sha256,
        "output_sha512": output_sha512,
        "coarse_factor_pixels": factor,
        "gdal_cachemax_bytes": gdal_cachemax_bytes,
        "coarse_cell_nominal_size_m": factor * int(contract["raster_pixel_size_m"]),
        "mask_summaries": summaries,
        "counties": county_audits,
        "claim_boundary": "historical spatial-fidelity sensitivity only; not future drought, damage, or SCC",
    }
    arguments.audit_out.parent.mkdir(parents=True, exist_ok=True)
    arguments.audit_out.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {rows_written} sparse county-mask-grid rows")


if __name__ == "__main__":
    main()
