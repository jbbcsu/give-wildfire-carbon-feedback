#!/usr/bin/env python3
"""Nested whole-ESM/whole-scenario evaluation with physical response links."""
from __future__ import annotations

import argparse
import hashlib
import json
import tomllib
from pathlib import Path

import numpy as np
import pandas as pd

from evaluate_isimip3b_structural_feature_response import (
    ESMS,
    FEATURES,
    FUTURE_SCENARIOS,
    design_matrix,
    inner_folds,
    prepare_training,
    require,
    ridge_predict,
)
from validate_isimip3b_physical_link_feature_response_contract import BOUNDED, COMPOSITION, POSITIVE, validate


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def feature_slice(feature: str, n_cells: int) -> slice:
    index = FEATURES.index(feature)
    return slice(index * n_cells, (index + 1) * n_cells)


def transform_response(response: np.ndarray, n_cells: int, links: dict[str, object]) -> tuple[np.ndarray, int]:
    require(response.shape[1] == len(FEATURES) * n_cells, "response width changed")
    transformed = response.copy()
    floor = float(links["positive_log_floor"])
    epsilon = float(links["bounded_logit_epsilon"])
    replacement = float(links["composition_zero_replacement"])
    for feature in POSITIVE:
        values = response[:, feature_slice(feature, n_cells)]
        require((values >= 0).all(), f"{feature} has negative training values")
        transformed[:, feature_slice(feature, n_cells)] = np.log(values + floor)
    for feature in BOUNDED:
        values = response[:, feature_slice(feature, n_cells)]
        require(((values >= 0) & (values <= 1)).all(), f"{feature} is outside [0,1]")
        clipped = np.clip(values, epsilon, 1 - epsilon)
        transformed[:, feature_slice(feature, n_cells)] = np.log(clipped / (1 - clipped))

    stage = np.stack([response[:, feature_slice(feature, n_cells)] for feature in COMPOSITION], axis=2)
    require((stage >= 0).all(), "stage composition has negative values")
    totals = stage.sum(axis=2, keepdims=True)
    valid = np.isclose(totals, 1.0, atol=1e-9) | np.isclose(totals, 0.0, atol=1e-12)
    require(valid.all(), "stage shares do not sum to zero or one")
    dry = np.isclose(totals, 0.0, atol=1e-12)
    composition = np.divide(stage, totals, out=np.full_like(stage, 1 / 3), where=~dry)
    composition = composition + replacement
    composition /= composition.sum(axis=2, keepdims=True)
    logs = np.log(composition)
    clr = logs - logs.mean(axis=2, keepdims=True)
    for index, feature in enumerate(COMPOSITION):
        transformed[:, feature_slice(feature, n_cells)] = clr[:, :, index]
    require(np.isfinite(transformed).all(), "transformed response is nonfinite")
    return transformed, int(dry.sum())


def inverse_response(transformed: np.ndarray, n_cells: int, links: dict[str, object]) -> np.ndarray:
    require(transformed.shape[1] == len(FEATURES) * n_cells, "transformed width changed")
    output = transformed.copy()
    for feature in POSITIVE:
        values = transformed[:, feature_slice(feature, n_cells)]
        require((values < 700).all(), f"{feature} inverse-log prediction overflow")
        output[:, feature_slice(feature, n_cells)] = np.exp(values)
    for feature in BOUNDED:
        values = transformed[:, feature_slice(feature, n_cells)]
        logistic = np.empty_like(values)
        positive = values >= 0
        logistic[positive] = 1 / (1 + np.exp(-values[positive]))
        exponential = np.exp(values[~positive])
        logistic[~positive] = exponential / (1 + exponential)
        output[:, feature_slice(feature, n_cells)] = logistic

    stage = np.stack([transformed[:, feature_slice(feature, n_cells)] for feature in COMPOSITION], axis=2)
    stage -= stage.max(axis=2, keepdims=True)
    exponential = np.exp(stage)
    composition = exponential / exponential.sum(axis=2, keepdims=True)
    for index, feature in enumerate(COMPOSITION):
        output[:, feature_slice(feature, n_cells)] = composition[:, :, index]
    require(np.isfinite(output).all(), "inverse-link predictions are nonfinite")
    return output


