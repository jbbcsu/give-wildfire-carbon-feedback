#!/usr/bin/env python3
"""Synthetic fold-product gates for the three-ESM validator."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from evaluate_isimip3b_five_esm_holdout_smoke import FEATURES  # noqa: E402
from validate_isimip3b_two_esm_four_scenario_holdout import validate_holdout_product  # noqa: E402


holdouts = {"A", "B", "C"}
frame = pd.DataFrame([
    {
        "split_type": "esm", "holdout_id": holdout, "feature_family": feature,
        "holdout_excluded": True, "n_train": 10, "n_test": 5, "n_cells": 1,
        "gmst_slope_per_k": 0.0, "rmse": 1.0, "mae": 0.5,
        "benchmark_rmse": 1.1, "benchmark_mae": 0.6,
    }
    for holdout in sorted(holdouts) for feature in FEATURES
])
validate_holdout_product(frame, split_type="esm", expected_holdouts=holdouts)
print("three-ESM holdout validator synthetic tests passed")
