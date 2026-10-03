#!/usr/bin/env python3
"""Build TIGER county-to-LOCA2 area weights from coordinate metadata only."""

from __future__ import annotations

import argparse
import hashlib
import json
import tomllib
from pathlib import Path

import numpy as np
import pandas as pd
import s3fs
import shapefile
import xarray as xr
from pyproj import CRS, Transformer
from shapely.geometry import Polygon, shape
from shapely.ops import transform


AREA_CRS = CRS.from_epsg(5070)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def coordinate_edges(values: np.ndarray, label: str) -> np.ndarray:
    values = np.asarray(values, dtype=float)
    require(values.ndim == 1 and len(values) >= 2 and np.isfinite(values).all(), f"{label} is not a finite vector")
    differences = np.diff(values)
    require((differences > 0).all(), f"{label} is not strictly increasing")
    require(np.allclose(differences, differences[0], rtol=0, atol=1e-10), f"{label} is not regular")
    edges = np.empty(len(values) + 1)
    edges[1:-1] = (values[:-1] + values[1:]) / 2
    edges[0] = values[0] - differences[0] / 2
    edges[-1] = values[-1] + differences[-1] / 2
    return edges


def longitude_west_east(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=float)
    converted = np.where(values > 180.0, values - 360.0, values)
    require((np.diff(converted) > 0).all(), "converted longitude is not strictly increasing")
    return converted


def load_county(shapefile_path: Path, geoid: str) -> tuple[object, CRS, dict[str, object]]:
    require(len(geoid) == 5 and geoid.isdigit(), "county GEOID must contain five digits")
    reader = shapefile.Reader(str(shapefile_path))
    fields = [field[0] for field in reader.fields[1:]]
    required = {"GEOID", "NAME", "STATEFP", "COUNTYFP", "ALAND", "AWATER"}
    require(required <= set(fields), "TIGER fields are incomplete")
    positions = {name: fields.index(name) for name in required}
    matches = [item for item in reader.iterShapeRecords() if str(item.record[positions["GEOID"]]) == geoid]
    require(len(matches) == 1, f"expected one TIGER county for {geoid}")
    item = matches[0]
    require(str(item.record[positions["STATEFP"]]).zfill(2) + str(item.record[positions["COUNTYFP"]]).zfill(3) == geoid, "TIGER component FIPS differ")
    geometry = shape(item.shape.__geo_interface__)
    require(not geometry.is_empty and geometry.is_valid, "TIGER geometry is empty or invalid")
    projection = shapefile_path.with_suffix(".prj")
    require(projection.is_file(), "TIGER projection file is missing")
    metadata = {
        "county_geoid": geoid,
        "county_name": str(item.record[positions["NAME"]]),
        "declared_land_area_m2": int(item.record[positions["ALAND"]]),
        "declared_water_area_m2": int(item.record[positions["AWATER"]]),
    }
    return geometry, CRS.from_wkt(projection.read_text()), metadata


def grid_coordinates(config: dict) -> tuple[np.ndarray, np.ndarray, dict[str, object]]:
    fs = s3fs.S3FileSystem(anon=True, client_kwargs={"endpoint_url": config["source"]["endpoint_url"]})
    ds = xr.open_zarr(fs.get_mapper(config["source"]["store"]), consolidated=True, chunks=None)
    require(ds.pr.attrs.get("LOCA2_version") == config["source"]["precipitation_version"], "LOCA2 precipitation version differs")
    latitude = ds.lat.values.astype(float)
    longitude_native = ds.lon.values.astype(float)
    longitude = longitude_west_east(longitude_native)
    metadata = {
        "store": config["source"]["store"],
        "endpoint_url": config["source"]["endpoint_url"],
        "precipitation_version": ds.pr.attrs["LOCA2_version"],
        "latitude_count": int(len(latitude)),
        "longitude_count": int(len(longitude)),
        "latitude_min": float(latitude.min()),
        "latitude_max": float(latitude.max()),
        "longitude_min": float(longitude.min()),
        "longitude_max": float(longitude.max()),
    }
    return latitude, longitude, metadata


