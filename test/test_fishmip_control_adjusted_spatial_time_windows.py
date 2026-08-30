#!/usr/bin/env python3
"""Synthetic gates for control-adjusted FishMIP spatial time windows."""

from __future__ import annotations

import copy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from evaluate_fishmip_control_adjusted_spatial_time_windows import (  # noqa: E402
    FUTURE_WINDOWS,
    summarize_time_window_robustness,
)
from evaluate_fishmip_spatial_change_distribution import SCENARIOS  # noqa: E402


rows = []
for scenario_index, scenario in enumerate(SCENARIOS):
    for window_index, (start, end) in enumerate(FUTURE_WINDOWS):
        rows.append({
            "climate_scenario": scenario,
            "future_period": {"start_year": start, "end_year": end},
            "area_weighted_cell_share_at_least_three_lower": 0.4 + 0.1 * window_index + 0.02 * scenario_index,
            "area_weighted_cell_share_unanimously_lower": 0.1 + 0.05 * window_index + 0.01 * scenario_index,
        })

summary = summarize_time_window_robustness(rows)
assert [row["climate_scenario"] for row in summary] == list(SCENARIOS)
assert all(row["at_least_three_lower_is_monotone_non_decreasing"] for row in summary)
assert all(row["unanimously_lower_is_monotone_non_decreasing"] for row in summary)
assert abs(summary[0]["area_weighted_at_least_three_lower_min"] - 0.4) < 1e-12
assert abs(summary[0]["area_weighted_at_least_three_lower_max"] - 0.6) < 1e-12

bad = copy.deepcopy(rows)
bad.pop()
try:
    summarize_time_window_robustness(bad)
except ValueError:
    pass
else:
    raise AssertionError("incomplete scenario-window product passed")

bad = copy.deepcopy(rows)
bad.append(copy.deepcopy(rows[0]))
try:
    summarize_time_window_robustness(bad)
except ValueError:
    pass
else:
    raise AssertionError("duplicate scenario-window row passed")

bad = copy.deepcopy(rows)
bad[0]["area_weighted_cell_share_unanimously_lower"] = 1.1
try:
    summarize_time_window_robustness(bad)
except ValueError:
    pass
else:
    raise AssertionError("out-of-range share passed")

print("FishMIP control-adjusted spatial time-window synthetic tests passed")
