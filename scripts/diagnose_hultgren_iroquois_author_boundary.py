#!/usr/bin/env python3
"""Run the Iroquois weather diagnostic on the authors' impact-region boundary."""

from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
import xarray as xr
from pyproj import CRS, Transformer
from shapely.geometry import Polygon
from shapely.ops import transform

from diagnose_hultgren_iroquois_gswp_aggregation import (
    AREA_CRS,
    FEATURES,
    MIRCA_IR_PATH,
    MIRCA_RF_PATH,
    PR_PATH,
    aggregate_features,
    compare,
    construct_cell_year_features,
    coordinate_edges,
    read_hultgren,
    read_weather,
)

ROOT = Path(__file__).resolve().parents[1]
REGION_POINTS = ROOT / "data/interim/hultgren_impact_regions/USA.14.630.csv"
IMPACT_REGIONS = ROOT / "data/raw/hultgren_response/gitlab_main_20250702/Fig2/data/shapes/impact_region_data_frame.fst"
HIERARCHY = ROOT / "data/raw/hultgren_response/gitlab_main_20250702/Table1/data/shapes/hierarchy.csv"
REGION_WEIGHTS = ROOT / "data/raw/hultgren_response/gitlab_main_20250702/Fig2/data/weights/agglomerated-world-new-hierid-crop-weights.csv"
OUTPUT = ROOT / "data/provenance/hultgren_iroquois_author_boundary_diagnostic_20260923.json"
ROBINSON = CRS.from_proj4(
    "+proj=robin +lon_0=0 +x_0=0 +y_0=0 +ellps=WGS84 +datum=WGS84 +units=m +no_defs"
)
EXPECTED = {
    IMPACT_REGIONS: (20_171_171, "438442adafdaa73156c1dd8baa45cc26a246cc55f9b47df596262b338adbb96af7172df089f0619b365ef4d4356d32a9540d8fc87f86b8af645f899391eb2eb6"),
    HIERARCHY: (2_930_270, "3722ccf2d7b62ce496e7c7257c48b8d47655895887bb582c15c3206f95dafb68d1c13eb77de6dee8ad9fd9040e3e5e41211f0fee62be17cdac055131c9124d93"),
    REGION_POINTS: (835, "caeff86237ab3c60a3268190cbb54f0c644676a99bdce2d08cbc9dfab3a22f2d9ba5c5b39bec6acb4e02bd50b7f6c4a6c3ac977d507b406584e619de9f7ad344"),
}


def digest(path: Path) -> str:
    value = hashlib.sha512()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def identity(path: Path) -> dict[str, object]:
    return {"path": str(path.relative_to(ROOT)), "bytes": path.stat().st_size, "sha512": digest(path)}


def load_author_region() -> tuple[object, dict[str, object]]:
    for path, expected in EXPECTED.items():
        if (path.stat().st_size, digest(path)) != expected:
            raise AssertionError(f"source identity mismatch: {path}")
    hierarchy = pd.read_csv(HIERARCHY, comment="#")
    match = hierarchy[(hierarchy["name"] == "Iroquois") & (hierarchy["parent-key"] == "USA.14")]
    if len(match) != 1 or match.iloc[0]["region-key"] != "USA.14.630":
        raise AssertionError("Iroquois hierarchy crosswalk changed")
    weights = pd.read_csv(REGION_WEIGHTS)
    weight = weights[weights.hierid == "USA.14.630"]
    if len(weight) != 1:
        raise AssertionError("Iroquois administrative crop-weight row changed")
    points = pd.read_csv(REGION_POINTS).sort_values("order")
    if (
        len(points) != 8
        or set(points.id) != {"USA.14.630"}
        or points.hole.any()
        or points.group.nunique() != 1
    ):
        raise AssertionError("Iroquois author polygon extraction changed")
    polygon_robinson = Polygon(zip(points["long"], points["lat"], strict=True))
    if not polygon_robinson.is_valid or polygon_robinson.is_empty:
        raise AssertionError("author Iroquois polygon is invalid")
    polygon_area = transform(Transformer.from_crs(ROBINSON, AREA_CRS, always_xy=True).transform, polygon_robinson)
    polygon_wgs84 = transform(Transformer.from_crs(ROBINSON, 4326, always_xy=True).transform, polygon_robinson)
    metadata = {
        "region_key": "USA.14.630",
        "parent_key": "USA.14",
        "gadmid": int(match.iloc[0]["gadmid"]),
        "agglomid": int(match.iloc[0]["agglomid"]),
        "stored_robinson_area_sqkm": float(points.area_sqkm.iloc[0]),
        "equal_area_polygon_sqkm": float(polygon_area.area / 1e6),
        "source_corn_weight": float(weight.corn.iloc[0]),
        "source_allcrop_weight": float(weight.allcrop.iloc[0]),
        "wgs84_bounds": list(map(float, polygon_wgs84.bounds)),
    }
    return (polygon_robinson, polygon_area, polygon_wgs84), metadata


