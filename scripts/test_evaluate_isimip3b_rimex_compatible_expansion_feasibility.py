#!/usr/bin/env python3
from __future__ import annotations

from evaluate_isimip3b_rimex_compatible_expansion_feasibility import summarize


result = summarize(member_tracks=7, scenarios=3, windows=4, maximum_members_per_family=2, minimum=51)
assert result["design"]["total_compatible_templates"] == 84
assert result["design"]["esm_families_at_least"] == 4
assert abs(result["design"]["largest_esm_family_member_share"] - 2 / 7) < 1e-15
assert result["holdout_training_templates"] == {
    "whole_esm_member": 72,
    "worst_case_whole_esm_family": 60,
    "whole_scenario": 56,
}
assert all(result["holdout_gates_strictly_exceed_minimum"].values())
assert result["six_track_minimality_check"] == {
    "whole_scenario_training_templates": 48,
    "worst_case_whole_esm_family_training_templates": 48,
    "whole_scenario_strict_gate_passed": False,
    "worst_case_whole_esm_family_strict_gate_passed": False,
}

weak_family_cap = summarize(member_tracks=7, scenarios=3, windows=4, maximum_members_per_family=3, minimum=51)
assert weak_family_cap["holdout_training_templates"]["worst_case_whole_esm_family"] == 48
assert weak_family_cap["holdout_gates_strictly_exceed_minimum"]["worst_case_whole_esm_family"] is False

print("compatible expansion feasibility evaluator tests passed")
