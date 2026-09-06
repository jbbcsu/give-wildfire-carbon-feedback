#!/usr/bin/env python3
"""Synthetic tamper tests for the saved moisture/Tmax artifact audit."""
from __future__ import annotations

from copy import deepcopy
import json

from validate_moisture_tmax_artifact import ARTIFACT, PROJECT, validate_data, validate_path


original = json.loads(ARTIFACT.read_text(encoding="utf-8"))
result = validate_path(ARTIFACT, PROJECT)
assert result["metric_rows_total"] == 240
assert result["comparison_summaries_total"] == 8
assert result["maximum_absolute_summary_reconciliation_error"] <= 1e-12
assert result["promotion_states"]["baseline"]["soybeans/non_irrigated"] is True
assert result["promotion_states"]["additional_stage_tmax"]["soybeans/non_irrigated"] is False


def expect_failure(mutator, message: str) -> None:
    candidate = deepcopy(original)
    mutator(candidate)
    try:
        validate_data(candidate, PROJECT)
    except ValueError:
        return
    raise AssertionError(f"accepted tamper: {message}")


expect_failure(lambda value: value.update(causal_or_scc_result=True), "top-level authorization")
expect_failure(lambda value: value.update(code_sha256="0" * 64), "source hash")
expect_failure(lambda value: value["results"]["baseline"]["metrics"].pop(), "metric support")
expect_failure(lambda value: value["results"]["baseline"]["metrics"][0].update(design_rank=1), "rank")
expect_failure(lambda value: value["results"]["baseline"]["metrics"][0].update(test_rows=1), "sample consistency")
expect_failure(
    lambda value: value["results"]["additional_stage_tmax"]["metrics"][0].update(
        feature_count_excluding_year_terms=value["results"]["additional_stage_tmax"]["metrics"][0]["feature_count_excluding_year_terms"] - 1
    ),
    "added feature count",
)
expect_failure(
    lambda value: value["results"]["additional_stage_tmax"]["comparison_summaries"][0].update(
        direct_distribution_mean_leave_state_out_rmse_improvement=99.0
    ),
    "summary arithmetic",
)
expect_failure(
    lambda value: value["results"]["baseline"].update(causal_effect_estimated=True),
    "result authorization",
)

print("moisture/Tmax artifact audit tamper tests passed")
