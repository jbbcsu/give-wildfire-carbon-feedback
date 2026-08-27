#!/usr/bin/env python3
"""Synthetic summary gates for the generic whole-scenario holdout smoke."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from evaluate_isimip3b_scenario_holdout_smoke import summarize_holdouts  # noqa: E402


frame = pd.DataFrame([
    {"holdout_id": "historical", "feature_family": "precip_mm", "rmse": 1.0, "benchmark_rmse": 2.0},
    {"holdout_id": "ssp126", "feature_family": "precip_mm", "rmse": 3.0, "benchmark_rmse": 2.0},
])
summary = summarize_holdouts(frame)
assert summary["comparison_count"] == 2
assert summary["gmst_model_better_than_cell_mean_count"] == 1
assert summary["scenario_summaries"]["historical"]["gmst_model_better_count"] == 1

bad = frame.copy()
bad.loc[0, "benchmark_rmse"] = 0.0
try:
    summarize_holdouts(bad)
except ValueError as error:
    assert "invalid" in str(error)
else:
    raise AssertionError("zero benchmark error was accepted")

print("generic ISIMIP3b scenario-holdout synthetic tests passed")
