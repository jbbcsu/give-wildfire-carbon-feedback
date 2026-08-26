#!/usr/bin/env python3
"""Validate keys and weights for county-crop daily-weather construction.

This is deliberately the pre-feature schema gate for the fixed-CDL
crop-pixel sensitivity. The separate county-polygon primary proxy has its own
strict weight and feature validators. This module validates an explicit
county/FIPS inventory, selected NASS outcome support, crop-pixel-to-grid
weights, crop-calendar rows, and wheat-class mixtures. It does not read daily
weather, calculate precipitation metrics, fit a yield response, or authorize
an SCC input.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


PRIMARY_WEATHER_SOURCE = "nclimgrid_daily_v1_0_0_20220829"
PRIMARY_WEATHER_GRID = "nclimgrid_daily_conus_1_24_degree"
PRIMARY_GRID_SHAPE = {"lat": 596, "lon": 1385}

OUTCOME_CROPS = {"corn_grain", "soybeans", "wheat_all_classes"}
CALENDAR_CROPS = {"corn_grain", "soybeans", "winter_wheat", "spring_wheat", "durum_wheat"}
ALLOWED_CROP_LINKS = {
    ("corn_grain", "corn_grain"),
    ("soybeans", "soybeans"),
    ("wheat_all_classes", "winter_wheat"),
    ("wheat_all_classes", "spring_wheat"),
    ("wheat_all_classes", "durum_wheat"),
}
WEIGHT_ROLES = {"fixed_crop_mask_sensitivity"}
CALENDAR_ROLES = {
    "fixed_primary",
    "fixed_broad_window_sensitivity",
    "realized_timing_sensitivity",
}
PRACTICES = {"irrigated", "non_irrigated", "all_production_practices"}
SAMPLE_ROLES = {"direct_practice_pair", "aggregate_high_rainfed"}

WEIGHT_COLUMNS = {
    "county_geoid",
    "state",
    "outcome_crop",
    "calendar_crop",
    "weather_source_id",
    "weather_grid_id",
    "grid_lat_index",
    "grid_lon_index",
    "crop_area_m2",
    "county_calendar_crop_area_m2",
    "county_outcome_crop_area_m2",
    "spatial_weight",
    "calendar_class_share",
    "calendar_class_share_source_id",
    "mask_source_id",
    "mask_vintage",
    "boundary_source_id",
    "boundary_vintage",
    "coverage_fraction",
    "weight_role",
    "feature_construction_eligible",
    "scc_authorized",
}
CALENDAR_COLUMNS = {
    "state",
    "calendar_crop",
    "harvest_year",
    "season_start",
    "season_end",
    "calendar_source_id",
    "calendar_source_url",
    "calendar_vintage",
    "calendar_role",
    "boundary_rule",
    "stage_definition",
    "feature_construction_eligible",
    "scc_authorized",
}
OUTCOME_COLUMNS = {
    "county_geoid",
    "state",
    "outcome_crop",
    "harvest_year",
    "outcome_source_id",
    "irrigation_practice",
    "sample_role",
    "feature_construction_eligible",
    "scc_authorized",
}
COUNTY_COLUMNS = {
    "county_geoid",
    "state",
    "boundary_source_id",
    "boundary_vintage",
    "historical_status",
    "crosswalk_source_id",
    "feature_construction_eligible",
    "scc_authorized",
}


def read_table(path: str) -> pd.DataFrame:
    source = Path(path)
    if source.suffix.lower() in {".parquet", ".pq"}:
        return pd.read_parquet(source)
    return pd.read_csv(source, dtype="string")


def require_columns(frame: pd.DataFrame, required: set[str], label: str) -> None:
    if missing := required - set(frame.columns):
        raise ValueError(f"{label} missing columns {sorted(missing)}")
    if frame.empty:
        raise ValueError(f"{label} is empty")


def normalize_strings(frame: pd.DataFrame, columns: set[str], label: str) -> None:
    for column in columns:
        frame[column] = frame[column].astype("string").str.strip()
        if frame[column].isna().any() or frame[column].eq("").any():
            raise ValueError(f"{label} {column} must be nonblank")


def parse_bool(series: pd.Series, label: str) -> pd.Series:
    if pd.api.types.is_bool_dtype(series):
        if series.isna().any():
            raise ValueError(f"{label} contains missing booleans")
        return series.astype(bool)
    values = series.astype("string").str.strip().str.lower()
    if values.isna().any() or (~values.isin(["true", "false"])).any():
        raise ValueError(f"{label} must contain only true/false")
    return values.eq("true")


def parse_integer(series: pd.Series, label: str) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce")
    if values.isna().any() or (values % 1 != 0).any():
        raise ValueError(f"{label} must contain integers")
    return values.astype("int64")


def validate_boundary_flags(frame: pd.DataFrame, label: str) -> None:
    frame["feature_construction_eligible"] = parse_bool(
        frame.feature_construction_eligible, f"{label} feature_construction_eligible"
    )
    frame["scc_authorized"] = parse_bool(frame.scc_authorized, f"{label} scc_authorized")
    if not frame.feature_construction_eligible.all():
        raise ValueError(f"{label} contains rows not eligible for feature construction")
    if frame.scc_authorized.any():
        raise ValueError(f"{label} cannot authorize SCC use")


def validate_geography(frame: pd.DataFrame, label: str) -> None:
    frame["county_geoid"] = frame.county_geoid.astype("string").str.strip()
    if frame.county_geoid.isna().any() or frame.county_geoid.str.fullmatch(r"\d{5}").ne(True).any():
        raise ValueError(f"{label} county_geoid must contain five-digit real-FIPS keys")
    frame["state"] = frame.state.astype("string").str.strip().str.upper()
    if frame.state.isna().any() or frame.state.str.fullmatch(r"[A-Z]{2}").ne(True).any():
        raise ValueError(f"{label} state must contain two-letter postal codes")
    if frame.groupby("county_geoid", observed=True).state.nunique().gt(1).any():
        raise ValueError(f"{label} associates one county_geoid with multiple states")


def validate_counties(counties: pd.DataFrame) -> pd.DataFrame:
    require_columns(counties, COUNTY_COLUMNS, "County inventory")
    counties = counties.copy()
    normalize_strings(
        counties,
        {"boundary_source_id", "boundary_vintage", "historical_status", "crosswalk_source_id"},
        "County inventory",
    )
    validate_geography(counties, "County inventory")
    validate_boundary_flags(counties, "County inventory")
    if counties.duplicated("county_geoid").any():
        raise ValueError("County inventory contains duplicate county GEOIDs")
    allowed = {"stable", "explicit_crosswalk", "unresolved_change"}
    if (~counties.historical_status.isin(allowed)).any():
        raise ValueError("County inventory contains an unknown historical_status")
    if counties.historical_status.eq("unresolved_change").any():
        raise ValueError("Unresolved historical county changes are not feature-eligible")
    explicit = counties.historical_status.eq("explicit_crosswalk")
    if (explicit & counties.crosswalk_source_id.eq("not_applicable")).any():
        raise ValueError("Historical county changes require an explicit crosswalk source")
    return counties.sort_values("county_geoid").reset_index(drop=True)


def validate_outcomes(outcomes: pd.DataFrame) -> pd.DataFrame:
    require_columns(outcomes, OUTCOME_COLUMNS, "Outcome support")
    outcomes = outcomes.copy()
    normalize_strings(
        outcomes,
        {"outcome_crop", "outcome_source_id", "irrigation_practice", "sample_role"},
        "Outcome support",
    )
    validate_geography(outcomes, "Outcome support")
    validate_boundary_flags(outcomes, "Outcome support")
    outcomes["harvest_year"] = parse_integer(outcomes.harvest_year, "harvest_year")
    if not outcomes.harvest_year.between(1900, 2100).all():
        raise ValueError("Outcome harvest_year is outside the accepted range")
    if (~outcomes.outcome_crop.isin(OUTCOME_CROPS)).any():
        raise ValueError("Outcome support contains an unknown outcome_crop")
    if (~outcomes.irrigation_practice.isin(PRACTICES)).any():
        raise ValueError("Outcome support contains an unknown irrigation_practice")
    if (~outcomes.sample_role.isin(SAMPLE_ROLES)).any():
        raise ValueError("Outcome support contains an unknown sample_role")
    keys = ["county_geoid", "outcome_crop", "harvest_year", "irrigation_practice"]
    if outcomes.duplicated(keys).any():
        raise ValueError("Outcome support contains duplicate county-crop-year-practice keys")
    group_keys = ["county_geoid", "outcome_crop", "harvest_year"]
    for _, group in outcomes.groupby(group_keys, observed=True):
        roles = set(group.sample_role)
        if len(roles) != 1:
            raise ValueError("One county-crop-year mixes outcome sample roles")
        practices = set(group.irrigation_practice)
        expected = (
            {"irrigated", "non_irrigated"}
            if next(iter(roles)) == "direct_practice_pair"
            else {"all_production_practices"}
        )
        if practices != expected:
            raise ValueError("Outcome practice support does not match its declared sample role")
    return outcomes.sort_values(keys).reset_index(drop=True)


def validate_weights(weights: pd.DataFrame, tolerance: float) -> pd.DataFrame:
    require_columns(weights, WEIGHT_COLUMNS, "Crop-area weights")
    weights = weights.copy()
    string_columns = {
        "outcome_crop",
        "calendar_crop",
        "weather_source_id",
        "weather_grid_id",
        "calendar_class_share_source_id",
        "mask_source_id",
        "mask_vintage",
        "boundary_source_id",
        "boundary_vintage",
        "weight_role",
    }
    normalize_strings(weights, string_columns, "Crop-area weights")
    validate_geography(weights, "Crop-area weights")
    validate_boundary_flags(weights, "Crop-area weights")
    if (~weights.outcome_crop.isin(OUTCOME_CROPS)).any():
        raise ValueError("Crop-area weights contain an unknown outcome_crop")
    if (~weights.calendar_crop.isin(CALENDAR_CROPS)).any():
        raise ValueError("Crop-area weights contain an unknown calendar_crop")
    pairs = set(zip(weights.outcome_crop, weights.calendar_crop, strict=True))
    if not pairs <= ALLOWED_CROP_LINKS:
        raise ValueError("Crop-area weights contain an invalid outcome-to-calendar crop link")
    if (~weights.weight_role.isin(WEIGHT_ROLES)).any():
        raise ValueError("Crop-area weights contain an unknown weight_role")
    if not weights.weather_source_id.eq(PRIMARY_WEATHER_SOURCE).all():
        raise ValueError("Current primary contract accepts only pinned nClimGrid-Daily weights")
    if not weights.weather_grid_id.eq(PRIMARY_WEATHER_GRID).all():
        raise ValueError("Current primary contract accepts only the pinned nClimGrid grid")
    weights["grid_lat_index"] = parse_integer(weights.grid_lat_index, "grid_lat_index")
    weights["grid_lon_index"] = parse_integer(weights.grid_lon_index, "grid_lon_index")
    if not weights.grid_lat_index.between(0, PRIMARY_GRID_SHAPE["lat"] - 1).all():
        raise ValueError("grid_lat_index lies outside the nClimGrid grid")
    if not weights.grid_lon_index.between(0, PRIMARY_GRID_SHAPE["lon"] - 1).all():
        raise ValueError("grid_lon_index lies outside the nClimGrid grid")
    numeric = [
        "crop_area_m2",
        "county_calendar_crop_area_m2",
        "county_outcome_crop_area_m2",
        "spatial_weight",
        "calendar_class_share",
        "coverage_fraction",
    ]
    weights[numeric] = weights[numeric].apply(pd.to_numeric, errors="raise")
    if not np.isfinite(weights[numeric].to_numpy(dtype=float)).all():
        raise ValueError("Crop-area weights contain non-finite numeric values")
    if (weights[["crop_area_m2", "county_calendar_crop_area_m2", "county_outcome_crop_area_m2"]] <= 0).any().any():
        raise ValueError("Crop-area weights and denominators must be positive")
    if ((weights[["spatial_weight", "calendar_class_share", "coverage_fraction"]] < 0) | (weights[["spatial_weight", "calendar_class_share", "coverage_fraction"]] > 1)).any().any():
        raise ValueError("Shares and coverage_fraction must lie within [0, 1]")
    cell_keys = [
        "county_geoid",
        "outcome_crop",
        "calendar_crop",
        "weather_grid_id",
        "grid_lat_index",
        "grid_lon_index",
        "mask_vintage",
        "weight_role",
    ]
    if weights.duplicated(cell_keys).any():
        raise ValueError("Crop-area weights contain duplicate county-crop-grid-cell rows")

    spatial_group = [
        "county_geoid",
        "outcome_crop",
        "calendar_crop",
        "weather_source_id",
        "weather_grid_id",
        "mask_source_id",
        "mask_vintage",
        "boundary_source_id",
        "boundary_vintage",
        "weight_role",
    ]
    for _, group in weights.groupby(spatial_group, observed=True):
        for column in [
            "county_calendar_crop_area_m2",
            "county_outcome_crop_area_m2",
            "calendar_class_share",
            "calendar_class_share_source_id",
            "coverage_fraction",
        ]:
            if group[column].nunique(dropna=False) != 1:
                raise ValueError(f"Crop-area group has inconsistent {column}")
        calendar_area = float(group.county_calendar_crop_area_m2.iloc[0])
        outcome_area = float(group.county_outcome_crop_area_m2.iloc[0])
        if not np.isclose(group.crop_area_m2.sum(), calendar_area, rtol=0, atol=tolerance):
            raise ValueError("Grid-cell crop areas do not reconcile to the calendar-crop denominator")
        if not np.allclose(
            group.spatial_weight.to_numpy(dtype=float),
            group.crop_area_m2.to_numpy(dtype=float) / calendar_area,
            rtol=0,
            atol=tolerance,
        ):
            raise ValueError("spatial_weight does not equal cell area divided by its denominator")
        if not np.isclose(group.spatial_weight.sum(), 1.0, rtol=0, atol=tolerance):
            raise ValueError("Spatial weights do not sum to one within county/calendar crop")
        if not np.isclose(
            float(group.calendar_class_share.iloc[0]),
            calendar_area / outcome_area,
            rtol=0,
            atol=tolerance,
        ):
            raise ValueError("calendar_class_share does not reconcile to crop-area denominators")

    class_group = [
        "county_geoid",
        "outcome_crop",
        "mask_source_id",
        "mask_vintage",
        "boundary_source_id",
        "boundary_vintage",
        "weight_role",
    ]
    class_rows = weights.drop_duplicates(spatial_group)
    for _, group in class_rows.groupby(class_group, observed=True):
        if group.county_outcome_crop_area_m2.nunique() != 1:
            raise ValueError("Calendar classes disagree on county outcome-crop area")
        if not np.isclose(group.calendar_class_share.sum(), 1.0, rtol=0, atol=tolerance):
            raise ValueError("Calendar-class shares do not sum to one within county/outcome crop")
        if not np.isclose(
            group.county_calendar_crop_area_m2.sum(),
            float(group.county_outcome_crop_area_m2.iloc[0]),
            rtol=0,
            atol=tolerance,
        ):
            raise ValueError("Calendar-crop areas do not reconcile to county outcome-crop area")
    return weights.sort_values(cell_keys).reset_index(drop=True)


def validate_calendar(calendar_frame: pd.DataFrame) -> pd.DataFrame:
    require_columns(calendar_frame, CALENDAR_COLUMNS, "Crop calendar")
    calendar_frame = calendar_frame.copy()
    strings = {
        "calendar_crop",
        "calendar_source_id",
        "calendar_source_url",
        "calendar_vintage",
        "calendar_role",
        "boundary_rule",
        "stage_definition",
    }
    normalize_strings(calendar_frame, strings, "Crop calendar")
    calendar_frame["state"] = calendar_frame.state.astype("string").str.strip().str.upper()
    if calendar_frame.state.isna().any() or calendar_frame.state.str.fullmatch(r"[A-Z]{2}").ne(True).any():
        raise ValueError("Crop calendar state must contain two-letter postal codes")
    validate_boundary_flags(calendar_frame, "Crop calendar")
    if (~calendar_frame.calendar_crop.isin(CALENDAR_CROPS)).any():
        raise ValueError("Crop calendar contains an unknown or aggregate calendar_crop")
    if (~calendar_frame.calendar_role.isin(CALENDAR_ROLES)).any():
        raise ValueError("Crop calendar contains an unknown calendar_role")
    calendar_frame["harvest_year"] = parse_integer(calendar_frame.harvest_year, "harvest_year")
    for column in ["season_start", "season_end"]:
        values = pd.to_datetime(calendar_frame[column], errors="raise")
        if values.isna().any():
            raise ValueError(f"Crop calendar {column} contains missing dates")
        calendar_frame[column] = values.dt.normalize()
    if (calendar_frame.season_end < calendar_frame.season_start).any():
        raise ValueError("Crop season ends before it starts")
    if calendar_frame.season_end.dt.year.ne(calendar_frame.harvest_year).any():
        raise ValueError("Crop season_end year must equal harvest_year")
    duration = (calendar_frame.season_end - calendar_frame.season_start).dt.days + 1
    if ((duration < 30) | (duration > 500)).any():
        raise ValueError("Crop-season duration lies outside the 30..500 day guardrail")
    keys = ["state", "calendar_crop", "harvest_year", "calendar_role"]
    if calendar_frame.duplicated(keys).any():
        raise ValueError("Crop calendar contains duplicate state-crop-year-role rows")
    primary = calendar_frame.loc[calendar_frame.calendar_role.eq("fixed_primary")].copy()
    if not primary.empty:
        primary["start_mmdd"] = primary.season_start.dt.strftime("%m-%d")
        primary["end_mmdd"] = primary.season_end.dt.strftime("%m-%d")
        grouped = primary.groupby(["state", "calendar_crop"], observed=True)
        if grouped.start_mmdd.nunique().gt(1).any() or grouped.end_mmdd.nunique().gt(1).any():
            raise ValueError("fixed_primary calendars must preserve fixed month/day boundaries")
    return calendar_frame.sort_values(keys).reset_index(drop=True)


def validate_links(
    weights: pd.DataFrame,
    calendar_frame: pd.DataFrame,
    outcomes: pd.DataFrame,
    counties: pd.DataFrame,
) -> dict[str, object]:
    county_state = counties.set_index("county_geoid").state
    used = set(outcomes.county_geoid) | set(weights.county_geoid)
    if missing := used - set(counties.county_geoid):
        raise ValueError(f"County inventory lacks used GEOIDs {sorted(missing)}")
    for label, frame in [("Outcome support", outcomes), ("Crop-area weights", weights)]:
        expected = frame.county_geoid.map(county_state)
        if not frame.state.reset_index(drop=True).equals(expected.reset_index(drop=True)):
            raise ValueError(f"{label} state does not reconcile to the county inventory")

    outcome_pairs = set(zip(outcomes.county_geoid, outcomes.outcome_crop, strict=True))
    weight_pairs = set(zip(weights.county_geoid, weights.outcome_crop, strict=True))
    if outcome_pairs != weight_pairs:
        raise ValueError("Outcome and crop-area-weight county/crop support do not match exactly")

    outcome_keys = outcomes[["county_geoid", "state", "outcome_crop", "harvest_year"]].drop_duplicates()
    class_keys = weights[["county_geoid", "outcome_crop", "calendar_crop"]].drop_duplicates()
    needed = outcome_keys.merge(class_keys, on=["county_geoid", "outcome_crop"], how="left", validate="many_to_many")
    if needed.calendar_crop.isna().any():
        raise ValueError("Outcome support lacks a calendar-crop mapping")
    available = set(
        map(
            tuple,
            calendar_frame[["state", "calendar_crop", "harvest_year"]]
            .drop_duplicates()
            .itertuples(index=False, name=None),
        )
    )
    required = set(
        map(
            tuple,
            needed[["state", "calendar_crop", "harvest_year"]]
            .drop_duplicates()
            .itertuples(index=False, name=None),
        )
    )
    if missing := required - available:
        raise ValueError(f"Crop calendar lacks required state-class-year rows {sorted(missing)}")
    return {
        "counties": int(len(counties)),
        "outcome_rows": int(len(outcomes)),
        "county_crop_years": int(len(outcome_keys)),
        "weight_rows": int(len(weights)),
        "calendar_rows": int(len(calendar_frame)),
        "calendar_classes": sorted(weights.calendar_crop.unique().tolist()),
        "weather_source_id": PRIMARY_WEATHER_SOURCE,
        "weather_grid_id": PRIMARY_WEATHER_GRID,
        "minimum_weight_coverage_fraction": float(weights.coverage_fraction.min()),
        "response_estimation_authorized": False,
        "scc_authorized": False,
        "role": "pre_feature_schema_and_support_audit_only",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--weights", required=True)
    parser.add_argument("--calendar", required=True)
    parser.add_argument("--outcomes", required=True)
    parser.add_argument("--counties", required=True)
    parser.add_argument("--out", required=True, help="JSON audit path")
    parser.add_argument("--tolerance", type=float, default=1e-8)
    args = parser.parse_args()
    if args.tolerance < 0:
        raise ValueError("--tolerance must be nonnegative")
    counties = validate_counties(read_table(args.counties))
    outcomes = validate_outcomes(read_table(args.outcomes))
    weights = validate_weights(read_table(args.weights), args.tolerance)
    calendar_frame = validate_calendar(read_table(args.calendar))
    audit = validate_links(weights, calendar_frame, outcomes, counties)
    destination = Path(args.out)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        f"validated {audit['county_crop_years']} county-crop-years and "
        f"{audit['weight_rows']} sparse crop-area weights; no response estimated"
    )


if __name__ == "__main__":
    main()
