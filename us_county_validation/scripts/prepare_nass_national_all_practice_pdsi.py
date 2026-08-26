#!/usr/bin/env python3
"""Prepare a national all-practice NASS/PDSI comparison input.

This route is intentionally separate from the paired irrigated/non-irrigated
county analysis.  It attaches retrospective NOAA nClimDiv PDSI summaries to
the all-practice corn and soybean outcome panel, while preserving the fixed
2019 county-envelope caveat and the fixed-2017 irrigation-share metadata.
The output is a data-only comparison input; it authorizes no response fit,
causal interpretation, damage calculation, or SCC use.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import tempfile
from datetime import timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from build_county_crop_calendar_drought_features import (
    FORBIDDEN_DIRECT_COLUMN,
    FORBIDDEN_OUTCOME_COLUMN,
    load_contract,
    validate_calendar,
    validate_monthly,
    window_metrics,
)
from download_nclimdiv_county_pdsi import (
    BULK_NAME,
    DEFAULT_PROVENANCE,
    load_pins,
    validate_bulk_schema,
    validate_local,
)
from extract_nclimdiv_county_pdsi import extract_rows


OUTCOME_KEYS = ["outcome_crop", "county_geoid", "harvest_year"]
JOIN_KEYS = ["county_geoid", "state", "calendar_crop", "harvest_year"]
FEATURE_KEYS = JOIN_KEYS + ["calendar_role", "window_id"]
ALLOWED_CROPS = {"corn_grain", "soybeans"}
ELIGIBLE_GEOGRAPHY_STATUSES = {
    "fixed_2019_proxy_no_substantial_page_hit",
    "name_or_code_review_no_boundary_change_in_page_entry",
}
FORBIDDEN_STACKED_COLUMN = re.compile(
    r"(^|_)(spei|tmean|gdd|cdd|wet_days?|wet_day_frequency|rx\d+day|dry_spell)(_|$)",
    re.IGNORECASE,
)
NATIONAL_OUTCOME_SOURCE_ID = "nass_quickstats_api_national_all_practice_1981_2019"
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[1]
IMPLEMENTATION_FILES = [
    Path(__file__).resolve(),
    SCRIPT_DIR / "build_county_crop_calendar_drought_features.py",
    SCRIPT_DIR / "download_nclimdiv_county_pdsi.py",
    SCRIPT_DIR / "extract_nclimdiv_county_pdsi.py",
]
EXPECTED_CALENDAR_ROLES = {"fixed_primary", "fixed_broad_window_sensitivity"}
EXPECTED_WINDOW_IDS = {"preplant90", "season", "stage1", "stage2", "stage3"}
EXPECTED_PDSI_FEATURE_METADATA: dict[str, object] = {
    "index_name": "nclimdiv_county_pdsi",
    "index_scale_months": 0,
    "index_scale_role": "stateful_palmer_index_not_fixed_accumulation",
    "index_distribution": "palmer_water_balance",
    "index_source_id": "noaa_nclimdiv_county_pdsi_v1_0_0_20260806",
    "index_calibration_start_year": 1931,
    "index_calibration_end_year": 1990,
    "index_calibration_role": "publisher_fixed_independent_of_crop_outcomes",
    "source_role": "historical_county_benchmark_not_future_scc_input",
}


def read_table(path: Path) -> pd.DataFrame:
    return (
        pd.read_parquet(path)
        if path.suffix.lower() in {".parquet", ".pq"}
        else pd.read_csv(path, dtype={"county_geoid": "string"})
    )


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(8 * 1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def project_relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT).as_posix()
    except ValueError as error:
        raise ValueError(f"route path is outside the isolated precipitation-SCC project: {path}") from error


def parse_bool(series: pd.Series, label: str) -> pd.Series:
    if pd.api.types.is_bool_dtype(series):
        if series.isna().any():
            raise ValueError(f"{label} contains missing values")
        return series.astype(bool)
    text = series.astype("string").str.strip().str.lower()
    if text.isna().any() or (~text.isin(["true", "false"])).any():
        raise ValueError(f"{label} must contain only true/false")
    return text.eq("true")


def validate_panel(frame: pd.DataFrame) -> pd.DataFrame:
    required = {
        *OUTCOME_KEYS, "state", "irrigation_practice", "yield_bu_acre",
        "irrigation_share_vintage", "irrigation_share", "outcome_value_eligible",
        "irrigation_share_eligible", "irrigation_share_missing_reason",
        "rainfed_dominant_10pct", "rainfed_dominant_20pct",
        "rainfed_dominant_30pct", "outcome_source_id",
        "feature_construction_authorized", "response_estimation_authorized",
        "scc_authorized",
    }
    if missing := required - set(frame.columns):
        raise ValueError(f"national all-practice panel lacks {sorted(missing)}")
    result = frame.copy()
    result["county_geoid"] = result.county_geoid.astype("string").str.strip()
    result["state"] = result.state.astype("string").str.strip().str.upper()
    result["outcome_crop"] = result.outcome_crop.astype("string").str.strip()
    result["irrigation_practice"] = result.irrigation_practice.astype("string").str.strip()
    result["harvest_year"] = pd.to_numeric(result.harvest_year, errors="raise").astype("int64")
    result["yield_bu_acre"] = pd.to_numeric(result.yield_bu_acre, errors="raise")
    result["irrigation_share"] = pd.to_numeric(result.irrigation_share, errors="coerce")
    result["irrigation_share_vintage"] = pd.to_numeric(
        result.irrigation_share_vintage, errors="raise"
    ).astype("int64")
    if result.empty or result.county_geoid.str.fullmatch(r"\d{5}").ne(True).any():
        raise ValueError("national all-practice panel is empty or has malformed GEOIDs")
    if set(result.outcome_crop) != ALLOWED_CROPS:
        raise ValueError("national all-practice panel must contain exactly corn and soybeans")
    if set(result.irrigation_practice) != {"all_practices"}:
        raise ValueError("national route cannot relabel all-practice outcomes as an irrigation practice")
    if not result.irrigation_share_vintage.eq(2017).all():
        raise ValueError("national route requires the fixed-2017 irrigation-share vintage")
    result["outcome_source_id"] = result.outcome_source_id.astype("string").str.strip()
    if not result.outcome_source_id.eq(NATIONAL_OUTCOME_SOURCE_ID).all():
        raise ValueError("national route outcome source differs from the locked NASS series")
    if not np.isfinite(result.yield_bu_acre).all() or (result.yield_bu_acre <= 0).any():
        raise ValueError("national all-practice panel contains nonpositive/nonfinite outcomes")
    if result.duplicated(OUTCOME_KEYS).any():
        raise ValueError("national all-practice panel contains duplicate outcome keys")
    for column in [
        "outcome_value_eligible", "irrigation_share_eligible", "rainfed_dominant_10pct",
        "rainfed_dominant_20pct", "rainfed_dominant_30pct",
        "feature_construction_authorized", "response_estimation_authorized",
        "scc_authorized",
    ]:
        result[column] = parse_bool(result[column], column)
    if not result.outcome_value_eligible.all():
        raise ValueError("national all-practice panel contains an ineligible outcome value")
    if not result.feature_construction_authorized.all():
        raise ValueError("national all-practice panel contains a feature-ineligible outcome")
    if result.response_estimation_authorized.any() or result.scc_authorized.any():
        raise ValueError("national all-practice panel unexpectedly authorizes estimation/SCC")
    share_observed = result.irrigation_share_eligible
    if result.loc[share_observed, "irrigation_share"].isna().any():
        raise ValueError("an eligible irrigation share is missing")
    if result.loc[share_observed, "irrigation_share"].lt(0).any() or result.loc[share_observed, "irrigation_share"].gt(1).any():
        raise ValueError("eligible irrigation shares must lie in [0,1]")
    if result.loc[~share_observed, "irrigation_share"].notna().any():
        raise ValueError("an ineligible irrigation share was numerically filled")
    missing_reasons = result.loc[
        ~share_observed, "irrigation_share_missing_reason"
    ].astype("string").str.strip()
    if missing_reasons.isna().any() or missing_reasons.eq("").any():
        raise ValueError("missing irrigation shares require an explicit reason")
    for threshold in (10, 20, 30):
        flag = result[f"rainfed_dominant_{threshold}pct"]
        expected = share_observed & result.irrigation_share.le(threshold / 100)
        if not flag.eq(expected).all():
            raise ValueError(f"rainfed_dominant_{threshold}pct does not match the fixed share")
    return result.sort_values(OUTCOME_KEYS).reset_index(drop=True)


def validate_geography(frame: pd.DataFrame) -> pd.DataFrame:
    required = {
        "county_geoid", "state", "tiger2019_exact_geoid_match",
        "geometry_change_review_required", "geography_gate_status",
        "minor_boundary_change_caveat", "feature_construction_eligible",
        "response_estimation_authorized", "scc_authorized",
    }
    if missing := required - set(frame.columns):
        raise ValueError(f"national geography gate lacks {sorted(missing)}")
    result = frame.copy()
    result["county_geoid"] = result.county_geoid.astype("string").str.strip()
    result["state"] = result.state.astype("string").str.strip().str.upper()
    if result.empty or result.county_geoid.str.fullmatch(r"\d{5}").ne(True).any():
        raise ValueError("national geography gate is empty or has malformed GEOIDs")
    if result.duplicated("county_geoid").any():
        raise ValueError("national geography gate contains duplicate counties")
    if result.state.str.fullmatch(r"[A-Z]{2}").ne(True).any():
        raise ValueError("national geography gate contains a malformed state code")
    for column in [
        "tiger2019_exact_geoid_match", "geometry_change_review_required",
        "minor_boundary_change_caveat", "feature_construction_eligible",
        "response_estimation_authorized", "scc_authorized",
    ]:
        result[column] = parse_bool(result[column], f"geography {column}")
    if result.response_estimation_authorized.any() or result.scc_authorized.any():
        raise ValueError("national geography gate unexpectedly authorizes estimation/SCC")
    eligible = result.feature_construction_eligible
    if not result.loc[eligible, "tiger2019_exact_geoid_match"].all():
        raise ValueError("an eligible geography lacks an exact 2019 TIGER GEOID")
    if result.loc[eligible, "geometry_change_review_required"].any():
        raise ValueError("an unresolved geometry-change county is marked eligible")
    if (~result.loc[eligible, "geography_gate_status"].isin(ELIGIBLE_GEOGRAPHY_STATUSES)).any():
        raise ValueError("an eligible geography has an unregistered fixed-proxy status")
    return result.sort_values("county_geoid").reset_index(drop=True)


def eligible_support(panel: pd.DataFrame, geography: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    panel = validate_panel(panel)
    geography = validate_geography(geography)
    geo_columns = [
        "county_geoid", "state", "geography_gate_status", "minor_boundary_change_caveat",
        "feature_construction_eligible",
    ]
    support = panel.merge(
        geography[geo_columns].rename(columns={
            "state": "geography_state",
            "feature_construction_eligible": "geography_eligible",
        }),
        on="county_geoid", how="left", validate="many_to_one",
    )
    if support.geography_eligible.isna().any():
        raise ValueError("a national outcome county is absent from the geography gate")
    if not support.state.eq(support.geography_state).all():
        raise ValueError("national outcome state does not match the fixed-2019 geography gate")
    support = support.drop(columns="geography_state")
    eligible = support.loc[support.geography_eligible].copy()
    blocked = support.loc[~support.geography_eligible].copy()
    if eligible.empty:
        raise ValueError("the national all-practice route has no eligible geography")
    return eligible.sort_values(OUTCOME_KEYS).reset_index(drop=True), blocked


def filter_calendars(calendar: pd.DataFrame, eligible: pd.DataFrame, contract: dict[str, Any]) -> pd.DataFrame:
    calendar_contract = contract.get("calendar")
    if not isinstance(calendar_contract, dict):
        raise ValueError("drought contract lacks calendar rules")
    validated = validate_calendar(calendar, calendar_contract)
    required = eligible[["state", "outcome_crop", "harvest_year"]].drop_duplicates().rename(
        columns={"outcome_crop": "calendar_crop"}
    )
    selected = required.merge(
        validated, on=["state", "calendar_crop", "harvest_year"],
        how="left", validate="one_to_many",
    )
    if selected.calendar_role.isna().any():
        missing = selected.loc[selected.calendar_role.isna(), ["state", "calendar_crop", "harvest_year"]]
        raise ValueError(f"eligible outcomes lack a fixed crop calendar: {missing.head(10).to_dict('records')}")
    expected_roles = {
        str(calendar_contract["primary_role"]), str(calendar_contract["sensitivity_role"]),
    }
    roles = selected.groupby(["state", "calendar_crop", "harvest_year"], observed=True).calendar_role.agg(set)
    if not roles.map(lambda value: value == expected_roles).all():
        raise ValueError("every eligible state/crop/year must retain both fixed calendar roles")
    return selected.sort_values(["state", "calendar_crop", "harvest_year", "calendar_role"]).reset_index(drop=True)


def build_support_features(
    monthly: pd.DataFrame,
    calendar: pd.DataFrame,
    eligible: pd.DataFrame,
    moderate_threshold: float,
    severe_threshold: float,
    preplant_days: int,
    fractions: list[float],
) -> pd.DataFrame:
    """Construct PDSI windows only for observed, eligible crop-county-years."""
    if not np.isfinite([moderate_threshold, severe_threshold]).all() or severe_threshold >= moderate_threshold:
        raise ValueError("severe threshold must be finite and lower than the moderate threshold")
    if preplant_days < 1:
        raise ValueError("preplant_days must be positive")
    if fractions[0] != 0 or fractions[-1] != 1 or any(b <= a for a, b in zip(fractions, fractions[1:])):
        raise ValueError("stage fractions must strictly increase from zero to one")
    outcomes = eligible[["county_geoid", "state", "outcome_crop", "harvest_year"]].drop_duplicates()
    if len(outcomes) != len(eligible):
        raise ValueError("eligible national outcomes duplicate crop-county-year keys")
    monthly_lookup: dict[str, dict[tuple[int, int], float]] = {}
    monthly_metadata: dict[str, pd.Series] = {}
    for geoid, group in monthly.groupby("county_geoid", observed=True, sort=False):
        geoid_text = str(geoid)
        monthly_lookup[geoid_text] = {
            (int(row.year), int(row.month)): float(row.index_value)
            for row in group.itertuples(index=False)
        }
        monthly_metadata[geoid_text] = group.iloc[0]
    if set(monthly_lookup) != set(outcomes.county_geoid.astype(str)):
        raise ValueError("monthly PDSI county support differs from the eligible outcome support")
    calendar_keys = ["state", "calendar_crop", "harvest_year", "calendar_role"]
    if calendar.duplicated(calendar_keys).any():
        raise ValueError("selected national calendar duplicates its exact keys")
    calendar_lookup = {
        tuple(getattr(row, key) for key in calendar_keys): row
        for row in calendar.itertuples(index=False)
    }
    roles = sorted(calendar.calendar_role.astype(str).unique())
    rows: list[dict[str, object]] = []
    for outcome in outcomes.itertuples(index=False):
        geoid = str(outcome.county_geoid)
        if geoid not in monthly_lookup:
            raise ValueError(f"eligible outcome county lacks monthly PDSI: {geoid}")
        lookup = monthly_lookup[geoid]
        metadata = monthly_metadata[geoid]
        if str(metadata.state_alpha) != str(outcome.state):
            raise ValueError(f"monthly PDSI state does not match eligible outcome state for {geoid}")
        for role in roles:
            key = (str(outcome.state), str(outcome.outcome_crop), int(outcome.harvest_year), role)
            if key not in calendar_lookup:
                raise ValueError(f"eligible national outcome lacks calendar role: {key}")
            calendar_row = calendar_lookup[key]
            season_start = pd.Timestamp(calendar_row.season_start).date()
            season_end = pd.Timestamp(calendar_row.season_end).date()
            season_days = (season_end - season_start).days + 1
            windows = [
                (
                    f"preplant{preplant_days}",
                    season_start - timedelta(days=preplant_days),
                    season_start - timedelta(days=1),
                )
            ]
            for stage, (left, right) in enumerate(zip(fractions, fractions[1:]), start=1):
                start_offset = int(np.floor(left * season_days))
                end_offset = int(np.floor(right * season_days)) - 1
                if end_offset < start_offset:
                    raise ValueError("crop stage has no days under the locked fractions")
                windows.append((
                    f"stage{stage}",
                    season_start + timedelta(days=start_offset),
                    season_start + timedelta(days=end_offset),
                ))
            windows.append(("season", season_start, season_end))
            for window_id, start, end in windows:
                metrics = window_metrics(lookup, start, end, moderate_threshold, severe_threshold)
                rows.append({
                    "county_geoid": geoid,
                    "state": str(outcome.state),
                    "calendar_crop": str(outcome.outcome_crop),
                    "harvest_year": int(outcome.harvest_year),
                    "calendar_role": role,
                    "calendar_source_id": calendar_row.calendar_source_id,
                    "calendar_vintage": calendar_row.calendar_vintage,
                    "boundary_rule": calendar_row.boundary_rule,
                    "stage_definition": calendar_row.stage_definition,
                    "window_id": window_id,
                    "window_start": pd.Timestamp(start),
                    "window_end": pd.Timestamp(end),
                    "window_days": (end - start).days + 1,
                    **metrics,
                    "moderate_threshold": moderate_threshold,
                    "severe_threshold": severe_threshold,
                    "monthly_value_day_weighted_not_daily_observation": True,
                    "drought_family": "pdsi",
                    "index_name": metadata.index_name,
                    "index_scale_months": int(metadata.index_scale_months),
                    "index_scale_role": metadata.index_scale_role,
                    "index_distribution": metadata.index_distribution,
                    "index_source_id": metadata.index_source_id,
                    "index_calibration_start_year": int(metadata.index_calibration_start_year),
                    "index_calibration_end_year": int(metadata.index_calibration_end_year),
                    "index_calibration_role": metadata.index_calibration_role,
                    "source_role": metadata.source_role,
                    "irrigation_in_index": False,
                    "analysis_role": "historical_national_predictive_input_only",
                    "response_estimation_authorized": False,
                    "scc_authorized": False,
                })
    result = pd.DataFrame(rows)
    if result.empty or result.duplicated(FEATURE_KEYS).any():
        raise ValueError("support-bound national PDSI features are empty or duplicate their keys")
    if not result.monthly_index_days_covered.eq(result.window_days).all():
        raise ValueError("support-bound national PDSI windows have incomplete monthly coverage")
    expected = len(eligible) * len(roles) * (len(fractions) - 1 + 2)
    if len(result) != expected:
        raise ValueError("support-bound national PDSI row count does not match the exact outcome contract")
    return result.sort_values(FEATURE_KEYS).reset_index(drop=True)


def join_features(eligible: pd.DataFrame, features: pd.DataFrame) -> pd.DataFrame:
    if features.empty or features.duplicated(FEATURE_KEYS).any():
        raise ValueError("national PDSI features are empty or duplicate their keys")
    if set(features.drought_family.astype(str)) != {"pdsi"}:
        raise ValueError("national PDSI route cannot contain another moisture family")
    for column, expected in EXPECTED_PDSI_FEATURE_METADATA.items():
        if column not in features:
            raise ValueError(f"national PDSI features lack locked metadata {column}")
        if isinstance(expected, int):
            observed = pd.to_numeric(features[column], errors="raise")
            matches = observed.eq(expected)
        else:
            observed = features[column].astype("string").str.strip()
            matches = observed.eq(str(expected))
        if matches.isna().any() or not matches.all():
            raise ValueError(f"national PDSI feature metadata differs from the locked {column}")
    forbidden = sorted(
        column for column in features.columns
        if FORBIDDEN_DIRECT_COLUMN.search(column)
        or FORBIDDEN_STACKED_COLUMN.search(column)
        or FORBIDDEN_OUTCOME_COLUMN.search(column)
    )
    if forbidden:
        raise ValueError(f"national PDSI route contains stacked direct/SPEI or outcome columns {forbidden}")
    for column in ["irrigation_in_index", "response_estimation_authorized", "scc_authorized"]:
        if column not in features:
            raise ValueError(f"national PDSI features lack the {column} gate")
        if parse_bool(features[column], f"PDSI feature {column}").any():
            raise ValueError(f"national PDSI features unexpectedly authorize {column}")
    eligible_keys = eligible[["county_geoid", "state", "outcome_crop", "harvest_year"]].rename(
        columns={"outcome_crop": "calendar_crop"}
    ).drop_duplicates()
    feature_keys = features[["county_geoid", "state", "calendar_crop", "harvest_year"]].drop_duplicates()
    key_columns = ["county_geoid", "state", "calendar_crop", "harvest_year"]
    eligible_index = pd.MultiIndex.from_frame(eligible_keys[key_columns])
    feature_index = pd.MultiIndex.from_frame(feature_keys[key_columns])
    if set(feature_index) != set(eligible_index):
        raise ValueError("national PDSI feature outcome-key support differs from eligible outcomes")
    routed = eligible.copy()
    routed["calendar_crop"] = routed.outcome_crop
    joined = routed.merge(features, on=JOIN_KEYS, how="left", validate="one_to_many", suffixes=("", "_pdsi"))
    if joined.index_source_id.isna().any():
        missing = joined.loc[joined.index_source_id.isna(), OUTCOME_KEYS]
        raise ValueError(f"eligible national outcomes lack PDSI features: {missing.head(10).to_dict('records')}")
    observed_roles = set(features.calendar_role.astype(str))
    observed_windows = set(features.window_id.astype(str))
    if observed_roles != EXPECTED_CALENDAR_ROLES or observed_windows != EXPECTED_WINDOW_IDS:
        raise ValueError("national PDSI features differ from the locked calendar-role/window set")
    expected_windows = features[["calendar_role", "window_id"]].drop_duplicates()
    role_counts = expected_windows.groupby("calendar_role", observed=True).size()
    if role_counts.nunique() != 1:
        raise ValueError("calendar roles do not have the same PDSI window set")
    expected_per_outcome = int(len(expected_windows))
    counts = joined.groupby(OUTCOME_KEYS, observed=True).size()
    if not counts.eq(expected_per_outcome).all():
        raise ValueError("national outcomes do not have the complete PDSI calendar/window set")
    joined["feature_family"] = "pdsi"
    joined["moisture_family_rule"] = "mutually_exclusive_not_stacked_with_direct_weather_or_spei"
    joined["outcome_irrigation_interpretation"] = "all_practices_mixture_not_direct_rainfed_yield"
    joined["geography_interpretation"] = "fixed_2019_county_envelope_proxy"
    joined["analysis_role"] = "historical_national_predictive_input_only"
    joined["response_estimation_authorized"] = False
    joined["scc_authorized"] = False
    return joined.sort_values(OUTCOME_KEYS + ["calendar_role", "window_id"]).reset_index(drop=True)


def atomic_parquet(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.partial-", suffix=".parquet", dir=path.parent)
    os.close(descriptor)
    temporary_path = Path(temporary)
    try:
        frame.to_parquet(temporary_path, index=False)
        temporary_path.replace(path)
        path.chmod(0o644)
    finally:
        temporary_path.unlink(missing_ok=True)


def atomic_json(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.partial-", suffix=".json", dir=path.parent)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        json.dump(payload, stream, indent=2, sort_keys=True)
        stream.write("\n")
    Path(temporary).replace(path)
    path.chmod(0o644)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--panel", required=True)
    parser.add_argument("--geography-gate", required=True)
    parser.add_argument("--calendar", required=True)
    parser.add_argument("--pdsi-input", default=f"data/raw/us_county/nclimdiv_pdsicy/{BULK_NAME}")
    parser.add_argument("--pdsi-provenance", default=str(DEFAULT_PROVENANCE))
    parser.add_argument("--contract", default="config/us_county_drought_predictor_contract_v1.toml")
    parser.add_argument("--monthly-out", required=True)
    parser.add_argument("--feature-out", required=True)
    parser.add_argument("--joined-out", required=True)
    parser.add_argument("--audit-out", required=True)
    args = parser.parse_args()

    paths = {name: Path(value) for name, value in vars(args).items() if name != "pdsi_input"}
    pdsi_input = Path(args.pdsi_input)
    contract, family_contract = load_contract(paths["contract"], "pdsi")
    eligible, blocked = eligible_support(read_table(paths["panel"]), read_table(paths["geography_gate"]))
    calendar = filter_calendars(read_table(paths["calendar"]), eligible, contract)

    _, pins = load_pins(paths["pdsi_provenance"])
    bulk_pin = next(item for item in pins if item["name"] == BULK_NAME)
    validate_local(pdsi_input, bulk_pin)
    validation = bulk_pin.get("validation")
    if not isinstance(validation, dict):
        raise ValueError("nClimDiv provenance lacks decoded validation expectations")
    validate_bulk_schema(pdsi_input, validation)
    monthly = extract_rows(
        pdsi_input, 1980, 2019,
        eligible.county_geoid.drop_duplicates().astype(str).sort_values().tolist(),
    )
    monthly = validate_monthly(monthly, "pdsi", family_contract)
    features = build_support_features(
        monthly, calendar, eligible,
        float(family_contract["moderate_threshold"]),
        float(family_contract["severe_threshold"]),
        int(contract["calendar"]["preplant_days"]),
        [float(value) for value in contract["calendar"]["stage_fractions"]],
    )
    joined = join_features(eligible, features)

    atomic_parquet(monthly, paths["monthly_out"])
    atomic_parquet(features, paths["feature_out"])
    atomic_parquet(joined, paths["joined_out"])
    audit = {
        "role": "national all-practice NASS/PDSI data-only comparison input",
        "input_positive_outcome_rows": int(len(eligible) + len(blocked)),
        "geography_eligible_outcome_rows": int(len(eligible)),
        "geography_blocked_outcome_rows": int(len(blocked)),
        "eligible_counties": int(eligible.county_geoid.nunique()),
        "eligible_corn_rows": int(eligible.outcome_crop.eq("corn_grain").sum()),
        "eligible_soybean_rows": int(eligible.outcome_crop.eq("soybeans").sum()),
        "monthly_pdsi_rows_1980_2019": int(len(monthly)),
        "calendar_rows": int(len(calendar)),
        "candidate_feature_rows": int(len(features)),
        "joined_outcome_window_rows": int(len(joined)),
        "joined_unique_outcome_rows": int(joined.drop_duplicates(OUTCOME_KEYS).shape[0]),
        "primary_rainfed_dominant_threshold": "fixed_2017 irrigation share <= 0.10; sample definition only",
        "outcome_irrigation_interpretation": "all-practice yield; never relabeled as rainfed",
        "missing_irrigation_share_rule": "missing/suppressed numerator remains missing and is never set to zero",
        "geography_role": "fixed 2019 TIGER county-envelope proxy after the registered historical-change screen",
        "pdsi_role": "retrospective competing moisture family; never stacked with direct weather or SPEI",
        "monthly_index_boundary_caveat": "partial boundary months day-weight a monthly value that contains the complete month's weather",
        "contains_outcome_values": True,
        "response_estimated": False,
        "causal_effect_estimated": False,
        "damage_calculated": False,
        "scc_calculated": False,
        "implementation": {
            "files": {
                project_relative(path): {"sha256": sha256(path)}
                for path in IMPLEMENTATION_FILES
            },
        },
        "inputs": {
            "panel": {"path": project_relative(paths["panel"]), "sha256": sha256(paths["panel"])},
            "geography_gate": {"path": project_relative(paths["geography_gate"]), "sha256": sha256(paths["geography_gate"])},
            "calendar": {"path": project_relative(paths["calendar"]), "sha256": sha256(paths["calendar"])},
            "pdsi_input": {"path": project_relative(pdsi_input), "sha256": sha256(pdsi_input)},
            "pdsi_provenance": {"path": project_relative(paths["pdsi_provenance"]), "sha256": sha256(paths["pdsi_provenance"])},
            "contract": {"path": project_relative(paths["contract"]), "sha256": sha256(paths["contract"])},
        },
        "outputs": {
            "monthly": {"path": project_relative(paths["monthly_out"]), "sha256": sha256(paths["monthly_out"])},
            "features": {"path": project_relative(paths["feature_out"]), "sha256": sha256(paths["feature_out"])},
            "joined": {"path": project_relative(paths["joined_out"]), "sha256": sha256(paths["joined_out"])},
        },
    }
    atomic_json(audit, paths["audit_out"])
    print(
        f"wrote {len(joined)} national all-practice PDSI window rows for "
        f"{eligible.county_geoid.nunique()} counties; response_estimation_authorized=false; "
        "scc_authorized=false"
    )


if __name__ == "__main__":
    main()
