#!/usr/bin/env python3
"""Run the locked, nonproduction direct-precipitation/scPDSI diagnostic.

Only aggregate predictive metrics are emitted. Coefficients, fitted values,
and row predictions are deliberately never returned or written.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from pandas.api.types import is_bool_dtype

from allocate_outcome_exposures import read_table
from build_direct_scpdsi_diagnostic_inputs import (
    COMMON_OUTPUT_FEATURES,
    CONTRACT_ID,
    DIRECT_OUTPUT_FEATURES,
    FALSE_GATES,
    HOLDOUT_IDS,
    KEYS,
    MODEL_IDS,
    OUTCOME,
    SCPDSI_OUTPUT_FEATURES,
    load_config,
    sha256_file,
)


CONTRACT_FIELDS = [
    "diagnostic_contract_id", "diagnostic_view", "family_mutually_exclusive",
    "families_stacked", "coefficients_emitted", "predictions_emitted",
    "diagnostic_fit_authorized", *FALSE_GATES,
]
FORBIDDEN_RESULT_KEY_TOKENS = (
    "coefficient", "coef", "beta", "prediction", "fitted_value",
    "estimate", "marginal_effect", "response_draw", "damage", "scc",
)


def _require_bool(frame: pd.DataFrame, column: str, expected: bool, label: str) -> None:
    if column not in frame or not is_bool_dtype(frame[column].dtype) or frame[column].isna().any() or not frame[column].eq(expected).all():
        raise ValueError(f"{label} {column} must be exactly {str(expected).lower()}")


def _feature_names() -> dict[str, list[str]]:
    return {
        "direct": DIRECT_OUTPUT_FEATURES,
        "scpdsi": SCPDSI_OUTPUT_FEATURES,
        "common": COMMON_OUTPUT_FEATURES,
    }


def _split_columns() -> list[str]:
    components = ["stress_direct_dry", "stress_direct_wet", "stress_scpdsi_drought", "stress_heat", "stress_union"]
    return [
        "spatial_block_5deg", "spatial_fold", "temporal_role", *components,
        "start_endpoint_id", "end_endpoint_id", *(f"train_eligible_{name}" for name in components),
    ]


def validate_view_frames(views: dict[str, pd.DataFrame]) -> pd.DataFrame:
    if set(views) != {"direct", "scpdsi", "common", "split"}:
        raise ValueError("Exactly the direct, scPDSI, common-control, and split views are required")
    features = _feature_names()
    expected_views = {
        "direct": "direct_quantity",
        "scpdsi": "historical_scpdsi",
        "common": "common_heat_temperature_controls",
        "split": "outcome_blind_outer_split_plan",
    }
    core: pd.DataFrame | None = None
    for name, frame in views.items():
        expected_features = _split_columns() if name == "split" else features[name]
        expected_columns = KEYS + [OUTCOME] + expected_features + CONTRACT_FIELDS
        if list(frame.columns) != expected_columns:
            raise ValueError(f"{name} view schema or column order differs from the locked contract")
        if frame.empty or frame.duplicated(KEYS).any() or frame[KEYS].isna().any().any():
            raise ValueError(f"{name} view has invalid pair support")
        if set(frame["diagnostic_contract_id"].astype(str)) != {CONTRACT_ID}:
            raise ValueError(f"{name} view contract identity differs")
        if set(frame["diagnostic_view"].astype(str)) != {expected_views[name]}:
            raise ValueError(f"{name} view identity differs")
        _require_bool(frame, "family_mutually_exclusive", True, name)
        _require_bool(frame, "families_stacked", False, name)
        _require_bool(frame, "coefficients_emitted", False, name)
        _require_bool(frame, "predictions_emitted", False, name)
        _require_bool(frame, "diagnostic_fit_authorized", True, name)
        for gate in FALSE_GATES:
            _require_bool(frame, gate, False, name)
        this_core = frame[KEYS + [OUTCOME]].reset_index(drop=True)
        if core is None:
            core = this_core
        elif not this_core.equals(core):
            raise ValueError("Views do not have exact pair/outcome equality")
    assert core is not None
    if not views["direct"].columns.intersection(SCPDSI_OUTPUT_FEATURES).empty:
        raise ValueError("Direct view contains scPDSI leakage")
    if not views["scpdsi"].columns.intersection(DIRECT_OUTPUT_FEATURES).empty:
        raise ValueError("scPDSI view contains direct-weather leakage")
    if any(name.startswith(("direct__", "scpdsi__")) for name in views["common"].columns):
        raise ValueError("Common-control view contains a moisture family")
    for name, names in features.items():
        numeric = views[name][names]
        if any(is_bool_dtype(numeric[column].dtype) or not pd.api.types.is_numeric_dtype(numeric[column].dtype) for column in names):
            raise ValueError(f"{name} model features must have non-Boolean numeric dtypes")
        if not np.isfinite(numeric.to_numpy(dtype=float)).all():
            raise ValueError(f"{name} model features are nonfinite")
    split = views["split"]
    if not split["end_year"].eq(split["start_year"] + 1).all():
        raise ValueError("Cross-period or nonconsecutive pair found")
    episode_ranges = {"early": (1982, 1989), "later": (2012, 2016)}
    for episode, group in split.groupby("episode", observed=True):
        if str(episode) not in episode_ranges:
            raise ValueError("Unknown episode in split view")
        lo, hi = episode_ranges[str(episode)]
        if group["start_year"].min() < lo or group["end_year"].max() > hi:
            raise ValueError("Cross-period pairing attempt")
    if not split["spatial_fold"].isin(range(5)).all():
        raise ValueError("Spatial fold is outside 0..4")
    block_folds = split.groupby(["crop", "spatial_block_5deg"], observed=True)["spatial_fold"].nunique()
    if not block_folds.eq(1).all():
        raise ValueError("A 5-degree spatial block leaks across folds")
    if not split["temporal_role"].eq(np.where(split["episode"].eq("early"), "train", "test")).all():
        raise ValueError("Temporal roles leak or differ from the locked episodes")
    for flag in ["stress_direct_dry", "stress_direct_wet", "stress_scpdsi_drought", "stress_heat", "stress_union"]:
        if not is_bool_dtype(split[flag].dtype) or split[flag].isna().any():
            raise ValueError(f"Split {flag} must be nonmissing Boolean")
        eligible = f"train_eligible_{flag}"
        if not is_bool_dtype(split[eligible].dtype) or split[eligible].isna().any():
            raise ValueError(f"Split {eligible} must be nonmissing Boolean")
        endpoints = set(split.loc[split[flag], "start_endpoint_id"]) | set(split.loc[split[flag], "end_endpoint_id"])
        train = split.loc[split[eligible]]
        if train["start_endpoint_id"].isin(endpoints).any() or train["end_endpoint_id"].isin(endpoints).any():
            raise ValueError(f"Endpoint overlap in purged training for {flag}")
        exact_eligible = ~(split["start_endpoint_id"].isin(endpoints) | split["end_endpoint_id"].isin(endpoints))
        if not split[eligible].equals(exact_eligible):
            raise ValueError(f"Endpoint purge differs from exact recomputation for {flag}")
    component_union = split[["stress_direct_dry", "stress_direct_wet", "stress_scpdsi_drought", "stress_heat"]].any(axis=1)
    if not split["stress_union"].equals(component_union):
        raise ValueError("Stress union differs from its components")
    return core


def _pair_hash(frame: pd.DataFrame) -> str:
    payload = frame[KEYS].to_json(orient="records", double_precision=15).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _masks(split: pd.DataFrame, holdout: str) -> tuple[pd.Series, pd.Series]:
    if holdout.startswith("spatial_fold_"):
        fold = int(holdout.rsplit("_", 1)[1])
        test = split["spatial_fold"].eq(fold)
        train = ~test
    elif holdout == "temporal_early_to_later_retrospective":
        train = split["temporal_role"].eq("train")
        test = split["temporal_role"].eq("test")
    elif holdout.startswith("stress_"):
        flag = holdout
        test = split[flag]
        train = split[f"train_eligible_{flag}"]
    else:
        raise ValueError(f"Unknown holdout {holdout}")
    if (train & test).any() or not train.any() or not test.any():
        raise ValueError(f"Holdout {holdout} has overlap or empty train/test support")
    if holdout.startswith("stress_"):
        train_endpoints = set(split.loc[train, "start_endpoint_id"]) | set(split.loc[train, "end_endpoint_id"])
        test_endpoints = set(split.loc[test, "start_endpoint_id"]) | set(split.loc[test, "end_endpoint_id"])
        if train_endpoints & test_endpoints:
            raise ValueError(f"Endpoint overlap in {holdout}")
    return train, test


def _metrics(observed: np.ndarray, predicted: np.ndarray) -> dict[str, Any]:
    residual = observed - predicted
    sse = float(np.dot(residual, residual))
    sae = float(np.abs(residual).sum())
    centered = observed - observed.mean()
    sst = float(np.dot(centered, centered))
    return {
        "n": int(len(observed)),
        "mean_observed": float(observed.mean()),
        "sum_squared_error": sse,
        "sum_absolute_error": sae,
        "sum_squared_total": sst,
        "rmse": float(np.sqrt(sse / len(observed))),
        "mae": float(sae / len(observed)),
        "r2": None if sst == 0 else float(1.0 - sse / sst),
    }


def _fit_metrics(
    data: pd.DataFrame, features: list[str], train: pd.Series, test: pd.Series
) -> tuple[dict[str, Any], dict[str, dict[str, Any]], dict[str, Any]]:
    x_train = data.loc[train, features].to_numpy(dtype=float)
    x_test = data.loc[test, features].to_numpy(dtype=float)
    y_train = data.loc[train, OUTCOME].to_numpy(dtype=float)
    y_test = data.loc[test, OUTCOME].to_numpy(dtype=float)
    if features:
        means = x_train.mean(axis=0)
        scales = x_train.std(axis=0, ddof=0)
        if not np.isfinite(means).all() or not np.isfinite(scales).all() or (scales <= 1e-12).any():
            raise ValueError("Training-only standardization found a zero/nonfinite scale")
        x_train = (x_train - means) / scales
        x_test = (x_test - means) / scales
    x_train = np.column_stack([np.ones(len(x_train)), x_train])
    x_test = np.column_stack([np.ones(len(x_test)), x_test])
    if len(y_train) <= x_train.shape[1] or np.linalg.matrix_rank(x_train) != x_train.shape[1]:
        raise ValueError("OLS training design is underidentified or rank deficient")
    condition_number = float(np.linalg.cond(x_train))
    if not np.isfinite(condition_number) or condition_number > 1e10:
        raise ValueError("OLS training design is numerically ill conditioned")
    internal_solution = np.linalg.lstsq(x_train, y_train, rcond=None)[0]
    try:
        with np.errstate(over="raise", invalid="raise", divide="raise"):
            # Elementwise reduction avoids platform BLAS floating-status noise
            # observed for small matrix-vector products while preserving exact
            # linear-prediction arithmetic.
            predicted = np.sum(x_test * internal_solution[None, :], axis=1)
    except FloatingPointError as error:
        raise ValueError("OLS prediction arithmetic overflowed") from error
    if not np.isfinite(internal_solution).all() or not np.isfinite(predicted).all():
        raise ValueError("OLS produced nonfinite internal values")
    pooled = _metrics(y_test, predicted)
    test_episode = data.loc[test, "episode"].to_numpy()
    by_episode = {
        episode: _metrics(y_test[test_episode == episode], predicted[test_episode == episode])
        for episode in sorted(set(test_episode))
    }
    training = {
        "n": int(len(y_train)),
        "feature_count_excluding_intercept": len(features),
        "training_only_centering_scaling_applied": True,
        "design_full_column_rank": True,
        "condition_number_below_1e10": True,
    }
    return pooled, by_episode, training


def _reject_forbidden_result_keys(value: Any, path: str = "result") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            lowered = key.lower()
            if any(token in lowered for token in FORBIDDEN_RESULT_KEY_TOKENS):
                # Exact false authorization fields are the only permitted uses.
                if key not in FALSE_GATES and key not in {"coefficients_emitted", "predictions_emitted"}:
                    raise ValueError(f"Forbidden coefficient/prediction/effect-like result field at {path}.{key}")
            _reject_forbidden_result_keys(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_forbidden_result_keys(child, f"{path}[{index}]")


def evaluate_views(config_path: Path, views: dict[str, pd.DataFrame]) -> dict[str, Any]:
    config = load_config(config_path)
    validate_view_frames(views)
    data = views["common"][KEYS + [OUTCOME] + COMMON_OUTPUT_FEATURES].merge(
        views["direct"][KEYS + DIRECT_OUTPUT_FEATURES], on=KEYS, validate="one_to_one"
    ).merge(
        views["scpdsi"][KEYS + SCPDSI_OUTPUT_FEATURES], on=KEYS, validate="one_to_one"
    ).merge(
        views["split"][KEYS + _split_columns()], on=KEYS, validate="one_to_one"
    )
    results: list[dict[str, Any]] = []
    model_specs = {model["id"]: model for model in config["models"]}
    for crop in ("mai", "soy"):
        crop_data = data.loc[data["crop"].eq(crop)].reset_index(drop=True)
        if crop_data.empty:
            raise ValueError(f"No pair support for crop {crop}")
        for model_id in MODEL_IDS:
            candidate = model_specs[model_id]["candidate_features"]
            features = [*COMMON_OUTPUT_FEATURES, *candidate]
            for holdout in HOLDOUT_IDS:
                train, test = _masks(crop_data, holdout)
                pooled, by_episode, training = _fit_metrics(crop_data, features, train, test)
                results.append({
                    "crop": crop,
                    "model_id": model_id,
                    "moisture_family": model_specs[model_id]["family"],
                    "holdout_id": holdout,
                    "test_pair_key_sha256": _pair_hash(crop_data.loc[test]),
                    "test_episode_prevalence": {
                        episode: float(value)
                        for episode, value in crop_data.loc[test, "episode"].value_counts(normalize=True, sort=False).sort_index().items()
                    },
                    "training": training,
                    "pooled_metrics": pooled,
                    "metrics_by_episode": by_episode,
                })
    expected_count = 2 * len(MODEL_IDS) * len(HOLDOUT_IDS)
    if len(results) != expected_count:
        raise AssertionError("Full crop-model-holdout result product is incomplete")
    result: dict[str, Any] = {
        "schema_version": 1,
        "contract_id": CONTRACT_ID,
        "status": "nonproduction_predictive_diagnostic_completed",
        "estimator": "ols_first_differences",
        "models": [
            {
                "id": model["id"],
                "family": model["family"],
                "common_controls": COMMON_OUTPUT_FEATURES,
                "candidate_features": model["candidate_features"],
            }
            for model in config["models"]
        ],
        "holdouts": HOLDOUT_IDS,
        "results": results,
        "result_count": expected_count,
        "full_model_holdout_product_complete": True,
        "metric_arithmetic_recomputed_by_validator": False,
        "training_only_centering_scaling": True,
        "observation_weighting": config["observation_weighting"],
        "loss_metrics": config["loss_metrics"],
        "model_selection_rule": config["model_selection_rule"],
        "spatial_validation_scope": config["spatial_validation_scope"],
        "scpdsi_calibration_period": config["scpdsi_calibration_period"],
        "scpdsi_temporal_evaluation": config["scpdsi_temporal_evaluation"],
        "temporal_holdout_prospective": config["temporal_holdout_prospective"],
        "views_joined_on_exact_pair_keys_only": True,
        "family_mutually_exclusive": True,
        "families_stacked": False,
        "coefficients_emitted": False,
        "predictions_emitted": False,
        "diagnostic_fit_authorized": True,
        **{gate: False for gate in FALSE_GATES},
    }
    _reject_forbidden_result_keys(result)
    return result


def evaluate_files(
    config_path: Path,
    input_audit_path: Path,
    view_paths: dict[str, Path],
    result_path: Path,
) -> dict[str, Any]:
    audit = json.loads(input_audit_path.read_text(encoding="utf-8"))
    if audit.get("contract_id") != CONTRACT_ID or audit.get("config_sha256") != sha256_file(config_path):
        raise ValueError("Input audit contract or config hash differs")
    if set(audit.get("output_files", {})) != set(view_paths):
        raise ValueError("Input audit output-file registry differs")
    for name, path in view_paths.items():
        record = audit["output_files"][name]
        if record != {"path": str(path), "sha256": sha256_file(path)}:
            raise ValueError(f"Input audit path or SHA-256 differs for {name}")
    result = evaluate_views(config_path, {name: read_table(path) for name, path in view_paths.items()})
    result["config_file"] = str(config_path)
    result["config_sha256"] = sha256_file(config_path)
    result["input_audit_file"] = str(input_audit_path)
    result["input_audit_sha256"] = sha256_file(input_audit_path)
    result["input_view_files"] = {
        name: {"path": str(path), "sha256": sha256_file(path)} for name, path in view_paths.items()
    }
    _reject_forbidden_result_keys(result)
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--input-audit", required=True)
    parser.add_argument("--direct-view", required=True)
    parser.add_argument("--scpdsi-view", required=True)
    parser.add_argument("--common-view", required=True)
    parser.add_argument("--split-view", required=True)
    parser.add_argument("--result-out", required=True)
    args = parser.parse_args()
    result = evaluate_files(
        Path(args.config), Path(args.input_audit),
        {"direct": Path(args.direct_view), "scpdsi": Path(args.scpdsi_view),
         "common": Path(args.common_view), "split": Path(args.split_view)},
        Path(args.result_out),
    )
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
