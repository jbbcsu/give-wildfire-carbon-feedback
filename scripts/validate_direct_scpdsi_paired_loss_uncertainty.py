#!/usr/bin/env python3
"""Exact deterministic validation of the paired-loss uncertainty sensitivity."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np

from build_direct_scpdsi_diagnostic_inputs import FALSE_GATES, sha256_file
from evaluate_direct_scpdsi_predictive_diagnostic import _reject_forbidden_result_keys
from evaluate_direct_scpdsi_paired_loss_uncertainty import (
    CONTRACT_ID,
    EXPECTED_COMPARISONS,
    evaluate_sensitivity,
    load_sensitivity_config,
)


def _check_result_structure(result: dict[str, Any], config: dict[str, Any]) -> None:
    _reject_forbidden_result_keys(result)
    if result.get("schema_version") != 1 or result.get("contract_id") != CONTRACT_ID:
        raise ValueError("Paired-loss result contract differs")
    if result.get("status") != "completed_nonproduction_paired_loss_uncertainty_sensitivity":
        raise ValueError("Paired-loss result status differs")
    for field in ("families_stacked", "coefficients_emitted", "predictions_emitted"):
        if result.get(field) is not False:
            raise ValueError(f"Paired-loss result {field} must be exactly false")
    for gate in FALSE_GATES:
        if result.get(gate) is not False:
            raise ValueError(f"Paired-loss result {gate} must be exactly false")
    if result.get("diagnostic_fit_authorized") is not True:
        raise ValueError("Paired-loss result diagnostic fit authorization differs")
    exact_fields = {
        "score_basis": config["score_basis"],
        "resampling_scheme": config["resampling_scheme"],
        "resampling_unit": config["resampling_unit"],
        "cluster_latitude_degrees": config["cluster_latitude_degrees"],
        "cluster_longitude_degrees": config["cluster_longitude_degrees"],
        "bootstrap_replicates": config["bootstrap_replicates"],
        "random_seed": config["random_seed"],
        "interval_probabilities": config["interval_probabilities"],
        "observation_weighting": config["observation_weighting"],
        "model_selection_rule": config["model_selection_rule"],
        "training_refit_within_bootstrap": False,
        "bootstrap_draws_emitted": False,
        "row_scores_emitted": False,
        "row_losses_emitted": False,
        "base_diagnostic_validation_recomputed": True,
        "all_five_fold_metrics_match_base": True,
    }
    for field, expected in exact_fields.items():
        if result.get(field) != expected:
            raise ValueError(f"Paired-loss result {field} differs")
    diagnostics = result.get("crop_cluster_diagnostics")
    if not isinstance(diagnostics, dict) or set(diagnostics) != {"mai", "soy"}:
        raise ValueError("Crop cluster diagnostics are incomplete")
    for crop, values in diagnostics.items():
        required = {
            "pair_count",
            "occupied_cluster_count",
            "effective_cluster_count_inverse_herfindahl",
            "maximum_cluster_pair_share",
            "minimum_cluster_pair_count",
            "median_cluster_pair_count",
            "maximum_cluster_pair_count",
            "crop_seed",
        }
        if not isinstance(values, dict) or set(values) != required:
            raise ValueError(f"Cluster diagnostics schema differs for {crop}")
        if values["occupied_cluster_count"] < config["minimum_occupied_clusters_per_crop"]:
            raise ValueError(f"Occupied cluster gate fails for {crop}")
        if values["maximum_cluster_pair_share"] > config["maximum_cluster_pair_share"]:
            raise ValueError(f"Maximum cluster share gate fails for {crop}")
        if values["pair_count"] <= 0 or values["effective_cluster_count_inverse_herfindahl"] <= 0:
            raise ValueError(f"Cluster support is invalid for {crop}")
    comparisons = result.get("comparisons")
    if not isinstance(comparisons, list) or len(comparisons) != result.get("comparison_count"):
        raise ValueError("Paired comparison results are incomplete")
    expected_keys = {
        (crop, identifier, candidate, reference)
        for crop in ("mai", "soy")
        for identifier, candidate, reference in EXPECTED_COMPARISONS
    }
    observed_keys: set[tuple[str, str, str, str]] = set()
    expected_fields = {
        "crop",
        "comparison_id",
        "candidate_model_id",
        "reference_model_id",
        "sign_convention",
        "pair_count",
        "candidate_oof_rmse",
        "reference_oof_rmse",
        "rmse_difference",
        "rmse_interval",
        "candidate_oof_mae",
        "reference_oof_mae",
        "mae_difference",
        "mae_interval",
    }
    for row in comparisons:
        if not isinstance(row, dict) or set(row) != expected_fields:
            raise ValueError("Paired comparison row schema differs")
        key = (
            row["crop"],
            row["comparison_id"],
            row["candidate_model_id"],
            row["reference_model_id"],
        )
        observed_keys.add(key)
        if row["pair_count"] != diagnostics[row["crop"]]["pair_count"]:
            raise ValueError("Paired comparison count differs from cluster support")
        if row["sign_convention"] != "candidate_minus_reference_negative_favors_candidate_on_loss":
            raise ValueError("Paired-loss sign convention differs")
        for metric in ("rmse", "mae"):
            candidate = row[f"candidate_oof_{metric}"]
            reference = row[f"reference_oof_{metric}"]
            difference = row[f"{metric}_difference"]
            interval = row[f"{metric}_interval"]
            if not all(type(value) in (int, float) and np.isfinite(value) for value in (candidate, reference, difference)):
                raise ValueError("Paired-loss point metrics must be finite numeric values")
            if candidate < 0 or reference < 0 or not np.isclose(
                difference, candidate - reference, rtol=1e-12, atol=1e-14
            ):
                raise ValueError("Paired-loss point arithmetic differs")
            if not isinstance(interval, dict) or set(interval) != {"lower", "upper"}:
                raise ValueError("Paired-loss interval schema differs")
            if not all(
                type(interval[name]) in (int, float) and np.isfinite(interval[name])
                for name in ("lower", "upper")
            ) or interval["lower"] > interval["upper"]:
                raise ValueError("Paired-loss interval bounds are invalid")
    if observed_keys != expected_keys:
        raise ValueError("Complete crop-by-registered-comparison product is absent")


def validate_sensitivity(config_path: Path, result_path: Path) -> dict[str, Any]:
    if not config_path.is_file() or not result_path.is_file():
        raise FileNotFoundError("Paired-loss config or result is missing")
    config = load_sensitivity_config(config_path)
    actual = json.loads(result_path.read_text(encoding="utf-8"))
    _check_result_structure(actual, config)
    expected = evaluate_sensitivity(config_path)
    if actual != expected:
        raise ValueError("Paired-loss result differs from exact deterministic recomputation")
    return {
        "schema_version": 1,
        "status": "validated_nonproduction_paired_loss_uncertainty_sensitivity",
        "contract_id": CONTRACT_ID,
        "config_sha256": sha256_file(config_path),
        "result_sha256": sha256_file(result_path),
        "base_diagnostic_validation_recomputed": True,
        "all_five_fold_metrics_match_base": True,
        "cluster_support_gates_passed": True,
        "complete_registered_comparison_product_passed": True,
        "point_and_interval_arithmetic_recomputed": True,
        "exact_deterministic_recomputation_passed": True,
        "independent_bootstrap_implementation": False,
        "training_refit_within_bootstrap": False,
        "bootstrap_draws_emitted": False,
        "row_scores_emitted": False,
        "row_losses_emitted": False,
        "diagnostic_fit_authorized": True,
        "coefficients_emitted": False,
        "predictions_emitted": False,
        **{gate: False for gate in FALSE_GATES},
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--result", required=True)
    parser.add_argument("--out")
    args = parser.parse_args()
    receipt = validate_sensitivity(Path(args.config), Path(args.result))
    rendered = json.dumps(receipt, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if args.out:
        output = Path(args.out)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()
