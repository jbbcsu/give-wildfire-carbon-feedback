#!/usr/bin/env python3
"""Invariant tests for the national all-practice NASS/PDSI route."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd


sys.path.insert(0, str(Path(__file__).resolve().parent))
from prepare_nass_national_all_practice_pdsi import (  # noqa: E402
    build_support_features,
    eligible_support,
    filter_calendars,
    join_features,
)
from build_county_crop_calendar_drought_features import load_contract  # noqa: E402


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def panel() -> pd.DataFrame:
    return pd.DataFrame({
        "outcome_crop": ["corn_grain", "soybeans", "corn_grain"],
        "county_geoid": ["31039", "31039", "31041"],
        "state": ["NE", "NE", "NE"],
        "harvest_year": [2000, 2000, 2000],
        "irrigation_practice": ["all_practices"] * 3,
        "yield_bu_acre": [150.0, 45.0, 120.0],
        "outcome_value_eligible": [True] * 3,
        "irrigation_share_vintage": [2017] * 3,
        "irrigation_share": [0.05, pd.NA, 0.25],
        "irrigation_share_eligible": [True, False, True],
        "irrigation_share_missing_reason": ["not_missing", "suppressed_not_zero", "not_missing"],
        "rainfed_dominant_10pct": [True, False, False],
        "rainfed_dominant_20pct": [True, False, False],
        "rainfed_dominant_30pct": [True, False, True],
        "outcome_source_id": ["nass_quickstats_api_national_all_practice_1981_2019"] * 3,
        "feature_construction_authorized": [True] * 3,
        "response_estimation_authorized": [False] * 3,
        "scc_authorized": [False] * 3,
    })


def geography() -> pd.DataFrame:
    return pd.DataFrame({
        "county_geoid": ["31039", "31041"],
        "state": ["NE", "NE"],
        "tiger2019_exact_geoid_match": [True, True],
        "geometry_change_review_required": [False, True],
        "geography_gate_status": [
            "fixed_2019_proxy_no_substantial_page_hit",
            "blocked_pending_historical_boundary_resolution",
        ],
        "minor_boundary_change_caveat": [True, True],
        "feature_construction_eligible": [True, False],
        "response_estimation_authorized": [False, False],
        "scc_authorized": [False, False],
    })


def calendar() -> pd.DataFrame:
    rows = []
    for crop in ["corn_grain", "soybeans"]:
        for role in ["fixed_primary", "fixed_broad_window_sensitivity"]:
            rows.append({
                "state": "NE", "calendar_crop": crop, "harvest_year": 2000,
                "season_start": "2000-05-01", "season_end": "2000-10-01",
                "calendar_source_id": "usda_nass_field_crops_usual_dates_2010",
                "calendar_source_url": "https://example.invalid/calendar",
                "calendar_vintage": "2010", "calendar_role": role,
                "boundary_rule": "synthetic", "stage_definition": "synthetic",
                "feature_construction_eligible": True, "scc_authorized": False,
            })
    rows.append({**rows[0], "state": "IA"})
    return pd.DataFrame(rows)


def features() -> pd.DataFrame:
    rows = []
    for crop in ["corn_grain", "soybeans"]:
        for role in ["fixed_primary", "fixed_broad_window_sensitivity"]:
            for window in ["preplant90", "season", "stage1", "stage2", "stage3"]:
                rows.append({
                    "county_geoid": "31039", "state": "NE", "calendar_crop": crop,
                    "harvest_year": 2000, "calendar_role": role, "window_id": window,
                    "drought_family": "pdsi", "index_name": "nclimdiv_county_pdsi",
                    "index_scale_months": 0,
                    "index_scale_role": "stateful_palmer_index_not_fixed_accumulation",
                    "index_distribution": "palmer_water_balance",
                    "index_source_id": "noaa_nclimdiv_county_pdsi_v1_0_0_20260806",
                    "index_calibration_start_year": 1931,
                    "index_calibration_end_year": 1990,
                    "index_calibration_role": "publisher_fixed_independent_of_crop_outcomes",
                    "source_role": "historical_county_benchmark_not_future_scc_input",
                    "index_day_weighted_mean": -1.0, "index_monthly_minimum": -2.0,
                    "index_day_equivalents_at_or_below_moderate": 10,
                    "index_day_equivalents_at_or_below_severe": 0,
                    "irrigation_in_index": False,
                    "response_estimation_authorized": False, "scc_authorized": False,
                })
    return pd.DataFrame(rows)


def monthly() -> pd.DataFrame:
    dates = pd.date_range("1999-01-01", "2000-12-01", freq="MS")
    return pd.DataFrame({
        "county_geoid": ["31039"] * len(dates), "state_alpha": ["NE"] * len(dates),
        "date": dates, "year": dates.year, "month": dates.month,
        "index_value": [-1.0] * len(dates), "drought_family": ["pdsi"] * len(dates),
        "index_name": ["nclimdiv_county_pdsi"] * len(dates),
        "index_scale_months": [0] * len(dates),
        "index_scale_role": ["stateful_palmer_index_not_fixed_accumulation"] * len(dates),
        "index_distribution": ["palmer_water_balance"] * len(dates),
        "index_source_id": ["noaa_nclimdiv_county_pdsi_v1_0_0_20260806"] * len(dates),
        "index_calibration_start_year": [1931] * len(dates),
        "index_calibration_end_year": [1990] * len(dates),
        "index_calibration_role": ["publisher_fixed_independent_of_crop_outcomes"] * len(dates),
        "source_role": ["historical_county_benchmark_not_future_scc_input"] * len(dates),
        "irrigation_in_index": [False] * len(dates),
        "response_estimation_authorized": [False] * len(dates),
        "scc_authorized": [False] * len(dates),
    })


contract, _ = load_contract(PROJECT_ROOT / "config/us_county_drought_predictor_contract_v1.toml", "pdsi")
eligible, blocked = eligible_support(panel(), geography())
assert len(eligible) == 2
assert len(blocked) == 1
assert eligible.irrigation_practice.unique().tolist() == ["all_practices"]
assert eligible.loc[eligible.outcome_crop.eq("soybeans"), "irrigation_share"].isna().all()

selected = filter_calendars(calendar(), eligible, contract)
assert len(selected) == 4
assert set(selected.calendar_crop) == {"corn_grain", "soybeans"}
support_features = build_support_features(
    monthly(), selected, eligible, -2.0, -3.0, 90, [0.0, 0.3, 0.7, 1.0]
)
assert len(support_features) == 20
assert set(support_features.county_geoid) == {"31039"}
assert set(support_features.calendar_crop) == {"corn_grain", "soybeans"}
joined = join_features(eligible, support_features)
assert len(joined) == 20
assert joined["feature_family"].eq("pdsi").all()
assert joined["outcome_irrigation_interpretation"].eq("all_practices_mixture_not_direct_rainfed_yield").all()
assert not joined.response_estimation_authorized.any()
assert not joined.scc_authorized.any()

relabeled = panel().copy()
relabeled.loc[0, "irrigation_practice"] = "non_irrigated"
try:
    eligible_support(relabeled, geography())
except ValueError as error:
    assert "cannot relabel" in str(error)
else:
    raise AssertionError("national route accepted a relabeled all-practice outcome")

filled_missing_share = panel().copy()
filled_missing_share.loc[1, "irrigation_share"] = 0.0
try:
    eligible_support(filled_missing_share, geography())
except ValueError as error:
    assert "numerically filled" in str(error)
else:
    raise AssertionError("national route accepted an imputed missing irrigation share")

missing_share_reason = panel().copy()
missing_share_reason.loc[1, "irrigation_share_missing_reason"] = pd.NA
try:
    eligible_support(missing_share_reason, geography())
except ValueError as error:
    assert "explicit reason" in str(error)
else:
    raise AssertionError("national route accepted a missing irrigation-share reason")

stacked = features().assign(precip_total_mm=100.0)
try:
    join_features(eligible, stacked)
except ValueError as error:
    assert "stacked" in str(error)
else:
    raise AssertionError("national PDSI route accepted stacked precipitation")

stacked_internal = features().assign(stage1_tmean_c=25.0)
try:
    join_features(eligible, stacked_internal)
except ValueError as error:
    assert "stacked" in str(error)
else:
    raise AssertionError("national PDSI route accepted embedded direct temperature")

leaked_outcome = features().assign(lagged_yield_bu_acre=100.0)
try:
    join_features(eligible, leaked_outcome)
except ValueError as error:
    assert "outcome" in str(error)
else:
    raise AssertionError("national PDSI route accepted an outcome column")

extra_support = pd.concat([
    features(),
    features().loc[features().calendar_crop.eq("corn_grain")].assign(county_geoid="31043"),
], ignore_index=True)
try:
    join_features(eligible, extra_support)
except ValueError as error:
    assert "outcome-key support" in str(error)
else:
    raise AssertionError("national PDSI route silently ignored extra outcome-key support")

wrong_panel_state = panel().copy()
wrong_panel_state.loc[0, "state"] = "IA"
try:
    eligible_support(wrong_panel_state, geography())
except ValueError as error:
    assert "does not match" in str(error)
else:
    raise AssertionError("national route accepted a panel/geography state mismatch")

wrong_pdsi_state = monthly().copy()
wrong_pdsi_state["state_alpha"] = "IA"
try:
    build_support_features(
        wrong_pdsi_state, selected, eligible, -2.0, -3.0, 90, [0.0, 0.3, 0.7, 1.0]
    )
except ValueError as error:
    assert "monthly PDSI state" in str(error)
else:
    raise AssertionError("national route accepted a PDSI/outcome state mismatch")

wrong_vintage = panel().copy()
wrong_vintage["irrigation_share_vintage"] = 2022
try:
    eligible_support(wrong_vintage, geography())
except ValueError as error:
    assert "fixed-2017" in str(error)
else:
    raise AssertionError("national route accepted a nonlocked irrigation-share vintage")

authorized_features = features().copy()
authorized_features["response_estimation_authorized"] = True
try:
    join_features(eligible, authorized_features)
except ValueError as error:
    assert "authorize" in str(error)
else:
    raise AssertionError("national PDSI route masked an upstream authorization flag")

irrigated_index = features().copy()
irrigated_index["irrigation_in_index"] = True
try:
    join_features(eligible, irrigated_index)
except ValueError as error:
    assert "irrigation_in_index" in str(error)
else:
    raise AssertionError("national PDSI route accepted an index claiming irrigation input")

wrong_calibration = features().copy()
wrong_calibration["index_calibration_end_year"] = 2019
try:
    join_features(eligible, wrong_calibration)
except ValueError as error:
    assert "index_calibration_end_year" in str(error)
else:
    raise AssertionError("national PDSI route accepted changed calibration metadata")

wrong_window = features().copy()
wrong_window.loc[wrong_window.window_id.eq("stage3"), "window_id"] = "stage4"
try:
    join_features(eligible, wrong_window)
except ValueError as error:
    assert "calendar-role/window" in str(error)
else:
    raise AssertionError("national PDSI route accepted an unregistered window set")

bad_geography = geography().copy()
bad_geography.loc[0, "geography_gate_status"] = "unreviewed_proxy"
try:
    eligible_support(panel(), bad_geography)
except ValueError as error:
    assert "unregistered fixed-proxy" in str(error)
else:
    raise AssertionError("national route accepted an unregistered geography proxy")

print("national all-practice NASS/PDSI route tests passed")
