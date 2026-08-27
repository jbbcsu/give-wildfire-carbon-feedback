#!/usr/bin/env python3
"""Synthetic fold-product gates for the joint holdout validator."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from evaluate_isimip3b_five_esm_holdout_smoke import FEATURES  # noqa: E402
from validate_isimip3b_two_esm_four_scenario_holdout import (  # noqa: E402
    require_summary_equal,
    validate_holdout_product,
)


def frame(split: str, holdouts: set[str]) -> pd.DataFrame:
    return pd.DataFrame([
        {
            "split_type": split,
            "holdout_id": holdout,
            "feature_family": feature,
            "holdout_excluded": True,
            "n_train": 10,
            "n_test": 5,
            "n_cells": 1,
            "gmst_slope_per_k": 0.0,
            "rmse": 1.0,
            "mae": 0.5,
            "benchmark_rmse": 1.1,
            "benchmark_mae": 0.6,
        }
        for holdout in sorted(holdouts) for feature in FEATURES
    ])


esm = frame("esm", {"A", "B"})
validate_holdout_product(esm, split_type="esm", expected_holdouts={"A", "B"})

duplicate = pd.concat([esm, esm.iloc[[0]]], ignore_index=True)
try:
    validate_holdout_product(duplicate, split_type="esm", expected_holdouts={"A", "B"})
except ValueError as error:
    assert "duplicate" in str(error)
else:
    raise AssertionError("duplicate holdout fold was accepted")

missing = esm.iloc[:-1].copy()
try:
    validate_holdout_product(missing, split_type="esm", expected_holdouts={"A", "B"})
except ValueError as error:
    assert "features changed" in str(error) or "incomplete" in str(error)
else:
    raise AssertionError("incomplete holdout fold product was accepted")

require_summary_equal({"ratio": 1.0}, {"ratio": 1.0 + 5e-13})
try:
    require_summary_equal({"ratio": 1.0}, {"ratio": 1.001})
except ValueError as error:
    assert "summary.ratio changed" in str(error)
else:
    raise AssertionError("material summary change was accepted")

print("joint holdout validator synthetic tests passed")
