#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import tomllib

from evaluate_isimip3b_rimex_dependence_pool_decision import summarize


root = Path(__file__).resolve().parents[1]
config = tomllib.loads((root / "config/isimip3b_rimex_dependence_pool_decision_v1.toml").read_text(encoding="utf-8"))
esms = config["matrix"]["expected_esms"]
scenarios = config["matrix"]["expected_scenarios"]
missing = {("MRI-ESM2-0", "ssp585"), *(('UKESM1-0-LL', scenario) for scenario in scenarios)}
identities = [(esm, scenario) for esm in esms for scenario in scenarios if (esm, scenario) not in missing]

stability = {esm: esm != "MRI-ESM2-0" for esm in esms if esm != "UKESM1-0-LL"}
result = summarize(identities, config, represented_stability_passed=False, mri_instability_resolved=False, esm_stability=stability)
assert result["decision"] == "no_pool_permitted_for_dependence_fit"
assert result["permitted_pool_count"] == 0
assert result["pooled_pool"]["current_templates"] == 88
assert result["pooled_pool"]["current_template_count_gate_passed"] is True
assert result["pooled_pool"]["complete_balanced_matrix_gate_passed"] is False
assert result["esm_conditional_structurally_sufficient_under_frozen_design"] is False
assert result["minimum_additional_distinct_templates_needed_per_complete_esm_pool"] == 27
assert [row["current_templates"] for row in result["esm_conditional_pools"]] == [24, 24, 24, 16, 0]
assert all(row["permitted_for_dependence_fit"] is False for row in result["esm_conditional_pools"])
assert [row["stability_evidence_gate_resolved"] for row in result["esm_conditional_pools"]] == [True, True, True, False, False]

complete = [(esm, scenario) for esm in esms for scenario in scenarios]
complete_result = summarize(complete, config | {"matrix": config["matrix"] | {"completed_templates_required": 120}}, True, True, {esm: True for esm in esms})
assert complete_result["pooled_pool"]["permitted_for_dependence_fit"] is True
assert all(row["permitted_for_dependence_fit"] is False for row in complete_result["esm_conditional_pools"])

print("dependence pool decision evaluator tests passed")
