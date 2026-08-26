#!/usr/bin/env python3
"""Audit county coverage under the locked all-practice nClimGrid gate.

This is a no-weight diagnostic.  It computes the same polygon/grid and
January-1981 weather-valid-mask area metrics as the national weight builder,
but it records sub-threshold counties instead of constructing or writing
renormalized weights.  It does not construct weather features or estimate a
response, causal effect, damage, or SCC.
"""
from __future__ import annotations

import argparse
import os
import tempfile
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import pandas as pd
from pyproj import CRS, Transformer
from shapely.geometry import Polygon
from shapely.ops import transform

from build_county_polygon_nclimgrid_weights import (
    AREA_CRS,
    coordinate_edges,
    load_grid,
)
from build_us_national_county_nclimgrid_weights import (
    DEFAULT_COUNTIES,
    DEFAULT_REFERENCE,
    _tiger_hashes,
    load_reference_valid_mask,
    load_selected_geometries,
)
from us_national_nclimgrid_common import (
    DEFAULT_BOUND_CALENDAR,
    DEFAULT_BOUND_CALENDAR_RECEIPT,
    DEFAULT_COMPETING_PROTOCOL,
    DEFAULT_HTTP_INVENTORY,
    DEFAULT_RAW_WEATHER_DIR,
    DEFAULT_REVIEWED_PRODUCT,
    PROJECT_ROOT,
    atomic_write_json,
    canonical_sha256,
    load_contract,
    prepare_support,
    read_table,
    sha256_file,
    sha256_records,
    validate_acquired_months,
    validate_bound_calendar_receipt,
)


SCHEMA = "us_national_all_practice_nclimgrid_coverage_gate_v1"
DETAIL_SCHEMA = "us_national_all_practice_nclimgrid_county_coverage_v1"
CONTRACT = PROJECT_ROOT / "us_county_validation/us_national_all_practice_nclimgrid_features_v1.toml"
PANEL = PROJECT_ROOT / "data/interim/us_county/nass_national_all_practice_panel_1981_2019.parquet"
GEOGRAPHY = (
    PROJECT_ROOT
    / "data/interim/us_county/nass_national_all_practice_panel_1981_2019_geography_gate.csv"
)
OUTPUT_DIR = PROJECT_ROOT / "outputs/us_county/national_all_practice_nclimgrid_coverage_v1"
DEFAULT_DETAIL = OUTPUT_DIR / "county_coverage.csv"
DEFAULT_AUDIT = OUTPUT_DIR / "coverage_audit.json"
DEFAULT_TRACKED_RECEIPT = (
    PROJECT_ROOT
    / "data/provenance/us_national_all_practice_nclimgrid_coverage_gate_20260826.json"
)
SENSITIVITY_VALID_LAND_THRESHOLDS = (0.99, 0.999)


def relative_path(path: Path) -> str:
    """Return a project-relative path, rejecting external or symlinked scope."""
    try:
        return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()
    except ValueError as error:
        raise ValueError(f"coverage-audit path lies outside the precipitation project: {path}") from error


def file_record(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"coverage-audit input is not a regular file: {path}")
    return {
        "path": relative_path(path),
        "sha256": sha256_file(path),
        "size_bytes": int(path.stat().st_size),
    }


