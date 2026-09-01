#!/usr/bin/env python3
"""Synthetic nested-holdout tests for the structural feature-response evaluator."""
from __future__ import annotations

import numpy as np
import pandas as pd

from evaluate_isimip3b_structural_feature_response import ESMS, FEATURES, SCENARIOS, evaluate, prepare_training


rows = []
years = {"historical": [2012, 2013, 2014], "ssp126": [2016, 2017, 2018, 2019], "ssp370": [2016, 2017, 2018, 2019], "ssp585": [2016, 2017, 2018, 2019]}
for esm_index, esm in enumerate(ESMS):
    member = "r1"
    for scenario_index, scenario in enumerate(SCENARIOS):
        for year in years[scenario]:
            gmst = 288 + esm_index * 0.1 + (year - 2012) * (0.02 + scenario_index * 0.01)
            for lon in (1.0, 2.0):
                for feature_index, feature in enumerate(FEATURES):
                    value = 2 + feature_index + lon + 0.5 * (gmst - 288) + 0.1 * scenario_index
                    rows.append({
                        "esm_id": esm, "member_id": member, "scenario": scenario, "year": year,
                        "harvest_year": year, "lat": 1.0, "lon_360": lon, "crop": "mai", "irrigation": "noirr",
                        "gmst_value_k": gmst, "gmst_esm_id": esm, "gmst_member_id": member,
                        "feature_family": feature, "feature_value": value,
                    })
frame = pd.DataFrame(rows)
observations, response, n_cells = prepare_training(frame)
assert n_cells == 2
holdouts = evaluate(observations, response, n_cells, [0.01, 0.1, 1.0])
assert len(holdouts) == 88
assert np.isfinite(holdouts[["rmse", "benchmark_rmse", "rmse_ratio_to_cell_mean"]].to_numpy()).all()
assert set(holdouts.holdout_type) == {"whole_esm", "whole_scenario"}

broken = frame.iloc[:-1]
try:
    prepare_training(broken)
except ValueError as error:
    assert "not rectangular" in str(error), error
else:
    raise AssertionError("missing feature-cell row should fail closed")

print("structural feature-response nested holdout tests passed")
