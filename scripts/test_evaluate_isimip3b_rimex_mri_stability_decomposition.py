#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import tomllib

import pandas as pd

from evaluate_isimip3b_rimex_mri_stability_decomposition import PAIR_COLUMN, summarize


root = Path(__file__).resolve().parents[1]
config = tomllib.loads((root / "config/isimip3b_rimex_mri_stability_decomposition_v1.toml").read_text(encoding="utf-8"))
esms = ["GFDL-ESM4", "IPSL-CM6A-LR", "MPI-ESM1-2-HR", "MRI-ESM2-0"]
scenarios = ["ssp126", "ssp370", "ssp585"]
years = list(range(2042, 2050))

template_records = []
for esm in esms:
    available = scenarios[:2] if esm == "MRI-ESM2-0" else scenarios
    for scenario in available:
        correlation = 0.18 if esm == "MRI-ESM2-0" else {"ssp126": 0.0, "ssp370": 0.4, "ssp585": -0.5}[scenario]
        for year in years:
            template_records.append({"esm": esm, "scenario": scenario, "center_year": year, PAIR_COLUMN: correlation})
templates = pd.DataFrame(template_records)

cell_records = []
for row in template_records:
    for crop in config["sample"]["crops_required"]:
        for irrigation in config["sample"]["irrigation_regimes_required"]:
            cell_records.append({**row, "crop": crop, "irrigation": irrigation, "rows": 100})
cells = pd.DataFrame(cell_records)

synthetic = dict(config)
synthetic["method"] = dict(config["method"])
synthetic["method"]["locked_original_failure_difference"] = 0.18
result = summarize(templates, cells, synthetic)
assert result["full_sample_reproduction"]["absolute_difference"] == 0.18
assert abs(result["scenario_matched_primary"]["absolute_difference"] - 0.02) < 1e-12
assert result["scenario_imbalance_sufficient_to_explain_locked_failure"] is True
assert len(result["shared_scenario_diagnostics"]) == 2
assert len(result["center_year_diagnostics"]) == 8
assert len(result["crop_regime_diagnostics"]) == 12

try:
    summarize(templates.iloc[:-1], cells, synthetic)
except ValueError as error:
    assert "template value count changed" in str(error)
else:
    raise AssertionError("incomplete template table passed")

print("MRI dependence-failure decomposition evaluator tests passed")