def atomic_write_csv(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    os.close(descriptor)
    temporary = Path(name)
    try:
        frame.to_csv(temporary, index=False, lineterminator="\n", float_format="%.15g")
        with temporary.open("rb") as stream:
            os.fsync(stream.fileno())
        temporary.replace(path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def _strict_support_bool(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame:
        raise ValueError(f"outcome support lacks {column}")
    values = frame[column]
    if pd.api.types.is_bool_dtype(values):
        if values.isna().any():
            raise ValueError(f"outcome support {column} contains missing booleans")
        return values.astype(bool)
    text = values.astype("string").str.strip().str.lower()
    if text.isna().any() or (~text.isin(["true", "false"])).any():
        raise ValueError(f"outcome support {column} must contain only true/false")
    return text.eq("true")


def county_outcome_support(support: pd.DataFrame) -> pd.DataFrame:
    """Collapse the validated all-practice panel to exact county support counts."""
    required = {
        "county_geoid", "state", "county_name", "outcome_crop", "harvest_year",
        "irrigation_practice", "irrigation_share_eligible", "rainfed_dominant_10pct",
        "rainfed_dominant_20pct", "rainfed_dominant_30pct",
    }
    if missing := required - set(support):
        raise ValueError(f"validated outcome support lacks columns {sorted(missing)}")
    if support.empty or set(support.irrigation_practice.astype(str)) != {"all_practices"}:
        raise ValueError("coverage audit requires nonempty all-practice support")
    keys = ["county_geoid", "outcome_crop", "harvest_year"]
    if support.duplicated(keys).any():
        raise ValueError("all-practice outcome support duplicates crop-county-year keys")

    work = support.copy()
    for column in [
        "irrigation_share_eligible", "rainfed_dominant_10pct",
        "rainfed_dominant_20pct", "rainfed_dominant_30pct",
    ]:
        work[column] = _strict_support_bool(work, column)
    grouped = work.groupby("county_geoid", sort=True, observed=True)
    rows: list[dict[str, Any]] = []
    for geoid, county in grouped:
        names = county[["state", "county_name"]].drop_duplicates()
        if len(names) != 1:
            raise ValueError(f"county {geoid} has inconsistent outcome metadata")
        rows.append(
            {
                "county_geoid": str(geoid),
                "state": str(names.state.iloc[0]),
                "nass_county_name": str(names.county_name.iloc[0]),
                "outcome_practice_rows": int(len(county)),
                "outcome_crop_county_years": int(county[keys].drop_duplicates().shape[0]),
                "corn_crop_county_years": int(county.outcome_crop.eq("corn_grain").sum()),
                "soy_crop_county_years": int(county.outcome_crop.eq("soybeans").sum()),
                "first_outcome_year": int(county.harvest_year.min()),
                "last_outcome_year": int(county.harvest_year.max()),
                "irrigation_share_eligible_rows": int(county.irrigation_share_eligible.sum()),
                "rainfed_dominant_10pct_rows": int(county.rainfed_dominant_10pct.sum()),
                "rainfed_dominant_20pct_rows": int(county.rainfed_dominant_20pct.sum()),
                "rainfed_dominant_30pct_rows": int(county.rainfed_dominant_30pct.sum()),
            }
        )
    result = pd.DataFrame(rows).sort_values("county_geoid").reset_index(drop=True)
    if result.county_geoid.duplicated().any():
        raise AssertionError("county support collapse produced duplicate GEOIDs")
    return result


def compute_county_coverage(
    county_source: Any,
    metadata: Mapping[str, Any],
    county_crs: CRS,
    latitude: np.ndarray,
    longitude: np.ndarray,
    valid_grid_mask: np.ndarray,
    *,
    minimum_geometric_coverage: float,
    minimum_valid_land_coverage: float,
    maximum_declared_area_relative_error: float,
    cell_area_cache: dict[tuple[int, int], Any] | None = None,
) -> dict[str, Any]:
    """Compute builder-equivalent coverage metrics without emitting weights."""
    if valid_grid_mask.shape != (len(latitude), len(longitude)):
        raise ValueError("weather-valid mask shape differs from the nClimGrid coordinates")
    if valid_grid_mask.dtype != bool:
        raise ValueError("weather-valid mask must be boolean")
    if not 0 < minimum_geometric_coverage <= 1:
        raise ValueError("minimum geometric coverage must lie within (0,1]")
    if not 0 < minimum_valid_land_coverage <= 1:
        raise ValueError("minimum valid-land coverage must lie within (0,1]")
    if maximum_declared_area_relative_error < 0:
        raise ValueError("maximum declared-area relative error must be nonnegative")

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
        raise ValueError(f"county {metadata['county_geoid']} has nonpositive/nonfinite area")
    declared_land = int(metadata["declared_land_area_m2"])
    declared_water = int(metadata["declared_water_area_m2"])
    declared_total = declared_land + declared_water
    if declared_land <= 0 or declared_total <= 0:
        raise ValueError(f"county {metadata['county_geoid']} has nonpositive declared land/total area")
    declared_error = abs(county_area_m2 - declared_total) / declared_total

    west, south, east, north = county_wgs84.bounds
    lat_indices = np.flatnonzero((lat_edges[:-1] < north) & (lat_edges[1:] > south))
    lon_indices = np.flatnonzero((lon_edges[:-1] < east) & (lon_edges[1:] > west))
    geometric_intersection_m2 = 0.0
    weather_valid_intersection_m2 = 0.0
    weather_masked_intersection_m2 = 0.0
    positive_geometric_cells = 0
    positive_weather_cells = 0
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
            if intersection <= 0:
                continue
            positive_geometric_cells += 1
            geometric_intersection_m2 += intersection
            if bool(valid_grid_mask[lat_index, lon_index]):
                positive_weather_cells += 1
                weather_valid_intersection_m2 += intersection
            else:
                weather_masked_intersection_m2 += intersection

    geometric_coverage = geometric_intersection_m2 / county_area_m2
    weather_valid_coverage = weather_valid_intersection_m2 / county_area_m2
    valid_land_ratio = weather_valid_intersection_m2 / declared_land
    passes_declared = declared_error <= maximum_declared_area_relative_error
    passes_geometric = (
        geometric_coverage >= minimum_geometric_coverage
        and geometric_coverage <= 1 + 1e-8
    )
    passes_valid_land = valid_land_ratio >= minimum_valid_land_coverage
    passes_primary = passes_declared and passes_geometric and passes_valid_land
    if positive_geometric_cells == 0:
        passes_geometric = False
        passes_primary = False

    return {
        "county_geoid": str(metadata["county_geoid"]),
        "state": str(metadata["state"]),
        "tiger2019_county_name": str(metadata["county_name"]),
        "declared_land_area_m2": declared_land,
        "declared_water_area_m2": declared_water,
        "declared_tiger_total_area_m2": declared_total,
        "county_polygon_area_m2_epsg5070": county_area_m2,
        "declared_area_relative_error": declared_error,
        "geometric_intersection_area_m2": geometric_intersection_m2,
        "weather_valid_intersection_area_m2": weather_valid_intersection_m2,
        "weather_masked_intersection_area_m2": weather_masked_intersection_m2,
        "geometric_grid_coverage_fraction": geometric_coverage,
        "weather_valid_coverage_fraction": weather_valid_coverage,
        "weather_valid_area_relative_to_declared_land": valid_land_ratio,
        "positive_geometric_cells": positive_geometric_cells,
        "positive_weather_cells": positive_weather_cells,
        "passes_declared_area_gate": bool(passes_declared),
        "passes_geometric_grid_gate": bool(passes_geometric),
        "passes_weather_valid_land_gate": bool(passes_valid_land),
        "passes_registered_primary_coverage_gate": bool(passes_primary),
        "weight_rows_written": 0,
        "weather_features_constructed": False,
        "relationship_estimated": False,
        "response_estimation_authorized": False,
        "causal_claim_authorized": False,
        "damage_claim_authorized": False,
        "scc_authorized": False,
    }


def _support_totals(frame: pd.DataFrame) -> dict[str, int]:
    return {
        "counties": int(len(frame)),
        "outcome_practice_rows": int(frame.outcome_practice_rows.sum()),
        "outcome_crop_county_years": int(frame.outcome_crop_county_years.sum()),
        "corn_crop_county_years": int(frame.corn_crop_county_years.sum()),
        "soy_crop_county_years": int(frame.soy_crop_county_years.sum()),
        "irrigation_share_eligible_rows": int(frame.irrigation_share_eligible_rows.sum()),
        "rainfed_dominant_10pct_rows": int(frame.rainfed_dominant_10pct_rows.sum()),
        "rainfed_dominant_20pct_rows": int(frame.rainfed_dominant_20pct_rows.sum()),
        "rainfed_dominant_30pct_rows": int(frame.rainfed_dominant_30pct_rows.sum()),
    }


def threshold_summary(
    frame: pd.DataFrame, valid_land_threshold: float
) -> dict[str, Any]:
    pass_mask = (
        frame.passes_declared_area_gate
        & frame.passes_geometric_grid_gate
        & frame.weather_valid_area_relative_to_declared_land.ge(valid_land_threshold)
    )
    passed = frame.loc[pass_mask]
    failed = frame.loc[~pass_mask]
    return {
        "weather_valid_area_relative_to_declared_land_threshold": valid_land_threshold,
        "passed": _support_totals(passed),
        "excluded": _support_totals(failed),
        "passed_county_geoid_sha256": sha256_records(
            passed, ["county_geoid"]
        ) if len(passed) else None,
        "excluded_county_geoid_sha256": sha256_records(
            failed, ["county_geoid"]
        ) if len(failed) else None,
    }


def validate_detail(frame: pd.DataFrame, expected_counties: int) -> None:
    required = {
        "county_geoid", "state", "outcome_practice_rows", "corn_crop_county_years",
        "soy_crop_county_years", "declared_area_relative_error",
        "geometric_grid_coverage_fraction", "weather_valid_coverage_fraction",
        "weather_valid_area_relative_to_declared_land", "passes_declared_area_gate",
        "passes_geometric_grid_gate", "passes_weather_valid_land_gate",
        "passes_registered_primary_coverage_gate", "weight_rows_written",
        "weather_features_constructed", "relationship_estimated",
        "response_estimation_authorized", "causal_claim_authorized",
        "damage_claim_authorized", "scc_authorized",
    }
    if missing := required - set(frame):
        raise ValueError(f"coverage detail lacks columns {sorted(missing)}")
    if len(frame) != expected_counties or frame.county_geoid.nunique() != expected_counties:
        raise ValueError("coverage detail does not contain the exact registered county support")
    if frame.county_geoid.astype(str).str.fullmatch(r"\d{5}").ne(True).any():
        raise ValueError("coverage detail contains malformed GEOIDs")
    numeric = [
        "declared_area_relative_error", "geometric_grid_coverage_fraction",
        "weather_valid_coverage_fraction", "weather_valid_area_relative_to_declared_land",
    ]
    if not np.isfinite(frame[numeric].to_numpy(dtype=float)).all():
        raise ValueError("coverage detail contains nonfinite metrics")
    if (frame.weight_rows_written != 0).any():
        raise ValueError("coverage audit must not write county weight rows")
    prohibited_true = [
        "weather_features_constructed", "relationship_estimated",
        "response_estimation_authorized", "causal_claim_authorized",
        "damage_claim_authorized", "scc_authorized",
    ]
    if frame[prohibited_true].astype(bool).any(axis=None):
        raise ValueError("coverage detail overstates scientific authorization")


def _quantiles(values: pd.Series) -> dict[str, float]:
    return {
        label: float(values.quantile(probability))
        for label, probability in [
            ("minimum", 0.0), ("p01", 0.01), ("p05", 0.05),
            ("median", 0.5), ("p95", 0.95), ("maximum", 1.0),
        ]
    }


def run_audit(
    *,
    detail_path: Path = DEFAULT_DETAIL,
    audit_path: Path = DEFAULT_AUDIT,
    tracked_receipt_path: Path = DEFAULT_TRACKED_RECEIPT,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    for output in [detail_path, audit_path, tracked_receipt_path]:
        relative_path(output)
    contract = load_contract(CONTRACT)
    if contract["contract_id"] != "us_national_all_practice_nclimgrid_features_v1":
        raise ValueError("coverage audit is bound to the all-practice contract only")
    calendar_receipt = validate_bound_calendar_receipt(
        DEFAULT_BOUND_CALENDAR, DEFAULT_BOUND_CALENDAR_RECEIPT, DEFAULT_COMPETING_PROTOCOL
    )
    support, _, sample_audit = prepare_support(
        read_table(PANEL), read_table(GEOGRAPHY), read_table(DEFAULT_BOUND_CALENDAR), contract
    )
    support_by_county = county_outcome_support(support)
    expected_counties = int(contract["sample"]["expected_counties"])
    if len(support_by_county) != expected_counties:
        raise ValueError("validated support differs from the registered county count")

    _, weather_identity = validate_acquired_months(
        [(1981, 1)],
        inventory_path=DEFAULT_HTTP_INVENTORY,
        reviewed_product_path=DEFAULT_REVIEWED_PRODUCT,
        raw_weather_dir=DEFAULT_RAW_WEATHER_DIR,
    )
    if DEFAULT_REFERENCE.resolve() != (
        DEFAULT_RAW_WEATHER_DIR / "ncdd-198101-grd-scaled.nc"
    ).resolve():
        raise ValueError("coverage audit reference differs from the validated January 1981 object")
    latitude, longitude = load_grid(DEFAULT_REFERENCE)
    valid_grid_mask = load_reference_valid_mask(DEFAULT_REFERENCE)
    if int(valid_grid_mask.sum()) != int(contract["weather"]["reference_valid_grid_cells"]):
        raise ValueError("reference weather-valid grid-cell count differs from the contract")
    geometries, county_crs = load_selected_geometries(DEFAULT_COUNTIES, support)

    minimum_geometric = float(contract["weather"]["minimum_geometric_grid_coverage"])
    minimum_valid_land = float(
        contract["weather"]["minimum_weather_valid_area_relative_to_declared_land"]
    )
    maximum_declared_error = float(
        contract["weather"]["maximum_declared_area_relative_error"]
    )
    cell_cache: dict[tuple[int, int], Any] = {}
    coverage_rows: list[dict[str, Any]] = []
    for geoid in sorted(geometries):
        coverage_rows.append(
            compute_county_coverage(
                *geometries[geoid], county_crs, latitude, longitude, valid_grid_mask,
                minimum_geometric_coverage=minimum_geometric,
                minimum_valid_land_coverage=minimum_valid_land,
                maximum_declared_area_relative_error=maximum_declared_error,
                cell_area_cache=cell_cache,
            )
        )
    coverage = pd.DataFrame(coverage_rows)
    detail = coverage.merge(
        support_by_county, on=["county_geoid", "state"], how="outer", validate="one_to_one",
        indicator=True,
    )
    if not detail._merge.eq("both").all():
        raise ValueError("coverage geometry and outcome support do not join exactly")
    detail = detail.drop(columns="_merge").sort_values("county_geoid").reset_index(drop=True)
    validate_detail(detail, expected_counties)
    atomic_write_csv(detail_path, detail)

    thresholds = [minimum_valid_land, *SENSITIVITY_VALID_LAND_THRESHOLDS]
    threshold_summaries = {
        f"valid_land_{threshold:g}": threshold_summary(detail, threshold)
        for threshold in thresholds
    }
    primary_failures = detail.loc[
        ~detail.passes_registered_primary_coverage_gate,
        [
            "county_geoid", "state", "tiger2019_county_name", "nass_county_name",
            "declared_land_area_m2", "declared_water_area_m2",
            "declared_area_relative_error", "geometric_grid_coverage_fraction",
            "weather_valid_coverage_fraction",
            "weather_valid_area_relative_to_declared_land",
            "weather_masked_intersection_area_m2", "positive_weather_cells",
            "passes_declared_area_gate", "passes_geometric_grid_gate",
            "passes_weather_valid_land_gate", "outcome_practice_rows",
            "corn_crop_county_years", "soy_crop_county_years",
            "rainfed_dominant_10pct_rows", "rainfed_dominant_20pct_rows",
            "rainfed_dominant_30pct_rows",
        ],
    ].to_dict("records")
    inputs = {
        "contract": file_record(CONTRACT),
        "panel": file_record(PANEL),
        "geography_gate": file_record(GEOGRAPHY),
        "fixed_calendar": file_record(DEFAULT_BOUND_CALENDAR),
        "calendar_validation": file_record(DEFAULT_BOUND_CALENDAR_RECEIPT),
        "calendar_protocol": file_record(DEFAULT_COMPETING_PROTOCOL),
        "nclimgrid_http_inventory": file_record(DEFAULT_HTTP_INVENTORY),
        "nclimgrid_reviewed_product": file_record(DEFAULT_REVIEWED_PRODUCT),
        "reference_climate": file_record(DEFAULT_REFERENCE),
        "tiger_components": {
            name: {
                "path": relative_path(DEFAULT_COUNTIES.with_name(name)),
                "sha256": digest,
                "size_bytes": int(DEFAULT_COUNTIES.with_name(name).stat().st_size),
            }
            for name, digest in sorted(_tiger_hashes(DEFAULT_COUNTIES).items())
        },
        "audit_script": file_record(Path(__file__)),
    }
    receipt: dict[str, Any] = {
        "schema": SCHEMA,
        "detail_schema": DETAIL_SCHEMA,
        "analysis_role": "historical_us_county_weather_coverage_gate_only",
        "inputs": inputs,
        "input_identity_sha256": canonical_sha256(inputs),
        "reference_weather_identity": weather_identity[0],
        "calendar_receipt_status": calendar_receipt["status"],
        "registered_sample": sample_audit,
        "registered_gates": {
            "minimum_geometric_grid_coverage": minimum_geometric,
            "minimum_weather_valid_area_relative_to_declared_land": minimum_valid_land,
            "maximum_declared_area_relative_error": maximum_declared_error,
            "reference_validity_mask": contract["weather"]["reference_validity_mask"],
            "reference_valid_grid_cells": int(valid_grid_mask.sum()),
        },
        "county_coverage_distribution": {
            "geometric_grid_coverage_fraction": _quantiles(
                detail.geometric_grid_coverage_fraction
            ),
            "weather_valid_coverage_fraction": _quantiles(
                detail.weather_valid_coverage_fraction
            ),
            "weather_valid_area_relative_to_declared_land": _quantiles(
                detail.weather_valid_area_relative_to_declared_land
            ),
        },
        "threshold_summaries": threshold_summaries,
        "primary_failures": primary_failures,
        "primary_failure_count": int(len(primary_failures)),
        "primary_rule": (
            "exclude counties failing any pre-registered declared-area, geometric-grid, "
            "or 0.95 weather-valid-area-relative-to-declared-land gate"
        ),
        "sensitivity_rule": (
            "repeat validation on stricter 0.99 and 0.999 weather-valid-land subsets; "
            "never relax the registered 0.95 threshold post hoc"
        ),
        "detail_output": {
            **file_record(detail_path),
            "rows": int(len(detail)),
            "county_geoid_sha256": sha256_records(detail, ["county_geoid"]),
        },
        "weight_rows_written": 0,
        "raw_yield_values_embedded": False,
        "weather_features_constructed": False,
        "relationship_estimated": False,
        "response_estimation_authorized": False,
        "causal_claim_authorized": False,
        "damage_claim_authorized": False,
        "scc_authorized": False,
    }
    atomic_write_json(audit_path, receipt)
    atomic_write_json(tracked_receipt_path, receipt)
    return detail, receipt


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--detail-out", default=str(DEFAULT_DETAIL))
    parser.add_argument("--audit-out", default=str(DEFAULT_AUDIT))
    parser.add_argument("--tracked-receipt", default=str(DEFAULT_TRACKED_RECEIPT))
    args = parser.parse_args()
    detail, receipt = run_audit(
        detail_path=Path(args.detail_out),
        audit_path=Path(args.audit_out),
        tracked_receipt_path=Path(args.tracked_receipt),
    )
    print(
        f"audited {len(detail)} counties; {receipt['primary_failure_count']} fail the locked "
        "coverage gate; wrote zero weights and authorized no response, damage, or SCC"
    )


if __name__ == "__main__":
    main()
