#!/usr/bin/env python3
"""Build monthly-index crop-calendar features for one drought family at a time."""
from __future__ import annotations

import argparse
import calendar as month_calendar
import re
import tomllib
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONTRACT = PROJECT_ROOT / "config/us_county_drought_predictor_contract_v1.toml"
MONTHLY_REQUIRED = {
    "county_geoid", "state_alpha", "date", "year", "month", "index_value",
    "drought_family", "index_name", "index_scale_months", "index_scale_role",
    "index_distribution", "index_source_id", "index_calibration_start_year",
    "index_calibration_end_year", "index_calibration_role", "source_role",
    "irrigation_in_index", "response_estimation_authorized", "scc_authorized",
}
CALENDAR_REQUIRED = {
    "state", "calendar_crop", "harvest_year", "season_start", "season_end",
    "calendar_source_id", "calendar_source_url", "calendar_vintage",
    "calendar_role", "boundary_rule", "stage_definition",
    "feature_construction_eligible", "scc_authorized",
}
FORBIDDEN_DIRECT_COLUMN = re.compile(
    r"(^|_)(pr|precip|precipitation|prcp|tas|temperature|tavg|tmin|tmax|pet|heat)(_|$)",
    re.IGNORECASE,
)
FORBIDDEN_OUTCOME_COLUMN = re.compile(
    r"(^|_)(yield|production|outcome_value|dependent_variable)(_|$)", re.IGNORECASE
)


def read_table(path: str) -> pd.DataFrame:
    source = Path(path)
    return pd.read_parquet(source) if source.suffix.lower() in {".parquet", ".pq"} else pd.read_csv(source)


def parse_bool(series: pd.Series, label: str) -> pd.Series:
    if pd.api.types.is_bool_dtype(series):
        if series.isna().any():
            raise ValueError(f"{label} contains missing values")
        return series.astype(bool)
    values = series.astype("string").str.strip().str.lower()
    if values.isna().any() or (~values.isin(["true", "false"])).any():
        raise ValueError(f"{label} must contain only true/false")
    return values.eq("true")


def _month_overlaps(start: date, end: date) -> list[tuple[tuple[int, int], int]]:
    result: list[tuple[tuple[int, int], int]] = []
    current = date(start.year, start.month, 1)
    while current <= end:
        month_end = date(current.year, current.month, month_calendar.monthrange(current.year, current.month)[1])
        left, right = max(start, current), min(end, month_end)
        if left <= right:
            result.append(((current.year, current.month), (right - left).days + 1))
        current = date(current.year + int(current.month == 12), current.month % 12 + 1, 1)
    return result


def window_metrics(
    lookup: dict[tuple[int, int], float],
    start: date,
    end: date,
    moderate_threshold: float,
    severe_threshold: float,
) -> dict[str, float | int]:
    if end < start:
        raise ValueError("drought feature window ends before it starts")
    weighted_sum = 0.0
    covered = 0
    moderate_days = 0
    severe_days = 0
    observed: list[float] = []
    for key, days in _month_overlaps(start, end):
        if key not in lookup:
            raise ValueError(f"monthly drought index is incomplete for {start} through {end}: missing {key}")
        value = float(lookup[key])
        if not np.isfinite(value):
            raise ValueError("monthly drought index contains a nonfinite value")
        weighted_sum += value * days
        covered += days
        moderate_days += days * int(value <= moderate_threshold)
        severe_days += days * int(value <= severe_threshold)
        observed.append(value)
    expected = (end - start).days + 1
    if covered != expected or not observed:
        raise ValueError("monthly drought overlap does not cover the exact requested window")
    return {
        "index_day_weighted_mean": weighted_sum / covered,
        "index_monthly_minimum": min(observed),
        "index_day_equivalents_at_or_below_moderate": moderate_days,
        "index_day_equivalents_at_or_below_severe": severe_days,
        "monthly_index_days_covered": covered,
    }


