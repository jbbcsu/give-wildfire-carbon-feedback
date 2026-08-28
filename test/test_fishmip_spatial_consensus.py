#!/usr/bin/env python3
"""Synthetic checks for FishMIP cross-matrix spatial sign consensus."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from evaluate_fishmip_spatial_consensus import summarize_consensus  # noqa: E402


support = np.array([[True, True, True], [True, False, True]])
latitude = np.array([-30.0, 30.0])
changes = [
    np.array([[-1.0, -1.0, 1.0], [-1.0, np.nan, 1.0]]),
    np.array([[-1.0, -1.0, -1.0], [-1.0, np.nan, 1.0]]),
    np.array([[-1.0, 1.0, -1.0], [-1.0, np.nan, 1.0]]),
    np.array([[-1.0, 1.0, -1.0], [-1.0, np.nan, 1.0]]),
]
result = summarize_consensus(changes, support, latitude)
assert result["common_finite_grid_cells"] == 5
assert abs(result["unweighted_cell_share_unanimously_lower"] - 0.4) < 1e-12
assert abs(sum(result["unweighted_cell_share_by_lower_trajectory_count"].values()) - 1.0) < 1e-12
assert abs(sum(result["area_weighted_cell_share_by_lower_trajectory_count"].values()) - 1.0) < 1e-12

try:
    summarize_consensus(changes[:3], support, latitude)
except ValueError:
    pass
else:
    raise AssertionError("incomplete trajectory matrix should fail")

bad = [array.copy() for array in changes]
bad[0][0, 0] = np.nan
try:
    summarize_consensus(bad, support, latitude)
except ValueError:
    pass
else:
    raise AssertionError("nonfinite common-support change should fail")

print("FishMIP spatial consensus synthetic tests passed")
