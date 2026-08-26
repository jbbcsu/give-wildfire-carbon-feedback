#!/usr/bin/env python3
"""Hand-check the fixed-effect residualizer and clustered OLS primitives."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from estimate_us_national_all_practice_pdsi_association import (  # noqa: E402
    alternating_residualize,
    clustered_ols,
)


rng = np.random.default_rng(20260826)
county = np.repeat(np.arange(30), 12)
year = np.tile(np.arange(12), 30)
state = county // 10
state_year = state * 12 + year
x = rng.normal(size=len(county))
county_fe = rng.normal(size=30)[county]
state_year_fe = rng.normal(size=36)[state_year]
y = 0.35 * x + county_fe + state_year_fe
values, iterations, change = alternating_residualize(
    np.column_stack([y, x]), [county, state_year], 1e-12, 1000
)
assert iterations > 0 and change <= 1e-12
for codes in [county, state_year]:
    for column in range(values.shape[1]):
        means = np.bincount(codes, weights=values[:, column]) / np.bincount(codes)
        assert np.max(np.abs(means)) < 1e-10
fit = clustered_ols(values[:, 0], values[:, 1:], county)
assert abs(float(fit["beta"][0]) - 0.35) < 1e-10
assert fit["clusters"] == 30

try:
    alternating_residualize(np.array([1.0, np.nan]), [np.array([0, 1])], 1e-10, 2)
except ValueError as error:
    assert "nonfinite" in str(error)
else:
    raise AssertionError("nonfinite residualization input was accepted")

print("national all-practice PDSI association primitive tests passed")