def load_contract(path: Path, family: str) -> tuple[dict[str, object], dict[str, object]]:
    try:
        contract = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise ValueError(f"cannot read drought predictor contract {path}") from error
    if family not in {"pdsi", "spei"} or not isinstance(contract.get(family), dict):
        raise ValueError("drought family must be pdsi or spei and exist in the contract")
    if contract.get("response_estimation_authorized") is not False or contract.get("scc_use_authorized") is not False:
        raise ValueError("drought input contract unexpectedly authorizes response estimation or SCC use")
    return contract, contract[family]


def validate_monthly(frame: pd.DataFrame, family: str, family_contract: dict[str, object]) -> pd.DataFrame:
    if missing := MONTHLY_REQUIRED - set(frame.columns):
        raise ValueError(f"monthly drought input lacks {sorted(missing)}")
    if forbidden := sorted(column for column in frame.columns if FORBIDDEN_DIRECT_COLUMN.search(column)):
        raise ValueError(f"drought-family input mechanically includes direct weather columns {forbidden}")
    if forbidden := sorted(column for column in frame.columns if FORBIDDEN_OUTCOME_COLUMN.search(column)):
        raise ValueError(f"monthly drought input includes outcome/leakage columns {forbidden}")
    if frame.empty:
        raise ValueError("monthly drought input is empty")
    result = frame.copy()
    result["county_geoid"] = result.county_geoid.astype("string").str.strip()
    result["state_alpha"] = result.state_alpha.astype("string").str.strip().str.upper()
    if result.county_geoid.str.fullmatch(r"\d{5}").ne(True).any():
        raise ValueError("monthly drought county_geoid must be five digits")
    if result.state_alpha.str.fullmatch(r"[A-Z]{2}").ne(True).any():
        raise ValueError("monthly drought state_alpha must be a USPS code")
    result["date"] = pd.to_datetime(result.date, errors="raise").dt.normalize()
    for column in ["year", "month", "index_scale_months", "index_calibration_start_year", "index_calibration_end_year"]:
        result[column] = pd.to_numeric(result[column], errors="raise").astype("int64")
    if not (result.date.dt.year.eq(result.year) & result.date.dt.month.eq(result.month) & result.date.dt.day.eq(1)).all():
        raise ValueError("monthly drought date/year/month do not reconcile to month starts")
    result["index_value"] = pd.to_numeric(result.index_value, errors="raise")
    if not np.isfinite(result.index_value.to_numpy(dtype=float)).all():
        raise ValueError("monthly drought index contains nonfinite values")
    if result.duplicated(["county_geoid", "year", "month"]).any():
        raise ValueError("monthly drought input contains duplicate county/year/month rows")
    for column in ["drought_family", "index_name", "index_scale_role", "index_distribution", "index_source_id", "index_calibration_role", "source_role"]:
        result[column] = result[column].astype("string").str.strip()
        if result[column].isna().any() or result[column].eq("").any() or result[column].nunique() != 1:
            raise ValueError(f"one drought-family invocation requires exactly one nonblank {column}")
    if result.drought_family.iloc[0] != family:
        raise ValueError("monthly drought family differs from the declared family")
    if result.index_source_id.iloc[0] != str(family_contract["source_id"]):
        raise ValueError("monthly drought source identity differs from the locked contract")
    result["irrigation_in_index"] = parse_bool(result.irrigation_in_index, "irrigation_in_index")
    result["response_estimation_authorized"] = parse_bool(result.response_estimation_authorized, "response_estimation_authorized")
    result["scc_authorized"] = parse_bool(result.scc_authorized, "scc_authorized")
    if result.irrigation_in_index.any() or result.response_estimation_authorized.any() or result.scc_authorized.any():
        raise ValueError("monthly climatic index cannot include irrigation or authorize estimation/SCC")
    if family == "pdsi":
        if not result.index_scale_months.eq(0).all() or result.index_distribution.iloc[0] != "palmer_water_balance":
            raise ValueError("PDSI scale/distribution metadata differ from the locked contract")
    else:
        allowed_scales = {int(value) for value in family_contract["candidate_scales_months"]}
        if result.index_scale_months.nunique() != 1 or int(result.index_scale_months.iloc[0]) not in allowed_scales:
            raise ValueError("SPEI input must contain exactly one locked candidate scale")
        allowed_distributions = {
            str(family_contract["primary_distribution_candidate"]),
            str(family_contract["sensitivity_distribution"]),
        }
        if result.index_distribution.iloc[0] not in allowed_distributions:
            raise ValueError("SPEI distribution differs from the locked candidates")
    expected_calibration = (
        int(family_contract["calibration_start_year"]), int(family_contract["calibration_end_year"])
    )
    if result.index_calibration_start_year.nunique() != 1 or result.index_calibration_end_year.nunique() != 1:
        raise ValueError("drought-index calibration metadata vary within one input")
    observed_calibration = (
        int(result.index_calibration_start_year.iloc[0]), int(result.index_calibration_end_year.iloc[0])
    )
    if observed_calibration != expected_calibration:
        raise ValueError("drought-index calibration period differs from the locked contract")
    return result.sort_values(["county_geoid", "date"]).reset_index(drop=True)


