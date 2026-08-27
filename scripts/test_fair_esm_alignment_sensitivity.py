#!/usr/bin/env python3
"""Synthetic checks for the bounded FAIR-to-ESM alignment sensitivity."""
from __future__ import annotations

import pandas as pd

from evaluate_fair_esm_alignment_sensitivity import (
    CONFIG_ROLE,
    CONFIG_SCHEMA,
    aligned_feature,
    fit_affine_surface,
    support,
    temperature_support_horizons,
    validate_method_equivalence,
)


assert CONFIG_SCHEMA == "fair_esm_alignment_sensitivity_config_v1"
assert "not_production_feature_response_damage_or_scc" in CONFIG_ROLE
assert support(-1.0, 0.0, 1.0) == "below"
assert support(0.0, 0.0, 1.0) == "within"
assert support(1.0, 0.0, 1.0) == "within"
assert support(2.0, 0.0, 1.0) == "above"

intercept, slope = fit_affine_surface([280.0, 281.0, 282.0], [10.0, 12.0, 14.0])
assert abs(intercept + slope * 281.0 - 12.0) < 1e-12
absolute = aligned_feature("absolute_anomaly_mapping", 1.5, 1.0, 281.0, intercept, slope)
centered = aligned_feature("centered_coordinate_mapping", 1.5, 1.0, 281.0, intercept, slope)
assert absolute == centered

rows = []
for method in ("absolute_anomaly_mapping", "centered_coordinate_mapping"):
    rows.append({
        "alignment_method": method,
        "esm_id": "esm",
        "member_id": "member",
        "year": 2021,
        "feature_family": "rain",
        "pulse_scale": 0.0001,
        "baseline_temperature_k": 281.0,
        "pulse_temperature_k": 281.1,
        "baseline_feature": 12.0,
        "pulse_feature": 12.2,
        "direct_difference": 0.2,
        "centered_difference": 0.2,
        "baseline_support": "within",
        "pulse_support": "within",
        "baseline_temperature_support": "within",
        "pulse_temperature_support": "within",
    })
frame = pd.DataFrame(rows)
assert validate_method_equivalence(frame, 1e-12) == 0.0
broken = frame.copy()
broken.loc[broken["alignment_method"] == "centered_coordinate_mapping", "pulse_feature"] += 0.01
try:
    validate_method_equivalence(broken, 1e-12)
except ValueError as error:
    assert "disagree" in str(error)
else:
    raise AssertionError("expected method-equivalence failure")

horizon_rows = []
for year, state in ((2020, "below"), (2021, "within"), (2022, "above")):
    horizon_rows.append({
        "alignment_method": "absolute_anomaly_mapping",
        "pulse_size_gtc": 0.0,
        "esm_id": "esm",
        "year": year,
        "baseline_temperature_support": state,
    })
horizon = temperature_support_horizons(pd.DataFrame(horizon_rows))[0]
assert horizon == {
    "esm_id": "esm",
    "first_within_year": 2021,
    "last_within_year": 2021,
    "within_year_count": 1,
    "last_below_year": 2020,
    "first_above_year": 2022,
}

print("FAIR-to-ESM alignment sensitivity synthetic tests passed")
