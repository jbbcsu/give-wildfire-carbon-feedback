#!/usr/bin/env python3
"""Validate and summarize a locked precipitation-distribution diagnostic."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

from evaluate_precipitation_distribution_diagnostic import (
    DIAGNOSTIC_CONTRACT_ID,
    LOCK_DEFAULT,
    NONSPATIAL_SPLIT_CONTRACT,
    PROJECT,
    SOURCE_ALLOCATION_ORDER,
    SOURCE_CONTRACT_ID,
    SPEC_DEFAULT,
    STATUS,
    assert_coefficients_suppressed,
    load_contract,
    locked_input,
    resolve_locked_path,
    run_diagnostic,
    sha256_path,
)


HOLDOUTS = ("spatial_block", "temporal", "climate_extreme")
PURGE_RULES = {
    "temporal": "drop_training_pairs_sharing_either_yield_endpoint_with_temporal_test",
    "climate_extreme": "drop_training_pairs_sharing_either_yield_endpoint_with_extreme_test",
}
SUMMARY_STATUS = "validated_distribution_comparison_not_causal_model_selection_or_scc_authorized"


def _positive_integer(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{name} must be a positive integer")
    return value


def _nonnegative_integer(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a nonnegative integer")
    return value


def _finite(value: Any, name: str, *, nonnegative: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be numeric")
    number = float(value)
    if not math.isfinite(number) or (nonnegative and number < 0):
        raise ValueError(f"{name} must be finite" + (" and nonnegative" if nonnegative else ""))
    return number


def _require_false(audit: dict[str, Any], name: str) -> None:
    if audit.get(name) is not False:
        raise ValueError(f"Diagnostic audit requires {name}=false")


def assert_recomputed_audit_matches(
    reported: Any,
    recomputed: Any,
    path: str = "audit",
) -> None:
    """Require a reported audit to match a fresh locked-data recomputation.

    Numeric fields use a tight tolerance so that harmless LAPACK differences
    across machines do not prevent reproduction. Structure, labels, row counts,
    authorization gates, and all other values must match exactly.
    """
    if isinstance(reported, bool) or isinstance(recomputed, bool):
        if type(reported) is not bool or type(recomputed) is not bool or reported is not recomputed:
            raise ValueError(f"Reported diagnostic differs from recomputation at {path}")
        return
    if isinstance(reported, (int, float)) and isinstance(recomputed, (int, float)):
        if isinstance(reported, int) and isinstance(recomputed, int):
            if reported != recomputed:
                raise ValueError(f"Reported diagnostic differs from recomputation at {path}")
        elif not (
            math.isfinite(float(reported))
            and math.isfinite(float(recomputed))
            and math.isclose(float(reported), float(recomputed), rel_tol=1e-12, abs_tol=1e-12)
        ):
            raise ValueError(f"Reported diagnostic differs from recomputation at {path}")
        return
    if isinstance(reported, dict) and isinstance(recomputed, dict):
        if set(reported) != set(recomputed):
            raise ValueError(f"Reported diagnostic structure differs from recomputation at {path}")
        for key in reported:
            assert_recomputed_audit_matches(reported[key], recomputed[key], f"{path}.{key}")
        return
    if isinstance(reported, list) and isinstance(recomputed, list):
        if len(reported) != len(recomputed):
            raise ValueError(f"Reported diagnostic length differs from recomputation at {path}")
        for index, (left, right) in enumerate(zip(reported, recomputed)):
            assert_recomputed_audit_matches(left, right, f"{path}[{index}]")
        return
    if type(reported) is not type(recomputed) or reported != recomputed:
        raise ValueError(f"Reported diagnostic differs from recomputation at {path}")


def validate_audit(
    audit: dict[str, Any],
    spec: dict[str, Any],
    lock: dict[str, Any],
    models: dict[str, list[str]],
    spec_hash: str,
    lock_hash: str,
    project_root: Path,
    *,
    verify_source_files: bool = True,
    recomputed_audit: dict[str, Any] | None = None,
) -> dict[str, Any]:
    assert_coefficients_suppressed(audit)
    if verify_source_files:
        if recomputed_audit is None:
            raise ValueError(
                "Locked-source validation requires a fresh recomputed diagnostic audit"
            )
        assert_coefficients_suppressed(recomputed_audit)
        assert_recomputed_audit_matches(audit, recomputed_audit)
    if audit.get("status") != STATUS:
        raise ValueError("Unrecognized diagnostic status")
    if audit.get("diagnostic_contract_id") != DIAGNOSTIC_CONTRACT_ID:
        raise ValueError("Diagnostic contract mismatch")
    if audit.get("spec_sha256") != spec_hash or audit.get("lock_sha256") != lock_hash:
        raise ValueError("Diagnostic specification or lock hash mismatch")
    if audit.get("models") != list(models):
        raise ValueError("Diagnostic model order/content mismatch")
    expected_counts = {name: len(features) for name, features in models.items()}
    if audit.get("model_feature_counts") != expected_counts:
        raise ValueError("Diagnostic model feature counts mismatch")
    if audit.get("nonspatial_split_contract") != NONSPATIAL_SPLIT_CONTRACT:
        raise ValueError("Diagnostic split contract mismatch")
    if audit.get("source_basis_contract_id") != SOURCE_CONTRACT_ID:
        raise ValueError("Diagnostic source-basis contract mismatch")
    if audit.get("source_basis_allocation_order") != SOURCE_ALLOCATION_ORDER:
        raise ValueError("Diagnostic source-basis allocation-order mismatch")
    if audit.get("source_basis_fit_authorized") is not False:
        raise ValueError("Source basis was improperly marked fit-authorized")
    if audit.get("held_out_predictive_fit_authorized") is not True:
        raise ValueError("Separate held-out predictive authorization is absent")
    if audit.get("coefficients_suppressed") is not True:
        raise ValueError("Coefficient suppression is not declared")
    for name in (
        "coefficient_export_authorized",
        "causal_interpretation_authorized",
        "production_model_selection_authorized",
        "response_draw_export_authorized",
        "scc_use_authorized",
    ):
        _require_false(audit, name)
    if audit.get("wet_day_threshold_mm") != spec["construction"]["wet_day_threshold_mm"]:
        raise ValueError("Diagnostic wet-day threshold mismatch")
    if audit.get("stage_fractions") != spec["construction"]["stage_fractions"]:
        raise ValueError("Diagnostic stage-fraction mismatch")
    if audit.get("algebraic_redundancy_rule") != spec["construction"]["algebraic_redundancy_rule"]:
        raise ValueError("Diagnostic algebraic-redundancy rule mismatch")
    validation = spec["validation"]
    expected_design = (
        f"block={float(validation['spatial_block_degrees']):g};"
        f"folds={int(validation['spatial_folds'])};"
        f"temporal_last={int(validation['temporal_holdout_years'])};"
        f"q={float(validation['extreme_quantile']):g};seed={validation['seed']}"
    )
    if audit.get("validation_design") != expected_design:
        raise ValueError("Diagnostic validation-design drift")

    crop = audit.get("crop")
    source = locked_input(lock, str(crop))
    if audit.get("source_panel_sha256") != source.get("panel_sha256"):
        raise ValueError("Diagnostic source-panel hash mismatch")
    if audit.get("source_allocation_audit_sha256") != source.get("allocation_audit_sha256"):
        raise ValueError("Diagnostic source allocation-audit hash mismatch")
    if verify_source_files:
        panel_path = resolve_locked_path(project_root, str(source["panel_path"]))
        source_audit_path = resolve_locked_path(project_root, str(source["allocation_audit_path"]))
        if sha256_path(panel_path) != source["panel_sha256"]:
            raise ValueError("Current source-panel file differs from lock")
        if sha256_path(source_audit_path) != source["allocation_audit_sha256"]:
            raise ValueError("Current source allocation-audit file differs from lock")

    n_levels = _positive_integer(audit.get("n_level_rows"), "n_level_rows")
    n_observed = _positive_integer(audit.get("n_observed_level_rows"), "n_observed_level_rows")
    n_pairs = _positive_integer(audit.get("n_consecutive_pairs"), "n_consecutive_pairs")
    if n_levels != source["expected_rows"] or n_observed != source["expected_observed_outcomes"]:
        raise ValueError("Diagnostic source row counts differ from lock")
    if n_pairs >= n_observed:
        raise ValueError("Consecutive-pair count must be below observed-level count")
    start = int(source["expected_year_start"])
    end = int(source["expected_year_end"])
    if audit.get("harvest_year_start") != start or audit.get("harvest_year_end") != end:
        raise ValueError("Diagnostic year bounds differ from lock")
    if audit.get("harvest_years") != list(range(start, end + 1)):
        raise ValueError("Diagnostic years are not complete and contiguous")
    source_validation = audit.get("source_validation")
    if not isinstance(source_validation, dict):
        raise ValueError("Diagnostic source validation is absent")
    if source_validation.get("response_basis_contract_id") != SOURCE_CONTRACT_ID:
        raise ValueError("Source-validation contract mismatch")
    if source_validation.get("basis_allocation_order") != SOURCE_ALLOCATION_ORDER:
        raise ValueError("Source-validation allocation order mismatch")
    if source_validation.get("basis_feature_count") != spec["source_basis_feature_count"]:
        raise ValueError("Source-validation feature count mismatch")
    if source_validation.get("rows") != n_levels or source_validation.get("observed_outcomes") != n_observed:
        raise ValueError("Source-validation row counts do not reconcile")
    if source_validation.get("fit_authorized") is not False or source_validation.get("scc_authorized") is not False:
        raise ValueError("Source validation improperly authorizes fitting or SCC use")

    entries = audit.get("results")
    if not isinstance(entries, list):
        raise ValueError("Diagnostic results must be a list")
    expected_keys = {(model, holdout) for model in models for holdout in HOLDOUTS}
    indexed: dict[tuple[str, str], dict[str, Any]] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("Every diagnostic result must be an object")
        key = (entry.get("model"), entry.get("holdout"))
        if key in indexed:
            raise ValueError(f"Duplicate diagnostic result {key}")
        indexed[key] = entry
    if set(indexed) != expected_keys:
        raise ValueError("Diagnostic result product is incomplete or contains extras")

    comparisons: list[dict[str, Any]] = []
    spatial_folds = int(spec["validation"]["spatial_folds"])
    for holdout in HOLDOUTS:
        rows = {model: indexed[(model, holdout)] for model in models}
        test_rows = [_positive_integer(row.get("test_rows"), "test_rows") for row in rows.values()]
        if len(set(test_rows)) != 1:
            raise ValueError(f"Test rows differ across models for {holdout}")
        benchmark = [_finite(row.get("zero_change_rmse"), "zero_change_rmse", nonnegative=True) for row in rows.values()]
        if not all(math.isclose(value, benchmark[0], rel_tol=1e-12, abs_tol=1e-12) for value in benchmark):
            raise ValueError(f"Zero-change RMSE differs across models for {holdout}")
        for model, row in rows.items():
            if row.get("feature_count") != len(models[model]):
                raise ValueError(f"Feature count mismatch for {model}/{holdout}")
            rmse = _finite(row.get("rmse"), "rmse", nonnegative=True)
            _finite(row.get("mae"), "mae", nonnegative=True)
            improvement = _finite(row.get("rmse_improvement_vs_zero"), "rmse_improvement_vs_zero")
            if not math.isclose(improvement, benchmark[0] - rmse, rel_tol=1e-10, abs_tol=1e-12):
                raise ValueError(f"RMSE arithmetic fails for {model}/{holdout}")
            for optional in ("r_squared", "correlation"):
                if row.get(optional) is not None:
                    _finite(row[optional], optional)
            if holdout == "spatial_block":
                folds = row.get("folds")
                if not isinstance(folds, list) or len(folds) != spatial_folds:
                    raise ValueError(f"Spatial-fold audit is incomplete for {model}")
                if sum(_positive_integer(fold.get("test_rows"), "fold test_rows") for fold in folds) != test_rows[0]:
                    raise ValueError(f"Spatial-fold rows do not reconcile for {model}")
                if {fold.get("fold") for fold in folds} != set(range(spatial_folds)):
                    raise ValueError(f"Spatial-fold IDs differ from the locked design for {model}")
                for fold in folds:
                    if _nonnegative_integer(fold.get("endpoint_overlap_count"), "endpoint overlap") != 0:
                        raise ValueError(f"Spatial yield endpoints overlap for {model}")
                    _positive_integer(fold.get("train_rows"), "fold train_rows")
                    rank = _positive_integer(fold.get("matrix_rank"), "fold matrix_rank")
                    if rank != len(models[model]) + 1:
                        raise ValueError(f"Spatial design rank differs from feature count for {model}")
                    if _finite(fold.get("condition_number"), "fold condition number") < 1:
                        raise ValueError("Condition number cannot be below one")
            else:
                _positive_integer(row.get("train_rows"), "train_rows")
                _nonnegative_integer(row.get("purged_train_rows"), "purged_train_rows")
                if _nonnegative_integer(row.get("endpoint_overlap_count"), "endpoint overlap") != 0:
                    raise ValueError(f"Nonspatial yield endpoints overlap for {model}/{holdout}")
                if row.get("purge_rule") != PURGE_RULES[holdout]:
                    raise ValueError(f"Unrecognized purge rule for {model}/{holdout}")
                rank = _positive_integer(row.get("matrix_rank"), "matrix_rank")
                if rank != len(models[model]) + 1:
                    raise ValueError(f"Nonspatial design rank differs from feature count for {model}/{holdout}")
                if _finite(row.get("condition_number"), "condition number") < 1:
                    raise ValueError("Condition number cannot be below one")
        if holdout != "spatial_block":
            if len({row["train_rows"] for row in rows.values()}) != 1:
                raise ValueError(f"Train rows differ across models for {holdout}")
            if len({row["purged_train_rows"] for row in rows.values()}) != 1:
                raise ValueError(f"Purged rows differ across models for {holdout}")
        else:
            split_signatures = [
                [
                    (
                        fold["fold"],
                        fold["train_rows"],
                        fold["test_rows"],
                        fold["endpoint_overlap_count"],
                    )
                    for fold in rows[model]["folds"]
                ]
                for model in models
            ]
            if any(signature != split_signatures[0] for signature in split_signatures[1:]):
                raise ValueError("Spatial split rows differ across models")

        temperature_rmse = float(rows["temperature_control"]["rmse"])
        quantity_rmse = float(rows["seasonal_quantity"]["rmse"])
        ranked = sorted(
            (
                {
                    "model": model,
                    "rmse": float(row["rmse"]),
                    "mae": float(row["mae"]),
                    "rmse_improvement_vs_zero": float(row["rmse_improvement_vs_zero"]),
                    "rmse_improvement_vs_temperature_control": temperature_rmse - float(row["rmse"]),
                    "rmse_improvement_vs_seasonal_quantity": quantity_rmse - float(row["rmse"]),
                }
                for model, row in rows.items()
            ),
            key=lambda item: (item["rmse"], list(models).index(item["model"])),
        )
        comparisons.append(
            {
                "holdout": holdout,
                "test_rows": test_rows[0],
                "zero_change_rmse": benchmark[0],
                "temperature_control_rmse": temperature_rmse,
                "seasonal_quantity_rmse": quantity_rmse,
                "seasonal_quantity_improvement_vs_temperature_control": temperature_rmse - quantity_rmse,
                "best_model_descriptive_only": ranked[0]["model"],
                "best_rmse": ranked[0]["rmse"],
                "ranked_models": ranked,
            }
        )

    return {
        "status": SUMMARY_STATUS,
        "diagnostic_contract_id": DIAGNOSTIC_CONTRACT_ID,
        "spec_sha256": spec_hash,
        "lock_sha256": lock_hash,
        "crop": crop,
        "source_panel_sha256": source["panel_sha256"],
        "source_basis_fit_authorized": False,
        "coefficients_suppressed": True,
        "causal_interpretation_authorized": False,
        "production_model_selection_authorized": False,
        "scc_use_authorized": False,
        "wet_day_threshold_mm": spec["construction"]["wet_day_threshold_mm"],
        "stage_fractions": spec["construction"]["stage_fractions"],
        "models": list(models),
        "n_level_rows": n_levels,
        "n_observed_level_rows": n_observed,
        "n_consecutive_pairs": n_pairs,
        "comparisons": comparisons,
        "warning": (
            "Rankings and incremental RMSE are descriptive held-out predictive comparisons. "
            "They are not causal effect estimates, model-selection authority, damages, or SCC inputs."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit", required=True, type=Path)
    parser.add_argument("--spec", type=Path, default=SPEC_DEFAULT)
    parser.add_argument("--lock", type=Path, default=LOCK_DEFAULT)
    parser.add_argument("--skip-source-file-verification", action="store_true")
    parser.add_argument("--summary-out", type=Path)
    args = parser.parse_args()
    spec, lock, models, spec_hash, lock_hash = load_contract(args.spec, args.lock)
    audit = json.loads(args.audit.read_text(encoding="utf-8"))
    recomputed = None
    if not args.skip_source_file_verification:
        recomputed = run_diagnostic(str(audit.get("crop")), args.spec, args.lock, PROJECT)
    summary = validate_audit(
        audit,
        spec,
        lock,
        models,
        spec_hash,
        lock_hash,
        PROJECT,
        verify_source_files=not args.skip_source_file_verification,
        recomputed_audit=recomputed,
    )
    rendered = json.dumps(summary, indent=2, sort_keys=True) + "\n"
    if args.summary_out:
        args.summary_out.parent.mkdir(parents=True, exist_ok=True)
        args.summary_out.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()