def validate_calendar(frame: pd.DataFrame, calendar_contract: dict[str, object]) -> pd.DataFrame:
    if missing := CALENDAR_REQUIRED - set(frame.columns):
        raise ValueError(f"crop calendar lacks {sorted(missing)}")
    if frame.empty:
        raise ValueError("crop calendar is empty")
    result = frame.copy()
    result["state"] = result.state.astype("string").str.strip().str.upper()
    result["calendar_crop"] = result.calendar_crop.astype("string").str.strip()
    result["calendar_role"] = result.calendar_role.astype("string").str.strip()
    for column in [
        "calendar_crop", "calendar_source_id", "calendar_source_url", "calendar_vintage",
        "calendar_role", "boundary_rule", "stage_definition",
    ]:
        result[column] = result[column].astype("string").str.strip()
        if result[column].isna().any() or result[column].eq("").any():
            raise ValueError(f"crop calendar {column} must be nonblank")
    if result.state.str.fullmatch(r"[A-Z]{2}").ne(True).any():
        raise ValueError("crop calendar state must be a USPS code")
    if not result.calendar_source_id.eq(str(calendar_contract["source_id"])).all():
        raise ValueError("crop calendar source differs from the locked contract")
    allowed_roles = {
        str(calendar_contract["primary_role"]), str(calendar_contract["sensitivity_role"]),
    }
    if (~result.calendar_role.isin(allowed_roles)).any():
        raise ValueError("crop calendar role differs from the locked primary/sensitivity roles")
    result["harvest_year"] = pd.to_numeric(result.harvest_year, errors="raise").astype("int64")
    result["season_start"] = pd.to_datetime(result.season_start, errors="raise").dt.normalize()
    result["season_end"] = pd.to_datetime(result.season_end, errors="raise").dt.normalize()
    result["feature_construction_eligible"] = parse_bool(result.feature_construction_eligible, "calendar feature flag")
    result["scc_authorized"] = parse_bool(result.scc_authorized, "calendar SCC flag")
    if not result.feature_construction_eligible.all() or result.scc_authorized.any():
        raise ValueError("calendar contains an ineligible or SCC-authorized row")
    if (result.season_end < result.season_start).any() or result.season_end.dt.year.ne(result.harvest_year).any():
        raise ValueError("calendar season dates do not form a valid harvest-year window")
    keys = ["state", "calendar_crop", "harvest_year", "calendar_role"]
    if result.duplicated(keys).any():
        raise ValueError("calendar contains duplicate state/crop/year/role rows")
    return result.sort_values(keys).reset_index(drop=True)


