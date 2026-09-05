#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import tomllib

from evaluate_isimip3b_rimex_template_compatibility_distinctness import maximum_nonoverlapping_centers, summarize


assert maximum_nonoverlapping_centers(list(range(2042, 2050)), 10) == [2042]
assert maximum_nonoverlapping_centers([2000, 2020, 2021], 10) == [2000, 2021]

root = Path(__file__).resolve().parents[1]
config = tomllib.loads((root / "config/isimip3b_rimex_template_compatibility_distinctness_v2.toml").read_text(encoding="utf-8"))
inventory = json.loads((root / "data/provenance/isimip3b_rimex_contiguous_completed_matrix_audit_20260903.json").read_text(encoding="utf-8"))
result = summarize(inventory, config)
assert result["compatible_inventory"]["nominal_centered_templates"] == 88
assert result["compatible_inventory"]["maximum_pairwise_nonoverlapping_templates"] == 11
assert result["compatible_inventory"]["complete_design_nominal_centered_templates"] == 120
assert result["compatible_inventory"]["complete_design_maximum_pairwise_nonoverlapping_templates"] == 15
assert result["incompatible_candidate_products"]["compatible_centered_multicrop_regime_templates_contributed"] == 0
assert result["complete_design_whole_esm_holdout_nonoverlap_upper_bound"] == 12
assert result["complete_design_whole_scenario_holdout_nonoverlap_upper_bound"] == 10
assert result["current_upper_bound_shortfall"] == 40
assert result["complete_design_upper_bound_shortfall"] == 36
assert result["current_upper_bound_gate_passed"] is False
assert result["complete_design_upper_bound_gate_passed"] is False
assert result["decision"] == "no_compatible_pool_meets_locked_distinct_template_minimum"

print("corrected template compatibility/distinctness evaluator tests passed")
