#!/usr/bin/env python3
"""Exact validation for the U.S. conditional paired-loss sensitivity."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Iterator

import numpy as np

from build_us_competing_moisture_inputs import sha256
from evaluate_us_competing_moisture_paired_loss_uncertainty import (
    BASE_PROTOCOL_ID,
    CONTRACT_ID,
    EXPECTED_ARTIFACT_IDS,
    EXPECTED_COMPARISONS,
    FALSE_GATES,
    PROJECT_ROOT,
    STATE_COMPARISON_ID,
    _artifact_registry,
    _project_relative,
    _reject_sensitive_payload,
    evaluate_sensitivity,
    load_sensitivity_config,
)


EVALUATOR_PATH = PROJECT_ROOT / (
    "us_county_validation/scripts/"
    "evaluate_us_competing_moisture_paired_loss_uncertainty.py"
)
TEST_PATH = PROJECT_ROOT / (
    "us_county_validation/scripts/"
    "test_us_competing_moisture_paired_loss_uncertainty.py"
)
EXPECTED_TOP_LEVEL_FIELDS = {
    "schema_version",
    "contract_id",
    "status",
    "config_file",
    "config_sha256",
    "base_protocol_id",
    "base_artifacts",
    "base_exact_validation_recomputed",
    "base_independent_audit_clear",
    "registered_point_metric_rows_recomputed",
    "all_registered_point_metrics_match",
    "registered_solver",
    "registered_solver_scores_reconstructed_exactly_in_memory",
    "identical_endpoint_purged_splits_recomputed",
    "all_models_share_exact_test_support_within_each_fit",
    "score_basis",
    "development_pooling",
    "resampling_scheme",
    "resampling_unit",
    "bootstrap_replicates",
    "random_seed",
    "seed_derivation",
    "interval_probabilities",
    "minimum_occupied_counties_per_report",
    "maximum_county_test_row_share",
    "state_specific_scope",
    "observation_weighting",
    "training_refit_within_bootstrap",
    "frozen_distribution_promotion_rule_revised",
    "frozen_distribution_promotion_outcomes_revised",
    "model_selection_rule",
    "cluster_diagnostics",
    "cluster_diagnostic_count",
    "state_specific_omissions",
    "state_specific_omission_count",
    "comparisons",
    "comparison_count",
    "post_hoc_support_sensitivity_authorized",
    "post_hoc_support_sensitivity_role",
    "post_hoc_support_selection_uses_outcome_values",
    "post_hoc_support_sensitivity_changes_primary_protocol",
    "post_hoc_support_sensitivity_changes_promotion_decision",
    "post_hoc_support_bootstrap_performed",
    "post_hoc_support_diagnostics",
    "post_hoc_support_diagnostic_count",
    "post_hoc_support_comparisons",
    "post_hoc_support_comparison_count",
    "post_hoc_ranking_flip_count_across_metric_comparisons",
    "uncertainty_scope",
    "unsupported_uncertainty",
    "dependence_boundary",
    "predictive_fit_authorized",
    "families_stacked",
    "coefficients_emitted",
    "row_predictions_emitted",
    "row_losses_emitted",
    "bootstrap_draws_emitted",
    *FALSE_GATES,
}


def _walk(value: Any, prefix: str = "") -> Iterator[tuple[str, Any]]:
    if isinstance(value, dict):
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            yield path, child
            yield from _walk(child, path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _walk(child, f"{prefix}[{index}]")


def _require_finite_and_relative(value: Any) -> None:
    for path, child in _walk(value):
        if isinstance(child, float) and not np.isfinite(child):
            raise ValueError(f"candidate contains a nonfinite value at {path}")
        if isinstance(child, str) and Path(child).is_absolute():
            raise ValueError(f"candidate contains an absolute path at {path}")


def _finite_number(value: Any, label: str) -> float:
    if type(value) not in (int, float) or not np.isfinite(value):
        raise ValueError(f"{label} must be a finite number")
    return float(value)


def _check_difference_row(row: dict[str, Any], with_intervals: bool) -> None:
    common_fields = {
        "comparison_id",
        "candidate_model_id",
        "reference_model_id",
        "sign_convention",
        "test_row_count",
        "candidate_rmse",
        "reference_rmse",
        "rmse_difference",
        "candidate_mae",
        "reference_mae",
        "mae_difference",
    }
    if row.get("sign_convention") != (
        "candidate_minus_reference_negative_favors_candidate_on_loss"
    ):
        raise ValueError("paired-loss sign convention differs")
    if not isinstance(row.get("test_row_count"), int) or row["test_row_count"] <= 0:
        raise ValueError("paired-loss test row count is invalid")
    for metric in ("rmse", "mae"):
        candidate = _finite_number(row.get(f"candidate_{metric}"), f"candidate {metric}")
        reference = _finite_number(row.get(f"reference_{metric}"), f"reference {metric}")
        difference = _finite_number(row.get(f"{metric}_difference"), f"{metric} difference")
        if candidate < 0 or reference < 0 or not np.isclose(
            difference, candidate - reference, rtol=1e-12, atol=1e-14
        ):
            raise ValueError("paired-loss point arithmetic differs")
        if with_intervals:
            interval = row.get(f"{metric}_interval")
            if not isinstance(interval, dict) or set(interval) != {"lower", "upper"}:
                raise ValueError("paired-loss interval schema differs")
            lower = _finite_number(interval["lower"], f"{metric} lower interval")
            upper = _finite_number(interval["upper"], f"{metric} upper interval")
            if lower > upper:
                raise ValueError("paired-loss interval bounds are reversed")
    expected = common_fields | ({"rmse_interval", "mae_interval"} if with_intervals else set())
    identity = {
        "report_id",
        "crop",
        "irrigation_practice",
        "report_scope",
        "split_id",
        "test_support_sha256",
    }
    if with_intervals and set(row) != expected | identity:
        raise ValueError("paired county-bootstrap comparison row schema differs")


def _check_result_structure(result: dict[str, Any], config: dict[str, Any]) -> None:
    if set(result) != EXPECTED_TOP_LEVEL_FIELDS:
        raise ValueError(
            "candidate top-level schema differs: "
            f"missing={sorted(EXPECTED_TOP_LEVEL_FIELDS - set(result))}, "
            f"extra={sorted(set(result) - EXPECTED_TOP_LEVEL_FIELDS)}"
        )
    _reject_sensitive_payload(result)
    _require_finite_and_relative(result)
    if result.get("schema_version") != 1 or result.get("contract_id") != CONTRACT_ID:
        raise ValueError("candidate sensitivity contract differs")
    if result.get("status") != "completed_conditional_paired_predictive_loss_sensitivity":
        raise ValueError("candidate sensitivity status differs")
    if result.get("base_protocol_id") != BASE_PROTOCOL_ID:
        raise ValueError("candidate base protocol identity differs")
    exact_true = (
        "base_exact_validation_recomputed",
        "base_independent_audit_clear",
        "all_registered_point_metrics_match",
        "registered_solver_scores_reconstructed_exactly_in_memory",
        "identical_endpoint_purged_splits_recomputed",
        "all_models_share_exact_test_support_within_each_fit",
        "predictive_fit_authorized",
        "post_hoc_support_sensitivity_authorized",
    )
    for field in exact_true:
        if result.get(field) is not True:
            raise ValueError(f"candidate true gate differs: {field}")
    exact_false = (
        "training_refit_within_bootstrap",
        "frozen_distribution_promotion_rule_revised",
        "frozen_distribution_promotion_outcomes_revised",
        "families_stacked",
        "coefficients_emitted",
        "row_predictions_emitted",
        "row_losses_emitted",
        "bootstrap_draws_emitted",
        "post_hoc_support_selection_uses_outcome_values",
        "post_hoc_support_sensitivity_changes_primary_protocol",
        "post_hoc_support_sensitivity_changes_promotion_decision",
        "post_hoc_support_bootstrap_performed",
        *FALSE_GATES,
    )
    for field in exact_false:
        if result.get(field) is not False:
            raise ValueError(f"candidate false gate differs: {field}")
    exact_config_fields = (
        "score_basis",
        "development_pooling",
        "resampling_scheme",
        "resampling_unit",
        "bootstrap_replicates",
        "random_seed",
        "seed_derivation",
        "interval_probabilities",
        "minimum_occupied_counties_per_report",
        "maximum_county_test_row_share",
        "state_specific_scope",
        "observation_weighting",
        "model_selection_rule",
    )
    for field in exact_config_fields:
        if result.get(field) != config[field]:
            raise ValueError(f"candidate {field} differs from config")
    if result.get("registered_point_metric_rows_recomputed") != 120:
        raise ValueError("candidate does not bind all 120 registered fits")
    if result.get("registered_solver") != (
        "numpy_lstsq_with_registered_relative_svd_cutoff"
    ):
        raise ValueError("candidate registered solver identity differs")

    registry = _artifact_registry(config)
    artifacts = result.get("base_artifacts")
    if not isinstance(artifacts, dict) or set(artifacts) != set(EXPECTED_ARTIFACT_IDS):
        raise ValueError("candidate base artifact registry differs")
    for identifier in EXPECTED_ARTIFACT_IDS:
        if artifacts[identifier] != {
            "path": registry[identifier]["path"],
            "sha256": registry[identifier]["sha256"],
        }:
            raise ValueError(f"candidate base artifact binding differs for {identifier}")

    diagnostics = result.get("cluster_diagnostics")
    if not isinstance(diagnostics, list) or len(diagnostics) != 26:
        raise ValueError("candidate county-cluster diagnostic product is incomplete")
    if result.get("cluster_diagnostic_count") != len(diagnostics):
        raise ValueError("candidate county-cluster diagnostic count differs")
    diagnostic_fields = {
        "report_id",
        "crop",
        "irrigation_practice",
        "report_scope",
        "split_id",
        "source_states",
        "source_state_count",
        "test_support_sha256",
        "bootstrap_seed",
        "test_row_count",
        "occupied_county_count",
        "effective_county_count_inverse_herfindahl",
        "maximum_county_test_row_share",
        "minimum_county_test_row_count",
        "median_county_test_row_count",
        "maximum_county_test_row_count",
    }
    diagnostics_by_id: dict[str, dict[str, Any]] = {}
    for index, row in enumerate(diagnostics):
        if not isinstance(row, dict) or set(row) != diagnostic_fields:
            raise ValueError("candidate county-cluster diagnostic schema differs")
        report_id = row.get("report_id")
        if not isinstance(report_id, str) or report_id in diagnostics_by_id:
            raise ValueError("candidate report identity is missing or duplicated")
        diagnostics_by_id[report_id] = row
        if row.get("bootstrap_seed") != config["random_seed"] + index:
            raise ValueError("candidate bootstrap seed derivation differs")
        if row.get("occupied_county_count", 0) < config[
            "minimum_occupied_counties_per_report"
        ]:
            raise ValueError("candidate reports too few occupied county clusters")
        if row.get("maximum_county_test_row_share", 1) > config[
            "maximum_county_test_row_share"
        ]:
            raise ValueError("candidate maximum county test-row share gate fails")
        if row.get("test_row_count", 0) <= 0 or row.get(
            "effective_county_count_inverse_herfindahl", 0
        ) <= 0:
            raise ValueError("candidate county-cluster support is invalid")
        if row.get("source_state_count") != len(row.get("source_states", [])):
            raise ValueError("candidate source state count differs")
        if not re.fullmatch(r"[0-9a-f]{64}", str(row.get("test_support_sha256", ""))):
            raise ValueError("candidate test support hash is malformed")

    comparison_rows = result.get("comparisons")
    if not isinstance(comparison_rows, list) or len(comparison_rows) != 62:
        raise ValueError("candidate paired comparison product is incomplete")
    if result.get("comparison_count") != len(comparison_rows):
        raise ValueError("candidate paired comparison count differs")
    comparisons_by_report: dict[str, list[dict[str, Any]]] = {}
    identities: set[tuple[str, str]] = set()
    all_ids = {item[0] for item in EXPECTED_COMPARISONS}
    for row in comparison_rows:
        if not isinstance(row, dict):
            raise ValueError("candidate paired comparison is not an object")
        _check_difference_row(row, with_intervals=True)
        report_id = str(row["report_id"])
        if report_id not in diagnostics_by_id:
            raise ValueError("candidate comparison lacks cluster diagnostics")
        diagnostic = diagnostics_by_id[report_id]
        for field in (
            "crop",
            "irrigation_practice",
            "report_scope",
            "split_id",
            "test_support_sha256",
            "test_row_count",
        ):
            if row[field] != diagnostic[field]:
                raise ValueError(f"candidate comparison/diagnostic mismatch at {field}")
        identity = (report_id, str(row["comparison_id"]))
        if identity in identities:
            raise ValueError("candidate comparison identity is duplicated")
        identities.add(identity)
        comparisons_by_report.setdefault(report_id, []).append(row)
    for report_id, rows in comparisons_by_report.items():
        scope = diagnostics_by_id[report_id]["report_scope"]
        observed_ids = {str(row["comparison_id"]) for row in rows}
        expected_ids = (
            {STATE_COMPARISON_ID}
            if scope == "state_specific_development_oof"
            else all_ids
        )
        if observed_ids != expected_ids:
            raise ValueError("candidate report comparison registry differs")

    omissions = result.get("state_specific_omissions")
    if not isinstance(omissions, list) or len(omissions) != 2:
        raise ValueError("candidate state-specific omission product differs")
    if result.get("state_specific_omission_count") != len(omissions):
        raise ValueError("candidate state-specific omission count differs")
    omission_fields = {
        "crop",
        "irrigation_practice",
        "report_scope",
        "state",
        "test_row_count",
        "occupied_county_count",
        "minimum_required_counties",
        "reason",
    }
    for row in omissions:
        if set(row) != omission_fields:
            raise ValueError("candidate state-specific omission schema differs")
        if row["occupied_county_count"] >= row["minimum_required_counties"]:
            raise ValueError("candidate omits a state with adequate county clusters")
        if row["minimum_required_counties"] != config[
            "minimum_occupied_counties_per_report"
        ]:
            raise ValueError("candidate state omission uses a different county floor")
        if row["reason"] != "below_locked_minimum_occupied_counties_not_reported":
            raise ValueError("candidate state omission reason differs")

    post_diagnostics = result.get("post_hoc_support_diagnostics")
    if not isinstance(post_diagnostics, list) or len(post_diagnostics) != 8:
        raise ValueError("candidate post hoc support diagnostics are incomplete")
    if result.get("post_hoc_support_diagnostic_count") != len(post_diagnostics):
        raise ValueError("candidate post hoc support diagnostic count differs")
    post_diagnostic_fields = {
        "crop",
        "irrigation_practice",
        "report_scope",
        "split_id",
        "selection_rule",
        "selection_uses_outcome_values",
        "endpoint_years",
        "test_row_count",
        "rows_removed_from_primary_terminal",
        "support_identical_to_primary_terminal",
        "occupied_county_count",
        "effective_county_count_inverse_herfindahl",
        "below_locked_bootstrap_minimum_counties",
        "paired_interval_reported",
        "test_support_sha256",
    }
    post_diagnostics_by_key: dict[tuple[str, str, str], dict[str, Any]] = {}
    for row in post_diagnostics:
        if not isinstance(row, dict) or set(row) != post_diagnostic_fields:
            raise ValueError("candidate post hoc support diagnostic schema differs")
        if row["selection_uses_outcome_values"] is not False:
            raise ValueError("candidate post hoc support selection uses outcomes")
        if row["paired_interval_reported"] is not False:
            raise ValueError("candidate post hoc support check emits an interval")
        below = row["occupied_county_count"] < config[
            "minimum_occupied_counties_per_report"
        ]
        if row["below_locked_bootstrap_minimum_counties"] is not below:
            raise ValueError("candidate post hoc county-floor diagnostic differs")
        key = (row["crop"], row["irrigation_practice"], row["report_scope"])
        if key in post_diagnostics_by_key:
            raise ValueError("candidate post hoc support diagnostic is duplicated")
        post_diagnostics_by_key[key] = row

    post_rows = result.get("post_hoc_support_comparisons")
    if not isinstance(post_rows, list) or len(post_rows) != 32:
        raise ValueError("candidate post hoc point comparison product is incomplete")
    if result.get("post_hoc_support_comparison_count") != len(post_rows):
        raise ValueError("candidate post hoc point comparison count differs")
    post_common = {
        "comparison_id",
        "candidate_model_id",
        "reference_model_id",
        "sign_convention",
        "test_row_count",
        "candidate_rmse",
        "reference_rmse",
        "rmse_difference",
        "candidate_mae",
        "reference_mae",
        "mae_difference",
        "crop",
        "irrigation_practice",
        "report_scope",
        "split_id",
        "test_support_sha256",
        "primary_terminal_rmse_difference",
        "rmse_ranking_flip_vs_primary_terminal",
        "primary_terminal_mae_difference",
        "mae_ranking_flip_vs_primary_terminal",
    }
    flip_count = 0
    post_identities: set[tuple[str, str, str, str]] = set()
    for row in post_rows:
        if not isinstance(row, dict) or set(row) != post_common:
            raise ValueError("candidate post hoc point comparison schema differs")
        _check_difference_row(
            {key: value for key, value in row.items() if key in {
                "comparison_id", "candidate_model_id", "reference_model_id",
                "sign_convention", "test_row_count", "candidate_rmse",
                "reference_rmse", "rmse_difference", "candidate_mae",
                "reference_mae", "mae_difference",
            }},
            with_intervals=False,
        )
        key = (row["crop"], row["irrigation_practice"], row["report_scope"])
        diagnostic = post_diagnostics_by_key.get(key)
        if diagnostic is None:
            raise ValueError("candidate post hoc point comparison lacks diagnostics")
        for field in ("split_id", "test_support_sha256", "test_row_count"):
            if row[field] != diagnostic[field]:
                raise ValueError(f"candidate post hoc comparison mismatch at {field}")
        identity = (*key, row["comparison_id"])
        if identity in post_identities:
            raise ValueError("candidate post hoc comparison identity is duplicated")
        post_identities.add(identity)
        for metric in ("rmse", "mae"):
            primary = _finite_number(
                row[f"primary_terminal_{metric}_difference"], f"primary terminal {metric}"
            )
            current = _finite_number(row[f"{metric}_difference"], f"post hoc {metric}")
            expected_flip = bool(primary * current < 0)
            if row[f"{metric}_ranking_flip_vs_primary_terminal"] is not expected_flip:
                raise ValueError("candidate post hoc ranking-flip arithmetic differs")
            flip_count += int(expected_flip)
    if result.get("post_hoc_ranking_flip_count_across_metric_comparisons") != flip_count:
        raise ValueError("candidate post hoc ranking-flip count differs")


def validate_sensitivity(config_path: Path, result_path: Path) -> dict[str, Any]:
    if not config_path.is_file() or not result_path.is_file():
        raise FileNotFoundError("sensitivity config or result is missing")
    config = load_sensitivity_config(config_path)
    actual = json.loads(result_path.read_text(encoding="utf-8"))
    if not isinstance(actual, dict):
        raise ValueError("candidate sensitivity result is not a JSON object")
    _check_result_structure(actual, config)
    expected = evaluate_sensitivity(config_path)
    if actual != expected:
        raise ValueError("candidate sensitivity differs from exact deterministic recomputation")
    registry = _artifact_registry(config)
    receipt: dict[str, Any] = {
        "schema_version": 1,
        "status": "validated_conditional_us_county_paired_predictive_loss_sensitivity",
        "contract_id": CONTRACT_ID,
        "config": {"path": _project_relative(config_path), "sha256": sha256(config_path)},
        "result": {"path": _project_relative(result_path), "sha256": sha256(result_path)},
        "implementation": {
            "evaluator": {"path": _project_relative(EVALUATOR_PATH), "sha256": sha256(EVALUATOR_PATH)},
            "validator": {
                "path": _project_relative(Path(__file__)),
                "sha256": sha256(Path(__file__)),
            },
            "synthetic_test": {
                "path": _project_relative(TEST_PATH),
                "sha256": sha256(TEST_PATH),
            },
        },
        "validated_base_bindings": {
            identifier: {
                "path": registry[identifier]["path"],
                "sha256": registry[identifier]["sha256"],
            }
            for identifier in (
                "protocol",
                "base_result",
                "base_validation",
                "independent_audit_receipt",
            )
        },
        "checks": {
            "all_configured_base_hashes_passed": True,
            "base_exact_validation_recomputed": True,
            "base_independent_audit_clear": True,
            "all_120_registered_solver_fits_match": True,
            "identical_endpoint_purges_recomputed": True,
            "mutually_exclusive_moisture_families_passed": True,
            "shared_test_support_passed": True,
            "finite_values_passed": True,
            "county_cluster_support_gates_passed": True,
            "complete_pooled_and_adequate_state_product_passed": True,
            "point_and_interval_arithmetic_recomputed": True,
            "exact_deterministic_recomputation_passed": True,
            "frozen_distribution_promotion_rule_unchanged": True,
            "post_hoc_support_selection_uses_outcome_values": False,
            "post_hoc_support_changes_primary_protocol_or_promotion": False,
        },
        "bootstrap_replicates": actual["bootstrap_replicates"],
        "cluster_diagnostics": actual["cluster_diagnostics"],
        "state_specific_omissions": actual["state_specific_omissions"],
        "comparisons": actual["comparisons"],
        "comparison_count": actual["comparison_count"],
        "post_hoc_support_diagnostics": actual["post_hoc_support_diagnostics"],
        "post_hoc_support_comparisons": actual["post_hoc_support_comparisons"],
        "post_hoc_ranking_flip_count_across_metric_comparisons": actual[
            "post_hoc_ranking_flip_count_across_metric_comparisons"
        ],
        "uncertainty_scope": actual["uncertainty_scope"],
        "unsupported_uncertainty": actual["unsupported_uncertainty"],
        "training_refit_within_bootstrap": False,
        "families_stacked": False,
        "coefficients_emitted": False,
        "row_predictions_emitted": False,
        "row_losses_emitted": False,
        "bootstrap_draws_emitted": False,
        **{gate: False for gate in FALSE_GATES},
    }
    _reject_sensitive_payload(receipt)
    _require_finite_and_relative(receipt)
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--result", required=True, type=Path)
    parser.add_argument("--out", type=Path)
    arguments = parser.parse_args()
    receipt = validate_sensitivity(arguments.config, arguments.result)
    serialized = json.dumps(receipt, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if arguments.out:
        arguments.out.parent.mkdir(parents=True, exist_ok=True)
        arguments.out.write_text(serialized, encoding="utf-8")
    print(
        f"validated {receipt['comparison_count']} aggregate county-bootstrap comparisons "
        "by exact deterministic recomputation; no coefficients, row predictions, row losses, or draws"
    )


if __name__ == "__main__":
    main()
