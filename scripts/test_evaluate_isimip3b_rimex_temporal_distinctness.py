#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import tomllib

from evaluate_isimip3b_rimex_temporal_distinctness import maximum_nonoverlapping_centers, summarize


assert maximum_nonoverlapping_centers([2012, 2013, 2014], 10) == [2012]
assert maximum_nonoverlapping_centers([2016, 2019, 2042, 2049, 2092, 2099], 10) == [2016, 2042, 2092]
assert maximum_nonoverlapping_centers([2000, 2020, 2021], 10) == [2000, 2021]

root = Path(__file__).resolve().parents[1]
config = tomllib.loads((root / "config/isimip3b_rimex_temporal_distinctness_v1.toml").read_text(encoding="utf-8"))
result = summarize(config)
assert result["nominal_exact_label_counts"] == {"future_only": 300, "historical": 15, "historical_augmented": 315}
assert result["permissive_pairwise_nonoverlap_upper_bounds"] == {
    "future_only": 45,
    "historical": 5,
    "historical_augmented_diagnostic": 50,
    "whole_esm_holdout_future_training": 36,
    "whole_scenario_holdout_future_training": 30,
}
assert result["future_only_shortfall"] == 6
assert result["historical_augmented_diagnostic_shortfall"] == 1
assert result["future_only_upper_bound_gate_passed"] is False
assert result["historical_augmented_diagnostic_gate_passed"] is False
assert result["whole_esm_holdout_future_training_gate_passed"] is False
assert result["whole_scenario_holdout_future_training_gate_passed"] is False
assert result["decision"] == "no_pool_meets_locked_distinct_template_minimum"

print("temporal distinctness evaluator tests passed")
