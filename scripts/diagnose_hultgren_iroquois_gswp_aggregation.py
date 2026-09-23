#!/usr/bin/env python3
"""Compare prespecified Iroquois spatial proxies with published maize features.

This is deliberately a transport diagnostic.  It uses GSWP3-W5E5 rather than
the paper's GMFD weather and TIGER/MIRCA rather than its SAGE any-crop weights.
All nonlinear weather transformations are constructed at grid-cell level and
only then aggregated, matching the order stated in the paper's SI.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
import shapefile
import xarray as xr
from pyproj import CRS, Transformer
from shapely.geometry import Polygon, shape
from shapely.ops import transform

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.diagnose_hultgren_iroquois_gswp_basis import (  # noqa: E402
    FEATURES,
    PR_PATH,
    SOURCE,
    TMAX_PATH,
    TMIN_PATH,
    read_hultgren,
)
from src.hultgren_crop_calendar import source_month_from_day  # noqa: E402
from src.hultgren_maize_weather import build_maize_weather_basis_from_daily  # noqa: E402

COUNTY_PATH = ROOT / "data/raw/us_county/tigerline/tl_2019_us_county/tl_2019_us_county.shp"
MIRCA_ROOT = ROOT / "data/raw/mirca_os_v2/extracted_30arcmin/00/30-arcminute"
MIRCA_RF_PATH = MIRCA_ROOT / "MIRCA-OS_Maize_2000_rf_30arcmin_v2.tif"
MIRCA_IR_PATH = MIRCA_ROOT / "MIRCA-OS_Maize_2000_ir_30arcmin_v2.tif"
DEFAULT_OUTPUT = ROOT / "data/provenance/hultgren_iroquois_gswp_aggregation_diagnostic_20260923.json"
AREA_CRS = CRS.from_epsg(5070)


def file_identity(path: Path) -> dict[str, object]:
    digest = hashlib.sha512()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return {
        "path": str(path.relative_to(ROOT)),
        "bytes": path.stat().st_size,
        "sha512": digest.hexdigest(),
    }


def coordinate_edges(values: np.ndarray, label: str) -> np.ndarray:
    values = np.asarray(values, dtype=float)
    differences = np.diff(values)
    if values.ndim != 1 or len(values) < 2 or not np.isfinite(values).all():
        raise ValueError(f"{label} must be a finite one-dimensional coordinate")
    if not (differences > 0).all() or not np.allclose(
        differences, differences[0], rtol=0, atol=1e-8
    ):
        raise ValueError(f"{label} must be a regular increasing grid")
    result = np.empty(len(values) + 1, dtype=float)
    result[1:-1] = (values[:-1] + values[1:]) / 2
    result[0] = values[0] - differences[0] / 2
    result[-1] = values[-1] + differences[-1] / 2
    return result


def load_county() -> tuple[object, CRS, dict[str, object]]:
    reader = shapefile.Reader(str(COUNTY_PATH))
    fields = [field[0] for field in reader.fields[1:]]
    positions = {field: fields.index(field) for field in ("GEOID", "NAME", "ALAND", "AWATER")}
    matches = [
        item for item in reader.iterShapeRecords()
        if str(item.record[positions["GEOID"]]) == "17075"
    ]
    if len(matches) != 1:
        raise AssertionError(f"expected one Iroquois County geometry, found {len(matches)}")
    item = matches[0]
    geometry = shape(item.shape.__geo_interface__)
    source_crs = CRS.from_wkt(COUNTY_PATH.with_suffix(".prj").read_text(encoding="utf-8"))
    metadata = {
        "geoid": "17075",
        "name": str(item.record[positions["NAME"]]),
        "declared_land_area_m2": int(item.record[positions["ALAND"]]),
        "declared_water_area_m2": int(item.record[positions["AWATER"]]),
    }
    return geometry, source_crs, metadata


def build_cell_weights(latitude: np.ndarray, longitude: np.ndarray) -> tuple[pd.DataFrame, dict[str, object]]:
    county, county_crs, metadata = load_county()
    lat_ascending = latitude[::-1]
    lat_edges = coordinate_edges(lat_ascending, "latitude")
    lon_edges = coordinate_edges(longitude, "longitude")
    county_wgs84 = transform(
        Transformer.from_crs(county_crs, 4326, always_xy=True).transform, county
    )
    county_area_geometry = transform(
        Transformer.from_crs(county_crs, AREA_CRS, always_xy=True).transform, county
    )
    weather_to_area = Transformer.from_crs(4326, AREA_CRS, always_xy=True)
    west, south, east, north = county_wgs84.bounds
    ascending_lat_indices = np.flatnonzero(
        (lat_edges[:-1] < north) & (lat_edges[1:] > south)
    )
    lon_indices = np.flatnonzero((lon_edges[:-1] < east) & (lon_edges[1:] > west))

    rows = []
    for ascending_lat_index in ascending_lat_indices:
        lat_index = len(latitude) - 1 - int(ascending_lat_index)
        for lon_index in lon_indices:
            cell_wgs84 = Polygon([
                (lon_edges[lon_index], lat_edges[ascending_lat_index]),
                (lon_edges[lon_index + 1], lat_edges[ascending_lat_index]),
                (lon_edges[lon_index + 1], lat_edges[ascending_lat_index + 1]),
                (lon_edges[lon_index], lat_edges[ascending_lat_index + 1]),
            ])
            cell_area_geometry = transform(weather_to_area.transform, cell_wgs84)
            intersection_area = float(county_area_geometry.intersection(cell_area_geometry).area)
            if intersection_area <= 0:
                continue
            rows.append({
                "lat_index": lat_index,
                "lon_index": int(lon_index),
                "latitude": float(latitude[lat_index]),
                "longitude": float(longitude[lon_index]),
                "cell_area_m2": float(cell_area_geometry.area),
                "intersection_area_m2": intersection_area,
            })
    cells = pd.DataFrame(rows).sort_values(["lat_index", "lon_index"]).reset_index(drop=True)
    county_area = float(county_area_geometry.area)
    declared_area = metadata["declared_land_area_m2"] + metadata["declared_water_area_m2"]
    coverage = float(cells["intersection_area_m2"].sum() / county_area)
    if len(cells) != 6 or not np.isclose(coverage, 1.0, atol=1e-8):
        raise AssertionError(f"unexpected Iroquois/grid support: {len(cells)} cells, {coverage=}")
    if abs(county_area - declared_area) / declared_area > 0.03:
        raise AssertionError("projected county area does not reconcile to TIGER declared area")
    cells["county_area_weight"] = cells["intersection_area_m2"] / cells["intersection_area_m2"].sum()

    with rasterio.open(MIRCA_RF_PATH) as rainfed, rasterio.open(MIRCA_IR_PATH) as irrigated:
        expected_transform = rasterio.Affine(0.5, 0.0, -180.0, 0.0, -0.5, 90.0)
        if rainfed.shape != (360, 720) or irrigated.shape != rainfed.shape:
            raise AssertionError("MIRCA rasters do not match the expected 0.5-degree grid")
        if not rainfed.transform.almost_equals(expected_transform) or not irrigated.transform.almost_equals(expected_transform):
            raise AssertionError("MIRCA rasters do not align with the GSWP 0.5-degree grid")
        rainfed_values = rainfed.read(1)
        irrigated_values = irrigated.read(1)
    cells["mirca_rainfed_ha_cell"] = [rainfed_values[i, j] for i, j in zip(cells.lat_index, cells.lon_index, strict=True)]
    cells["mirca_irrigated_ha_cell"] = [irrigated_values[i, j] for i, j in zip(cells.lat_index, cells.lon_index, strict=True)]
    cells["cell_overlap_fraction"] = cells["intersection_area_m2"] / cells["cell_area_m2"]
    cells["mirca_maize_ha_proxy"] = (
        cells["mirca_rainfed_ha_cell"] + cells["mirca_irrigated_ha_cell"]
    ) * cells["cell_overlap_fraction"]
    if not np.isfinite(cells["mirca_maize_ha_proxy"]).all() or cells["mirca_maize_ha_proxy"].sum() <= 0:
        raise AssertionError("MIRCA maize proxy weights are not positive and finite")
    cells["mirca_maize_weight"] = cells["mirca_maize_ha_proxy"] / cells["mirca_maize_ha_proxy"].sum()
    dominant = int(cells["county_area_weight"].idxmax())
    cells["nearest_cell_weight"] = 0.0
    cells.loc[dominant, "nearest_cell_weight"] = 1.0
    audit = {
        **metadata,
        "county_polygon_area_m2_epsg5070": county_area,
        "coverage_fraction": coverage,
        "positive_intersection_cells": int(len(cells)),
        "mirca_within_county_maize_area_proxy_ha": float(cells["mirca_maize_ha_proxy"].sum()),
        "mirca_within_county_irrigated_share_proxy": float(
            (cells["mirca_irrigated_ha_cell"] * cells["cell_overlap_fraction"]).sum()
            / cells["mirca_maize_ha_proxy"].sum()
        ),
    }
    return cells, audit


def read_weather(cells: pd.DataFrame) -> tuple[pd.DatetimeIndex, np.ndarray, np.ndarray, np.ndarray]:
    for path, variable in ((PR_PATH, "pr"), (TMIN_PATH, "tasmin"), (TMAX_PATH, "tasmax")):
        if path.stat().st_size != SOURCE[variable]["bytes"]:
            raise AssertionError(f"resident {variable} file size differs from source contract")
    point_lat = xr.DataArray(cells.lat_index.to_numpy(dtype=int), dims="cell")
    point_lon = xr.DataArray(cells.lon_index.to_numpy(dtype=int), dims="cell")
    with xr.open_dataset(PR_PATH, decode_timedelta=False) as pr_ds, xr.open_dataset(
        TMIN_PATH, decode_timedelta=False
    ) as tn_ds, xr.open_dataset(TMAX_PATH, decode_timedelta=False) as tx_ds:
        if not np.array_equal(pr_ds.time.values, tn_ds.time.values) or not np.array_equal(pr_ds.time.values, tx_ds.time.values):
            raise AssertionError("GSWP dates differ across variables")
        dates = pd.DatetimeIndex(pr_ds.time.values)
        time_indices = np.flatnonzero((dates.month >= 5) & (dates.month <= 10))
        rain = pr_ds.pr.isel(time=time_indices, lat=point_lat, lon=point_lon).load().values.astype(np.float64) * 86_400.0
        tmin = tn_ds.tasmin.isel(time=time_indices, lat=point_lat, lon=point_lon).load().values.astype(np.float64) - 273.15
        tmax = tx_ds.tasmax.isel(time=time_indices, lat=point_lat, lon=point_lon).load().values.astype(np.float64) - 273.15
    selected_dates = dates[time_indices]
    if rain.shape != (1_840, len(cells)) or not all(np.isfinite(x).all() for x in (rain, tmin, tmax)):
        raise AssertionError("GSWP daily multi-cell support is incomplete or nonfinite")
    return selected_dates, rain, tmin, tmax


def construct_cell_year_features(
    dates: pd.DatetimeIndex, rain: np.ndarray, tmin: np.ndarray, tmax: np.ndarray
) -> pd.DataFrame:
    rows = []
    for cell in range(rain.shape[1]):
        records = [
            (stamp.date(), float(pr), float(tn), float(tx))
            for stamp, pr, tn, tx in zip(dates, rain[:, cell], tmin[:, cell], tmax[:, cell], strict=True)
        ]
        for year in range(1981, 1991):
            season = dates.year == year
            basis = build_maize_weather_basis_from_daily(
                records, report_year=year, plant_month=5, harvest_month=10, iso="USA"
            )
            rows.append({
                "cell": cell,
                "year": year,
                "mean_daily_tmax_c": float(tmax[season, cell].mean()),
                "gdd": basis.gdd,
                "kdd": basis.kdd,
                **{f"prcp_poly_1_bin{i + 1}": value for i, value in enumerate(basis.prcp_poly_1_bins)},
                **{f"prcp_poly_2_bin{i + 1}": value for i, value in enumerate(basis.prcp_poly_2_bins)},
            })
    return pd.DataFrame(rows)


def aggregate_features(cell_year: pd.DataFrame, weights: np.ndarray) -> pd.DataFrame:
    feature_columns = ["mean_daily_tmax_c", *FEATURES]
    merged = cell_year.copy()
    merged["weight"] = merged["cell"].map(dict(enumerate(weights)))
    aggregated = merged.groupby("year", sort=True).apply(
        lambda group: pd.Series({name: float(np.dot(group[name], group["weight"])) for name in feature_columns}),
        include_groups=False,
    )
    return aggregated.reset_index()


def compare(source: pd.DataFrame, candidate: pd.DataFrame) -> dict[str, dict[str, float | None]]:
    result = {}
    mappings = [(name, name) for name in FEATURES] + [("season_mean_tmax", "mean_daily_tmax_c")]
    for label, candidate_name in mappings:
        source_name = "GMFD_tmax_poly_1" if label == "season_mean_tmax" else label
        observed = source[source_name].to_numpy(dtype=float)
        values = candidate[candidate_name].to_numpy(dtype=float)
        difference = values - observed
        correlation = float(np.corrcoef(values, observed)[0, 1])
        result[label] = {
            "published_gmfd_mean": float(observed.mean()),
            "gswp_proxy_mean": float(values.mean()),
            "gswp_minus_published_mean": float(difference.mean()),
            "rmse": float(np.sqrt(np.mean(difference * difference))),
            "pearson_correlation": correlation if math.isfinite(correlation) else None,
        }
    observed_rain = source[[f"prcp_poly_1_bin{i}" for i in (1, 2, 3)]].sum(axis=1).to_numpy(dtype=float)
    values_rain = candidate[[f"prcp_poly_1_bin{i}" for i in (1, 2, 3)]].sum(axis=1).to_numpy(dtype=float)
    difference = values_rain - observed_rain
    result["season_total_precipitation"] = {
        "published_gmfd_mean": float(observed_rain.mean()),
        "gswp_proxy_mean": float(values_rain.mean()),
        "gswp_minus_published_mean": float(difference.mean()),
        "rmse": float(np.sqrt(np.mean(difference * difference))),
        "pearson_correlation": float(np.corrcoef(values_rain, observed_rain)[0, 1]),
    }
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    source = read_hultgren()
    if {source_month_from_day(value) for value in source.median_plant_date} != {5} or {
        source_month_from_day(value) for value in source.median_harvest_date
    } != {10}:
        raise AssertionError("Iroquois source calendar is not consistently May through October")

    with xr.open_dataset(PR_PATH, decode_timedelta=False) as dataset:
        latitude = dataset.lat.values.astype(float)
        longitude = dataset.lon.values.astype(float)
    if not (np.diff(latitude) < 0).all() or not (np.diff(longitude) > 0).all():
        raise AssertionError("unexpected GSWP coordinate orientation")
    cells, spatial_audit = build_cell_weights(latitude, longitude)
    dates, rain, tmin, tmax = read_weather(cells)
    cell_year = construct_cell_year_features(dates, rain, tmin, tmax)

    variants = {
        "nearest_cell": cells.nearest_cell_weight.to_numpy(dtype=float),
        "county_area_overlap": cells.county_area_weight.to_numpy(dtype=float),
        "mirca_maize_overlap_proxy": cells.mirca_maize_weight.to_numpy(dtype=float),
    }
    comparisons = {}
    for name, weights in variants.items():
        if not np.isclose(weights.sum(), 1.0, atol=1e-12):
            raise AssertionError(f"{name} weights do not sum to one")
        comparisons[name] = compare(source, aggregate_features(cell_year, weights))

    cell_records = cells.to_dict(orient="records")
    payload = {
        "schema": "hultgren_iroquois_gswp_aggregation_diagnostic/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "role": "prespecified_spatial_proxy_transport_diagnostic_not_gmfd_sage_replication",
        "sources": {
            "published_historical_dataset": str((ROOT / "data/raw/hultgren_response/historical_git/dae5fe8d0d4a260328e4baa45b547368bd6790b3/corn_gmfd_v1_ready.dta").relative_to(ROOT)),
            "gswp_pr": {"path": str(PR_PATH.relative_to(ROOT)), **SOURCE["pr"]},
            "gswp_tasmin": {"path": str(TMIN_PATH.relative_to(ROOT)), **SOURCE["tasmin"]},
            "gswp_tasmax": {"path": str(TMAX_PATH.relative_to(ROOT)), **SOURCE["tasmax"]},
            "county_boundary": {
                suffix: file_identity(COUNTY_PATH.with_suffix(suffix))
                for suffix in (".shp", ".shx", ".dbf", ".prj")
            },
            "mirca_rainfed_maize": file_identity(MIRCA_RF_PATH),
            "mirca_irrigated_maize": file_identity(MIRCA_IR_PATH),
        },
        "spatial_audit": spatial_audit,
        "cells": cell_records,
        "weight_variants": {
            "nearest_cell": "dominant county-overlap cell; reproduces the earlier one-cell diagnostic",
            "county_area_overlap": "EPSG:5070 TIGER polygon intersection area; not crop weighted",
            "mirca_maize_overlap_proxy": "fixed-2000 MIRCA maize hectares times within-cell county overlap; not the paper's SAGE any-crop weights",
        },
        "transformation_order": "daily/monthly nonlinear features at cell level, then fixed spatial weighting",
        "comparisons": comparisons,
        "validation_gates": {
            "published_overlap_1981_1990_complete": len(source) == 10,
            "county_grid_coverage_complete": spatial_audit["coverage_fraction"] >= 0.999999,
            "six_positive_intersection_cells": len(cells) == 6,
            "daily_support_complete": rain.shape == (1_840, 6),
            "all_features_finite": bool(np.isfinite(cell_year[["mean_daily_tmax_c", *FEATURES]].to_numpy()).all()),
            "all_variant_weights_normalized": all(np.isclose(value.sum(), 1.0, atol=1e-12) for value in variants.values()),
            "nonlinear_transform_precedes_spatial_aggregation": True,
        },
        "claim_gates": {
            "multi_cell_spatial_proxy_operational": True,
            "gmfd_features_reproduced": False,
            "sage_anycrop_weights_reproduced": False,
            "aggregation_choice_frozen": False,
            "future_climate_projection_validated": False,
            "damage_estimate_validated": False,
            "scc_estimate_validated": False,
        },
        "interpretation": (
            "The three alternatives were specified before reading their comparison results. "
            "They isolate sensitivity to local spatial support but cannot identify the paper's "
            "source aggregation because both GMFD and SAGE any-crop weights remain absent."
        ),
    }
    if not all(payload["validation_gates"].values()):
        raise AssertionError(f"aggregation diagnostic gate failed: {payload['validation_gates']}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    summary = {
        variant: {
            feature: {
                "bias": values["gswp_minus_published_mean"],
                "rmse": values["rmse"],
                "correlation": values["pearson_correlation"],
            }
            for feature, values in result.items()
            if feature in ("gdd", "kdd", "season_total_precipitation")
        }
        for variant, result in comparisons.items()
    }
    print(json.dumps({"status": "ok", "spatial_audit": spatial_audit, "summary": summary}, indent=2))


if __name__ == "__main__":
    main()
