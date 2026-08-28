#!/usr/bin/env python3
"""Audit Trigg County's nClimGrid mask with official TIGER area-water polygons.

The audit is diagnostic only. It retains the registered 0.95 land-coverage
threshold, writes no county-weight partition, and estimates fractional water
inside each area-water feature from its published AWATER/(ALAND+AWATER)
attributes rather than treating every hydrographic polygon as entirely water.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import shapefile
from pyproj import CRS, Transformer
from shapely.geometry import Polygon, shape
from shapely.ops import transform

from build_county_polygon_nclimgrid_weights import AREA_CRS, coordinate_edges, load_grid
from build_us_national_county_nclimgrid_weights import (
    load_reference_valid_mask,
    load_selected_geometries,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "us_trigg_tiger2019_fractional_water_mask_audit_v1"
GEOID = "21221"
REGISTERED_THRESHOLD = 0.95
EXPECTED_ZIP_BYTES = 625481
EXPECTED_ZIP_SHA512 = (
    "7246180a102bb6734bf2b80d17e5801572ef4a3b164fcbd28ea22dee05ad2bef2"
    "319270d3120b3b2c7b73335f1bda01a3c59dd5d8d4b418b3c96b5b955dc24da"
)
SOURCE_URL = (
    "https://www2.census.gov/geo/tiger/TIGER2019/AREAWATER/"
    "tl_2019_21221_areawater.zip"
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def digest_file(path: Path, algorithm: str) -> str:
    digest = hashlib.new(algorithm)
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path.resolve())


def atomic_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".partial")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def load_water_features(path: Path, area_crs: CRS) -> tuple[list[tuple[Any, float]], dict[str, Any]]:
    reader = shapefile.Reader(str(path))
    fields = [field[0] for field in reader.fields[1:]]
    required = {"ALAND", "AWATER", "MTFCC"}
    require(required <= set(fields), "TIGER area-water fields changed")
    positions = {name: fields.index(name) for name in required}
    source_crs = CRS.from_wkt(path.with_suffix(".prj").read_text(encoding="utf-8"))
    projector = Transformer.from_crs(source_crs, area_crs, always_xy=True)
    features: list[tuple[Any, float]] = []
    declared_land = 0
    declared_water = 0
    projected_area = 0.0
    mtfcc = Counter()
    for item in reader.iterShapeRecords():
        geometry = shape(item.shape.__geo_interface__)
        require(not geometry.is_empty and geometry.is_valid, "TIGER area-water geometry is invalid")
        aland = int(item.record[positions["ALAND"]])
        awater = int(item.record[positions["AWATER"]])
        require(aland >= 0 and awater >= 0 and aland + awater > 0, "TIGER area-water attributes are invalid")
        area_geometry = transform(projector.transform, geometry)
        require(area_geometry.area > 0, "projected area-water geometry is empty")
        water_fraction = awater / (aland + awater)
        features.append((area_geometry, water_fraction))
        declared_land += aland
        declared_water += awater
        projected_area += float(area_geometry.area)
        mtfcc[str(item.record[positions["MTFCC"]])] += 1
    require(features, "TIGER area-water file contains no features")
    return features, {
        "records": len(features),
        "attribute_land_area_m2": declared_land,
        "attribute_water_area_m2": declared_water,
        "projected_feature_area_m2": projected_area,
        "mtfcc_record_counts": dict(sorted(mtfcc.items())),
    }


def fractional_water_area(target: Any, features: Iterable[tuple[Any, float]]) -> float:
    total = 0.0
    for geometry, water_fraction in features:
        if target.intersects(geometry):
            total += float(target.intersection(geometry).area) * float(water_fraction)
    return total


def audit(
    county_path: Path,
    area_water_path: Path,
    area_water_zip: Path,
    reference_weather: Path,
    support: Any,
) -> dict[str, Any]:
    require(area_water_zip.stat().st_size == EXPECTED_ZIP_BYTES, "area-water ZIP size changed")
    require(digest_file(area_water_zip, "sha512") == EXPECTED_ZIP_SHA512, "area-water ZIP SHA-512 changed")
    selected, county_crs = load_selected_geometries(county_path, support)
    require(set(selected) == {GEOID}, "county support must contain only Trigg County")
    county_source, metadata = selected[GEOID]
    county_to_wgs84 = Transformer.from_crs(county_crs, CRS.from_epsg(4326), always_xy=True)
    county_to_area = Transformer.from_crs(county_crs, AREA_CRS, always_xy=True)
    weather_to_area = Transformer.from_crs(CRS.from_epsg(4326), AREA_CRS, always_xy=True)
    county_wgs84 = transform(county_to_wgs84.transform, county_source)
    county_area = transform(county_to_area.transform, county_source)
    water_features, water_summary = load_water_features(area_water_path, AREA_CRS)
    require(water_summary["records"] == 2123, "area-water record count changed")
    require(
        water_summary["attribute_water_area_m2"] == metadata["declared_water_area_m2"],
        "area-water attributes do not reconcile to county AWATER",
    )

    latitude, longitude = load_grid(reference_weather)
    valid_mask = load_reference_valid_mask(reference_weather)
    lat_edges = coordinate_edges(latitude, "latitude")
    lon_edges = coordinate_edges(longitude, "longitude")
    west, south, east, north = county_wgs84.bounds
    lat_indices = np.flatnonzero((lat_edges[:-1] < north) & (lat_edges[1:] > south))
    lon_indices = np.flatnonzero((lon_edges[:-1] < east) & (lon_edges[1:] > west))

    total_polygon = 0.0
    total_fractional_water = 0.0
    valid_polygon = 0.0
    valid_fractional_water = 0.0
    masked_polygon = 0.0
    masked_fractional_water = 0.0
    positive_cells = 0
    valid_cells = 0
    masked_cells = 0
    for lat_index in lat_indices:
        for lon_index in lon_indices:
            cell = Polygon(
                [
                    (lon_edges[lon_index], lat_edges[lat_index]),
                    (lon_edges[lon_index + 1], lat_edges[lat_index]),
                    (lon_edges[lon_index + 1], lat_edges[lat_index + 1]),
                    (lon_edges[lon_index], lat_edges[lat_index + 1]),
                ]
            )
            cell_area = transform(weather_to_area.transform, cell)
            county_cell = county_area.intersection(cell_area)
            polygon_area = float(county_cell.area)
            if polygon_area <= 0:
                continue
            water_area = fractional_water_area(county_cell, water_features)
            require(-1e-6 <= water_area <= polygon_area + 1e-6, "fractional water exceeds county-cell area")
            water_area = min(max(water_area, 0.0), polygon_area)
            positive_cells += 1
            total_polygon += polygon_area
            total_fractional_water += water_area
            if bool(valid_mask[lat_index, lon_index]):
                valid_cells += 1
                valid_polygon += polygon_area
                valid_fractional_water += water_area
            else:
                masked_cells += 1
                masked_polygon += polygon_area
                masked_fractional_water += water_area

    total_fractional_land = total_polygon - total_fractional_water
    valid_fractional_land = valid_polygon - valid_fractional_water
    masked_fractional_land = masked_polygon - masked_fractional_water
    require(
        abs(total_polygon - float(county_area.area)) / float(county_area.area) <= 1e-8,
        "weather grid does not exhaust the county polygon",
    )
    require(
        abs(total_fractional_water - metadata["declared_water_area_m2"])
        / metadata["declared_water_area_m2"]
        <= 1e-6,
        "fractional area-water intersections do not reconcile to county AWATER",
    )
    require(
        abs(total_fractional_land - metadata["declared_land_area_m2"])
        / metadata["declared_land_area_m2"]
        <= 1e-6,
        "fractional area-water intersections do not reconcile to county ALAND",
    )
    fractional_land_coverage = valid_fractional_land / total_fractional_land
    legacy_gross_valid_to_declared_land = valid_polygon / metadata["declared_land_area_m2"]
    return {
        "schema": SCHEMA,
        "status": "passed_source_audit_registered_weather_gate_still_failed" if fractional_land_coverage < REGISTERED_THRESHOLD else "passed_source_audit_registered_weather_gate_passed",
        "analysis_role": "historical_us_county_fractional_water_diagnostic_only",
        "county_geoid": GEOID,
        "county_name": metadata["county_name"],
        "registered_minimum_land_coverage": REGISTERED_THRESHOLD,
        "registered_threshold_relaxed": False,
        "source": {
            "url": SOURCE_URL,
            "vintage": 2019,
            "rights": "public_domain_us_census_bureau",
            "zip_path": display_path(area_water_zip),
            "zip_bytes": area_water_zip.stat().st_size,
            "zip_sha512": EXPECTED_ZIP_SHA512,
            "shapefile_path": display_path(area_water_path),
            "component_sha256": {
                area_water_path.with_suffix(suffix).name: digest_file(area_water_path.with_suffix(suffix), "sha256")
                for suffix in [".shp", ".shx", ".dbf", ".prj"]
            },
        },
        "county_declared": {
            "land_area_m2": metadata["declared_land_area_m2"],
            "water_area_m2": metadata["declared_water_area_m2"],
            "projected_polygon_area_m2": float(county_area.area),
        },
        "area_water_features": water_summary,
        "grid_intersections": {
            "positive_cells": positive_cells,
            "weather_valid_cells": valid_cells,
            "weather_masked_cells": masked_cells,
            "total_polygon_area_m2": total_polygon,
            "weather_valid_polygon_area_m2": valid_polygon,
            "weather_masked_polygon_area_m2": masked_polygon,
            "fractional_water_area_m2": total_fractional_water,
            "weather_valid_fractional_water_area_m2": valid_fractional_water,
            "weather_masked_fractional_water_area_m2": masked_fractional_water,
            "fractional_land_area_m2": total_fractional_land,
            "weather_valid_fractional_land_area_m2": valid_fractional_land,
            "weather_masked_fractional_land_area_m2": masked_fractional_land,
            "fractional_land_coverage": fractional_land_coverage,
            "legacy_gross_valid_area_relative_to_declared_land": legacy_gross_valid_to_declared_land,
            "passes_registered_land_coverage_gate": fractional_land_coverage >= REGISTERED_THRESHOLD,
        },
        "fractional_method": (
            "Within each official TIGER area-water polygon, allocate its published AWATER share "
            "uniformly over the polygon and retain its published ALAND share as land. Intersect "
            "those fractions with exact county-grid polygons in EPSG:5070."
        ),
        "county_weight_partition_written": False,
        "county_excluded": False,
        "relationship_estimated": False,
        "response_damage_or_scc_authorized": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--counties", type=Path, required=True)
    parser.add_argument("--area-water", type=Path, required=True)
    parser.add_argument("--area-water-zip", type=Path, required=True)
    parser.add_argument("--reference-weather", type=Path, required=True)
    parser.add_argument("--support", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    import pandas as pd

    support = pd.read_csv(args.support, dtype={"county_geoid": str})
    support["county_geoid"] = support.county_geoid.str.zfill(5)
    support = support.loc[support.county_geoid == GEOID, ["county_geoid", "state", "county_name"]].drop_duplicates()
    require(len(support) == 1, "support does not identify exactly one Trigg County row")
    result = audit(
        args.counties.resolve(),
        args.area_water.resolve(),
        args.area_water_zip.resolve(),
        args.reference_weather.resolve(),
        support,
    )
    atomic_json(args.out.resolve(), result)
    summary = result["grid_intersections"]
    print(
        "Trigg fractional-water audit: "
        f"land coverage={summary['fractional_land_coverage']:.9f}; "
        f"passes registered 0.95 gate={summary['passes_registered_land_coverage_gate']}"
    )


if __name__ == "__main__":
    main()
