#!/usr/bin/env python3
"""Invariant tests for the data-only paired-practice NASS/PDSI join."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd


sys.path.insert(0, str(Path(__file__).resolve().parent))
from join_nass_pdsi_features import join_panel  # noqa: E402


def panel() -> pd.DataFrame:
    rows = []
    for crop, geoid, state, year in [
        ("corn_grain", "08001", "CO", 2000),
        ("soybeans", "20001", "KS", 2000),
        ("wheat_all_classes", "16001", "ID", 2000),
    ]:
        for practice, value in [("irrigated", 100.0), ("non_irrigated", 60.0)]:
            rows.append({
                "outcome_crop": crop, "county_geoid": geoid, "state": state,
                "harvest_year": year, "irrigation_practice": practice,
                "yield_bu_acre": value, "outcome_source_id": "test_nass",
                "feature_construction_eligible": False,
                "response_estimation_authorized": False, "scc_authorized": False,
            })
    return pd.DataFrame(rows)


def geography() -> pd.DataFrame:
    return pd.DataFrame({
        "county_geoid": ["08001", "20001", "16001"],
        "state": ["CO", "KS", "ID"],
        "geography_gate_status": ["stable", "stable", "stable"],
        "feature_construction_eligible": [True, False, True],
        "response_estimation_authorized": [False] * 3,
        "scc_authorized": [False] * 3,
    })


def features() -> pd.DataFrame:
    rows = []
    for geoid, state, crop in [
        ("08001", "CO", "corn_grain"),
        ("16001", "ID", "winter_wheat"),
        ("16001", "ID", "spring_wheat"),
        ("16001", "ID", "durum_wheat"),
    ]:
        for role in ["fixed_primary", "fixed_broad_window_sensitivity"]:
            for window in ["stage1", "season"]:
                rows.append({
                    "county_geoid": geoid, "state": state, "calendar_crop": crop,
                    "harvest_year": 2000, "calendar_role": role, "window_id": window,
                    "window_days": 100, "index_day_weighted_mean": -1.0,
                    "index_monthly_minimum": -2.0,
                    "index_day_equivalents_at_or_below_moderate": 20,
                    "index_day_equivalents_at_or_below_severe": 0,
                    "monthly_index_days_covered": 100, "drought_family": "pdsi",
                    "index_name": "nclimdiv_county_pdsi", "index_source_id": "test_pdsi",
                    "index_scale_months": 0, "index_distribution": "palmer_water_balance",
                    "calendar_source_id": "test_calendar",
                    "monthly_value_day_weighted_not_daily_observation": True,
                    "response_estimation_authorized": False, "scc_authorized": False,
                })
    return pd.DataFrame(rows)


joined, audit = join_panel(panel(), geography(), features())
assert audit["input_paired_crop_county_years"] == 3
assert audit["geography_eligible_paired_crop_county_years"] == 2
assert audit["geography_blocked_paired_crop_county_years"] == 1
assert audit["direct_calendar_paired_crop_county_years"] == 1
assert audit["all_wheat_paired_crop_county_years"] == 1
assert audit["all_wheat_calendar_candidate_pair_counts"] == {
    "durum_wheat": 1, "spring_wheat": 1, "winter_wheat": 1,
}
assert len(joined) == 32  # 2 practices * 4 calendar routes * 2 roles * 2 windows
assert set(joined.feature_family) == {"pdsi"}
assert not joined.response_estimation_authorized.any()
assert not joined.scc_authorized.any()

contaminated = features().assign(drought_family="spei")
try:
    join_panel(panel(), geography(), contaminated)
except ValueError as error:
    assert "PDSI-only" in str(error)
else:
    raise AssertionError("PDSI join accepted a SPEI feature family")

broken = panel().loc[lambda frame: ~(
    frame.outcome_crop.eq("corn_grain") & frame.irrigation_practice.eq("irrigated")
)].copy()
try:
    join_panel(broken, geography(), features())
except ValueError as error:
    assert "exact practice pairs" in str(error)
else:
    raise AssertionError("PDSI join accepted an incomplete practice pair")

print("paired-practice NASS/PDSI join tests passed")
