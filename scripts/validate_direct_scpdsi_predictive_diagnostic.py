#!/usr/bin/env python3
"""Fully recompute and validate the locked direct/scPDSI diagnostic."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from allocate_outcome_exposures import read_table
from build_direct_scpdsi_diagnostic_inputs import (
    CONTRACT_ID,
    FALSE_GATES,
    assemble_diagnostic_inputs,
    sha256_file,
)
from evaluate_direct_scpdsi_predictive_diagnostic import (
    _reject_forbidden_result_keys,
    evaluate_views,
    validate_view_frames,
)


def _assert_frame(actual: pd.DataFrame, expected: pd.DataFrame, label: str) -> None:
    try:
        pd.testing.assert_frame_equal(
            actual.reset_index(drop=True), expected.reset_index(drop=True),
            check_dtype=True, check_exact=True,
        )
    except AssertionError as error:
        raise ValueError(f"{label} differs from locked immediate-input recomputation") from error


def _check_metric(metric: dict[str, Any], label: str) -> None:
    expected_fields = {
        "n", "mean_observed", "sum_squared_error", "sum_absolute_error",
        "sum_squared_total", "rmse", "mae", "r2",
    }
    if set(metric) != expected_fields:
        raise ValueError(f"{label} metric schema differs")
    n = metric["n"]
    if type(n) is not int or n <= 0:
        raise ValueError(f"{label} n must be a positive integer")
    numeric = [metric[name] for name in (
        "mean_observed", "sum_squared_error", "sum_absolute_error",
        "sum_squared_total", "rmse", "mae",
    )]
    if not all(type(value) in (int, float) and np.isfinite(value) for value in numeric):
        raise ValueError(f"{label} contains a nonfinite metric")
    if any(metric[name] < 0 for name in ("sum_squared_error", "sum_absolute_error", "sum_squared_total", "rmse", "mae")):
        raise ValueError(f"{label} contains a negative loss or sum of squares")
    if not np.isclose(metric["rmse"], np.sqrt(metric["sum_squared_error"] / n), rtol=1e-12, atol=1e-14):
        raise ValueError(f"{label} RMSE arithmetic differs")
    if not np.isclose(metric["mae"], metric["sum_absolute_error"] / n, rtol=1e-12, atol=1e-14):
        raise ValueError(f"{label} MAE arithmetic differs")
    if metric["sum_squared_total"] == 0:
        if metric["r2"] is not None:
            raise ValueError(f"{label} R2 must be null when total variation is zero")
    else:
        expected_r2 = 1.0 - metric["sum_squared_error"] / metric["sum_squared_total"]
        if type(metric["r2"]) not in (int, float) or not np.isclose(metric["r2"], expected_r2, rtol=1e-12, atol=1e-14):
            raise ValueError(f"{label} R2 arithmetic differs")


def _check_result_structure(result: dict[str, Any]) -> None:
    _reject_forbidden_result_keys(result)
    for gate in FALSE_GATES:
        if result.get(gate) is not False:
            raise ValueError(f"Result {gate} must be exactly false")
    for field in ("families_stacked", "coefficients_emitted", "predictions_emitted"):
        if result.get(field) is not False:
            raise ValueError(f"Result {field} must be exactly false")
    if result.get("temporal_holdout_prospective") is not False:
        raise ValueError("Result temporal holdout must be labeled retrospective, not prospective")
    if (
        result.get("scpdsi_calibration_period") != "1901-2025"
        or result.get("scpdsi_temporal_evaluation")
        != "retrospective_not_prospective_full_record_calibration"
        or result.get("observation_weighting")
        != "equal_crop_grid_year_pair_weighting_not_area_production_or_welfare_weighted"
        or result.get("loss_metrics") != ["rmse", "mae", "r2"]
        or result.get("model_selection_rule")
        != "none_nonproduction_diagnostic_reports_all_metrics"
        or result.get("spatial_validation_scope")
        != "hashed_5degree_blocks_unbuffered_adjacent_blocks_may_cross_folds"
    ):
        raise ValueError("Result calibration, temporal, or observation-weighting boundary differs")
    if result.get("diagnostic_fit_authorized") is not True:
        raise ValueError("Result diagnostic_fit_authorized must be exactly true")
    models = result.get("models")
    if not isinstance(models, list) or not models:
        raise ValueError("Result model registry is missing")
    common_controls = models[0].get("common_controls")
    if any(model.get("common_controls") != common_controls for model in models):
        raise ValueError("Common controls differ across candidate models")
    for model in models:
        features = model.get("candidate_features")
        if not isinstance(features, list):
            raise ValueError("Model candidate-feature registry is invalid")
        if any(name.startswith("direct__") for name in features) and any(name.startswith("scpdsi__") for name in features):
            raise ValueError("Family stacking appears in the result registry")
    results = result.get("results")
    if not isinstance(results, list) or len(results) != result.get("result_count"):
        raise ValueError("A required crop-model-holdout result is missing")
    keys = [(row.get("crop"), row.get("model_id"), row.get("holdout_id")) for row in results]
    if len(keys) != len(set(keys)):
        raise ValueError("Duplicate crop-model-holdout result")
    expected = {
        (crop, model["id"], holdout)
        for crop in ("mai", "soy") for model in models for holdout in result.get("holdouts", [])
    }
    if set(keys) != expected or result.get("full_model_holdout_product_complete") is not True:
        raise ValueError("Full crop-model-holdout product is incomplete")
    key_hash_by_holdout: dict[tuple[str, str], str] = {}
    for row in results:
        label = f"{row.get('crop')} {row.get('model_id')} {row.get('holdout_id')}"
        _check_metric(row.get("pooled_metrics", {}), label + " pooled")
        by_episode = row.get("metrics_by_episode")
        if not isinstance(by_episode, dict) or not by_episode:
            raise ValueError(f"{label} episode-stratified metrics are missing")
        for episode, metric in by_episode.items():
            _check_metric(metric, label + f" {episode}")
        key = (row["crop"], row["holdout_id"])
        observed_hash = row.get("test_pair_key_sha256")
        if key in key_hash_by_holdout and observed_hash != key_hash_by_holdout[key]:
            raise ValueError(f"Models do not use identical test pair keys for {key}")
        key_hash_by_holdout[key] = observed_hash


def validate_diagnostic(
    config_path: Path,
    input_audit_path: Path,
    view_paths: dict[str, Path],
    result_path: Path,
) -> dict[str, Any]:
    required = [config_path, input_audit_path, result_path, *view_paths.values()]
    if missing := [str(path) for path in required if not path.is_file()]:
        raise FileNotFoundError(f"Required diagnostic result/input is missing: {missing}")
    actual_audit = json.loads(input_audit_path.read_text(encoding="utf-8"))
    if actual_audit.get("schema_version") != 1 or actual_audit.get("contract_id") != CONTRACT_ID:
        raise ValueError("Input audit contract differs")
    for gate in FALSE_GATES:
        if actual_audit.get(gate) is not False:
            raise ValueError(f"Input audit {gate} must be exactly false")
    expected_views, expected_audit = assemble_diagnostic_inputs(config_path)
    expected_audit["output_files"] = {
        name: {"path": str(path), "sha256": sha256_file(path)}
        for name, path in view_paths.items()
    }
    if actual_audit != expected_audit:
        raise ValueError("Input audit differs from full locked immediate-input recomputation")
    actual_views = {name: read_table(path) for name, path in view_paths.items()}
    validate_view_frames(actual_views)
    for name in expected_views:
        _assert_frame(actual_views[name], expected_views[name], f"{name} view")

    actual_result = json.loads(result_path.read_text(encoding="utf-8"))
    _check_result_structure(actual_result)
    if actual_result.get("contract_id") != CONTRACT_ID:
        raise ValueError("Result contract differs")
    expected_result = evaluate_views(config_path, actual_views)
    expected_result.update({
        "config_file": str(config_path),
        "config_sha256": sha256_file(config_path),
        "input_audit_file": str(input_audit_path),
        "input_audit_sha256": sha256_file(input_audit_path),
        "input_view_files": {
            name: {"path": str(path), "sha256": sha256_file(path)} for name, path in view_paths.items()
        },
    })
    if actual_result != expected_result:
        raise ValueError("Result differs from full locked metric recomputation")
    return {
        "schema_version": 1,
        "status": "validated_nonproduction_predictive_diagnostic",
        "contract_id": CONTRACT_ID,
        "config_sha256": sha256_file(config_path),
        "input_audit_sha256": sha256_file(input_audit_path),
        "input_view_sha256": {
            name: sha256_file(path) for name, path in sorted(view_paths.items())
        },
        "result_sha256": sha256_file(result_path),
        "input_audit_sha256_verified": True,
        "all_input_and_output_sha256_verified": True,
        "common_bundles_revalidated": True,
        "immediate_input_recomputation_passed": True,
        "exact_pair_outcome_split_equality_passed": True,
        "common_control_identity_passed": True,
        "family_leakage_and_stacking_checks_passed": True,
        "training_only_scaling_and_endpoint_purge_recomputed": True,
        "full_model_holdout_product_passed": True,
        "metric_arithmetic_recomputed": True,
        "scpdsi_temporal_evaluation": "retrospective_not_prospective_full_record_calibration",
        "temporal_holdout_prospective": False,
        "coefficient_and_prediction_fields_absent": True,
        "coefficients_emitted": False,
        "predictions_emitted": False,
        "diagnostic_fit_authorized": True,
        **{gate: False for gate in FALSE_GATES},
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--input-audit", required=True)
    parser.add_argument("--direct-view", required=True)
    parser.add_argument("--scpdsi-view", required=True)
    parser.add_argument("--common-view", required=True)
    parser.add_argument("--split-view", required=True)
    parser.add_argument("--result", required=True)
    parser.add_argument("--out")
    args = parser.parse_args()
    receipt = validate_diagnostic(
        Path(args.config), Path(args.input_audit),
        {"direct": Path(args.direct_view), "scpdsi": Path(args.scpdsi_view),
         "common": Path(args.common_view), "split": Path(args.split_view)},
        Path(args.result),
    )
    rendered = json.dumps(receipt, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if args.out:
        output = Path(args.out)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()
