#!/usr/bin/env python3
"""Build locked, first-differenced U.S. moisture diagnostic inputs.

This script performs no fit.  It writes one outcome/control table and separate
direct-precipitation and PDSI predictor tables on identical keys.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import tomllib
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_PROTOCOL = SCRIPT_DIR.parent / "us_competing_moisture_predictive_v1.toml"
KEYS = ["county_geoid", "outcome_crop", "harvest_year", "irrigation_practice"]
PAIR_KEYS = ["county_geoid", "outcome_crop", "harvest_year"]
PDSI_WINDOWS = {"preplant90", "season", "stage1", "stage2", "stage3"}
SOURCE_RECEIPT_STATUS = "validated_us_competing_moisture_source_input"
SOURCE_FAMILIES = {"calendar", "direct_weather", "pdsi"}
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
EXPECTED_MODEL_BLOCKS = {
    "controls_only": [],
    "direct_quantity": ["direct_quantity"],
    "direct_quantity_distribution": [
        "direct_quantity", "direct_distribution_extension"
    ],
    "pdsi_season_mean": ["pdsi_primary"],
    "pdsi_stage_sensitivity": ["pdsi_stage_sensitivity"],
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(8 * 1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def read_table(path: Path) -> pd.DataFrame:
    return (
        pd.read_parquet(path)
        if path.suffix.lower() in {".parquet", ".pq"}
        else pd.read_csv(path, dtype={"county_geoid": "string"})
    )


def load_protocol(path: Path = DEFAULT_PROTOCOL) -> dict[str, Any]:
    try:
        protocol = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise ValueError(f"cannot read protocol {path}") from error
    for section in [
        "sample", "features", "direct_source", "pdsi_source", "validation",
        "models", "output",
    ]:
        if not isinstance(protocol.get(section), dict):
            raise ValueError(f"protocol lacks [{section}]")
    if protocol.get("predictive_diagnostic_authorized") is not True:
        raise ValueError("protocol does not authorize the bounded predictive diagnostic")
    for flag in ["causal_claim_authorized", "damage_claim_authorized", "scc_claim_authorized"]:
        if protocol.get(flag) is not False:
            raise ValueError(f"protocol unexpectedly authorizes {flag}")
    if protocol["output"].get("coefficients_allowed") is not False:
        raise ValueError("protocol unexpectedly permits coefficient output")
    if protocol["output"].get("row_predictions_allowed") is not False:
        raise ValueError("protocol unexpectedly permits row-prediction output")
    if protocol["sample"].get("first_difference_consecutive_years_only") is not True:
        raise ValueError("protocol must require consecutive-year first differences")
    models = {
        str(model): list(map(str, blocks))
        for model, blocks in protocol["models"].items()
    }
    if models != EXPECTED_MODEL_BLOCKS:
        raise ValueError(
            "protocol [models] must equal the exact locked mutually exclusive model schema"
        )
    validation = protocol["validation"]
    for key in [
        "distribution_minimum_absolute_rmse_improvement",
        "distribution_minimum_relative_rmse_improvement",
    ]:
        value = float(validation.get(key, -1))
        if not np.isfinite(value) or value <= 0:
            raise ValueError(f"protocol {key} must be finite and positive")
    for section, required in {
        "direct_source": {
            "outcome_source_id", "weather_source_id", "weather_grid_id",
            "calendar_source_id", "calendar_vintage", "calendar_boundary_rule",
            "stage_definition", "weather_day_alignment", "wet_day_threshold_mm",
            "weight_role", "crop_pixel_exposure",
        },
        "pdsi_source": {
            "outcome_source_id", "index_source_id", "index_name", "drought_family",
            "index_scale_months", "index_distribution", "calendar_source_id",
            "calendar_vintage", "calendar_boundary_rule", "stage_definition",
            "calibration_start_year", "calibration_end_year", "irrigation_in_index",
        },
    }.items():
        if missing := required - set(protocol[section]):
            raise ValueError(f"protocol [{section}] lacks {sorted(missing)}")
    if protocol["direct_source"].get("crop_pixel_exposure") is not False:
        raise ValueError("primary direct-weather protocol must identify county-polygon exposure")
    if protocol["pdsi_source"].get("irrigation_in_index") is not False:
        raise ValueError("PDSI protocol cannot claim irrigation is represented in the index")
    if str(protocol["direct_source"]["calendar_source_id"]) != str(
        protocol["pdsi_source"]["calendar_source_id"]
    ):
        raise ValueError("direct-weather and PDSI protocols must use the same calendar source")
    for key in ["calendar_vintage", "calendar_boundary_rule", "stage_definition"]:
        if str(protocol["direct_source"][key]) != str(protocol["pdsi_source"][key]):
            raise ValueError(f"direct-weather and PDSI protocols disagree on {key}")
    return protocol


def normalize_date(series: pd.Series, label: str) -> pd.Series:
    values = pd.to_datetime(series, errors="raise").dt.normalize()
    if values.isna().any():
        raise ValueError(f"{label} contains missing dates")
    return values


def strict_bool(series: pd.Series, label: str) -> pd.Series:
    if pd.api.types.is_bool_dtype(series):
        if series.isna().any():
            raise ValueError(f"{label} contains missing values")
        return series.astype(bool)
    text = series.astype("string").str.strip().str.lower()
    if text.isna().any() or (~text.isin(["true", "false"])).any():
        raise ValueError(f"{label} must contain only true/false")
    return text.eq("true")


def normalize_keys(frame: pd.DataFrame, label: str) -> pd.DataFrame:
    if missing := set(KEYS) - set(frame.columns):
        raise ValueError(f"{label} lacks {sorted(missing)}")
    result = frame.copy()
    result["county_geoid"] = result.county_geoid.astype("string").str.strip()
    if result.county_geoid.str.fullmatch(r"\d{5}").ne(True).any():
        raise ValueError(f"{label} contains malformed county GEOIDs")
    result["outcome_crop"] = result.outcome_crop.astype("string").str.strip()
    result["irrigation_practice"] = result.irrigation_practice.astype("string").str.strip()
    result["harvest_year"] = pd.to_numeric(result.harvest_year, errors="raise").astype("int64")
    return result


def require_county_state_fips(frame: pd.DataFrame, label: str) -> None:
    """Require each postal state to equal the state encoded by county GEOID."""
    expected = frame.county_geoid.astype("string").str[:2].map(STATE_FIPS_TO_ALPHA)
    observed = frame.state.astype("string").str.strip().str.upper()
    if expected.isna().any():
        bad = sorted(set(frame.loc[expected.isna(), "county_geoid"].astype(str)))[:10]
        raise ValueError(f"{label} contains unknown state FIPS prefixes {bad}")
    if not observed.eq(expected.astype("string")).all():
        raise ValueError(f"{label} state does not reconcile to county GEOID state FIPS")


def numeric_finite(frame: pd.DataFrame, columns: list[str], label: str) -> None:
    for column in columns:
        values = pd.to_numeric(frame[column], errors="raise").to_numpy(dtype=float)
        if not np.isfinite(values).all():
            raise ValueError(f"{label} {column} contains missing/nonfinite values")


def require_exact_practice_pairs(frame: pd.DataFrame, practices: set[str], label: str) -> None:
    observed = frame.groupby(PAIR_KEYS, observed=True).irrigation_practice.agg(set)
    if not observed.map(lambda value: value == practices).all():
        raise ValueError(f"{label} does not preserve exact irrigation-practice pairs")


def require_shared_exposure(
    frame: pd.DataFrame, columns: list[str], practices: set[str], label: str
) -> None:
    require_exact_practice_pairs(frame, practices, label)
    for column in columns:
        counts = frame.groupby(PAIR_KEYS, observed=True)[column].nunique(dropna=False)
        if counts.ne(1).any():
            raise ValueError(f"{label} {column} differs between irrigation-practice outcomes")


def require_exact_pdsi_calendar_windows(frame: pd.DataFrame) -> None:
    fractions = [0.0, 0.3, 0.7, 1.0]
    for key, group in frame.groupby(KEYS, observed=True, sort=False):
        windows = group.set_index("window_id")
        season_start = pd.Timestamp(windows.loc["season", "window_start"]).normalize()
        season_end = pd.Timestamp(windows.loc["season", "window_end"]).normalize()
        season_days = (season_end - season_start).days + 1
        expected: dict[str, tuple[pd.Timestamp, pd.Timestamp]] = {
            "preplant90": (
                season_start - pd.Timedelta(days=90),
                season_start - pd.Timedelta(days=1),
            ),
            "season": (season_start, season_end),
        }
        for stage, (left, right) in enumerate(
            zip(fractions[:-1], fractions[1:], strict=True), start=1
        ):
            start = season_start + pd.Timedelta(days=int(np.floor(left * season_days)))
            end = season_start + pd.Timedelta(days=int(np.floor(right * season_days)) - 1)
            expected[f"stage{stage}"] = (start, end)
        for window, (expected_start, expected_end) in expected.items():
            observed_start = pd.Timestamp(windows.loc[window, "window_start"]).normalize()
            observed_end = pd.Timestamp(windows.loc[window, "window_end"]).normalize()
            if observed_start != expected_start or observed_end != expected_end:
                raise ValueError(
                    f"PDSI calendar window {window} does not reconcile to the locked "
                    f"season/stage rule for key {key}"
                )


def validate_direct(frame: pd.DataFrame, protocol: dict[str, Any]) -> pd.DataFrame:
    sample = protocol["sample"]
    features = protocol["features"]
    crops = set(map(str, sample["crops"]))
    practices = set(map(str, sample["irrigation_practices"]))
    controls = list(map(str, features["common_temperature_controls"]))
    moisture = list(map(str, features["direct_quantity"])) + list(
        map(str, features["direct_distribution_extension"])
    )
    required = {
        *KEYS, "state", "yield_bu_acre", "outcome_source_id", "calendar_role",
        "season_start", "season_end", "calendar_source_id", "calendar_vintage",
        "calendar_boundary_rule", "stage_definition", "weather_source_id",
        "weather_grid_id", "weather_day_alignment", "wet_day_threshold_mm",
        "weight_role", "crop_pixel_exposure", "weather_exposure_shared_across_practices",
        "feature_construction_eligible", "response_estimation_authorized", "scc_authorized",
        *controls, *moisture,
    }
    if missing := required - set(frame.columns):
        raise ValueError(f"direct-weather input lacks {sorted(missing)}")
    result = normalize_keys(frame, "direct-weather input")
    result = result.loc[
        result.outcome_crop.isin(crops)
        & result.irrigation_practice.isin(practices)
        & result.calendar_role.astype("string").eq(str(sample["calendar_role"]))
        & result.harvest_year.between(int(sample["year_min"]), int(sample["year_max"]))
    ].copy()
    if result.empty or set(result.outcome_crop) != crops or set(result.irrigation_practice) != practices:
        raise ValueError("direct-weather input does not populate every locked crop/practice")
    if result.duplicated(KEYS).any():
        raise ValueError("direct-weather input duplicates outcome keys")
    result["state"] = result.state.astype("string").str.strip().str.upper()
    if result.state.str.fullmatch(r"[A-Z]{2}").ne(True).any():
        raise ValueError("direct-weather input contains malformed states")
    require_county_state_fips(result, "direct-weather input")
    numeric_finite(result, ["yield_bu_acre", *controls, *moisture], "direct-weather input")
    if (pd.to_numeric(result.yield_bu_acre) <= 0).any():
        raise ValueError("direct-weather input has nonpositive yields")
    result["season_start"] = normalize_date(result.season_start, "direct season_start")
    result["season_end"] = normalize_date(result.season_end, "direct season_end")
    if (result.season_end < result.season_start).any():
        raise ValueError("direct-weather input contains an invalid crop season")
    if result.season_end.dt.year.ne(result.harvest_year).any():
        raise ValueError("direct-weather season_end does not match harvest_year")
    duration = result.season_end.sub(result.season_start).dt.days.add(1)
    if not duration.between(30, 500).all():
        raise ValueError("direct-weather crop-season duration lies outside 30..500 days")
    fixed_calendar = result.assign(
        start_mmdd=result.season_start.dt.strftime("%m-%d"),
        end_mmdd=result.season_end.dt.strftime("%m-%d"),
    ).groupby(["state", "outcome_crop"], observed=True)
    if fixed_calendar.start_mmdd.nunique().gt(1).any() or fixed_calendar.end_mmdd.nunique().gt(1).any():
        raise ValueError("direct fixed-primary calendar changes month/day within a state/crop")
    for flag in ["response_estimation_authorized", "scc_authorized"]:
        if strict_bool(result[flag], f"direct {flag}").any():
            raise ValueError(f"direct-weather source unexpectedly authorizes {flag}")
    if not strict_bool(
        result.feature_construction_eligible, "direct feature_construction_eligible"
    ).all():
        raise ValueError("direct-weather source contains feature-ineligible rows")
    if not strict_bool(
        result.weather_exposure_shared_across_practices,
        "direct weather_exposure_shared_across_practices",
    ).all():
        raise ValueError("direct-weather exposure is not declared shared across practices")
    crop_pixel = strict_bool(result.crop_pixel_exposure, "direct crop_pixel_exposure")
    if crop_pixel.any():
        raise ValueError("primary direct-weather input cannot claim crop-pixel exposure")
    if result.weather_source_id.astype("string").str.strip().eq("").any():
        raise ValueError("direct-weather source identity is blank")
    source = protocol["direct_source"]
    if set(result.weather_source_id.astype(str)) != {str(source["weather_source_id"])}:
        raise ValueError("direct-weather source identity differs from the locked protocol")
    if set(result.weather_grid_id.astype(str)) != {str(source["weather_grid_id"])}:
        raise ValueError("direct-weather grid identity differs from the locked protocol")
    if set(result.calendar_source_id.astype(str)) != {str(source["calendar_source_id"])}:
        raise ValueError("direct-weather calendar identity differs from the locked protocol")
    for column, key in [
        ("outcome_source_id", "outcome_source_id"),
        ("calendar_vintage", "calendar_vintage"),
        ("calendar_boundary_rule", "calendar_boundary_rule"),
        ("stage_definition", "stage_definition"),
        ("weather_day_alignment", "weather_day_alignment"),
        ("weight_role", "weight_role"),
    ]:
        values = result[column].astype("string").str.strip()
        if values.isna().any() or values.eq("").any() or set(values.astype(str)) != {
            str(source[key])
        }:
            raise ValueError(f"direct-weather {column} differs from the locked protocol")
    wet_day = pd.to_numeric(result.wet_day_threshold_mm, errors="raise").to_numpy(dtype=float)
    if not np.isfinite(wet_day).all() or not np.allclose(
        wet_day, float(source["wet_day_threshold_mm"]), rtol=0, atol=0
    ):
        raise ValueError("direct-weather wet-day threshold differs from the locked protocol")
    exposure = [
        "state", "outcome_source_id", "calendar_role", "season_start", "season_end",
        "weather_source_id", "weather_grid_id", "calendar_source_id", "calendar_vintage",
        "calendar_boundary_rule", "stage_definition", "weather_day_alignment",
        "wet_day_threshold_mm", "weight_role", "crop_pixel_exposure",
        "weather_exposure_shared_across_practices", "feature_construction_eligible",
        *controls, *moisture,
    ]
    require_shared_exposure(result, exposure, practices, "direct-weather input")
    return result.sort_values(KEYS).reset_index(drop=True)


def validate_pdsi_long(frame: pd.DataFrame, protocol: dict[str, Any]) -> pd.DataFrame:
    sample = protocol["sample"]
    crops = set(map(str, sample["crops"]))
    practices = set(map(str, sample["irrigation_practices"]))
    required = {
        *KEYS, "state", "yield_bu_acre", "outcome_source_id", "calendar_role",
        "calendar_source_id", "calendar_vintage", "boundary_rule", "stage_definition",
        "window_id", "window_start", "window_end", "index_day_weighted_mean",
        "drought_family", "monthly_value_day_weighted_not_daily_observation",
        "index_calibration_start_year", "index_calibration_end_year",
        "feature_construction_eligible", "irrigation_in_index",
        "response_estimation_authorized_pdsi", "scc_authorized_pdsi",
    }
    if missing := required - set(frame.columns):
        raise ValueError(f"PDSI join lacks {sorted(missing)}")
    result = normalize_keys(frame, "PDSI join")
    result = result.loc[
        result.outcome_crop.isin(crops)
        & result.irrigation_practice.isin(practices)
        & result.calendar_role.astype("string").eq(str(sample["calendar_role"]))
        & result.harvest_year.between(int(sample["year_min"]), int(sample["year_max"]))
    ].copy()
    if result.empty or set(result.outcome_crop) != crops or set(result.irrigation_practice) != practices:
        raise ValueError("PDSI join does not populate every locked crop/practice")
    if set(result.window_id.astype(str)) != PDSI_WINDOWS:
        raise ValueError("PDSI join does not have exactly the locked five windows")
    if result.duplicated(KEYS + ["window_id"]).any():
        raise ValueError("PDSI join duplicates outcome/window keys")
    counts = result.groupby(KEYS, observed=True).window_id.agg(set)
    if not counts.map(lambda value: value == PDSI_WINDOWS).all():
        raise ValueError("a PDSI outcome key lacks a complete window set")
    if set(result.drought_family.astype(str)) != {"pdsi"}:
        raise ValueError("PDSI input contains another moisture family")
    result["state"] = result.state.astype("string").str.strip().str.upper()
    if result.state.str.fullmatch(r"[A-Z]{2}").ne(True).any():
        raise ValueError("PDSI input contains malformed states")
    require_county_state_fips(result, "PDSI input")
    result["window_start"] = normalize_date(result.window_start, "PDSI window_start")
    result["window_end"] = normalize_date(result.window_end, "PDSI window_end")
    if (result.window_end < result.window_start).any():
        raise ValueError("PDSI input contains an invalid calendar window")
    require_exact_pdsi_calendar_windows(result)
    numeric_finite(result, ["yield_bu_acre", "index_day_weighted_mean"], "PDSI join")
    for column in [
        "state", "yield_bu_acre", "outcome_source_id", "index_source_id", "index_name",
        "index_scale_months", "index_distribution", "calendar_source_id",
        "calendar_vintage", "boundary_rule", "stage_definition",
        "index_calibration_start_year", "index_calibration_end_year",
    ]:
        counts = result.groupby(KEYS, observed=True)[column].nunique(dropna=False)
        if counts.ne(1).any():
            raise ValueError(f"PDSI {column} varies across windows for one outcome key")
    for flag in ["response_estimation_authorized_pdsi", "scc_authorized_pdsi", "irrigation_in_index"]:
        if strict_bool(result[flag], f"PDSI {flag}").any():
            raise ValueError(f"PDSI input unexpectedly sets {flag}=true")
    if not strict_bool(
        result.feature_construction_eligible, "PDSI feature_construction_eligible"
    ).all():
        raise ValueError("PDSI source contains feature-ineligible rows")
    if not strict_bool(
        result.monthly_value_day_weighted_not_daily_observation,
        "PDSI monthly index weighting flag",
    ).all():
        raise ValueError("PDSI input is not marked as monthly-index day-weighted")
    for column in ["index_source_id", "index_calibration_start_year", "index_calibration_end_year"]:
        if result[column].nunique(dropna=False) != 1:
            raise ValueError(f"PDSI {column} varies within the locked input")
    source = protocol["pdsi_source"]
    if set(result.index_source_id.astype(str)) != {str(source["index_source_id"])}:
        raise ValueError("PDSI source identity differs from the locked protocol")
    for column, key in [
        ("outcome_source_id", "outcome_source_id"),
        ("index_name", "index_name"),
        ("drought_family", "drought_family"),
        ("index_distribution", "index_distribution"),
        ("calendar_source_id", "calendar_source_id"),
        ("calendar_vintage", "calendar_vintage"),
        ("boundary_rule", "calendar_boundary_rule"),
        ("stage_definition", "stage_definition"),
    ]:
        values = result[column].astype("string").str.strip()
        if values.isna().any() or values.eq("").any() or set(values.astype(str)) != {
            str(source[key])
        }:
            raise ValueError(f"PDSI {column} differs from the locked protocol")
    scales = pd.to_numeric(result.index_scale_months, errors="raise")
    if set(scales) != {int(source["index_scale_months"])}:
        raise ValueError("PDSI scale differs from the locked protocol")
    starts = pd.to_numeric(result.index_calibration_start_year, errors="raise")
    ends = pd.to_numeric(result.index_calibration_end_year, errors="raise")
    if set(starts) != {int(source["calibration_start_year"])} or set(ends) != {
        int(source["calibration_end_year"])
    }:
        raise ValueError("PDSI calibration differs from the locked protocol")
    if int(protocol["validation"]["terminal_temporal_holdout_start"]) <= int(
        source["calibration_end_year"]
    ):
        raise ValueError("terminal temporal holdout does not begin after PDSI calibration")
    require_exact_practice_pairs(
        result.drop_duplicates(KEYS), practices, "PDSI outcome support"
    )
    return result.sort_values(KEYS + ["window_id"]).reset_index(drop=True)


def validate_calendar_source(
    frame: pd.DataFrame, protocol: dict[str, Any]
) -> pd.DataFrame:
    """Validate the bound 2010 NASS calendar rows used by this diagnostic."""
    required = {
        "state", "calendar_crop", "harvest_year", "season_start", "season_end",
        "calendar_source_id", "calendar_vintage", "calendar_role", "boundary_rule",
        "stage_definition", "feature_construction_eligible",
        "response_estimation_authorized", "scc_authorized",
    }
    if missing := required - set(frame.columns):
        raise ValueError(f"calendar input lacks {sorted(missing)}")
    sample = protocol["sample"]
    source = protocol["direct_source"]
    crops = set(map(str, sample["crops"]))
    result = frame.copy()
    result["state"] = result.state.astype("string").str.strip().str.upper()
    result["calendar_crop"] = result.calendar_crop.astype("string").str.strip()
    result["harvest_year"] = pd.to_numeric(
        result.harvest_year, errors="raise"
    ).astype("int64")
    result = result.loc[
        result.calendar_crop.isin(crops)
        & result.calendar_role.astype("string").eq(str(sample["calendar_role"]))
        & result.harvest_year.between(int(sample["year_min"]), int(sample["year_max"]))
    ].copy()
    if result.empty or set(result.calendar_crop) != crops:
        raise ValueError("calendar input does not populate every locked crop")
    valid_states = set(STATE_FIPS_TO_ALPHA.values())
    if result.state.isna().any() or (~result.state.isin(valid_states)).any():
        raise ValueError("calendar input contains an unknown postal state code")
    keys = ["state", "calendar_crop", "harvest_year"]
    if result.duplicated(keys).any():
        raise ValueError("calendar input duplicates locked state/crop/year rows")
    result["season_start"] = normalize_date(result.season_start, "calendar season_start")
    result["season_end"] = normalize_date(result.season_end, "calendar season_end")
    if (result.season_end < result.season_start).any():
        raise ValueError("calendar input contains a reversed season")
    if result.season_end.dt.year.ne(result.harvest_year).any():
        raise ValueError("calendar season_end does not match harvest_year")
    duration = result.season_end.sub(result.season_start).dt.days.add(1)
    if not duration.between(30, 500).all():
        raise ValueError("calendar crop-season duration lies outside 30..500 days")
    fixed = result.assign(
        start_mmdd=result.season_start.dt.strftime("%m-%d"),
        end_mmdd=result.season_end.dt.strftime("%m-%d"),
    ).groupby(["state", "calendar_crop"], observed=True)
    if fixed.start_mmdd.nunique().gt(1).any() or fixed.end_mmdd.nunique().gt(1).any():
        raise ValueError("bound fixed-primary calendar changes month/day within state/crop")
    for flag in ["response_estimation_authorized", "scc_authorized"]:
        if strict_bool(result[flag], f"calendar {flag}").any():
            raise ValueError(f"calendar source unexpectedly authorizes {flag}")
    if not strict_bool(
        result.feature_construction_eligible, "calendar feature_construction_eligible"
    ).all():
        raise ValueError("calendar source contains feature-ineligible rows")
    for column, expected in [
        ("calendar_source_id", source["calendar_source_id"]),
        ("calendar_vintage", source["calendar_vintage"]),
        ("boundary_rule", source["calendar_boundary_rule"]),
        ("stage_definition", source["stage_definition"]),
    ]:
        values = result[column].astype("string").str.strip()
        if values.isna().any() or values.eq("").any() or set(values.astype(str)) != {
            str(expected)
        }:
            raise ValueError(f"calendar {column} differs from the locked protocol")
    return result.sort_values(keys).reset_index(drop=True)


def require_bound_calendar(
    frame: pd.DataFrame, calendar: pd.DataFrame, label: str
) -> None:
    """Reconcile every source level row to the hash-bound calendar table."""
    calendar_keys = ["state", "outcome_crop", "harvest_year"]
    bound = calendar.rename(columns={
        "calendar_crop": "outcome_crop",
        "boundary_rule": "calendar_boundary_rule",
    })[
        calendar_keys + [
            "season_start", "season_end", "calendar_source_id", "calendar_vintage",
            "calendar_boundary_rule", "stage_definition",
        ]
    ]
    source = frame.merge(
        bound,
        on=calendar_keys,
        how="left",
        validate="many_to_one",
        suffixes=("", "_bound_calendar"),
        indicator=True,
    )
    if source._merge.ne("both").any():
        examples = source.loc[
            source._merge.ne("both"), calendar_keys
        ].drop_duplicates().head(10).to_dict("records")
        raise ValueError(f"{label} lacks bound calendar rows for {examples}")
    for column in [
        "season_start", "season_end", "calendar_source_id", "calendar_vintage",
        "calendar_boundary_rule", "stage_definition",
    ]:
        bound_column = f"{column}_bound_calendar"
        if column in {"season_start", "season_end"}:
            equal = pd.to_datetime(source[column]).eq(pd.to_datetime(source[bound_column]))
        else:
            equal = source[column].astype("string").eq(
                source[bound_column].astype("string")
            )
        if not equal.all():
            raise ValueError(f"{label} {column} differs from the bound calendar input")


def pdsi_wide(frame: pd.DataFrame, practices: set[str]) -> pd.DataFrame:
    metadata = frame.groupby(KEYS, observed=True).agg(
        state=("state", "first"),
        yield_bu_acre=("yield_bu_acre", "first"),
        outcome_source_id=("outcome_source_id", "first"),
        index_source_id=("index_source_id", "first"),
        index_name=("index_name", "first"),
        index_scale_months=("index_scale_months", "first"),
        index_distribution=("index_distribution", "first"),
        index_calibration_start_year=("index_calibration_start_year", "first"),
        index_calibration_end_year=("index_calibration_end_year", "first"),
        calendar_source_id=("calendar_source_id", "first"),
        calendar_vintage=("calendar_vintage", "first"),
        calendar_boundary_rule=("boundary_rule", "first"),
        stage_definition=("stage_definition", "first"),
    ).reset_index()
    season = frame.loc[frame.window_id.astype(str).eq("season"), KEYS + ["window_start", "window_end"]]
    if season.duplicated(KEYS).any():
        raise ValueError("PDSI input duplicates the season calendar window")
    season = season.rename(
        columns={"window_start": "season_start", "window_end": "season_end"}
    )
    metadata = metadata.merge(season, on=KEYS, how="inner", validate="one_to_one")
    wide = frame.pivot(index=KEYS, columns="window_id", values="index_day_weighted_mean").reset_index()
    wide = wide.rename(columns={window: f"pdsi_{window}_mean" for window in PDSI_WINDOWS})
    result = metadata.merge(wide, on=KEYS, how="inner", validate="one_to_one")
    predictors = [f"pdsi_{window}_mean" for window in sorted(PDSI_WINDOWS)]
    require_shared_exposure(
        result,
        [
            "state", "outcome_source_id", "index_source_id", "index_name",
            "index_scale_months", "index_distribution", "calendar_source_id",
            "calendar_vintage", "calendar_boundary_rule", "stage_definition",
            "season_start", "season_end", *predictors,
        ],
        practices,
        "PDSI input",
    )
    return result


def _unique_values(frame: pd.DataFrame, column: str) -> list[str]:
    values = frame[column].astype("string").str.strip()
    if values.isna().any() or values.eq("").any():
        raise ValueError(f"source-lineage column {column} contains blank values")
    return sorted(set(values.astype(str)))


def source_lineage(validated: pd.DataFrame, family: str) -> dict[str, Any]:
    if family == "calendar":
        return {
            "calendar_source_id": _unique_values(validated, "calendar_source_id"),
            "calendar_vintage": _unique_values(validated, "calendar_vintage"),
            "calendar_role": _unique_values(validated, "calendar_role"),
            "calendar_boundary_rule": _unique_values(validated, "boundary_rule"),
            "stage_definition": _unique_values(validated, "stage_definition"),
            "crops": sorted(set(validated.calendar_crop.astype(str))),
            "states": sorted(set(validated.state.astype(str))),
            "years": [
                int(validated.harvest_year.min()), int(validated.harvest_year.max())
            ],
            "feature_construction_eligible": True,
        }
    if family == "direct_weather":
        return {
            "outcome_source_id": _unique_values(validated, "outcome_source_id"),
            "weather_source_id": _unique_values(validated, "weather_source_id"),
            "weather_grid_id": _unique_values(validated, "weather_grid_id"),
            "calendar_source_id": _unique_values(validated, "calendar_source_id"),
            "calendar_vintage": _unique_values(validated, "calendar_vintage"),
            "calendar_role": _unique_values(validated, "calendar_role"),
            "calendar_boundary_rule": _unique_values(validated, "calendar_boundary_rule"),
            "stage_definition": _unique_values(validated, "stage_definition"),
            "weather_day_alignment": _unique_values(validated, "weather_day_alignment"),
            "weight_role": _unique_values(validated, "weight_role"),
            "wet_day_threshold_mm": sorted(
                set(pd.to_numeric(validated.wet_day_threshold_mm, errors="raise").astype(float))
            ),
            "crop_pixel_exposure": False,
        }
    if family == "pdsi":
        return {
            "outcome_source_id": _unique_values(validated, "outcome_source_id"),
            "index_source_id": _unique_values(validated, "index_source_id"),
            "index_name": _unique_values(validated, "index_name"),
            "drought_family": _unique_values(validated, "drought_family"),
            "index_scale_months": sorted(
                set(pd.to_numeric(validated.index_scale_months, errors="raise").astype(int))
            ),
            "index_distribution": _unique_values(validated, "index_distribution"),
            "index_calibration_start_year": sorted(
                set(pd.to_numeric(validated.index_calibration_start_year, errors="raise").astype(int))
            ),
            "index_calibration_end_year": sorted(
                set(pd.to_numeric(validated.index_calibration_end_year, errors="raise").astype(int))
            ),
            "calendar_source_id": _unique_values(validated, "calendar_source_id"),
            "calendar_vintage": _unique_values(validated, "calendar_vintage"),
            "calendar_role": _unique_values(validated, "calendar_role"),
            "calendar_boundary_rule": _unique_values(validated, "boundary_rule"),
            "stage_definition": _unique_values(validated, "stage_definition"),
            "monthly_value_day_weighted_not_daily_observation": True,
            "irrigation_in_index": False,
        }
    raise ValueError(f"unknown source family {family}")


def build_source_receipt(
    input_path: Path,
    family: str,
    protocol_path: Path = DEFAULT_PROTOCOL,
) -> dict[str, Any]:
    if family not in SOURCE_FAMILIES:
        raise ValueError(f"source family must be one of {sorted(SOURCE_FAMILIES)}")
    protocol = load_protocol(protocol_path)
    raw = read_table(input_path)
    if family == "calendar":
        validated = validate_calendar_source(raw, protocol)
    elif family == "direct_weather":
        validated = validate_direct(raw, protocol)
    else:
        validated = validate_pdsi_long(raw, protocol)
    return {
        "status": SOURCE_RECEIPT_STATUS,
        "protocol_id": str(protocol["protocol_id"]),
        "family": family,
        "candidate": {
            "path": str(input_path.resolve()),
            "sha256": sha256(input_path),
            "validated_rows_on_locked_sample": int(len(validated)),
        },
        "protocol": {
            "path": str(protocol_path.resolve()),
            "sha256": sha256(protocol_path),
        },
        "lineage": source_lineage(validated, family),
        "immediate_input_schema_and_lineage_recomputed": True,
        "upstream_raw_daily_monthly_or_calendar_pdf_recomputed": False,
        "predictive_fit_executed": False,
        "causal_effect_estimated": False,
        "damage_calculated": False,
        "scc_calculated": False,
    }


def validate_source_receipt(
    receipt_path: Path,
    input_path: Path,
    family: str,
    protocol_path: Path = DEFAULT_PROTOCOL,
) -> dict[str, Any]:
    try:
        candidate = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"cannot read {family} validation receipt {receipt_path}") from error
    expected = build_source_receipt(input_path, family, protocol_path)
    if candidate != expected:
        raise ValueError(
            f"{family} validation receipt differs from deterministic source validation"
        )
    return candidate


def build_inputs(
    direct_raw: pd.DataFrame,
    pdsi_raw: pd.DataFrame,
    calendar_raw: pd.DataFrame,
    protocol: dict[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    direct = validate_direct(direct_raw, protocol)
    pdsi_long = validate_pdsi_long(pdsi_raw, protocol)
    calendar = validate_calendar_source(calendar_raw, protocol)
    practices = set(map(str, protocol["sample"]["irrigation_practices"]))
    pdsi = pdsi_wide(pdsi_long, practices)
    require_bound_calendar(direct, calendar, "direct-weather input")
    require_bound_calendar(pdsi, calendar, "PDSI input")
    controls = list(map(str, protocol["features"]["common_temperature_controls"]))
    quantity = list(map(str, protocol["features"]["direct_quantity"]))
    distribution = list(map(str, protocol["features"]["direct_distribution_extension"]))
    pdsi_primary = list(map(str, protocol["features"]["pdsi_primary"]))
    pdsi_stage = list(map(str, protocol["features"]["pdsi_stage_sensitivity"]))
    pdsi_features = pdsi_primary + pdsi_stage
    if missing := set(pdsi_features) - set(pdsi.columns):
        raise ValueError(f"PDSI wide input lacks locked predictors {sorted(missing)}")

    direct_keys = pd.MultiIndex.from_frame(direct[KEYS])
    pdsi_keys = pd.MultiIndex.from_frame(pdsi[KEYS])
    common_keys = direct_keys.intersection(pdsi_keys)
    direct_common = direct.loc[direct_keys.isin(common_keys)].copy()
    pdsi_common = pdsi.loc[pdsi_keys.isin(common_keys)].copy()
    lineage = [
        "state", "outcome_source_id", "calendar_source_id", "calendar_vintage",
        "calendar_boundary_rule", "stage_definition", "season_start", "season_end",
    ]
    selected_direct = direct_common[
        KEYS + ["yield_bu_acre", *lineage, *controls, *quantity, *distribution]
    ]
    selected_pdsi = pdsi_common[KEYS + ["yield_bu_acre", *lineage, *pdsi_features]]
    levels = selected_direct.merge(
        selected_pdsi, on=KEYS, how="inner", validate="one_to_one", suffixes=("", "_pdsi")
    )
    if not np.allclose(levels.yield_bu_acre, levels.yield_bu_acre_pdsi, rtol=0, atol=1e-10):
        raise ValueError("direct-weather and PDSI inputs disagree on outcome values")
    levels = levels.drop(columns="yield_bu_acre_pdsi")
    for column in lineage:
        pdsi_column = f"{column}_pdsi"
        if pdsi_column not in levels:
            raise ValueError(f"PDSI merge lost required lineage column {column}")
        if pd.api.types.is_datetime64_any_dtype(levels[column]):
            equal = levels[column].eq(levels[pdsi_column])
        else:
            equal = levels[column].astype("string").eq(levels[pdsi_column].astype("string"))
        if not equal.all():
            raise ValueError(f"direct-weather and PDSI inputs disagree on {column}")
        levels = levels.drop(columns=pdsi_column)
    all_features = controls + quantity + distribution + pdsi_features
    require_shared_exposure(
        levels, [*lineage, *all_features], practices, "common level support"
    )

    levels = levels.sort_values(["county_geoid", "outcome_crop", "irrigation_practice", "harvest_year"])
    groups = levels.groupby(["county_geoid", "outcome_crop", "irrigation_practice"], observed=True)
    previous_year = groups.harvest_year.shift(1)
    consecutive = levels.harvest_year.sub(previous_year).eq(1)
    differenced = levels.loc[consecutive, KEYS + ["state", "yield_bu_acre", *all_features]].copy()
    differenced["difference_previous_harvest_year"] = (
        previous_year.loc[consecutive].to_numpy(dtype="int64")
    )
    if not differenced.harvest_year.sub(differenced.difference_previous_harvest_year).eq(1).all():
        raise ValueError("first-difference endpoints are not consecutive years")
    previous_yield = groups.yield_bu_acre.shift(1).loc[consecutive]
    differenced["delta_log_yield"] = np.log(differenced.yield_bu_acre) - np.log(previous_yield)
    for column in all_features:
        differenced[f"d_{column}"] = (
            levels[column].loc[consecutive].to_numpy(dtype=float)
            - groups[column].shift(1).loc[consecutive].to_numpy(dtype=float)
        )
    differenced["level_precip_mm"] = levels.loc[consecutive, "precip_mm"].to_numpy(dtype=float)
    differenced = differenced.reset_index(drop=True)

    expected_strata = {
        (crop, practice)
        for crop in map(str, protocol["sample"]["crops"])
        for practice in map(str, protocol["sample"]["irrigation_practices"])
    }
    observed_strata = set(
        map(
            tuple,
            differenced[["outcome_crop", "irrigation_practice"]]
            .drop_duplicates().itertuples(index=False, name=None),
        )
    )
    if observed_strata != expected_strata:
        raise ValueError(
            "common direct/PDSI support does not yield consecutive-year differences "
            f"for every locked crop/practice: observed={sorted(observed_strata)}"
        )

    validation = protocol["validation"]
    if str(validation["geographic_holdout_unit"]) != "state":
        raise ValueError("this locked diagnostic implements state geographic holdouts only")
    holdout_start = int(validation["terminal_temporal_holdout_start"])
    differenced["geographic_group"] = differenced.state.astype("string")
    differenced["is_temporal_holdout"] = differenced.harvest_year.ge(holdout_start)
    lower_q = float(validation["extreme_lower_quantile"])
    upper_q = float(validation["extreme_upper_quantile"])
    if not 0 < lower_q < upper_q < 1:
        raise ValueError("extreme quantiles must satisfy 0 < lower < upper < 1")
    differenced["is_precipitation_extreme"] = False
    cutoffs: dict[str, dict[str, float]] = {}
    for (crop, practice), positions in differenced.groupby(
        ["outcome_crop", "irrigation_practice"], observed=True
    ).groups.items():
        dev_positions = [i for i in positions if not bool(differenced.loc[i, "is_temporal_holdout"])]
        values = differenced.loc[dev_positions, "level_precip_mm"]
        if values.empty:
            raise ValueError(f"{crop}/{practice} has no development rows for extreme cutoffs")
        lower, upper = float(values.quantile(lower_q)), float(values.quantile(upper_q))
        if not np.isfinite([lower, upper]).all() or lower >= upper:
            raise ValueError(f"{crop}/{practice} has degenerate precipitation-extreme cutoffs")
        differenced.loc[positions, "is_precipitation_extreme"] = (
            differenced.loc[positions, "level_precip_mm"].le(lower)
            | differenced.loc[positions, "level_precip_mm"].ge(upper)
        )
        cutoffs[f"{crop}/{practice}"] = {"lower_mm": lower, "upper_mm": upper}

    minimum_rows = int(protocol["sample"]["minimum_rows_per_crop_practice"])
    minimum_counties = int(protocol["sample"]["minimum_counties_per_crop_practice"])
    minimum_test = int(validation["minimum_test_rows"])
    minimum_geographic_groups = int(validation["minimum_geographic_groups_per_crop_practice"])
    stratum_counts: dict[str, Any] = {}
    for (crop, practice), group in differenced.groupby(
        ["outcome_crop", "irrigation_practice"], observed=True
    ):
        label = f"{crop}/{practice}"
        dev = group.loc[~group.is_temporal_holdout]
        geographic_counts = dev.geographic_group.value_counts().sort_index()
        eligible_geographic = geographic_counts.loc[geographic_counts.ge(minimum_test)]
        development_counties = set(dev.county_geoid.astype(str))
        temporal = group.loc[group.is_temporal_holdout]
        temporal_common_counties = temporal.county_geoid.astype(str).isin(development_counties)
        temporal_n = int(temporal_common_counties.sum())
        temporal_unseen_county_n = int((~temporal_common_counties).sum())
        extreme_n = int((~group.is_temporal_holdout & group.is_precipitation_extreme).sum())
        if len(group) < minimum_rows or group.county_geoid.nunique() < minimum_counties:
            raise ValueError(f"{label} fails locked row/county minimums")
        if len(eligible_geographic) < minimum_geographic_groups:
            raise ValueError(f"{label} fails the minimum eligible leave-state-out groups")
        if temporal_n < minimum_test or extreme_n < minimum_test:
            raise ValueError(f"{label} fails a locked outer-test minimum")
        stratum_counts[label] = {
            "rows": int(len(group)),
            "counties": int(group.county_geoid.nunique()),
            "years": [int(group.harvest_year.min()), int(group.harvest_year.max())],
            "development_geographic_group_rows": {
                str(k): int(v) for k, v in geographic_counts.items()
            },
            "eligible_leave_state_out_groups": list(map(str, eligible_geographic.index)),
            "temporal_holdout_same_county_rows": temporal_n,
            "temporal_holdout_unseen_county_rows_excluded": temporal_unseen_county_n,
            "development_extreme_rows": extreme_n,
        }

    common_columns = KEYS + [
        "state", "difference_previous_harvest_year", "delta_log_yield",
        "geographic_group", "is_temporal_holdout", "is_precipitation_extreme",
    ] + [f"d_{column}" for column in controls]
    common = differenced[common_columns].copy()
    direct_family = differenced[KEYS + [f"d_{column}" for column in quantity + distribution]].copy()
    pdsi_family = differenced[KEYS + [f"d_{column}" for column in pdsi_features]].copy()
    for frame, family in [(direct_family, "direct_weather"), (pdsi_family, "pdsi")]:
        frame["feature_family"] = family
        frame["predictive_diagnostic_authorized"] = True
        frame["causal_claim_authorized"] = False
        frame["damage_claim_authorized"] = False
        frame["scc_claim_authorized"] = False
    common["predictive_diagnostic_authorized"] = True
    common["causal_claim_authorized"] = False
    common["damage_claim_authorized"] = False
    common["scc_claim_authorized"] = False
    for label, frame in [("common", common), ("direct", direct_family), ("pdsi", pdsi_family)]:
        if frame.duplicated(KEYS).any():
            raise ValueError(f"{label} output duplicates diagnostic keys")
        numeric_finite(
            frame,
            [column for column in frame.columns if column.startswith("d_") or column == "delta_log_yield"],
            f"{label} output",
        )

    audit: dict[str, Any] = {
        "status": "common_first_difference_inputs_constructed_not_fitted",
        "protocol_id": str(protocol["protocol_id"]),
        "direct_level_rows": int(len(direct)),
        "pdsi_level_rows": int(len(pdsi)),
        "bound_calendar_rows_on_locked_sample": int(len(calendar)),
        "all_direct_and_pdsi_level_rows_reconciled_to_bound_calendar": True,
        "common_level_rows": int(len(levels)),
        "direct_only_level_rows_dropped": int(len(direct) - len(levels)),
        "pdsi_only_level_rows_dropped": int(len(pdsi) - len(levels)),
        "common_consecutive_difference_rows": int(len(common)),
        "nonconsecutive_or_initial_rows_not_differenced": int(len(levels) - len(common)),
        "first_difference_endpoint_columns_recorded": [
            "difference_previous_harvest_year", "harvest_year"
        ],
        "split_specific_shared_endpoint_purge_pending_evaluator": True,
        "strata": stratum_counts,
        "precipitation_extreme_cutoffs_from_development_inputs_without_outcomes": cutoffs,
        "wheat_included": False,
        "moisture_families_stacked_in_any_model": False,
        "train_only_preprocessing_pending_evaluator": True,
        "contains_outcome_in_common_table_only": True,
        "predictive_fit_executed": False,
        "causal_effect_estimated": False,
        "damage_calculated": False,
        "scc_calculated": False,
        "upstream_daily_weather_recomputed_in_this_step": False,
    }
    return common.sort_values(KEYS), direct_family.sort_values(KEYS), pdsi_family.sort_values(KEYS), audit


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--direct-weather", required=True)
    parser.add_argument("--direct-validation", required=True)
    parser.add_argument("--pdsi-join", required=True)
    parser.add_argument("--pdsi-validation", required=True)
    parser.add_argument("--calendar", required=True)
    parser.add_argument("--calendar-validation", required=True)
    parser.add_argument("--protocol", default=str(DEFAULT_PROTOCOL))
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--audit-out", required=True)
    args = parser.parse_args()
    direct_path = Path(args.direct_weather)
    direct_validation_path = Path(args.direct_validation)
    pdsi_path = Path(args.pdsi_join)
    pdsi_validation_path = Path(args.pdsi_validation)
    calendar_path = Path(args.calendar)
    calendar_validation_path = Path(args.calendar_validation)
    protocol_path = Path(args.protocol)
    protocol = load_protocol(protocol_path)
    direct_receipt = validate_source_receipt(
        direct_validation_path, direct_path, "direct_weather", protocol_path
    )
    pdsi_receipt = validate_source_receipt(
        pdsi_validation_path, pdsi_path, "pdsi", protocol_path
    )
    calendar_receipt = validate_source_receipt(
        calendar_validation_path, calendar_path, "calendar", protocol_path
    )
    common, direct, pdsi, audit = build_inputs(
        read_table(direct_path), read_table(pdsi_path), read_table(calendar_path), protocol
    )
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = {
        "common": output_dir / "common_outcomes_controls_folds.parquet",
        "direct_weather": output_dir / "direct_weather.parquet",
        "pdsi": output_dir / "pdsi.parquet",
    }
    common.to_parquet(outputs["common"], index=False)
    direct.to_parquet(outputs["direct_weather"], index=False)
    pdsi.to_parquet(outputs["pdsi"], index=False)
    audit["inputs"] = {
        "direct_weather": {"path": str(direct_path), "sha256": sha256(direct_path)},
        "direct_validation": {
            "path": str(direct_validation_path),
            "sha256": sha256(direct_validation_path),
            "status": direct_receipt["status"],
        },
        "pdsi_join": {"path": str(pdsi_path), "sha256": sha256(pdsi_path)},
        "pdsi_validation": {
            "path": str(pdsi_validation_path),
            "sha256": sha256(pdsi_validation_path),
            "status": pdsi_receipt["status"],
        },
        "calendar": {"path": str(calendar_path), "sha256": sha256(calendar_path)},
        "calendar_validation": {
            "path": str(calendar_validation_path),
            "sha256": sha256(calendar_validation_path),
            "status": calendar_receipt["status"],
        },
        "protocol": {"path": str(protocol_path), "sha256": sha256(protocol_path)},
    }
    audit["outputs"] = {
        name: {"path": str(path), "sha256": sha256(path)} for name, path in outputs.items()
    }
    audit_path = Path(args.audit_out)
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        f"wrote {len(common)} common consecutive differences; no model fit, causal effect, damage, or SCC"
    )


if __name__ == "__main__":
    main()
