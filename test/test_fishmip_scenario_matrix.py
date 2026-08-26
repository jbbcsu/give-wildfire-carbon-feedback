#!/usr/bin/env python3
"""Synthetic failure-mode tests for the FishMIP scenario matrix audit."""
from __future__ import annotations

import copy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from export_fishmip_scenario_matrix import FORCINGS, MODELS, SCENARIOS, robustness_summary


def fixture() -> list[dict[str, object]]:
    rows = []
    for forcing_index, forcing in enumerate(sorted(FORCINGS)):
        for scenario in sorted(SCENARIOS):
            models = []
            for model_index, model in enumerate(sorted(MODELS)):
                base = -0.1 - forcing_index * 0.01 - model_index * 0.02
                high = -0.03 if scenario == "ssp585" else 0.0
                models.append({
                    "model": model,
                    "reference_mean_density_g_m2": 1.0 + forcing_index + model_index,
                    "relative_change_from_reference": {
                        "near": base / 2 + high,
                        "mid": base + high,
                        "late": base * 2 + high,
                    },
                })
            rows.append({
                "climate_forcing": forcing,
                "climate_scenario": scenario,
                "common_finite_grid_cells": 40000 + forcing_index,
                "models": models,
            })
    return rows


rows = fixture()
summary = robustness_summary(rows)
assert summary["trajectory_count"] == 8
assert summary["negative_change_counts_out_of_8"] == {"late": 8, "mid": 8, "near": 8}
assert summary["ssp585_more_negative_than_ssp126_counts_out_of_4"] == {"late": 4, "mid": 4, "near": 4}
assert summary["absolute_model_levels_averaged"] is False

bad = copy.deepcopy(rows)
bad.pop()
try:
    robustness_summary(bad)
except ValueError as error:
    assert "factorial is incomplete" in str(error)
else:
    raise AssertionError("expected incomplete-factorial failure")

bad = copy.deepcopy(rows)
bad[1]["common_finite_grid_cells"] += 1
try:
    robustness_summary(bad)
except ValueError as error:
    assert "support differs" in str(error)
else:
    raise AssertionError("expected support-drift failure")

bad = copy.deepcopy(rows)
bad[1]["models"][0]["reference_mean_density_g_m2"] += 0.01
try:
    robustness_summary(bad)
except ValueError as error:
    assert "historical reference differs" in str(error)
else:
    raise AssertionError("expected reference-drift failure")

bad = copy.deepcopy(rows)
bad[0]["models"][0]["relative_change_from_reference"]["late"] = float("nan")
try:
    robustness_summary(bad)
except ValueError as error:
    assert "invalid reporting-period" in str(error)
else:
    raise AssertionError("expected nonfinite-change failure")

print("FishMIP scenario matrix synthetic tests passed")