def build_weights(latitude: np.ndarray, longitude: np.ndarray, county_geometry, county_crs: CRS, metadata: dict[str, object], min_coverage: float, declared_tolerance: float) -> tuple[pd.DataFrame, dict[str, object]]:
    lat_edges = coordinate_edges(latitude, "latitude")
    lon_edges = coordinate_edges(longitude, "longitude")
    to_wgs84 = Transformer.from_crs(county_crs, CRS.from_epsg(4326), always_xy=True)
    county_to_area = Transformer.from_crs(county_crs, AREA_CRS, always_xy=True)
    weather_to_area = Transformer.from_crs(CRS.from_epsg(4326), AREA_CRS, always_xy=True)
    county_wgs84 = transform(to_wgs84.transform, county_geometry)
    county_area_geometry = transform(county_to_area.transform, county_geometry)
    county_area = float(county_area_geometry.area)
    declared_area = int(metadata["declared_land_area_m2"]) + int(metadata["declared_water_area_m2"])
    declared_error = abs(county_area - declared_area) / declared_area
    require(declared_error <= declared_tolerance, "projected TIGER area differs from declared area")

    west, south, east, north = county_wgs84.bounds
    lat_indices = np.flatnonzero((lat_edges[:-1] < north) & (lat_edges[1:] > south))
    lon_indices = np.flatnonzero((lon_edges[:-1] < east) & (lon_edges[1:] > west))
    rows = []
    for lat_index in lat_indices:
        for lon_index in lon_indices:
            cell = Polygon([
                (lon_edges[lon_index], lat_edges[lat_index]),
                (lon_edges[lon_index + 1], lat_edges[lat_index]),
                (lon_edges[lon_index + 1], lat_edges[lat_index + 1]),
                (lon_edges[lon_index], lat_edges[lat_index + 1]),
            ])
            intersection = float(county_area_geometry.intersection(transform(weather_to_area.transform, cell)).area)
            if intersection > 0:
                rows.append({
                    "county_geoid": metadata["county_geoid"],
                    "county_name": metadata["county_name"],
                    "grid_lat_index": int(lat_index),
                    "grid_lon_index": int(lon_index),
                    "grid_lat": float(latitude[lat_index]),
                    "grid_lon_degrees_east": float(longitude[lon_index] % 360.0),
                    "grid_lon_degrees_west_east": float(longitude[lon_index]),
                    "intersection_area_m2": intersection,
                })
    require(rows, "county has no LOCA2 grid intersections")
    weights = pd.DataFrame(rows)
    intersected = float(weights.intersection_area_m2.sum())
    coverage = intersected / county_area
    require(min_coverage <= coverage <= 1.0 + 1e-8, "county/LOCA2 grid coverage fails")
    weights["county_polygon_area_m2"] = county_area
    weights["intersected_area_m2"] = intersected
    weights["spatial_weight"] = weights.intersection_area_m2 / intersected
    weights["coverage_fraction"] = coverage
    weights["weather_grid_id"] = "CMIP6_LOCA2_1_16_degree"
    weights["boundary_source_id"] = "tigerline_2019_county"
    weights["analysis_role"] = "climate_validation_county_average_proxy"
    require(np.isclose(weights.spatial_weight.sum(), 1.0, rtol=0, atol=1e-12), "weights do not sum to one")
    require(not weights.duplicated(["county_geoid", "grid_lat_index", "grid_lon_index"]).any(), "duplicate grid weights")
    audit = {
        **metadata,
        "county_polygon_area_m2_epsg5070": county_area,
        "declared_tiger_total_area_m2": declared_area,
        "declared_area_relative_error": declared_error,
        "intersected_area_m2": intersected,
        "coverage_fraction": coverage,
        "positive_grid_cells": int(len(weights)),
        "spatial_weight_sum": float(weights.spatial_weight.sum()),
    }
    return weights.sort_values(["grid_lat_index", "grid_lon_index"]).reset_index(drop=True), audit


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    config = tomllib.loads(args.config.read_text())
    root = Path(__file__).resolve().parents[2]
    shapefile_path = root / config["county"]["shapefile"]
    weights_path = root / config["outputs"]["weights"]
    receipt_path = root / config["outputs"]["receipt"]
    require(not weights_path.exists() and not receipt_path.exists(), "fresh outputs required")
    latitude, longitude, grid_metadata = grid_coordinates(config)
    geometry, county_crs, county_metadata = load_county(shapefile_path, config["county"]["geoid"])
    require(county_metadata["county_name"] == config["county"]["name"], "county name differs")
    weights, audit = build_weights(
        latitude,
        longitude,
        geometry,
        county_crs,
        county_metadata,
        float(config["county"]["minimum_grid_coverage"]),
        float(config["county"]["maximum_declared_area_relative_error"]),
    )
    weights_path.parent.mkdir(parents=True, exist_ok=True)
    weights.to_parquet(weights_path, index=False)
    components = {}
    for suffix in (".shp", ".shx", ".dbf", ".prj", ".cpg"):
        path = shapefile_path.with_suffix(suffix)
        if path.is_file():
            components[suffix] = {"path": str(path.relative_to(root)), "bytes": path.stat().st_size, "sha256": sha256(path)}
    receipt = {
        "schema": "loca2_us_county_weights/v1",
        "status": "pass",
        "role": "geometry_only_no_climate_values_or_outcomes",
        "config": {"path": str(args.config), "sha256": sha256(args.config)},
        "grid": grid_metadata,
        "boundary_components": components,
        "audit": audit,
        "output": {"path": str(weights_path.relative_to(root)), "bytes": weights_path.stat().st_size, "sha256": sha256(weights_path)},
        "claim_gates": {
            "county_geometry_weights": True,
            "weather_validity": False,
            "historical_climate_validation": False,
            "outcome_response": False,
            "causal_damage": False,
            "SCC": False,
        },
    }
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": "pass", **audit, "output_bytes": weights_path.stat().st_size}, indent=2))


if __name__ == "__main__":
    main()
