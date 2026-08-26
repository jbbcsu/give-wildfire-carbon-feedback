#!/usr/bin/env python3
"""Synthetic tests for harvested-area and conditional-production support audit."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd


PROJECT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "audit_mirca_welfare_support",
    PROJECT / "scripts" / "audit_mirca_welfare_support.py",
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def make_weights() -> pd.DataFrame:
    rows = []
    for lat, total, irrigated in ((0.25, 100.0, 20.0), (0.75, 300.0, 0.0), (1.25, 600.0, 600.0)):
        rainfed = total - irrigated
        for regime, area in (("firr", irrigated), ("noirr", rainfed)):
            rows.append(
                {
                    "lat": lat,
                    "lon_360": 0.25,
                    "crop": "mai",
                    "irrigation": regime,
                    "area_share": area / total,
                    "share_year": 2000,
                    "irrigated_area_ha": irrigated,
                    "rainfed_area_ha": rainfed,
                    "total_area_ha": total,
                    "production_eligible": True,
                    "season_specific_share": True,
                    "weight_source_id": "synthetic_mirca_2000",
                    "source_role": MODULE.REQUIRED_SOURCE_ROLE,
                }
            )
    return pd.DataFrame(rows)


weights = make_weights()
panel = pd.DataFrame(
    [
        {"harvest_year": 1982, "lat": 0.25, "lon_360": 0.25, "crop": "mai", "yield_observed": True},
        {"harvest_year": 1983, "lat": 0.25, "lon_360": 0.25, "crop": "mai", "yield_observed": True},
        {"harvest_year": 1982, "lat": 0.75, "lon_360": 0.25, "crop": "mai", "yield_observed": False},
        {"harvest_year": 1982, "lat": 1.75, "lon_360": 0.25, "crop": "mai", "yield_observed": True},
    ]
)
baseline = pd.DataFrame(
    [
        {"lat": 0.25, "lon_360": 0.25, "yield_t_ha": 2.0},
        {"lat": 0.75, "lon_360": 0.25, "yield_t_ha": 3.0},
        {"lat": 1.25, "lon_360": 0.25, "yield_t_ha": None},
    ]
)

audit = MODULE.audit_support(weights, [panel], {"mai": baseline}, 2000)
summary = audit["crop_summaries"][0]
assert summary["observed_cells"] == 2
assert summary["matched_mirca_cells"] == 1
assert summary["unmatched_observed_cells"] == 1
assert summary["observed_crop_grid_years"] == 3
assert summary["matched_crop_grid_years"] == 2
assert summary["consecutive_observed_pairs"] == 1
assert summary["consecutive_pairs_with_mirca_support"] == 1
assert summary["cells_with_consecutive_observed_pair"] == 1
assert summary["consecutive_pair_cells_with_mirca_support"] == 1
area = summary["harvested_area"]
assert area["global_mirca_area_ha"] == 1000.0
assert area["area_in_panel_observed_cells_ha"] == 100.0
assert area["coverage_fraction"] == 0.1
assert area["irrigated_area_coverage_fraction"] == 20.0 / 620.0
assert area["rainfed_area_coverage_fraction"] == 80.0 / 380.0
assert area["consecutive_pair_area_coverage_fraction"] == 0.1
production = summary["conditional_production_proxy"]
assert production["mirca_area_with_baseline_yield_ha"] == 400.0
assert production["mirca_area_with_baseline_yield_fraction"] == 0.4
assert production["conditional_total_tonnes"] == 1100.0
assert production["conditional_tonnes_in_panel_observed_cells"] == 200.0
assert production["conditional_coverage_fraction"] == 200.0 / 1100.0
assert production["conditional_consecutive_pair_coverage_fraction"] == 200.0 / 1100.0
assert not production["proxy_defined_for_all_positive_mirca_area"]
assert not production["global_observed_production_coverage_identified"]
assert not summary["revenue_coverage"]["identified"]
assert not audit["scc_authorized"]

bad_area = weights.copy()
bad_area.loc[0, "total_area_ha"] = 101.0
try:
    MODULE.audit_support(bad_area, [panel], {"mai": baseline}, 2000)
except ValueError as error:
    assert "must equal total_area_ha" in str(error)
else:
    raise AssertionError("Inconsistent area components were accepted")

bad_yield = baseline.copy()
bad_yield.loc[0, "yield_t_ha"] = -1.0
try:
    MODULE.audit_support(weights, [panel], {"mai": bad_yield}, 2000)
except ValueError as error:
    assert "negative" in str(error)
else:
    raise AssertionError("Negative baseline yield was accepted")

try:
    MODULE.audit_support(weights, [panel], {"mai": baseline}, 2005)
except ValueError as error:
    assert "must equal" in str(error)
else:
    raise AssertionError("Misaligned baseline and share years were accepted")

try:
    MODULE.audit_support(weights, [panel], {}, 2000)
except ValueError as error:
    assert "must match panel crops exactly" in str(error)
else:
    raise AssertionError("Missing baseline-yield input was accepted")

print("MIRCA welfare-support synthetic tests passed")
