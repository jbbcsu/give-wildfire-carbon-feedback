#!/usr/bin/env python3
"""Synthetic gates for control-adjusted FishMIP spatial summaries."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from evaluate_fishmip_control_adjusted_spatial_consensus import (  # noqa: E402
    normalized_control_adjusted_change,
    summarize_adjusted_change,
)


latitude = np.array([-30.0, 30.0])
support = np.array([[True, True], [True, False]])
forced_reference = np.array([[2.0, 2.0], [2.0, np.nan]])
forced_future = np.array([[1.5, 2.5], [1.5, np.nan]])
control_reference = np.array([[1.0, 1.0], [1.0, np.nan]])
control_future = np.array([[0.9, 1.2], [0.9, np.nan]])

change, global_summary = normalized_control_adjusted_change(
    forced_reference, forced_future, control_reference, control_future, support, latitude
)
expected = np.array([[-0.15, 0.05], [-0.15, np.nan]])
assert np.allclose(change[support], expected[support])
assert abs(global_summary["difference_in_relative_changes"] + 1.0 / 12.0) < 1e-12
summary = summarize_adjusted_change(change, support, latitude)
assert summary["common_finite_grid_cells"] == 3
assert abs(summary["unweighted_cell_share_lower"] - 2.0 / 3.0) < 1e-12
assert abs(
    summary["area_weighted_cell_share_lower"]
    + summary["area_weighted_cell_share_higher"]
    + summary["area_weighted_cell_share_exactly_unchanged"]
    - 1.0
) < 1e-12

bad = forced_future.copy()
bad[0, 0] = -1.0
try:
    normalized_control_adjusted_change(
        forced_reference, bad, control_reference, control_future, support, latitude
    )
except ValueError:
    pass
else:
    raise AssertionError("negative catch density passed")

try:
    summarize_adjusted_change(change, np.zeros_like(support), latitude)
except ValueError:
    pass
else:
    raise AssertionError("empty support passed")

print("FishMIP control-adjusted spatial-consensus synthetic tests passed")
