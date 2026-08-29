#!/usr/bin/env python3
"""Synthetic contract and arithmetic tests for FishMIP factorial sensitivity."""
from __future__ import annotations

import copy
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from evaluate_fishmip_factorial_sensitivity import FORCINGS, MODELS, PERIODS, SCENARIOS, evaluate


def fixture() -> dict[str, object]:
    benchmarks = []
    for forcing_index, forcing in enumerate(FORCINGS):
        for scenario_index, scenario in enumerate(SCENARIOS):
            models = []
            for model_index, model in enumerate(MODELS):
                changes = {
                    period: -0.1 * (period_index + 1) + 0.01 * forcing_index + 0.08 * model_index - 0.02 * scenario_index
                    for period_index, period in enumerate(PERIODS)
                }
                models.append({"model": model, "relative_change_from_reference": changes})
            benchmarks.append({
                "climate_forcing": forcing,
                "climate_scenario": scenario,
                "models": models,
            })
    return {
        "schema": "fishmip_scenario_benchmark_matrix_v1",
        "status": "validated_biophysical_scenario_diagnostic_only",
        "benchmarks": benchmarks,
        "observed_catch": False,
        "matched_co2_pulse": False,
        "welfare_estimated": False,
        "damage_estimated": False,
        "scc_authorized": False,
    }


result = evaluate(fixture())
assert result["scenario_period_cells"] == 6
assert result["ecosystem_contrast_dominance_cells"] == 6
assert all(abs(row["difference_in_differences"]) < 1e-12 for row in result["rows"])
assert result["absolute_model_levels_averaged"] is False
assert result["scc_authorized"] is False

bad = fixture()
bad["benchmarks"].pop()
try:
    evaluate(bad)
except ValueError as error:
    assert "exact forcing/scenario/model/period factorial" in str(error)
else:
    raise AssertionError("incomplete factorial passed")

bad = fixture()
bad["scc_authorized"] = True
try:
    evaluate(bad)
except ValueError as error:
    assert "opens scc_authorized" in str(error)
else:
    raise AssertionError("opened SCC gate passed")

bad = copy.deepcopy(fixture())
bad["benchmarks"][0]["models"][0]["relative_change_from_reference"]["late"] = float("nan")
try:
    evaluate(bad)
except ValueError as error:
    assert "nonfinite" in str(error)
else:
    raise AssertionError("nonfinite relative change passed")

print("FishMIP factorial sensitivity synthetic tests passed")
