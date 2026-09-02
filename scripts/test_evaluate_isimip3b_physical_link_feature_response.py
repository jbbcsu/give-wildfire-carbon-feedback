#!/usr/bin/env python3
"""Synthetic transform and nested-holdout tests for the physical-link candidate."""
from __future__ import annotations

import tomllib
from pathlib import Path

import numpy as np
import pandas as pd

from evaluate_isimip3b_physical_link_feature_response import evaluate, inverse_response, transform_response
from evaluate_isimip3b_structural_feature_response import ESMS, FEATURES, SCENARIOS, prepare_training


root = Path(__file__).resolve().parents[1]
links = tomllib.loads((root / "config/isimip3b_physical_link_feature_response_v1.toml").read_text(encoding="utf-8"))["response_links"]
rows = []
years = {"historical": [2012, 2013, 2014], "ssp126": [2016, 2017, 2018, 2019], "ssp370": [2016, 2017, 2018, 2019], "ssp585": [2016, 2017, 2018, 2019]}
for esm_index, esm in enumerate(ESMS):
    for scenario_index, scenario in enumerate(SCENARIOS):
        for year in years[scenario]:
            gmst = 288 + esm_index * 0.1 + (year - 2012) * (0.02 + scenario_index * 0.01)
            for lon in (1.0, 2.0):
                stage = [0.0, 0.0, 0.0] if lon == 1.0 and year == years[scenario][1] else [0.2, 0.3, 0.5]
                values = {
                    "tmean_c": 20 + 0.5 * (gmst - 288),
                    "precip_mm": max(0, 20 + 2 * (gmst - 288)),
                    "wet_days_n": max(0, 5 + gmst - 288),
                    "cdd_max_days": max(0, 12 - (gmst - 288)),
                    "rx1day_mm": max(0, 4 + gmst - 288),
                    "rx5day_mm": max(0, 8 + gmst - 288),
                    "stage1_precip_share": stage[0],
                    "stage2_precip_share": stage[1],
                    "stage3_precip_share": stage[2],
                    "precipitation_timing_centroid": min(1, max(0, 0.5 + 0.01 * scenario_index)),
                    "precipitation_concentration_hhi": min(1, max(0, 0.4 + 0.01 * esm_index)),
                }
                for feature in FEATURES:
                    rows.append({
                        "esm_id": esm, "member_id": "r1", "scenario": scenario, "year": year,
                        "harvest_year": year, "lat": 1.0, "lon_360": lon, "crop": "mai", "irrigation": "noirr",
                        "gmst_value_k": gmst, "gmst_esm_id": esm, "gmst_member_id": "r1",
                        "feature_family": feature, "feature_value": values[feature],
                    })
frame = pd.DataFrame(rows)
observations, original, n_cells = prepare_training(frame)
transformed, dry = transform_response(original, n_cells, links)
assert dry > 0
reconstructed = inverse_response(transformed, n_cells, links)
assert np.isfinite(reconstructed).all()
assert (reconstructed[:, n_cells:6 * n_cells] > 0).all()
stage = np.stack([reconstructed[:, FEATURES.index(feature) * n_cells:(FEATURES.index(feature) + 1) * n_cells] for feature in FEATURES[6:9]], axis=2)
assert np.allclose(stage.sum(axis=2), 1)
holdouts = evaluate(observations, original, transformed, n_cells, links, [0.01, 0.1, 1.0])
assert len(holdouts) == 88
assert (holdouts.negative_prediction_count == 0).all()
assert (holdouts.above_one_prediction_count == 0).all()
assert holdouts.maximum_stage_composition_sum_error.max() <= 1e-12

broken = original.copy()
broken[:, FEATURES.index("stage1_precip_share") * n_cells] = 0.8
broken[:, FEATURES.index("stage2_precip_share") * n_cells] = 0.8
try:
    transform_response(broken, n_cells, links)
except ValueError as error:
    assert "sum to zero or one" in str(error), error
else:
    raise AssertionError("invalid stage composition should fail closed")

print("physical-link feature-response tests passed")
