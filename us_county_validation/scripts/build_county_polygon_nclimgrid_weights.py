#!/usr/bin/env python3
"""Build exact county-polygon-to-nClimGrid area weights.

These weights implement the approved full-period U.S. primary proxy: all land
and water inside the legal county polygon, not crop pixels. They are useful for
1981--2019 coverage but must stay labeled as a county-average proxy. The 2017
CDL crop-pixel route is a separate sensitivity.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import shapefile
import xarray as xr
from pyproj import CRS, Transformer
from shapely.geometry import Polygon, shape
from shapely.ops import transform


WEATHER_SOURCE_ID = "nclimgrid_daily_v1_0_0_20220829"
WEATHER_GRID_ID = "nclimgrid_daily_conus_1_24_degree"
EXPECTED_FIELDS = {"prcp", "tavg", "tmax", "tmin"}
EXPECTED_TITLE = "nClimGrid-Daily, Gridded Fields"
EXPECTED_VERSION = "v1-0-0 20220829"
AREA_CRS = CRS.from_epsg(5070)
STATE_FIPS_TO_ALPHA = {
    "01": "AL", "02": "AK", "04": "AZ", "05": "AR", "06": "CA",
    "08": "CO", "09": "CT", "10": "DE", "11": "DC", "12": "FL",
    "13": "GA", "15": "HI", "16": "ID", "17": "IL", "18": "IN",
    "19": "IA", "20": "KS", "21": "KY", "22": "LA", "23": "ME",
    "24": "MD", "25": "MA", "26": "MI", "27": "MN", "28": "MS",
    "29": "MO", "30": "MT", "31": "NE", "32": "NV", "33": "NH",
    "34": "NJ", "35": "NM", "36": "NY", "37": "NC", "38": "ND",
    "39": "OH", "40": "OK", "41": "OR", "42": "PA", "44": "RI",
    "45": "SC", "46": "SD", "47": "TN", "48": "TX", "49": "UT",
    "50": "VT", "51": "VA", "53": "WA", "54": "WV", "55": "WI",
    "56": "WY", "60": "AS", "66": "GU", "69": "MP", "72": "PR",
    "78": "VI",
}


def coordinate_edges(values: np.ndarray, label: str) -> np.ndarray:
    values = np.asarray(values, dtype=float)
    if values.ndim != 1 or len(values) < 2 or not np.isfinite(values).all():
        raise ValueError(f"{label} must be a finite one-dimensional coordinate")
    differences = np.diff(values)
    if not (differences > 0).all():
        raise ValueError(f"{label} must be strictly increasing")
    if not np.allclose(differences, differences[0], rtol=0, atol=1e-5):
        raise ValueError(f"{label} is not a regular grid")
    edges = np.empty(len(values) + 1, dtype=float)
    edges[1:-1] = (values[:-1] + values[1:]) / 2
    edges[0] = values[0] - differences[0] / 2
    edges[-1] = values[-1] + differences[-1] / 2
    return edges


def load_grid(path: Path) -> tuple[np.ndarray, np.ndarray]:
    with xr.open_dataset(path, engine="h5netcdf") as dataset:
        if set(dataset.data_vars) != EXPECTED_FIELDS:
            raise ValueError("nClimGrid file does not contain the exact four-variable schema")
        if dataset.attrs.get("title") != EXPECTED_TITLE:
            raise ValueError("nClimGrid title differs from the reviewed product")
        if dataset.attrs.get("product_version") != EXPECTED_VERSION:
            raise ValueError("nClimGrid version differs from the reviewed product")
        if not ({"lat", "lon"} <= set(dataset.coords)):
            raise ValueError("nClimGrid latitude/longitude coordinates are absent")
        return dataset.lat.values.astype(float), dataset.lon.values.astype(float)


def load_county(
    shapefile_path: Path, county_geoid: str
) -> tuple[object, CRS, dict[str, object]]:
    if not isinstance(county_geoid, str) or not county_geoid.isdigit() or len(county_geoid) != 5:
        raise ValueError("county_geoid must be a five-digit GEOID")
    reader = shapefile.Reader(str(shapefile_path))
    fields = [field[0] for field in reader.fields[1:]]
    required = {"STATEFP", "COUNTYFP", "GEOID", "NAME", "ALAND", "AWATER"}
    if missing := required - set(fields):
        raise ValueError(f"County shapefile lacks fields {sorted(missing)}")
    positions = {name: fields.index(name) for name in required}
    matches = []
    for item in reader.iterShapeRecords():
        if str(item.record[positions["GEOID"]]) == county_geoid:
            matches.append(item)
    if len(matches) != 1:
        raise ValueError(f"Expected exactly one county geometry for {county_geoid}, got {len(matches)}")
    item = matches[0]
    state_fips = str(item.record[positions["STATEFP"]]).zfill(2)
    county_fips = str(item.record[positions["COUNTYFP"]]).zfill(3)
    if state_fips + county_fips != county_geoid:
        raise ValueError("County STATEFP/COUNTYFP do not reconcile to GEOID")
    if state_fips not in STATE_FIPS_TO_ALPHA:
        raise ValueError(f"No postal-code mapping for state FIPS {state_fips}")
    geometry = shape(item.shape.__geo_interface__)
    if geometry.is_empty or not geometry.is_valid:
        raise ValueError("County geometry is empty or invalid")
    projection_path = shapefile_path.with_suffix(".prj")
    if not projection_path.is_file():
        raise ValueError("County shapefile lacks its .prj CRS record")
    source_crs = CRS.from_wkt(projection_path.read_text(encoding="utf-8"))
    metadata = {
        "county_geoid": county_geoid,
        "state_fips": state_fips,
        "state": STATE_FIPS_TO_ALPHA[state_fips],
        "county_name": str(item.record[positions["NAME"]]),
        "declared_land_area_m2": int(item.record[positions["ALAND"]]),
        "declared_water_area_m2": int(item.record[positions["AWATER"]]),
    }
    return geometry, source_crs, metadata


def build_weights(
    shapefile_path: Path,
    county_geoid: str,
    climate_path: Path,
    min_coverage: float = 0.999,
    declared_area_relative_tolerance: float = 0.03,
) -> tuple[pd.DataFrame, dict[str, object]]:
    if not 0 < min_coverage <= 1:
        raise ValueError("min_coverage must lie within (0, 1]")
    if declared_area_relative_tolerance < 0:
        raise ValueError("declared-area tolerance must be nonnegative")
    latitude, longitude = load_grid(climate_path)
    lat_edges = coordinate_edges(latitude, "latitude")
    lon_edges = coordinate_edges(longitude, "longitude")
    county_source, county_crs, metadata = load_county(shapefile_path, county_geoid)

    county_to_wgs84 = Transformer.from_crs(county_crs, CRS.from_epsg(4326), always_xy=True)
    county_to_area = Transformer.from_crs(county_crs, AREA_CRS, always_xy=True)
    weather_to_area = Transformer.from_crs(CRS.from_epsg(4326), AREA_CRS, always_xy=True)
    county_wgs84 = transform(county_to_wgs84.transform, county_source)
    county_area_geometry = transform(county_to_area.transform, county_source)
    county_area_m2 = float(county_area_geometry.area)
    if not np.isfinite(county_area_m2) or county_area_m2 <= 0:
        raise ValueError("Projected county polygon area is not positive and finite")
    declared_total = metadata["declared_land_area_m2"] + metadata["declared_water_area_m2"]
    declared_relative_error = abs(county_area_m2 - declared_total) / declared_total
    if declared_relative_error > declared_area_relative_tolerance:
        raise ValueError("Projected county area does not reconcile to TIGER ALAND+AWATER")

    west, south, east, north = county_wgs84.bounds
    lat_indices = np.flatnonzero((lat_edges[:-1] < north) & (lat_edges[1:] > south))
    lon_indices = np.flatnonzero((lon_edges[:-1] < east) & (lon_edges[1:] > west))
    if len(lat_indices) == 0 or len(lon_indices) == 0:
        raise ValueError("County polygon does not overlap the nClimGrid domain")

    rows: list[dict[str, object]] = []
    for lat_index in lat_indices:
        for lon_index in lon_indices:
            cell_wgs84 = Polygon(
                [
                    (lon_edges[lon_index], lat_edges[lat_index]),
                    (lon_edges[lon_index + 1], lat_edges[lat_index]),
                    (lon_edges[lon_index + 1], lat_edges[lat_index + 1]),
                    (lon_edges[lon_index], lat_edges[lat_index + 1]),
                ]
            )
            cell_area = transform(weather_to_area.transform, cell_wgs84)
            intersection_area = float(county_area_geometry.intersection(cell_area).area)
            if intersection_area <= 0:
                continue
            rows.append(
                {
                    "county_geoid": county_geoid,
                    "state": metadata["state"],
                    "county_name": metadata["county_name"],
                    "weather_source_id": WEATHER_SOURCE_ID,
                    "weather_grid_id": WEATHER_GRID_ID,
                    "grid_lat_index": int(lat_index),
                    "grid_lon_index": int(lon_index),
                    "grid_lat": float(latitude[lat_index]),
                    "grid_lon": float(longitude[lon_index]),
                    "intersection_area_m2": intersection_area,
                }
            )
    if not rows:
        raise ValueError("No positive county/weather-cell intersections were constructed")
    weights = pd.DataFrame(rows)
    intersected_area_m2 = float(weights.intersection_area_m2.sum())
    coverage = intersected_area_m2 / county_area_m2
    if coverage < min_coverage or coverage > 1 + 1e-8:
        raise ValueError(f"County/weather-grid coverage {coverage:.9f} fails the declared gate")
    weights["county_polygon_area_m2"] = county_area_m2
    weights["intersected_area_m2"] = intersected_area_m2
    weights["spatial_weight"] = weights.intersection_area_m2 / intersected_area_m2
    weights["coverage_fraction"] = coverage
    weights["boundary_source_id"] = "tigerline_2019_county"
    weights["boundary_vintage"] = "2019-01-01"
    weights["area_crs"] = "EPSG:5070"
    weights["weight_role"] = "county_polygon_primary_proxy"
    weights["analysis_role"] = "historical_county_validation_only"
    weights["feature_construction_eligible"] = True
    weights["scc_authorized"] = False
    if not np.isclose(weights.spatial_weight.sum(), 1, rtol=0, atol=1e-12):
        raise ValueError("County-polygon weights do not sum to one")
    keys = ["county_geoid", "grid_lat_index", "grid_lon_index"]
    if weights.duplicated(keys).any():
        raise ValueError("Duplicate county/weather-cell weight keys")
    audit = {
        **metadata,
        "county_polygon_area_m2_epsg5070": county_area_m2,
        "declared_tiger_total_area_m2": declared_total,
        "declared_area_relative_error": declared_relative_error,
        "intersected_area_m2": intersected_area_m2,
        "coverage_fraction": coverage,
        "positive_weather_cells": int(len(weights)),
        "spatial_weight_sum": float(weights.spatial_weight.sum()),
        "weather_source_id": WEATHER_SOURCE_ID,
        "weather_grid_id": WEATHER_GRID_ID,
        "weight_role": "county_polygon_primary_proxy",
        "crop_pixel_exposure": False,
        "response_estimation_authorized": False,
        "scc_authorized": False,
    }
    return weights.sort_values(keys).reset_index(drop=True), audit


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--counties", required=True, help="Census county shapefile (.shp)")
    parser.add_argument("--county-geoid", required=True)
    parser.add_argument("--climate", required=True, help="one validated nClimGrid monthly NetCDF")
    parser.add_argument("--out", required=True, help="sparse Parquet weight table")
    parser.add_argument("--audit-out", required=True)
    parser.add_argument("--min-coverage", type=float, default=0.999)
    args = parser.parse_args()
    weights, audit = build_weights(
        Path(args.counties), args.county_geoid, Path(args.climate), args.min_coverage
    )
    destination = Path(args.out)
    destination.parent.mkdir(parents=True, exist_ok=True)
    weights.to_parquet(destination, index=False)
    audit_path = Path(args.audit_out)
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        f"wrote {len(weights)} county-polygon weights for {args.county_geoid}; "
        f"coverage={audit['coverage_fraction']:.9f}; no response estimated"
    )


if __name__ == "__main__":
    main()
