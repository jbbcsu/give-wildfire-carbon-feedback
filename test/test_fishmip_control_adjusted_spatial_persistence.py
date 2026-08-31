#!/usr/bin/env python3
"""Synthetic gates for persistent control-adjusted FishMIP spatial signs."""

from __future__ import annotations

import copy
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from evaluate_fishmip_control_adjusted_spatial_persistence import (  # noqa: E402
    summarize_persistent_consensus,
)
from evaluate_fishmip_control_adjusted_spatial_time_windows import FUTURE_WINDOWS  # noqa: E402
from evaluate_fishmip_spatial_change_distribution import FORCINGS, MODELS, SCENARIOS  # noqa: E402


support = np.ones((1, 4), dtype=bool)
latitude = np.array([0.0])
window_changes = {}
for scenario in SCENARIOS:
    for trajectory_index, (forcing, model) in enumerate(
        (pair for forcing in FORCINGS for pair in ((forcing, MODELS[0]), (forcing, MODELS[1])))
    ):
        base = np.array([[-1.0, -1.0, -1.0, -1.0]])
        changes = [base.copy() for _ in FUTURE_WINDOWS]
        changes[-1][0, trajectory_index] = 1.0
        window_changes[(scenario, forcing, model)] = changes

summary = summarize_persistent_consensus(window_changes, support, latitude)
assert [row["climate_scenario"] for row in summary] == list(SCENARIOS)
for row in summary:
    assert abs(row["area_weighted_cell_share_unanimously_lower"] - 0.0) < 1e-12
    assert abs(row["area_weighted_cell_share_at_least_three_lower"] - 1.0) < 1e-12
    assert all(
        abs(item["area_weighted_cell_share_lower_in_every_window"] - 0.75) < 1e-12
        for item in row["trajectory_persistence"]
    )

bad = copy.deepcopy(window_changes)
bad.pop(next(iter(bad)))
try:
    summarize_persistent_consensus(bad, support, latitude)
except ValueError:
    pass
else:
    raise AssertionError("incomplete scenario/forcing/model product passed")

bad = copy.deepcopy(window_changes)
first = next(iter(bad))
bad[first] = bad[first][:-1]
try:
    summarize_persistent_consensus(bad, support, latitude)
except ValueError:
    pass
else:
    raise AssertionError("incomplete future-window product passed")

bad = copy.deepcopy(window_changes)
bad[first][0][0, 0] = np.nan
try:
    summarize_persistent_consensus(bad, support, latitude)
except ValueError:
    pass
else:
    raise AssertionError("nonfinite persistent trajectory passed")

print("FishMIP persistent control-adjusted spatial-sign synthetic tests passed")
