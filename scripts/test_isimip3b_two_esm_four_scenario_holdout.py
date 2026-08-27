#!/usr/bin/env python3
"""Synthetic summary gates for the joint ESM/scenario holdout audit."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from evaluate_isimip3b_two_esm_four_scenario_holdout import summarize  # noqa: E402


esm = pd.DataFrame([
    {"split_type": "esm", "holdout_id": "A", "rmse": 1.0, "benchmark_rmse": 2.0},
    {"split_type": "esm", "holdout_id": "B", "rmse": 3.0, "benchmark_rmse": 2.0},
])
scenario = pd.DataFrame([
    {"split_type": "scenario", "holdout_id": "historical", "rmse": 1.5, "benchmark_rmse": 2.0},
    {"split_type": "scenario", "holdout_id": "ssp126", "rmse": 2.5, "benchmark_rmse": 2.0},
])
result = summarize(esm, scenario)
assert result["esm"]["comparisons"] == 2
assert result["esm"]["gmst_model_better_count"] == 1
assert result["scenario"]["gmst_model_better_count"] == 1

bad = scenario.copy()
bad["split_type"] = "esm"
try:
    summarize(esm, bad)
except ValueError as error:
    assert "split identity" in str(error)
else:
    raise AssertionError("wrong scenario split identity was accepted")

print("joint two-ESM/four-scenario holdout synthetic tests passed")
