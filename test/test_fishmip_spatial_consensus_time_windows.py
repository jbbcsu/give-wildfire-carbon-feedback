#!/usr/bin/env python3
"""Synthetic gates for fixed-window FishMIP sign consensus."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "evaluate_fishmip_spatial_consensus_time_windows.py"
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location("fishmip_window_consensus", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

assert module.FUTURE_WINDOWS == ((2071, 2080), (2081, 2090), (2091, 2100))

support = np.array([[True, True], [True, False]])
latitude = np.array([-30.0, 30.0])
changes = [
    np.array([[-1.0, -1.0], [-1.0, np.nan]]),
    np.array([[-2.0, -1.0], [-1.0, np.nan]]),
    np.array([[-1.0, -1.0], [1.0, np.nan]]),
    np.array([[-1.0, 1.0], [-1.0, np.nan]]),
]
summary = module.summarize_consensus(changes, support, latitude)
assert summary["common_finite_grid_cells"] == 3
assert np.isclose(summary["unweighted_cell_share_unanimously_lower"], 1 / 3)
assert np.isclose(summary["unweighted_cell_share_at_least_three_lower"], 1.0)

try:
    module.summarize_consensus(changes[:3], support, latitude)
except ValueError as exc:
    assert "exact two-forcing by two-model matrix" in str(exc)
else:
    raise AssertionError("incomplete trajectory matrix should fail")

print("FishMIP temporal sign-consensus synthetic tests passed")
