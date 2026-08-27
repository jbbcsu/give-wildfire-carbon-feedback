#!/usr/bin/env python3
"""Synthetic tests for FishMIP spatial-change distribution summaries."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from evaluate_fishmip_spatial_change_distribution import summarize_distribution  # noqa: E402


reference = np.array([[1.0, 2.0], [3.0, np.nan]])
future = np.array([[0.5, 2.0], [6.0, np.nan]])
support = np.array([[True, True], [True, False]])
result = summarize_distribution(reference, future, support, np.array([-60.0, 60.0]))
assert result["common_finite_grid_cells"] == 3
assert abs(result["unweighted_cell_share_lower"] - 1 / 3) < 1e-12
assert abs(result["unweighted_cell_share_higher"] - 1 / 3) < 1e-12
assert abs(result["unweighted_cell_share_exactly_unchanged"] - 1 / 3) < 1e-12
assert abs(
    result["area_weighted_cell_share_lower"]
    + result["area_weighted_cell_share_higher"]
    + result["area_weighted_cell_share_exactly_unchanged"]
    - 1
) < 1e-12

try:
    summarize_distribution(reference, future[:, :1], support, np.array([-60.0, 60.0]))
except ValueError as error:
    assert "different shapes" in str(error)
else:
    raise AssertionError("mismatched spatial arrays were accepted")

negative = future.copy()
negative[0, 0] = -1
try:
    summarize_distribution(reference, negative, support, np.array([-60.0, 60.0]))
except ValueError as error:
    assert "negative" in str(error)
else:
    raise AssertionError("negative catch density was accepted")

print("FishMIP spatial-change distribution synthetic tests passed")
