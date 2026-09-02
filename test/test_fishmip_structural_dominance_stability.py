#!/usr/bin/env python3
"""Synthetic and real-source tests for structural-dominance stability."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from evaluate_fishmip_structural_dominance_stability import BANDS, SCENARIOS, WINDOWS, evaluate  # noqa: E402


def source() -> dict[str, object]:
    cells = []
    for scenario_index, scenario in enumerate(SCENARIOS):
        for window_index, window in enumerate(WINDOWS):
            for band_index, band in enumerate(BANDS):
                climate = 2.0 if (scenario_index + window_index + band_index) % 2 == 0 else 1.0
                ecosystem = 1.0 if climate == 2.0 else 2.0
                cells.append({
                    "climate_scenario": scenario,
                    "future_period": {"start_year": window[0], "end_year": window[1]},
                    "latitude_band": band,
                    "climate_forcing_contrast_ipsl_minus_gfdl": {"root_mean_square_contrast": climate},
                    "ecosystem_model_contrast_ecoocean_minus_boats": {"root_mean_square_contrast": ecosystem},
                    "larger_rms_structural_contrast": "climate_forcing" if climate > ecosystem else "ecosystem_model",
                })
    return {
        "schema": "fishmip_structural_contrast_sensitivity_v1",
        "status": "validated_factor_contrasts_structural_sensitivity_only",
        "probability_or_variance_decomposition": False,
        "cells": cells,
    }


result = evaluate(source(), 1.25)
assert result["summary"]["materially_dominant_cells"] == 30
assert result["summary"]["scenario_pairs"] == 15
assert result["scc_authorized"] is False

broken = source()
broken["cells"].append(dict(broken["cells"][0]))
try:
    evaluate(broken, 1.25)
except ValueError as error:
    assert "cell count" in str(error), error
else:
    raise AssertionError("duplicate source cell should fail closed")

root = Path(__file__).resolve().parents[1]
real = json.loads((root / "data/provenance/fishmip_structural_contrast_sensitivity_20260901.json").read_text(encoding="utf-8"))
real_result = evaluate(real, 1.25)
assert len(real_result["cells"]) == 30
assert real_result["probability_or_variance_decomposition"] is False

print("FishMIP structural-dominance stability tests passed")
