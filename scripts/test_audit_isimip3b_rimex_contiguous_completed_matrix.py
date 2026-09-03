#!/usr/bin/env python3
from audit_isimip3b_rimex_contiguous_completed_matrix import summarize


identities = [
    ("GFDL-ESM4", scenario) for scenario in ("ssp126", "ssp370", "ssp585")
] + [
    ("IPSL-CM6A-LR", scenario) for scenario in ("ssp126", "ssp370", "ssp585")
] + [
    ("MPI-ESM1-2-HR", scenario) for scenario in ("ssp126", "ssp370", "ssp585")
] + [
    ("MRI-ESM2-0", scenario) for scenario in ("ssp126", "ssp370")
]

result = summarize(identities)
assert result["completed_dataset_cells"] == 11
assert result["completed_templates"] == 88
assert result["minimum_training_templates_across_represented_holdouts"] == 56
assert result["all_represented_holdouts_clear_minimum"] is True
assert result["whole_esm_holdouts"]["MRI-ESM2-0"] == {"test_templates": 16, "training_templates": 72}
assert result["whole_esm_holdouts"]["UKESM1-0-LL"] == {"test_templates": 0, "training_templates": 88}
assert result["whole_scenario_holdouts"]["ssp585"] == {"test_templates": 24, "training_templates": 64}
assert result["missing_dataset_cells"] == [
    {"esm": "MRI-ESM2-0", "scenario": "ssp585"},
    {"esm": "UKESM1-0-LL", "scenario": "ssp126"},
    {"esm": "UKESM1-0-LL", "scenario": "ssp370"},
    {"esm": "UKESM1-0-LL", "scenario": "ssp585"},
]
assert result["balanced_five_esm_three_scenario_matrix_complete"] is False
assert result["response_damage_or_scc_authorized"] is False
print("completed contiguous matrix inventory tests passed")