def build_features(
    monthly: pd.DataFrame,
    calendar: pd.DataFrame,
    family: str,
    moderate_threshold: float,
    severe_threshold: float,
    preplant_days: int,
    fractions: list[float],
) -> pd.DataFrame:
    if not np.isfinite([moderate_threshold, severe_threshold]).all() or severe_threshold >= moderate_threshold:
        raise ValueError("severe threshold must be finite and lower than the moderate threshold")
    if preplant_days < 1:
        raise ValueError("preplant_days must be positive")
    if fractions[0] != 0 or fractions[-1] != 1 or any(b <= a for a, b in zip(fractions, fractions[1:])):
        raise ValueError("stage fractions must strictly increase from zero to one")
    rows: list[dict[str, object]] = []
    monthly_by_county = {key: group for key, group in monthly.groupby("county_geoid", observed=True)}
    for calendar_row in calendar.itertuples(index=False):
        state_counties = [
            (geoid, group) for geoid, group in monthly_by_county.items()
            if str(group.state_alpha.iloc[0]) == str(calendar_row.state)
        ]
        if not state_counties:
            raise ValueError(f"no monthly drought county matches calendar state {calendar_row.state}")
        season_start = calendar_row.season_start.date()
        season_end = calendar_row.season_end.date()
        season_days = (season_end - season_start).days + 1
        windows: list[tuple[str, date, date]] = [
            (f"preplant{preplant_days}", season_start - timedelta(days=preplant_days), season_start - timedelta(days=1))
        ]
        for stage, (left, right) in enumerate(zip(fractions, fractions[1:]), start=1):
            start_offset = int(np.floor(left * season_days))
            end_offset = int(np.floor(right * season_days)) - 1
            if end_offset < start_offset:
                raise ValueError("crop stage has no days under the locked fractions")
            windows.append((f"stage{stage}", season_start + timedelta(days=start_offset), season_start + timedelta(days=end_offset)))
        windows.append(("season", season_start, season_end))
        for geoid, group in state_counties:
            lookup = {(int(row.year), int(row.month)): float(row.index_value) for row in group.itertuples(index=False)}
            metadata = group.iloc[0]
            for window_id, start, end in windows:
                metrics = window_metrics(lookup, start, end, moderate_threshold, severe_threshold)
                rows.append({
                    "county_geoid": geoid,
                    "state": calendar_row.state,
                    "calendar_crop": calendar_row.calendar_crop,
                    "harvest_year": int(calendar_row.harvest_year),
                    "calendar_role": calendar_row.calendar_role,
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
                    "drought_family": family,
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
                    "analysis_role": "historical_county_validation_input_only",
                    "response_estimation_authorized": False,
                    "scc_authorized": False,
                })
    result = pd.DataFrame(rows)
    keys = ["county_geoid", "calendar_crop", "harvest_year", "calendar_role", "window_id"]
    if result.empty or result.duplicated(keys).any():
        raise ValueError("drought crop-calendar features are empty or have duplicate keys")
    if not result.monthly_index_days_covered.eq(result.window_days).all():
        raise ValueError("drought crop-calendar window coverage is incomplete")
    return result.sort_values(keys).reset_index(drop=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--monthly-index", required=True)
    parser.add_argument("--calendar", required=True)
    parser.add_argument("--family", required=True, choices=["pdsi", "spei"])
    parser.add_argument("--contract", default=str(DEFAULT_CONTRACT))
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    contract, family_contract = load_contract(Path(args.contract), args.family)
    calendar_contract = contract.get("calendar")
    if not isinstance(calendar_contract, dict):
        raise ValueError("drought input contract lacks calendar rules")
    monthly = validate_monthly(read_table(args.monthly_index), args.family, family_contract)
    calendar = validate_calendar(read_table(args.calendar), calendar_contract)
    features = build_features(
        monthly,
        calendar,
        args.family,
        float(family_contract["moderate_threshold"]),
        float(family_contract["severe_threshold"]),
        int(calendar_contract["preplant_days"]),
        [float(value) for value in calendar_contract["stage_fractions"]],
    )
    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    features.to_parquet(output, index=False)
    print(
        f"wrote {len(features)} {args.family} crop-calendar window rows; "
        "response_estimation_authorized=false; scc_authorized=false"
    )


if __name__ == "__main__":
    main()
