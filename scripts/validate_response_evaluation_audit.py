#!/usr/bin/env python3
"""Validate and summarize a coefficient-suppressing response audit.

This gate verifies that an audit was produced by the exact frozen response
specification, covers an explicitly declared crop set, and contains one
internally consistent result for every crop/model/holdout combination.  It
does not select a response model or authorize coefficients for SCC use.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import tomllib
from pathlib import Path
from typing import Any


STATUS = "diagnostic_held_out_prediction_not_causal_or_scc_authorized"
HOLDOUTS = ("spatial_block", "temporal", "climate_extreme")
SUMMARY_STATUS = "validated_diagnostic_summary_not_model_selection_or_scc_authorized"
NONSPATIAL_SPLIT_CONTRACT = "yield_endpoint_disjoint_purged_training_pairs"
PURGE_RULES = {
    "temporal": "drop_training_pairs_sharing_either_yield_endpoint_with_temporal_test",
    "climate_extreme": "drop_training_pairs_sharing_either_yield_endpoint_with_extreme_test",
}
RAW_REGIME_INPUT = "regime_primitive_weather"
PREBUILT_WEIGHTED_INPUT = "prebuilt_irrigation_weighted_basis"
PREBUILT_CONTRACT_ID = "gdhy_aggregate_irrigation_basis_v1"


def _positive_integer(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{name} must be a positive integer")
    return value


def _nonnegative_integer(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a nonnegative integer")
    return value


def _finite_number(value: Any, name: str, *, nonnegative: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be numeric")
    number = float(value)
    if not math.isfinite(number) or (nonnegative and number < 0):
        qualifier = "finite and nonnegative" if nonnegative else "finite"
        raise ValueError(f"{name} must be {qualifier}")
    return number


def load_spec(path: Path) -> tuple[list[str], str]:
    raw = path.read_bytes()
    spec = tomllib.loads(raw.decode("utf-8"))
    models = list(spec.get("models", {}))
    if not models or len(models) != len(set(models)):
        raise ValueError("Response specification must declare unique models")
    return models, hashlib.sha256(raw).hexdigest()


def validate_audit(
    audit: dict[str, Any],
    models: list[str],
    spec_sha256: str,
    expected_crops: list[str],
    expected_year_start: int | None = None,
    expected_year_end: int | None = None,
    expected_input_basis_mode: str | None = None,
) -> dict[str, Any]:
    if audit.get("status") != STATUS:
        raise ValueError("Audit has an unauthorized or unrecognized status")
    if audit.get("spec_sha256") != spec_sha256:
        raise ValueError("Audit does not match the frozen response specification")
    if audit.get("models") != models:
        raise ValueError("Audit model order/content does not match the response specification")
    if audit.get("nonspatial_split_contract") != NONSPATIAL_SPLIT_CONTRACT:
        raise ValueError("Audit lacks the required yield-endpoint-disjoint split contract")
    basis_mode = audit.get("input_basis_mode")
    if basis_mode not in {RAW_REGIME_INPUT, PREBUILT_WEIGHTED_INPUT}:
        raise ValueError("Audit has an unrecognized input-basis mode")
    if expected_input_basis_mode is not None and basis_mode != expected_input_basis_mode:
        raise ValueError("Audit input-basis mode differs from expectation")
    contract_id = audit.get("response_basis_contract_id")
    expected_contract = PREBUILT_CONTRACT_ID if basis_mode == PREBUILT_WEIGHTED_INPUT else None
    if contract_id != expected_contract:
        raise ValueError("Audit response-basis contract is inconsistent with its input mode")
    if not expected_crops or len(expected_crops) != len(set(expected_crops)):
        raise ValueError("Expected crops must be a nonempty unique list")
    crops = audit.get("crops")
    if crops != sorted(expected_crops):
        raise ValueError(f"Audit crop coverage {crops!r} does not equal {sorted(expected_crops)!r}")

    n_levels = _positive_integer(audit.get("n_level_rows"), "n_level_rows")
    n_observed = _positive_integer(audit.get("n_observed_level_rows"), "n_observed_level_rows")
    n_pairs = _positive_integer(audit.get("n_consecutive_pairs"), "n_consecutive_pairs")
    if n_observed > n_levels or n_pairs >= n_observed:
        raise ValueError("Audit row counts violate level/observed/pair ordering")

    validated_years: list[int] | None = None
    if (expected_year_start is None) != (expected_year_end is None):
        raise ValueError("Expected year start and end must be supplied together")
    if expected_year_start is not None and expected_year_end is not None:
        if expected_year_end < expected_year_start:
            raise ValueError("Expected year end precedes start")
        validated_years = list(range(expected_year_start, expected_year_end + 1))
        if audit.get("harvest_year_start") != expected_year_start:
            raise ValueError("Audit harvest-year start differs from expectation")
        if audit.get("harvest_year_end") != expected_year_end:
            raise ValueError("Audit harvest-year end differs from expectation")
        if audit.get("harvest_years") != validated_years:
            raise ValueError("Audit harvest-year coverage is not complete and contiguous")

    entries = audit.get("results")
    if not isinstance(entries, list):
        raise ValueError("Audit results must be a list")
    expected_keys = {
        (crop, model, holdout)
        for crop in sorted(expected_crops)
        for model in models
        for holdout in HOLDOUTS
    }
    observed: dict[tuple[str, str, str], dict[str, Any]] = {}
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError(f"Result {index} must be an object")
        key = (entry.get("crop"), entry.get("model"), entry.get("holdout"))
        if key in observed:
            raise ValueError(f"Duplicate result key {key}")
        observed[key] = entry
    if set(observed) != expected_keys:
        missing = sorted(expected_keys - set(observed))
        extra = sorted(set(observed) - expected_keys)
        raise ValueError(f"Incomplete result product; missing={missing}, extra={extra}")

    comparisons: list[dict[str, Any]] = []
    for crop in sorted(expected_crops):
        for holdout in HOLDOUTS:
            rows = [observed[(crop, model, holdout)] for model in models]
            test_rows = [_positive_integer(row.get("test_rows"), "test_rows") for row in rows]
            if len(set(test_rows)) != 1:
                raise ValueError(f"test_rows differs across models for {(crop, holdout)}")
            benchmarks = [
                _finite_number(row.get("zero_change_rmse"), "zero_change_rmse", nonnegative=True)
                for row in rows
            ]
            if not all(math.isclose(value, benchmarks[0], rel_tol=1e-12, abs_tol=1e-12) for value in benchmarks):
                raise ValueError(f"Zero-change benchmark differs across models for {(crop, holdout)}")

            ranked: list[dict[str, Any]] = []
            for model, row in zip(models, rows):
                rmse = _finite_number(row.get("rmse"), "rmse", nonnegative=True)
                mae = _finite_number(row.get("mae"), "mae", nonnegative=True)
                improvement = _finite_number(row.get("rmse_improvement_vs_zero"), "rmse_improvement_vs_zero")
                if not math.isclose(improvement, benchmarks[0] - rmse, rel_tol=1e-10, abs_tol=1e-12):
                    raise ValueError(f"RMSE-improvement arithmetic fails for {(crop, model, holdout)}")
                for optional in ("r_squared", "correlation"):
                    if row.get(optional) is not None:
                        _finite_number(row[optional], optional)
                if holdout == "spatial_block":
                    folds = row.get("folds")
                    if not isinstance(folds, list) or len(folds) < 2:
                        raise ValueError(f"Spatial result lacks fold audits for {(crop, model)}")
                    fold_ids: set[int] = set()
                    fold_test_rows = 0
                    for fold in folds:
                        fold_id = fold.get("fold")
                        if isinstance(fold_id, bool) or not isinstance(fold_id, int) or fold_id in fold_ids:
                            raise ValueError(f"Spatial fold IDs are invalid for {(crop, model)}")
                        fold_ids.add(fold_id)
                        _positive_integer(fold.get("train_rows"), "fold train_rows")
                        fold_test_rows += _positive_integer(fold.get("test_rows"), "fold test_rows")
                        _positive_integer(fold.get("matrix_rank"), "fold matrix_rank")
                        condition = _finite_number(fold.get("condition_number"), "fold condition_number")
                        if condition < 1:
                            raise ValueError("Fold condition number cannot be below one")
                    if fold_test_rows != test_rows[0]:
                        raise ValueError(f"Spatial fold rows do not reconcile for {(crop, model)}")
                else:
                    _positive_integer(row.get("train_rows"), "train_rows")
                    purged = _nonnegative_integer(row.get("purged_train_rows"), "purged_train_rows")
                    overlap = _nonnegative_integer(row.get("endpoint_overlap_count"), "endpoint_overlap_count")
                    if overlap != 0:
                        raise ValueError(f"Yield endpoints overlap for {(crop, model, holdout)}")
                    if row.get("purge_rule") != PURGE_RULES[holdout]:
                        raise ValueError(f"Unrecognized purge rule for {(crop, model, holdout)}")
                    _positive_integer(row.get("matrix_rank"), "matrix_rank")
                    condition = _finite_number(row.get("condition_number"), "condition_number")
                    if condition < 1:
                        raise ValueError("Condition number cannot be below one")
                ranked.append({"model": model, "rmse": rmse, "mae": mae, "rmse_improvement_vs_zero": improvement})
            if holdout != "spatial_block":
                train_rows = [row["train_rows"] for row in rows]
                purged_rows = [row["purged_train_rows"] for row in rows]
                if len(set(train_rows)) != 1 or len(set(purged_rows)) != 1:
                    raise ValueError(f"Purged split rows differ across models for {(crop, holdout)}")
            ranked.sort(key=lambda item: (item["rmse"], models.index(item["model"])))
            comparisons.append({
                "crop": crop,
                "holdout": holdout,
                "test_rows": test_rows[0],
                "zero_change_rmse": benchmarks[0],
                "best_model_descriptive_only": ranked[0]["model"],
                "best_rmse": ranked[0]["rmse"],
                "best_rmse_improvement_vs_zero": ranked[0]["rmse_improvement_vs_zero"],
                "all_models_beat_zero": all(item["rmse_improvement_vs_zero"] > 0 for item in ranked),
                "ranked_models": ranked,
            })

    summary = {
        "status": SUMMARY_STATUS,
        "audit_status": STATUS,
        "spec_sha256": spec_sha256,
        "crops": sorted(expected_crops),
        "models": models,
        "holdouts": list(HOLDOUTS),
        "nonspatial_split_contract": NONSPATIAL_SPLIT_CONTRACT,
        "input_basis_mode": basis_mode,
        "response_basis_contract_id": contract_id,
        "n_level_rows": n_levels,
        "n_observed_level_rows": n_observed,
        "n_consecutive_pairs": n_pairs,
        "comparisons": comparisons,
        "warning": (
            "Best-model labels are descriptive within this fixed diagnostic. "
            "They are not a selection rule, causal estimate, response export, or SCC authorization."
        ),
    }
    if validated_years is not None:
        summary.update({
            "harvest_year_start": expected_year_start,
            "harvest_year_end": expected_year_end,
            "harvest_years": validated_years,
        })
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit", required=True)
    parser.add_argument("--spec", default="config/response_evaluation_spec.toml")
    parser.add_argument("--expected-crop", action="append", required=True)
    parser.add_argument("--expected-year-start", type=int)
    parser.add_argument("--expected-year-end", type=int)
    parser.add_argument(
        "--expected-input-basis-mode",
        choices=[RAW_REGIME_INPUT, PREBUILT_WEIGHTED_INPUT],
    )
    parser.add_argument("--summary-out")
    args = parser.parse_args()
    models, digest = load_spec(Path(args.spec))
    audit = json.loads(Path(args.audit).read_text(encoding="utf-8"))
    summary = validate_audit(
        audit, models, digest, args.expected_crop,
        args.expected_year_start, args.expected_year_end,
        args.expected_input_basis_mode,
    )
    rendered = json.dumps(summary, indent=2, sort_keys=True) + "\n"
    if args.summary_out:
        output = Path(args.summary_out)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()
