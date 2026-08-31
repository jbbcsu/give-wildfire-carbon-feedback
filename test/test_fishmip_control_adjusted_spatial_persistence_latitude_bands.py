#!/usr/bin/env python3
"""Synthetic gates for persistent FishMIP signs by latitude band."""

from __future__ import annotations

import copy
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from evaluate_fishmip_control_adjusted_spatial_persistence_latitude_bands import (  # noqa: E402
    persistent_band_results,
)
from evaluate_fishmip_control_adjusted_spatial_time_windows import FUTURE_WINDOWS  # noqa: E402
from evaluate_fishmip_spatial_change_distribution import FORCINGS, MODELS, SCENARIOS  # noqa: E402


latitude = np.array([-60.0, -30.0, 0.0, 30.0, 60.0])
support = np.ones((5, 2), dtype=bool)
window_changes = {}
for scenario in SCENARIOS:
    for forcing in FORCINGS:
        for model in MODELS:
            base = np.full(support.shape, -1.0)
            window_changes[(scenario, forcing, model)] = [base.copy() for _ in FUTURE_WINDOWS]

first_trajectory = (SCENARIOS[0], FORCINGS[0], MODELS[0])
for change in window_changes[first_trajectory]:
    change[2, :] = 1.0

rows = persistent_band_results(window_changes, support, latitude)
assert len(rows) == len(SCENARIOS) * 5
first_tropics = next(
    row for row in rows
    if row["climate_scenario"] == SCENARIOS[0] and row["latitude_band"] == "tropics"
)
assert np.isclose(first_tropics["area_weighted_cell_share_unanimously_lower"], 0.0)
assert np.isclose(first_tropics["area_weighted_cell_share_at_least_three_lower"], 1.0)
for scenario in SCENARIOS:
    scenario_rows = [row for row in rows if row["climate_scenario"] == scenario]
    assert sum(int(row["common_finite_grid_cells"]) for row in scenario_rows) == int(support.sum())
    assert np.isclose(
        sum(float(row["area_weighted_share_of_global_common_support"]) for row in scenario_rows),
        1.0,
    )

bad = copy.deepcopy(window_changes)
bad.pop(next(iter(bad)))
try:
    persistent_band_results(bad, support, latitude)
except ValueError:
    pass
else:
    raise AssertionError("incomplete trajectory product passed")

bad = copy.deepcopy(window_changes)
bad[first_trajectory] = bad[first_trajectory][:-1]
try:
    persistent_band_results(bad, support, latitude)
except ValueError:
    pass
else:
    raise AssertionError("incomplete future-window product passed")

print("FishMIP persistent latitude-band synthetic tests passed")
