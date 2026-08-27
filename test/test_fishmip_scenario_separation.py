#!/usr/bin/env python3
"""Synthetic gates for the FishMIP annual scenario-separation audit."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from evaluate_fishmip_scenario_separation import (  # noqa: E402
    YEARS,
    persistence_summary,
    weighted_mean,
)


values = np.linspace(0.02, -0.20, len(YEARS))
summary = persistence_summary(values)
assert summary["year_count"] == 86
assert summary["ssp585_lower_than_ssp126_years"] > 0
assert summary["longest_consecutive_ssp585_lower_years"] >= 10
assert summary["first_ten_consecutive_ssp585_lower_start_year"] is not None
assert set(summary["normalized_difference_period_means"]) == {"near", "mid", "late"}

support = np.array([[True, False], [True, True]])
weights = np.array([[1.0, 1.0], [0.5, 0.5]])
field = np.array([[2.0, np.nan], [4.0, 6.0]])
assert abs(weighted_mean(field, support, weights) - 3.5) < 1e-12

try:
    persistence_summary(np.zeros(len(YEARS) - 1))
except ValueError as error:
    assert "wrong length" in str(error)
else:
    raise AssertionError("wrong-length annual series was accepted")

bad = field.copy()
bad[0, 0] = np.nan
try:
    weighted_mean(bad, support, weights)
except ValueError as error:
    assert "nonfinite" in str(error)
else:
    raise AssertionError("nonfinite supported value was accepted")

print("FishMIP scenario-separation synthetic tests passed")