def choose_lambda(lambdas: list[float], scores: np.ndarray) -> float:
    minimum = float(scores.min())
    eligible = [value for value, score in zip(lambdas, scores) if score <= minimum * 1.001]
    return max(eligible)


def select_lambdas(
    observations: pd.DataFrame,
    original: np.ndarray,
    transformed: np.ndarray,
    n_cells: int,
    links: dict[str, object],
    outer_type: str,
    outer_id: str,
    lambdas: list[float],
) -> dict[str, float]:
    squared_errors = np.zeros((len(lambdas), len(FEATURES)))
    counts = np.zeros(len(FEATURES), dtype=int)
    for train, test in inner_folds(observations, outer_type, outer_id):
        matrix, penalty = design_matrix(observations, train)
        for lambda_index, value in enumerate(lambdas):
            prediction_link = ridge_predict(matrix[train], transformed[train], matrix[test], penalty, value)
            prediction = inverse_response(prediction_link, n_cells, links)
            errors = (prediction - original[test]) ** 2
            for feature_index, feature in enumerate(FEATURES):
                block = feature_slice(feature, n_cells)
                squared_errors[lambda_index, feature_index] += float(errors[:, block].sum())
        counts += len(original[test]) * n_cells
    require((counts > 0).all(), "nested validation counts are empty")
    rmse = np.sqrt(squared_errors / counts[None, :])
    selected = {feature: choose_lambda(lambdas, rmse[:, index]) for index, feature in enumerate(FEATURES)}
    composition_error = squared_errors[:, [FEATURES.index(feature) for feature in COMPOSITION]].sum(axis=1)
    composition_count = counts[[FEATURES.index(feature) for feature in COMPOSITION]].sum()
    composition_lambda = choose_lambda(lambdas, np.sqrt(composition_error / composition_count))
    for feature in COMPOSITION:
        selected[feature] = composition_lambda
    return selected


