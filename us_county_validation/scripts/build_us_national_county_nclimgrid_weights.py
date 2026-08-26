#!/usr/bin/env python3
"""Build resumable county-polygon/nClimGrid weights for U.S. corn/soy support.

One atomic partition and hash-bound receipt is written per eligible county.
The fixed 2019 polygon is a county-average proxy, never crop-pixel exposure.
No daily weather feature or response relationship is constructed here.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import shapefile
import xarray as xr
from pyproj import CRS, Transformer
from shapely.geometry import Polygon, shape
from shapely.ops import transform

from build_county_nclimgrid_feature_smoke import validate_polygon_weights
from build_county_polygon_nclimgrid_weights import (
    AREA_CRS,
    STATE_FIPS_TO_ALPHA,
    WEATHER_GRID_ID,
    WEATHER_SOURCE_ID,
    coordinate_edges,
    load_grid,
)
from us_national_nclimgrid_common import (
    DEFAULT_CONTRACT,
    DEFAULT_BOUND_CALENDAR,
    DEFAULT_BOUND_CALENDAR_RECEIPT,
    DEFAULT_COMPETING_PROTOCOL,
    DEFAULT_HTTP_INVENTORY,
    DEFAULT_RAW_WEATHER_DIR,
    DEFAULT_REVIEWED_PRODUCT,
    PROJECT_ROOT,
    atomic_write_json,
    atomic_write_parquet,
    canonical_sha256,
    load_contract,
    prepare_support,
    read_table,
    sha256_file,
    sha256_records,
    validate_acquired_months,
    validate_bound_calendar_receipt,
)


SCHEMA = "us_national_county_nclimgrid_weight_partition_v1"
DEFAULT_PANEL = PROJECT_ROOT / "data/interim/us_county/nass_direct_practice_panel_1981_2019.parquet"
DEFAULT_GEOGRAPHY = PROJECT_ROOT / "data/interim/us_county/nass_direct_practice_panel_1981_2019_geography_gate.csv"
DEFAULT_CALENDAR = DEFAULT_BOUND_CALENDAR
DEFAULT_COUNTIES = PROJECT_ROOT / "data/raw/us_county/tigerline/tl_2019_us_county/tl_2019_us_county.shp"
DEFAULT_REFERENCE = DEFAULT_RAW_WEATHER_DIR / "ncdd-198101-grd-scaled.nc"
DEFAULT_OUT_DIR = PROJECT_ROOT / "data/interim/us_county/nclimgrid_polygon_weights_national_v1"
DEFAULT_MANIFEST = DEFAULT_OUT_DIR / "manifest.json"


def _tiger_hashes(shapefile_path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for suffix in [".shp", ".shx", ".dbf", ".prj"]:
        path = shapefile_path.with_suffix(suffix)
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"TIGER input lacks required regular file {path}")
        result[path.name] = sha256_file(path)
    return result


def load_selected_geometries(
    shapefile_path: Path, support: pd.DataFrame
) -> tuple[dict[str, tuple[Any, dict[str, Any]]], CRS]:
    requested = set(support.county_geoid.astype(str))
    names = (
        support[["county_geoid", "state", "county_name"]]
        .drop_duplicates()
        .set_index("county_geoid")
    )
    if names.index.duplicated().any():
        raise ValueError("one eligible GEOID has inconsistent NASS county metadata")
    reader = shapefile.Reader(str(shapefile_path))
    fields = [field[0] for field in reader.fields[1:]]
    required = {"STATEFP", "COUNTYFP", "GEOID", "NAME", "ALAND", "AWATER"}
    if missing := required - set(fields):
        raise ValueError(f"TIGER county shapefile lacks fields {sorted(missing)}")
    positions = {name: fields.index(name) for name in required}
    selected: dict[str, tuple[Any, dict[str, Any]]] = {}
    for item in reader.iterShapeRecords():
        geoid = str(item.record[positions["GEOID"]]).zfill(5)
        if geoid not in requested:
            continue
        if geoid in selected:
            raise ValueError(f"TIGER county shapefile duplicates eligible GEOID {geoid}")
        state_fips = str(item.record[positions["STATEFP"]]).zfill(2)
        county_fips = str(item.record[positions["COUNTYFP"]]).zfill(3)
        if state_fips + county_fips != geoid or state_fips not in STATE_FIPS_TO_ALPHA:
            raise ValueError(f"TIGER FIPS fields do not reconcile for {geoid}")
        state = STATE_FIPS_TO_ALPHA[state_fips]
        if str(names.loc[geoid, "state"]) != state:
            raise ValueError(f"TIGER and NASS state differ for {geoid}")
        geometry = shape(item.shape.__geo_interface__)
        if geometry.is_empty or not geometry.is_valid:
            raise ValueError(f"TIGER geometry is empty/invalid for {geoid}")
        selected[geoid] = (
            geometry,
            {
                "county_geoid": geoid,
                "state_fips": state_fips,
                "state": state,
                "county_name": str(item.record[positions["NAME"]]),
                "nass_county_name": str(names.loc[geoid, "county_name"]),
                "declared_land_area_m2": int(item.record[positions["ALAND"]]),
                "declared_water_area_m2": int(item.record[positions["AWATER"]]),
            },
        )
    missing = sorted(requested - set(selected))
    if missing:
        raise ValueError(f"TIGER shapefile lacks eligible GEOIDs {missing[:10]}")
    projection_path = shapefile_path.with_suffix(".prj")
    source_crs = CRS.from_wkt(projection_path.read_text(encoding="utf-8"))
    return selected, source_crs


def build_county_partition(
    county_source: Any,
    metadata: dict[str, Any],
    county_crs: CRS,
    latitude: np.ndarray,
    longitude: np.ndarray,
    *,
    min_coverage: float,
    valid_grid_mask: np.ndarray,
    min_valid_land_coverage: float,
    declared_area_relative_tolerance: float,
    cell_area_cache: dict[tuple[int, int], Any] | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    if not 0 < min_coverage <= 1:
        raise ValueError("min_coverage must lie within (0,1]")
    if declared_area_relative_tolerance < 0:
        raise ValueError("declared-area tolerance must be nonnegative")
    if valid_grid_mask.shape != (len(latitude), len(longitude)) or valid_grid_mask.dtype != bool:
        raise ValueError("reference weather-valid mask does not match the nClimGrid shape")
    if not 0 < min_valid_land_coverage <= 1:
        raise ValueError("minimum valid-land coverage must lie within (0,1]")
    cache = cell_area_cache if cell_area_cache is not None else {}
    lat_edges = coordinate_edges(latitude, "latitude")
    lon_edges = coordinate_edges(longitude, "longitude")
    county_to_wgs84 = Transformer.from_crs(county_crs, CRS.from_epsg(4326), always_xy=True)
    county_to_area = Transformer.from_crs(county_crs, AREA_CRS, always_xy=True)
    weather_to_area = Transformer.from_crs(CRS.from_epsg(4326), AREA_CRS, always_xy=True)
    county_wgs84 = transform(county_to_wgs84.transform, county_source)
    county_area_geometry = transform(county_to_area.transform, county_source)
    county_area_m2 = float(county_area_geometry.area)
    if not np.isfinite(county_area_m2) or county_area_m2 <= 0:
        raise ValueError("projected county polygon area is not positive/finite")
    declared_total = int(metadata["declared_land_area_m2"]) + int(metadata["declared_water_area_m2"])
    if declared_total <= 0:
        raise ValueError("TIGER declared county area is not positive")
    declared_error = abs(county_area_m2 - declared_total) / declared_total
    if declared_error > declared_area_relative_tolerance:
        raise ValueError("projected county area does not reconcile to TIGER ALAND+AWATER")

    west, south, east, north = county_wgs84.bounds
    lat_indices = np.flatnonzero((lat_edges[:-1] < north) & (lat_edges[1:] > south))
    lon_indices = np.flatnonzero((lon_edges[:-1] < east) & (lon_edges[1:] > west))
    rows: list[dict[str, Any]] = []
    geometric_intersection_m2 = 0.0
    masked_intersection_m2 = 0.0
    for lat_index in lat_indices:
        for lon_index in lon_indices:
            key = (int(lat_index), int(lon_index))
            cell_area = cache.get(key)
            if cell_area is None:
                cell_wgs84 = Polygon(
                    [
                        (lon_edges[lon_index], lat_edges[lat_index]),
                        (lon_edges[lon_index + 1], lat_edges[lat_index]),
                        (lon_edges[lon_index + 1], lat_edges[lat_index + 1]),
                        (lon_edges[lon_index], lat_edges[lat_index + 1]),
                    ]
                )
                cell_area = transform(weather_to_area.transform, cell_wgs84)
                cache[key] = cell_area
            intersection = float(county_area_geometry.intersection(cell_area).area)
            if intersection > 0:
                geometric_intersection_m2 += intersection
                if not bool(valid_grid_mask[lat_index, lon_index]):
                    masked_intersection_m2 += intersection
                    continue
                rows.append(
                    {
                        "county_geoid": metadata["county_geoid"],
                        "state": metadata["state"],
                        "county_name": metadata["county_name"],
                        "weather_source_id": WEATHER_SOURCE_ID,
                        "weather_grid_id": WEATHER_GRID_ID,
                        "grid_lat_index": int(lat_index),
                        "grid_lon_index": int(lon_index),
                        "grid_lat": float(latitude[lat_index]),
                        "grid_lon": float(longitude[lon_index]),
                        "intersection_area_m2": intersection,
                    }
                )
    if not rows:
        raise ValueError(f"no nClimGrid intersections for {metadata['county_geoid']}")
    weights = pd.DataFrame(rows)
    intersected = float(weights.intersection_area_m2.sum())
    coverage = geometric_intersection_m2 / county_area_m2
    if coverage < min_coverage or coverage > 1 + 1e-8:
        raise ValueError(f"county/grid geometric coverage {coverage:.9f} fails for {metadata['county_geoid']}")
    valid_coverage = intersected / county_area_m2
    valid_land_ratio = intersected / int(metadata["declared_land_area_m2"])
    if valid_land_ratio < min_valid_land_coverage:
        raise ValueError(
            f"county/weather-valid area relative to declared land {valid_land_ratio:.9f} "
            f"fails for {metadata['county_geoid']}"
        )
    weights["county_polygon_area_m2"] = county_area_m2
    weights["intersected_area_m2"] = intersected
    weights["spatial_weight"] = weights.intersection_area_m2 / intersected
    weights["coverage_fraction"] = coverage
    weights["weather_valid_coverage_fraction"] = valid_coverage
    weights["weather_valid_area_relative_to_declared_land"] = valid_land_ratio
    weights["weather_masked_intersection_area_m2"] = masked_intersection_m2
    weights["boundary_source_id"] = "tigerline_2019_county"
    weights["boundary_vintage"] = "2019-01-01"
    weights["area_crs"] = "EPSG:5070"
    weights["weight_role"] = "county_polygon_primary_proxy"
    weights["analysis_role"] = "historical_county_validation_only"
    weights["feature_construction_eligible"] = True
    weights["scc_authorized"] = False
    weights = validate_polygon_weights(weights)
    audit = {
        **metadata,
        "county_polygon_area_m2_epsg5070": county_area_m2,
        "declared_tiger_total_area_m2": declared_total,
        "declared_area_relative_error": declared_error,
        "intersected_area_m2": intersected,
        "coverage_fraction": coverage,
        "weather_valid_coverage_fraction": valid_coverage,
        "weather_valid_area_relative_to_declared_land": valid_land_ratio,
        "weather_masked_intersection_area_m2": masked_intersection_m2,
        "positive_weather_cells": int(len(weights)),
        "spatial_weight_sum": float(weights.spatial_weight.sum()),
    }
    return weights, audit


def load_reference_valid_mask(path: Path) -> np.ndarray:
    """Return cells finite for all four fields on every reference-month day."""
    with xr.open_dataset(path, engine="h5netcdf") as dataset:
        if set(dataset.data_vars) != {"prcp", "tavg", "tmin", "tmax"}:
            raise ValueError("reference nClimGrid variables changed")
        if dataset.attrs.get("title") != "nClimGrid-Daily, Gridded Fields":
            raise ValueError("reference nClimGrid title changed")
        if dataset.attrs.get("product_version") != "v1-0-0 20220829":
            raise ValueError("reference nClimGrid version changed")
        valid = np.ones((len(dataset.lat), len(dataset.lon)), dtype=bool)
        for field in ["prcp", "tavg", "tmin", "tmax"]:
            variable = dataset[field]
            if variable.dims != ("time", "lat", "lon"):
                raise ValueError(f"reference nClimGrid {field} dimensions changed")
            valid &= np.isfinite(variable.values).all(axis=0)
    if not valid.any() or valid.all():
        raise ValueError("reference nClimGrid validity mask is degenerate")
    return valid


def _partition_paths(out_dir: Path, geoid: str) -> tuple[Path, Path]:
    directory = out_dir / f"county_geoid={geoid}"
    return directory / "weights.parquet", directory / "receipt.json"


def validate_existing_partition(
    output: Path,
    receipt_path: Path,
    expected_fingerprint: str,
    geoid: str,
    expected_identity: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    if not output.is_file() or not receipt_path.is_file():
        return None
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        identity = receipt.get("input_identity")
        if not isinstance(identity, dict):
            return None
        if canonical_sha256(identity) != receipt.get("input_fingerprint_sha256"):
            return None
        if receipt.get("schema") != SCHEMA or receipt.get("input_fingerprint_sha256") != expected_fingerprint:
            return None
        if expected_identity is not None and identity != expected_identity:
            return None
        if receipt.get("county_geoid") != geoid or receipt.get("output_sha256") != sha256_file(output):
            return None
        weights = validate_polygon_weights(pd.read_parquet(output))
        if set(weights.county_geoid.astype(str)) != {geoid} or len(weights) != int(receipt["weight_rows"]):
            return None
        if not np.isclose(float(weights.coverage_fraction.iloc[0]), float(receipt["coverage_fraction"]), rtol=0, atol=1e-12):
            return None
        for column in [
            "weather_valid_coverage_fraction",
            "weather_valid_area_relative_to_declared_land",
            "weather_masked_intersection_area_m2",
        ]:
            if column not in weights or column not in receipt:
                return None
            if not np.isclose(
                float(weights[column].iloc[0]), float(receipt[column]), rtol=0, atol=1e-12
            ):
                return None
        minimum_valid_land = float(
            identity["minimum_weather_valid_area_relative_to_declared_land"]
        )
        if float(weights.weather_valid_area_relative_to_declared_land.min()) < minimum_valid_land:
            return None
        if not weights.weather_valid_coverage_fraction.between(0, 1 + 1e-8).all():
            return None
        if (weights.weather_masked_intersection_area_m2 < 0).any():
            return None
        expected_flags = {
            "crop_pixel_exposure": False,
            "relationship_estimated": False,
            "response_estimation_authorized": False,
            "scc_authorized": False,
        }
        if any(receipt.get(key) is not expected for key, expected in expected_flags.items()):
            return None
        return receipt
    except (OSError, ValueError, KeyError, json.JSONDecodeError):
        return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--panel", default=str(DEFAULT_PANEL))
    parser.add_argument("--geography", default=str(DEFAULT_GEOGRAPHY))
    parser.add_argument("--calendar", default=str(DEFAULT_CALENDAR))
    parser.add_argument("--calendar-validation", default=str(DEFAULT_BOUND_CALENDAR_RECEIPT))
    parser.add_argument("--calendar-protocol", default=str(DEFAULT_COMPETING_PROTOCOL))
    parser.add_argument("--contract", default=str(DEFAULT_CONTRACT))
    parser.add_argument("--counties", default=str(DEFAULT_COUNTIES))
    parser.add_argument("--reference-climate", default=str(DEFAULT_REFERENCE))
    parser.add_argument("--inventory", default=str(DEFAULT_HTTP_INVENTORY))
    parser.add_argument("--reviewed-product", default=str(DEFAULT_REVIEWED_PRODUCT))
    parser.add_argument("--raw-weather-dir", default=str(DEFAULT_RAW_WEATHER_DIR))
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--manifest-out", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--county-geoid", action="append")
    parser.add_argument("--max-counties", type=int)
    parser.add_argument("--min-coverage", type=float, default=0.999)
    parser.add_argument("--min-valid-land-coverage", type=float, default=0.95)
    parser.add_argument("--declared-area-relative-tolerance", type=float, default=0.03)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    if args.max_counties is not None and args.max_counties < 1:
        raise ValueError("max-counties must be positive")

    paths = {
        "panel": Path(args.panel), "geography": Path(args.geography),
        "calendar": Path(args.calendar), "contract": Path(args.contract),
        "counties": Path(args.counties), "reference_climate": Path(args.reference_climate),
    }
    contract = load_contract(paths["contract"])
    if args.min_coverage != float(contract["weather"]["minimum_geometric_grid_coverage"]):
        raise ValueError("CLI geometric coverage gate differs from the registered contract")
    if args.min_valid_land_coverage != float(
        contract["weather"]["minimum_weather_valid_area_relative_to_declared_land"]
    ):
        raise ValueError("CLI weather-valid land gate differs from the registered contract")
    if args.declared_area_relative_tolerance != float(
        contract["weather"]["maximum_declared_area_relative_error"]
    ):
        raise ValueError("CLI declared-area tolerance differs from the registered contract")
    calendar_receipt = validate_bound_calendar_receipt(
        paths["calendar"], Path(args.calendar_validation), Path(args.calendar_protocol)
    )
    support, _, sample_audit = prepare_support(
        read_table(paths["panel"]), read_table(paths["geography"]),
        read_table(paths["calendar"]), contract,
    )
    geoids = sorted(support.county_geoid.unique().tolist())
    if args.county_geoid:
        requested = list(dict.fromkeys(args.county_geoid))
        unknown = sorted(set(requested) - set(geoids))
        if unknown:
            raise ValueError(f"requested GEOIDs are outside eligible support: {unknown}")
        geoids = sorted(requested)
    if args.max_counties is not None:
        geoids = geoids[: args.max_counties]

    reference_name = paths["reference_climate"].name
    if reference_name != "ncdd-198101-grd-scaled.nc":
        raise ValueError("national weight grid reference must be the reviewed January 1981 object")
    _, weather_identity = validate_acquired_months(
        [(1981, 1)], inventory_path=Path(args.inventory),
        reviewed_product_path=Path(args.reviewed_product),
        raw_weather_dir=Path(args.raw_weather_dir),
    )
    if paths["reference_climate"].resolve() != (
        Path(args.raw_weather_dir) / reference_name
    ).resolve():
        raise ValueError("reference climate path differs from the validated acquisition object")
    latitude, longitude = load_grid(paths["reference_climate"])
    valid_grid_mask = load_reference_valid_mask(paths["reference_climate"])
    geometries, county_crs = load_selected_geometries(paths["counties"], support)
    common_identity = {
        "schema": SCHEMA,
        "contract_sha256": sha256_file(paths["contract"]),
        "panel_sha256": sha256_file(paths["panel"]),
        "geography_sha256": sha256_file(paths["geography"]),
        "calendar_sha256": sha256_file(paths["calendar"]),
        "calendar_validation_sha256": sha256_file(Path(args.calendar_validation)),
        "calendar_protocol_sha256": sha256_file(Path(args.calendar_protocol)),
        "calendar_receipt_status": calendar_receipt["status"],
        "tiger_component_sha256": _tiger_hashes(paths["counties"]),
        "reference_weather_identity": weather_identity[0],
        "builder_sha256": sha256_file(Path(__file__)),
        "min_coverage": args.min_coverage,
        "declared_area_relative_tolerance": args.declared_area_relative_tolerance,
        "reference_validity_mask_rule": "all_four_fields_finite_on_every_day_of_1981_01",
        "reference_valid_grid_cells": int(valid_grid_mask.sum()),
        "minimum_weather_valid_area_relative_to_declared_land": args.min_valid_land_coverage,
    }
    out_dir = Path(args.out_dir)
    cell_cache: dict[tuple[int, int], Any] = {}
    completed: list[dict[str, Any]] = []
    rebuilt = resumed = 0
    for geoid in geoids:
        county_support = support.loc[support.county_geoid.eq(geoid)]
        county_identity = {
            **common_identity,
            "county_geoid": geoid,
            "county_outcome_key_sha256": sha256_records(county_support, [*county_support.columns]),
        }
        fingerprint = canonical_sha256(county_identity)
        output, receipt_path = _partition_paths(out_dir, geoid)
        receipt = None if args.force else validate_existing_partition(
            output, receipt_path, fingerprint, geoid, county_identity
        )
        if receipt is None:
            weights, audit = build_county_partition(
                *geometries[geoid], county_crs, latitude, longitude,
                min_coverage=args.min_coverage,
                valid_grid_mask=valid_grid_mask,
                min_valid_land_coverage=args.min_valid_land_coverage,
                declared_area_relative_tolerance=args.declared_area_relative_tolerance,
                cell_area_cache=cell_cache,
            )
            atomic_write_parquet(output, weights)
            receipt = {
                "schema": SCHEMA,
                "county_geoid": geoid,
                "input_fingerprint_sha256": fingerprint,
                "input_identity": county_identity,
                "output_path": str(output),
                "output_sha256": sha256_file(output),
                "weight_rows": int(len(weights)),
                "coverage_fraction": float(audit["coverage_fraction"]),
                "weather_valid_coverage_fraction": float(audit["weather_valid_coverage_fraction"]),
                "weather_valid_area_relative_to_declared_land": float(
                    audit["weather_valid_area_relative_to_declared_land"]
                ),
                "weather_masked_intersection_area_m2": float(
                    audit["weather_masked_intersection_area_m2"]
                ),
                "spatial_weight_sum": float(audit["spatial_weight_sum"]),
                "positive_weather_cells": int(audit["positive_weather_cells"]),
                "support_crop_county_years": int(county_support.drop_duplicates(
                    ["county_geoid", "outcome_crop", "harvest_year"]
                ).shape[0]),
                "analysis_role": "historical_county_validation_weight_input_only",
                "crop_pixel_exposure": False,
                "relationship_estimated": False,
                "response_estimation_authorized": False,
                "scc_authorized": False,
            }
            atomic_write_json(receipt_path, receipt)
            rebuilt += 1
        else:
            resumed += 1
        completed.append(receipt)

    manifest = {
        "schema": "us_national_county_nclimgrid_weight_manifest_v1",
        "registered_sample": sample_audit,
        "requested_counties": geoids,
        "requested_county_count": len(geoids),
        "complete_registered_scope": len(geoids) == int(contract["sample"]["expected_counties"]),
        "resumed_partitions": resumed,
        "rebuilt_partitions": rebuilt,
        "total_weight_rows": int(sum(int(value["weight_rows"]) for value in completed)),
        "minimum_coverage_fraction": float(min(float(value["coverage_fraction"]) for value in completed)),
        "maximum_coverage_fraction": float(max(float(value["coverage_fraction"]) for value in completed)),
        "minimum_weather_valid_coverage_fraction": float(min(
            float(value["weather_valid_coverage_fraction"]) for value in completed
        )),
        "minimum_weather_valid_area_relative_to_declared_land": float(min(
            float(value["weather_valid_area_relative_to_declared_land"]) for value in completed
        )),
        "partition_receipts": [
            {
                "county_geoid": value["county_geoid"],
                "output_sha256": value["output_sha256"],
                "input_fingerprint_sha256": value["input_fingerprint_sha256"],
            }
            for value in completed
        ],
        "relationship_estimated": False,
        "response_estimation_authorized": False,
        "scc_authorized": False,
    }
    atomic_write_json(Path(args.manifest_out), manifest)
    print(
        f"validated {len(completed)} county weight partitions "
        f"({rebuilt} rebuilt, {resumed} resumed); no response estimated"
    )


if __name__ == "__main__":
    main()
