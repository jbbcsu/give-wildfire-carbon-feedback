#!/usr/bin/env python3
"""Build an alternative 0.5-degree crop-cell to Hultgren-region crosswalk."""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
from pyproj import CRS, Transformer
from shapely import Polygon, make_valid, union_all
from shapely.geometry import box
from shapely.ops import transform
from shapely.strtree import STRtree

ROOT = Path(__file__).resolve().parents[1]
ROBINSON = CRS.from_proj4(
    "+proj=robin +lon_0=0 +x_0=0 +y_0=0 +ellps=WGS84 +datum=WGS84 +units=m +no_defs"
)
AREA_CRS = CRS.from_epsg(6933)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def polygonal_valid(geometry: object) -> object:
    candidate = geometry if geometry.is_valid else make_valid(geometry)
    if candidate.geom_type in ("Polygon", "MultiPolygon"):
        return candidate
    parts = [part for part in candidate.geoms if part.geom_type in ("Polygon", "MultiPolygon")]
    return union_all(parts)


def build_regions(points_path: Path) -> tuple[list[str], list[object], dict[str, object]]:
    columns = ["long", "lat", "order", "hole", "id", "group", "area_sqkm"]
    points = pd.read_csv(points_path, usecols=columns)
    require(len(points) == 714_615, "author point count changed")
    require(points.id.nunique() == 24_376 and points.group.nunique() == 27_005, "author region/ring count changed")
    rings: dict[str, dict[str, object]] = {}
    invalid_rings = 0
    for group, frame in points.groupby("group", sort=False):
        require(frame.id.nunique() == 1 and frame.hole.nunique() == 1, f"mixed ring metadata: {group}")
        ring = Polygon(frame.sort_values("order")[["long", "lat"]].to_numpy(dtype=float))
        if not ring.is_valid:
            invalid_rings += 1
            ring = polygonal_valid(ring)
        require(not ring.is_empty and ring.area > 0, f"empty author ring: {group}")
        region_id = str(frame.id.iloc[0])
        entry = rings.setdefault(region_id, {"outer": [], "holes": [], "source_area_sqkm": float(frame.area_sqkm.iloc[0])})
        entry["holes" if bool(frame.hole.iloc[0]) else "outer"].append(ring)
    del points
    gc.collect()

    ids: list[str] = []
    geometries: list[object] = []
    invalid_regions = 0
    area_ratios = []
    for region_id, parts in rings.items():
        require(len(parts["outer"]) > 0, f"region has no outer ring: {region_id}")
        geometry = union_all(parts["outer"])
        if parts["holes"]:
            geometry = geometry.difference(union_all(parts["holes"]))
        if not geometry.is_valid:
            invalid_regions += 1
            geometry = polygonal_valid(geometry)
        require(not geometry.is_empty and geometry.area > 0, f"empty author region: {region_id}")
        ids.append(region_id)
        geometries.append(geometry)
        area_ratios.append((geometry.area / 1e6) / float(parts["source_area_sqkm"]))
    del rings
    gc.collect()
    ratios = np.asarray(area_ratios, dtype=float)
    audit = {
        "regions": len(ids),
        "invalid_rings_repaired": invalid_rings,
        "invalid_regions_repaired": invalid_regions,
        "robinson_polygon_area_over_stored_area_quantiles": {
            str(q): float(np.quantile(ratios, q)) for q in (0.0, 0.01, 0.5, 0.99, 1.0)
        },
    }
    return ids, geometries, audit


def read_area(path: Path) -> np.ndarray:
    with rasterio.open(path) as source:
        require(source.shape == (360, 720), "crop-area grid shape changed")
        require(source.crs == rasterio.crs.CRS.from_epsg(4326), "crop-area CRS changed")
        require(np.allclose(source.transform.a, 0.5) and np.allclose(source.transform.e, -0.5), "crop-area resolution changed")
        result = np.asarray(source.read(1), dtype=np.float64)
    require(np.isfinite(result).all() and (result >= 0).all(), "crop area must be finite and nonnegative")
    return result