def evaluate(
    observations: pd.DataFrame,
    original: np.ndarray,
    transformed: np.ndarray,
    n_cells: int,
    links: dict[str, object],
    lambdas: list[float],
) -> pd.DataFrame:
    rows = []
    outer = [("whole_esm", esm) for esm in ESMS] + [("whole_scenario", scenario) for scenario in FUTURE_SCENARIOS]
    for outer_type, outer_id in outer:
        column = "esm_id" if outer_type == "whole_esm" else "scenario"
        test = observations[column].eq(outer_id).to_numpy()
        train = ~test
        selected = select_lambdas(observations, original, transformed, n_cells, links, outer_type, outer_id, lambdas)
        matrix, penalty = design_matrix(observations, train)
        prediction_link = np.empty_like(original[test])
        for feature in FEATURES:
            block = feature_slice(feature, n_cells)
            prediction_link[:, block] = ridge_predict(
                matrix[train], transformed[train, block], matrix[test], penalty, selected[feature]
            )
        prediction = inverse_response(prediction_link, n_cells, links)
        stage_prediction = np.stack([prediction[:, feature_slice(feature, n_cells)] for feature in COMPOSITION], axis=2)
        stage_sum_error = np.abs(stage_prediction.sum(axis=2) - 1)
        for feature in FEATURES:
            block = feature_slice(feature, n_cells)
            y_train, y_test = original[train, block], original[test, block]
            estimate = prediction[:, block]
            benchmark = np.broadcast_to(y_train.mean(axis=0), y_test.shape)
            rmse = float(np.sqrt(np.mean((estimate - y_test) ** 2)))
            benchmark_rmse = float(np.sqrt(np.mean((benchmark - y_test) ** 2)))
            require(benchmark_rmse > 0, "cell-mean benchmark RMSE is zero")
            nonnegative = feature in POSITIVE or feature in COMPOSITION or feature in BOUNDED
            bounded_unit = feature in COMPOSITION or feature in BOUNDED
            rows.append({
                "holdout_type": outer_type,
                "holdout_id": outer_id,
                "feature_family": feature,
                "link": "identity" if feature == "tmean_c" else "positive_log" if feature in POSITIVE else "centered_log_ratio" if feature in COMPOSITION else "bounded_logit",
                "selected_lambda": selected[feature],
                "n_test_values": int(y_test.size),
                "rmse": rmse,
                "benchmark_rmse": benchmark_rmse,
                "rmse_ratio_to_cell_mean": rmse / benchmark_rmse,
                "negative_prediction_count": int((estimate < 0).sum()) if nonnegative else 0,
                "above_one_prediction_count": int((estimate > 1).sum()) if bounded_unit else 0,
                "maximum_stage_composition_sum_error": float(stage_sum_error.max()) if feature in COMPOSITION else 0.0,
            })
    output = pd.DataFrame(rows)
    require(len(output) == (len(ESMS) + len(FUTURE_SCENARIOS)) * len(FEATURES), "outer holdout product is incomplete")
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--holdouts-out", type=Path, required=True)
    parser.add_argument("--audit-out", type=Path, required=True)
    args = parser.parse_args()
    contract_receipt = validate(args.config, args.root)
    config = tomllib.loads(args.config.read_text(encoding="utf-8"))
    training_path = args.root / str(config["training_artifact"])
    frame = pd.read_parquet(training_path)
    observations, original, n_cells = prepare_training(frame)
    links = config["response_links"]
    transformed, all_zero_compositions = transform_response(original, n_cells, links)
    lambdas = [float(value) for value in config["regularization"]["lambda_grid"]]
    holdouts = evaluate(observations, original, transformed, n_cells, links, lambdas)
    args.holdouts_out.parent.mkdir(parents=True, exist_ok=True)
    holdouts.to_csv(args.holdouts_out, index=False)
    ratios = holdouts.rmse_ratio_to_cell_mean
    criteria = {
        "maximum_rmse_ratio_passed": bool(ratios.max() <= float(config["promotion"]["maximum_outer_holdout_rmse_ratio_to_cell_mean"])),
        "median_rmse_ratio_passed": bool(ratios.median() <= float(config["promotion"]["median_outer_holdout_rmse_ratio_to_cell_mean"])),
        "every_feature_both_holdout_types_passed": bool((holdouts.groupby(["holdout_type", "feature_family"]).rmse_ratio_to_cell_mean.max() <= 1).all()),
        "physical_prediction_bounds_passed": bool((holdouts.negative_prediction_count == 0).all() and (holdouts.above_one_prediction_count == 0).all()),
        "stage_composition_sum_passed": bool(holdouts.maximum_stage_composition_sum_error.max() <= 1e-12),
    }
    audit = {
        "schema": "isimip3b_physical_link_feature_response_holdout_audit_v1",
        "status": "evaluated_not_promoted",
        "contract": contract_receipt["config"],
        "implementation": {"path": Path(__file__).resolve().relative_to(args.root.resolve()).as_posix(), "sha256": sha256(Path(__file__))},
        "training": {"path": config["training_artifact"], "sha256": sha256(training_path), "input_rows": len(frame), "retained_observations": len(observations), "cells": n_cells, "response_values": int(original.size), "all_zero_stage_compositions": all_zero_compositions},
        "holdouts": {"artifact_name": args.holdouts_out.name, "sha256": sha256(args.holdouts_out), "comparisons": len(holdouts)},
        "results": {
            "physical_link_model_better_than_cell_mean_count": int((ratios < 1).sum()),
            "median_rmse_ratio_to_cell_mean": float(ratios.median()),
            "maximum_rmse_ratio_to_cell_mean": float(ratios.max()),
            "negative_prediction_count": int(holdouts.negative_prediction_count.sum()),
            "above_one_prediction_count": int(holdouts.above_one_prediction_count.sum()),
            "maximum_stage_composition_sum_error": float(holdouts.maximum_stage_composition_sum_error.max()),
        },
        "promotion_criteria": criteria,
        "all_holdout_criteria_passed": all(criteria.values()),
        "actual_fair_candidate_path_evaluated": False,
        "human_review_completed": False,
        "production_promoted": False,
        "response_estimation_authorized": False,
        "damage_or_scc_authorized": False,
    }
    args.audit_out.parent.mkdir(parents=True, exist_ok=True)
    args.audit_out.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"physical-link feature response: {len(holdouts)} comparisons, improved {(ratios < 1).sum()}, median ratio {ratios.median():.6f}, max {ratios.max():.6f}")


if __name__ == "__main__":
    main()