def build_cells(
    polygon_area: object, polygon_wgs84: object, latitude: np.ndarray, longitude: np.ndarray
) -> pd.DataFrame:
    lat_ascending = latitude[::-1]
    lat_edges = coordinate_edges(lat_ascending, "latitude")
    lon_edges = coordinate_edges(longitude, "longitude")
    west, south, east, north = polygon_wgs84.bounds
    area_transformer = Transformer.from_crs(4326, AREA_CRS, always_xy=True)
    rows = []
    for ascending_lat_index in np.flatnonzero((lat_edges[:-1] < north) & (lat_edges[1:] > south)):
        lat_index = len(latitude) - 1 - int(ascending_lat_index)
        for lon_index in np.flatnonzero((lon_edges[:-1] < east) & (lon_edges[1:] > west)):
            cell = Polygon([
                (lon_edges[lon_index], lat_edges[ascending_lat_index]),
                (lon_edges[lon_index + 1], lat_edges[ascending_lat_index]),
                (lon_edges[lon_index + 1], lat_edges[ascending_lat_index + 1]),
                (lon_edges[lon_index], lat_edges[ascending_lat_index + 1]),
            ])
            cell_area = transform(area_transformer.transform, cell)
            intersection = float(polygon_area.intersection(cell_area).area)
            if intersection > 0:
                rows.append({
                    "lat_index": lat_index,
                    "lon_index": int(lon_index),
                    "latitude": float(latitude[lat_index]),
                    "longitude": float(longitude[lon_index]),
                    "cell_area_m2": float(cell_area.area),
                    "intersection_area_m2": intersection,
                })
    cells = pd.DataFrame(rows).sort_values(["lat_index", "lon_index"]).reset_index(drop=True)
    coverage = float(cells.intersection_area_m2.sum() / polygon_area.area)
    if len(cells) != 6 or not np.isclose(coverage, 1.0, atol=1e-10):
        raise AssertionError("author polygon does not have complete six-cell support")
    cells["author_area_weight"] = cells.intersection_area_m2 / cells.intersection_area_m2.sum()
    with rasterio.open(MIRCA_RF_PATH) as rainfed, rasterio.open(MIRCA_IR_PATH) as irrigated:
        rf = rainfed.read(1)
        ir = irrigated.read(1)
    cells["mirca_rainfed_ha_cell"] = [rf[i, j] for i, j in zip(cells.lat_index, cells.lon_index, strict=True)]
    cells["mirca_irrigated_ha_cell"] = [ir[i, j] for i, j in zip(cells.lat_index, cells.lon_index, strict=True)]
    cells["cell_overlap_fraction"] = cells.intersection_area_m2 / cells.cell_area_m2
    cells["mirca_maize_ha_proxy"] = (
        cells.mirca_rainfed_ha_cell + cells.mirca_irrigated_ha_cell
    ) * cells.cell_overlap_fraction
    cells["author_mirca_maize_weight"] = cells.mirca_maize_ha_proxy / cells.mirca_maize_ha_proxy.sum()
    return cells