def build_crosswalk(
    ids: list[str], geometries: list[object], rainfed: np.ndarray, irrigated: np.ndarray,
    region_weights: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, object]]:
    tree = STRtree(geometries)
    transformer = Transformer.from_crs(4326, AREA_CRS, always_xy=True)
    support_rows, support_cols = np.nonzero((rainfed + irrigated) > 0)
    records = []
    cells_without_region = 0
    cells_overlap_over_one = 0
    rainfed_without_region = 0.0
    irrigated_without_region = 0.0
    overlap_sums = []
    for row, col in zip(support_rows, support_cols, strict=True):
        north = 90.0 - row * 0.5
        south = north - 0.5
        west = -180.0 + col * 0.5
        east = west + 0.5
        cell = transform(transformer.transform, box(west, south, east, north))
        candidates = tree.query(cell)
        cell_records = []
        overlap_sum = 0.0
        for index in candidates:
            intersection_area = float(cell.intersection(geometries[int(index)]).area)
            if intersection_area <= 0:
                continue
            fraction = intersection_area / cell.area
            overlap_sum += fraction
            cell_records.append({
                "native_lat_index": int(row),
                "native_lon_index": int(col),
                "latitude": float(89.75 - row * 0.5),
                "longitude": float(-179.75 + col * 0.5),
                "region_key": ids[int(index)],
                "cell_area_equal_area_m2": float(cell.area),
                "intersection_area_equal_area_m2": intersection_area,
                "cell_overlap_fraction": fraction,
                "rainfed_maize_ha_proxy_within_region": float(rainfed[row, col] * fraction),
                "irrigated_maize_ha_proxy_within_region": float(irrigated[row, col] * fraction),
            })
        if not cell_records:
            cells_without_region += 1
            rainfed_without_region += float(rainfed[row, col])
            irrigated_without_region += float(irrigated[row, col])
        if overlap_sum > 1.000001:
            cells_overlap_over_one += 1
        overlap_sums.append(overlap_sum)
        records.extend(cell_records)
    result = pd.DataFrame(records).sort_values(
        ["native_lat_index", "native_lon_index", "region_key"]
    ).reset_index(drop=True)
    for regime in ("rainfed", "irrigated"):
        proxy = f"{regime}_maize_ha_proxy_within_region"
        denominator = result.groupby("region_key")[proxy].transform("sum")
        result[f"{regime}_weight_within_region"] = np.where(denominator > 0, result[proxy] / denominator, 0.0)
    result["combined_maize_ha_proxy_within_region"] = (
        result.rainfed_maize_ha_proxy_within_region + result.irrigated_maize_ha_proxy_within_region
    )
    combined_denominator = result.groupby("region_key").combined_maize_ha_proxy_within_region.transform("sum")
    result["combined_weight_within_region"] = np.where(
        combined_denominator > 0,
        result.combined_maize_ha_proxy_within_region / combined_denominator,
        0.0,
    )
    region_proxy = result.groupby("region_key", as_index=False).agg(
        mirca_rainfed_proxy_ha=("rainfed_maize_ha_proxy_within_region", "sum"),
        mirca_irrigated_proxy_ha=("irrigated_maize_ha_proxy_within_region", "sum"),
    )
    region_proxy["mirca_combined_proxy_ha"] = region_proxy.mirca_rainfed_proxy_ha + region_proxy.mirca_irrigated_proxy_ha
    region_proxy = region_proxy.merge(
        region_weights[["hierid", "corn"]].rename(columns={"hierid": "region_key", "corn": "author_corn_weight"}),
        on="region_key", how="left", validate="one_to_one",
    )
    positive = region_proxy[(region_proxy.mirca_combined_proxy_ha > 0) & (region_proxy.author_corn_weight > 0)].copy()
    ratio = positive.mirca_combined_proxy_ha / positive.author_corn_weight
    total_rf = float(rainfed.sum())
    total_ir = float(irrigated.sum())
    audit = {
        "positive_union_crop_cells": len(support_rows),
        "crosswalk_rows": len(result),
        "mapped_regions": int(result.region_key.nunique()),
        "cells_without_region_intersection": cells_without_region,
        "cells_with_overlap_fraction_above_one_tolerance": cells_overlap_over_one,
        "cell_overlap_sum_quantiles": {
            str(q): float(np.quantile(overlap_sums, q)) for q in (0.0, 0.01, 0.5, 0.99, 1.0)
        },
        "overlap_interpretation": "expected because the author impact-region system contains mixed-resolution regions; weights are normalized within each region, not allocated across regions",
        "mirca_global_rainfed_ha": total_rf,
        "mirca_global_irrigated_ha": total_ir,
        "mirca_global_combined_ha": total_rf + total_ir,
        "rainfed_ha_in_cells_without_region_intersection": rainfed_without_region,
        "irrigated_ha_in_cells_without_region_intersection": irrigated_without_region,
        "combined_crop_fraction_in_cells_without_region_intersection": float(
            (rainfed_without_region + irrigated_without_region) / (total_rf + total_ir)
        ),
        "author_global_corn_weight": float(region_weights.corn.sum()),
        "author_corn_minus_mirca_global_fraction": float(region_weights.corn.sum() / (total_rf + total_ir) - 1.0),
        "regions_with_positive_mirca_proxy": int((region_proxy.mirca_combined_proxy_ha > 0).sum()),
        "regions_with_positive_author_corn_weight": int((region_proxy.author_corn_weight > 0).sum()),
        "regions_with_both_positive": len(positive),
        "log1p_region_proxy_author_correlation": float(
            np.corrcoef(np.log1p(positive.mirca_combined_proxy_ha), np.log1p(positive.author_corn_weight))[0, 1]
        ),
        "region_mirca_proxy_over_author_corn_quantiles": {
            str(q): float(np.quantile(ratio, q)) for q in (0.01, 0.1, 0.5, 0.9, 0.99)
        },
        "within_region_weight_sum_maximum_absolute_error": float(max(
            (lambda sums: (sums[sums > 0] - 1.0).abs().max())(
                result.groupby("region_key")[f"{regime}_weight_within_region"].sum()
            )
            for regime in ("rainfed", "irrigated")
        )),
    }
    return result, audit


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--points", type=Path, required=True)
    parser.add_argument("--source-fst", type=Path, required=True)
    parser.add_argument("--hierarchy", type=Path, required=True)
    parser.add_argument("--rainfed-area", type=Path, required=True)
    parser.add_argument("--irrigated-area", type=Path, required=True)
    parser.add_argument("--region-weights", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    receipt = args.output.with_suffix(args.output.suffix + ".result.json")
    require(not args.output.exists() and not receipt.exists(), "fresh output and receipt required")
    ids, geometries, geometry_audit = build_regions(args.points)
    equal_area_transformer = Transformer.from_crs(ROBINSON, AREA_CRS, always_xy=True)
    for index in range(len(geometries)):
        geometries[index] = transform(equal_area_transformer.transform, geometries[index])
    hierarchy = pd.read_csv(args.hierarchy, comment="#")
    terminal = set(hierarchy.loc[hierarchy.is_terminal.eq(True), "region-key"])
    geometry_ids = set(ids)
    hierarchy_audit = {
        "terminal_regions": len(terminal),
        "geometry_regions": len(geometry_ids),
        "geometry_not_terminal": sorted(geometry_ids - terminal),
        "terminal_without_geometry_count": len(terminal - geometry_ids),
        "terminal_without_geometry_examples": sorted(terminal - geometry_ids)[:50],
    }
    require(not hierarchy_audit["geometry_not_terminal"], "geometry IDs absent from terminal hierarchy")
    rainfed = read_area(args.rainfed_area)
    irrigated = read_area(args.irrigated_area)
    region_weights = pd.read_csv(args.region_weights)
    require(region_weights.hierid.is_unique and len(region_weights) == 24_378, "author region weights changed")
    crosswalk, allocation_audit = build_crosswalk(ids, geometries, rainfed, irrigated, region_weights)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    crosswalk.to_parquet(args.output, index=False, compression="zstd")
    normalized = allocation_audit["within_region_weight_sum_maximum_absolute_error"] <= 1e-12
    result = {
        "schema": "hultgren_impact_region_grid_crosswalk/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "alternative_half_degree_within_region_mirca_weight_proxy_not_sage_replication",
        "sources": {
            "source_impact_region_fst": {"path": str(args.source_fst), "bytes": args.source_fst.stat().st_size, "sha256": digest(args.source_fst)},
            "points": {"path": str(args.points), "bytes": args.points.stat().st_size, "sha256": digest(args.points)},
            "hierarchy": {"path": str(args.hierarchy), "bytes": args.hierarchy.stat().st_size, "sha256": digest(args.hierarchy)},
            "rainfed_area": {"path": str(args.rainfed_area), "bytes": args.rainfed_area.stat().st_size, "sha256": digest(args.rainfed_area)},
            "irrigated_area": {"path": str(args.irrigated_area), "bytes": args.irrigated_area.stat().st_size, "sha256": digest(args.irrigated_area)},
            "region_weights": {"path": str(args.region_weights), "bytes": args.region_weights.stat().st_size, "sha256": digest(args.region_weights)},
        },
        "geometry_audit": geometry_audit,
        "hierarchy_audit": hierarchy_audit,
        "allocation_audit": allocation_audit,
        "output": {"path": str(args.output), "rows": len(crosswalk), "bytes": args.output.stat().st_size, "sha256": digest(args.output)},
        "method": "author polygons transformed from source Robinson coordinates to EPSG:6933; exact equal-area positive-area cell intersections; MIRCA crop proxy allocated uniformly within each 0.5-degree cell and normalized separately within every overlapping author impact region",
        "claim_gates": {
            "author_impact_region_geometry_used": True,
            "mixed_resolution_region_overlap_explicit": allocation_audit["cells_with_overlap_fraction_above_one_tolerance"] > 0,
            "within_region_proxy_weights_normalized": normalized,
            "source_sage_pixel_weights_reproduced": False,
            "weather_aggregation_validated": False,
            "response_damage_or_scc_validated": False,
        },
        "implementation": {"path": str(Path(__file__).resolve().relative_to(ROOT)), "sha256": digest(Path(__file__).resolve())},
        "point_export_implementation": {
            "path": "scripts/export_hultgren_impact_region_points.R",
            "sha256": digest(ROOT / "scripts/export_hultgren_impact_region_points.R"),
        },
    }
    receipt.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "geometry": geometry_audit, "hierarchy": hierarchy_audit, "allocation": allocation_audit}, indent=2))


if __name__ == "__main__":
    main()
