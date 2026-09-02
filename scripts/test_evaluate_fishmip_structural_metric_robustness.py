#!/usr/bin/env python3
"""Synthetic tests for FishMIP structural-metric robustness."""
from __future__ import annotations

import copy

from evaluate_fishmip_structural_contrast_sensitivity import contrast_summary
from evaluate_fishmip_structural_metric_robustness import summarize_cell


def cell(ecosystem: list[float], climate: list[float]) -> dict[str, object]:
    ecosystem_summary = contrast_summary(ecosystem)
    climate_summary = contrast_summary(climate)
    return {
        "climate_scenario": "ssp126",
        "future_period": {"start_year": 2021, "end_year": 2030},
        "latitude_band": "tropics",
        "ecosystem_model_contrast_ecoocean_minus_boats": ecosystem_summary,
        "climate_forcing_contrast_ipsl_minus_gfdl": climate_summary,
        "larger_rms_structural_contrast": "ecosystem_model" if ecosystem_summary["root_mean_square_contrast"] > climate_summary["root_mean_square_contrast"] else "climate_forcing",
    }


stable = summarize_cell(cell([4.0, 4.0], [2.0, 2.0]))
assert stable["larger_axis_agrees_across_metrics"] is True
assert stable["rms"]["larger_axis"] == "ecosystem_model"

changing = summarize_cell(cell([5.0, 0.0], [3.0, 3.0]))
assert changing["rms"]["larger_axis"] == "ecosystem_model"
assert changing["mean_absolute"]["larger_axis"] == "climate_forcing"
assert changing["larger_axis_agrees_across_metrics"] is False

tampered = cell([4.0, 4.0], [2.0, 2.0])
tampered = copy.deepcopy(tampered)
tampered["ecosystem_model_contrast_ecoocean_minus_boats"]["mean_absolute_contrast"] = 99.0
try:
    summarize_cell(tampered)
except ValueError as error:
    assert "mean-absolute" in str(error)
else:
    raise AssertionError("tampered contrast summary was accepted")

print("FishMIP structural metric robustness tests passed")