def main() -> None:
    source = read_hultgren()
    geometries, metadata = load_author_region()
    _, polygon_area, polygon_wgs84 = geometries
    with xr.open_dataset(PR_PATH, decode_timedelta=False) as dataset:
        latitude = dataset.lat.values.astype(float)
        longitude = dataset.lon.values.astype(float)
    cells = build_cells(polygon_area, polygon_wgs84, latitude, longitude)
    dates, rain, tmin, tmax = read_weather(cells)
    cell_year = construct_cell_year_features(dates, rain, tmin, tmax)
    variants = {
        "author_boundary_area_overlap": cells.author_area_weight.to_numpy(float),
        "author_boundary_mirca_maize_proxy": cells.author_mirca_maize_weight.to_numpy(float),
    }
    comparisons = {
        name: compare(source, aggregate_features(cell_year, weights))
        for name, weights in variants.items()
    }
    mirca_proxy = float(cells.mirca_maize_ha_proxy.sum())
    source_corn = metadata["source_corn_weight"]
    metadata.update({
        "positive_intersection_cells": len(cells),
        "coverage_fraction": float(cells.intersection_area_m2.sum() / polygon_area.area),
        "mirca_within_author_boundary_maize_area_proxy_ha": mirca_proxy,
        "mirca_minus_source_corn_weight_relative": mirca_proxy / source_corn - 1.0,
        "mirca_within_boundary_irrigated_share_proxy": float(
            (cells.mirca_irrigated_ha_cell * cells.cell_overlap_fraction).sum() / mirca_proxy
        ),
    })
    payload = {
        "schema": "hultgren_iroquois_author_boundary_diagnostic/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "role": "author_boundary_alternative_crop_weight_transport_diagnostic_not_sage_pixel_weight_replication",
        "sources": {
            "impact_region_points_fst": identity(IMPACT_REGIONS),
            "hierarchy": identity(HIERARCHY),
            "extracted_region_points": identity(REGION_POINTS),
            "administrative_crop_weights": identity(REGION_WEIGHTS),
            "mirca_rainfed": identity(MIRCA_RF_PATH),
            "mirca_irrigated": identity(MIRCA_IR_PATH),
        },
        "spatial_audit": metadata,
        "cells": cells.to_dict(orient="records"),
        "comparisons": comparisons,
        "validation_gates": {
            "hierarchy_crosswalk_unique": True,
            "author_polygon_valid": True,
            "author_polygon_grid_coverage_complete": metadata["coverage_fraction"] >= 0.999999,
            "six_positive_intersection_cells": len(cells) == 6,
            "mirca_area_proxy_within_two_percent_of_source_corn_weight": abs(metadata["mirca_minus_source_corn_weight_relative"]) < 0.02,
            "nonlinear_transform_precedes_spatial_aggregation": True,
        },
        "claim_gates": {
            "source_administrative_boundary_recovered": True,
            "source_hierarchy_crosswalk_recovered": True,
            "source_administrative_crop_total_recovered": True,
            "source_sage_anycrop_pixel_weights_recovered": False,
            "gmfd_features_reproduced": False,
            "future_response_validated": False,
            "damage_estimate_validated": False,
            "scc_estimate_validated": False,
        },
        "interpretation": (
            "The author boundary and hierarchy close the administrative geometry/crosswalk gap. "
            "MIRCA maize area within that boundary closely matches the authors' regional corn total, "
            "but MIRCA does not reproduce the within-region SAGE any-crop pixel weights used for weather."
        ),
    }
    if not all(payload["validation_gates"].values()):
        raise AssertionError(f"author-boundary diagnostic gate failed: {payload['validation_gates']}")
    OUTPUT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    summary = {}
    for variant, result in comparisons.items():
        summary[variant] = {
            feature: {
                "bias": values["gswp_minus_published_mean"],
                "rmse": values["rmse"],
                "correlation": values["pearson_correlation"],
            }
            for feature, values in result.items()
            if feature in ("gdd", "kdd", "season_total_precipitation")
        }
    print(json.dumps({"status": "ok", "spatial_audit": metadata, "summary": summary}, indent=2))


if __name__ == "__main__":
    main()
