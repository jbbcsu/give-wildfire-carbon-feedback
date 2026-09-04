#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from audit_fishmip_robust_scenario_pair_stability import BANDS, SCENARIOS, WINDOWS, audit  # noqa: E402


metric_cells = []
dominance_cells = []
for scenario in SCENARIOS:
    for window in WINDOWS:
        for band in BANDS:
            axis = "climate_forcing"
            metric_agreement = not (scenario == "ssp585" and band == "north_high")
            material = not (scenario == "ssp126" and band == "south_high")
            metric_cells.append({
                "climate_scenario": scenario,
                "future_period": {"start_year": window[0], "end_year": window[1]},
                "latitude_band": band,
                "rms": {"larger_axis": axis},
                "larger_axis_agrees_across_metrics": metric_agreement,
            })
            dominance_cells.append({
                "climate_scenario": scenario,
                "future_period": {"start_year": window[0], "end_year": window[1]},
                "latitude_band": band,
                "larger_rms_structural_contrast": axis,
                "material_dominance_at_fixed_ratio": material,
            })

metric = {
    "preferred_metric_selected": False,
    "probability_or_variance_decomposition": False,
    "scc_authorized": False,
    "cells": metric_cells,
}
dominance = {
    "material_dominance_ratio_threshold": 1.25,
    "probability_or_variance_decomposition": False,
    "scc_authorized": False,
    "cells": dominance_cells,
}

with tempfile.TemporaryDirectory() as temporary:
    metric_path = Path(temporary) / "metric.json"
    dominance_path = Path(temporary) / "dominance.json"
    metric_path.write_text(json.dumps(metric), encoding="utf-8")
    dominance_path.write_text(json.dumps(dominance), encoding="utf-8")
    result = audit(metric_path, dominance_path)
    assert result["scenario_pairs"] == 15
    assert result["both_scenarios_metric_agreeing_and_materially_dominant"] == 9
    assert result["both_robust_and_same_axis_across_scenarios"] == 9
    assert result["robust_scenario_stable_axis_counts"] == {"climate_forcing": 9, "ecosystem_model": 0}
    assert result["common_structural_axis_selected"] is False

print("FishMIP robust scenario-pair stability tests passed")
