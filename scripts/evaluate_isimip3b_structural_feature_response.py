#!/usr/bin/env python3
"""Nested whole-ESM/whole-scenario evaluation of the preregistered response basis."""
from __future__ import annotations

import argparse
import hashlib
import json
import tomllib
from pathlib import Path

import numpy as np
import pandas as pd

from validate_isimip3b_structural_feature_response_contract import ESMS, FEATURES, SCENARIOS, validate


OBS_KEYS = ["esm_id", "member_id", "scenario", "year"]
CELL_KEYS = ["lat", "lon_360", "crop", "irrigation"]
FUTURE_SCENARIOS = [scenario for scenario in SCENARIOS if scenario != "historical"]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def prepare_training(frame: pd.DataFrame) -> tuple[pd.DataFrame, np.ndarray, int]:
    required = set(OBS_KEYS + CELL_KEYS + ["gmst_value_k", "gmst_esm_id", "gmst_member_id", "feature_family", "feature_value"])
    require(not (required - set(frame.columns)), "training schema is incomplete")
    require(set(frame.esm_id.astype(str)) == set(ESMS), "training ESM set changed")
    require(set(frame.scenario.astype(str)) == set(SCENARIOS), "training scenario set changed")
    require(set(frame.feature_family.astype(str)) == set(FEATURES), "training feature set changed")
    require((frame.esm_id.astype(str) == frame.gmst_esm_id.astype(str)).all(), "feature and GMST ESM differ")
    require((frame.member_id.astype(str) == frame.gmst_member_id.astype(str)).all(), "feature and GMST member differ")
    require(np.isfinite(frame[["gmst_value_k", "feature_value"]].to_numpy(float)).all(), "training values are nonfinite")
    require(not frame.duplicated(OBS_KEYS + CELL_KEYS + ["feature_family"]).any(), "training keys are duplicated")

    observations = frame[OBS_KEYS + ["gmst_value_k"]].drop_duplicates().sort_values(OBS_KEYS).reset_index(drop=True)
    require(not observations.duplicated(OBS_KEYS).any(), "GMST is not unique within observation keys")
    references = observations.loc[
        observations.scenario.eq("historical") & observations.year.between(2012, 2014)
    ].groupby("esm_id", observed=True).gmst_value_k.mean()
    require(set(references.index.astype(str)) == set(ESMS), "historical GMST references are incomplete")
    observations["gmst_anomaly_k"] = observations.gmst_value_k - observations.esm_id.map(references)
    observations["previous_year"] = observations.groupby(["esm_id", "scenario"], observed=True).year.shift()
    observations["previous_gmst"] = observations.groupby(["esm_id", "scenario"], observed=True).gmst_value_k.shift()
    observations["gmst_one_year_change_k"] = observations.gmst_value_k - observations.previous_gmst
    consecutive = observations.year - observations.previous_year == 1
    observations = observations.loc[consecutive].drop(columns=["previous_year", "previous_gmst"]).reset_index(drop=True)
    observations["years_since_2020"] = observations.year - 2020
    observations["obs_id"] = np.arange(len(observations))

    retained = frame.merge(observations[OBS_KEYS + ["obs_id"]], on=OBS_KEYS, how="inner", validate="many_to_one")
    cells = retained[CELL_KEYS].drop_duplicates().sort_values(CELL_KEYS).reset_index(drop=True)
    require(not cells.empty, "training has no retained cells")
    matrices = []
    for feature in FEATURES:
        subset = retained.loc[retained.feature_family.eq(feature), ["obs_id", *CELL_KEYS, "feature_value"]]
        wide = subset.pivot(index="obs_id", columns=CELL_KEYS, values="feature_value")
        wide = wide.reindex(index=observations.obs_id, columns=pd.MultiIndex.from_frame(cells))
        require(wide.shape == (len(observations), len(cells)) and not wide.isna().any().any(), f"{feature} product is not rectangular")
        matrices.append(wide.to_numpy(float))
    response = np.concatenate(matrices, axis=1)
    require(np.isfinite(response).all(), "response matrix is nonfinite")
    return observations, response, len(cells)


def design_matrix(observations: pd.DataFrame, train_mask: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    anomaly = observations.gmst_anomaly_k.to_numpy(float)
    change = observations.gmst_one_year_change_k.to_numpy(float)
    time = observations.years_since_2020.to_numpy(float)
    raw = np.column_stack([anomaly, change, time, anomaly**2, anomaly * change, anomaly * time])
    means = raw[train_mask].mean(axis=0)
    scales = raw[train_mask].std(axis=0)
    require(np.isfinite(means).all() and np.isfinite(scales).all() and (scales > 0).all(), "training predictor scale is invalid")
    standardized = (raw - means) / scales
    columns = [np.ones(len(observations)), *[standardized[:, index] for index in range(standardized.shape[1])]]
    for esm in ESMS:
        indicator = observations.esm_id.eq(esm).to_numpy(float)
        columns.extend([indicator, indicator * standardized[:, 0], indicator * standardized[:, 1]])
    matrix = np.column_stack(columns)
    penalty = np.ones(matrix.shape[1])
    penalty[0] = 0.0
    require(matrix.shape[1] == 22 and np.isfinite(matrix).all(), "design matrix changed")
    return matrix, penalty


def ridge_predict(x_train: np.ndarray, y_train: np.ndarray, x_test: np.ndarray, penalty: np.ndarray, value: float) -> np.ndarray:
    # Some sandboxed BLAS builds emit spurious floating-point status warnings
    # for finite matrix products, so suppress the status flag and validate the
    # resulting arrays explicitly.
    with np.errstate(over="ignore", divide="ignore", invalid="ignore"):
        gram = x_train.T @ x_train + value * np.diag(penalty)
        coefficients = np.linalg.solve(gram, x_train.T @ y_train)
        prediction = x_test @ coefficients
    require(np.isfinite(prediction).all(), "ridge predictions are nonfinite")
    return prediction


def inner_folds(observations: pd.DataFrame, outer_type: str, outer_id: str) -> list[tuple[np.ndarray, np.ndarray]]:
    outer_train = ~observations["esm_id" if outer_type == "whole_esm" else "scenario"].eq(outer_id).to_numpy()
    folds = []
    identities = FUTURE_SCENARIOS if outer_type == "whole_esm" else ESMS
    column = "scenario" if outer_type == "whole_esm" else "esm_id"
    for identity in identities:
        test = outer_train & observations[column].eq(identity).to_numpy()
        train = outer_train & ~observations[column].eq(identity).to_numpy()
        require(test.any() and train.any() and not (test & train).any(), "nested fold is empty or overlapping")
        folds.append((train, test))
    return folds


def select_lambdas(observations: pd.DataFrame, response: np.ndarray, n_cells: int, outer_type: str, outer_id: str, lambdas: list[float]) -> list[float]:
    squared_errors = np.zeros((len(lambdas), len(FEATURES)))
    counts = np.zeros(len(FEATURES), dtype=int)
    for train, test in inner_folds(observations, outer_type, outer_id):
        matrix, penalty = design_matrix(observations, train)
        y_train, y_test = response[train], response[test]
        for lambda_index, value in enumerate(lambdas):
            prediction = ridge_predict(matrix[train], y_train, matrix[test], penalty, value)
            errors = (prediction - y_test) ** 2
            for feature_index in range(len(FEATURES)):
                block = slice(feature_index * n_cells, (feature_index + 1) * n_cells)
                squared_errors[lambda_index, feature_index] += float(errors[:, block].sum())
        counts += len(y_test) * n_cells
    require((counts > 0).all(), "nested validation counts are empty")
    rmse = np.sqrt(squared_errors / counts[None, :])
    selected = []
    for feature_index in range(len(FEATURES)):
        minimum = float(rmse[:, feature_index].min())
        eligible = [value for value, score in zip(lambdas, rmse[:, feature_index]) if score <= minimum * 1.001]
        selected.append(max(eligible))
    return selected


def evaluate(observations: pd.DataFrame, response: np.ndarray, n_cells: int, lambdas: list[float]) -> pd.DataFrame:
    rows = []
    outer = [("whole_esm", esm) for esm in ESMS] + [("whole_scenario", scenario) for scenario in FUTURE_SCENARIOS]
    for outer_type, outer_id in outer:
        column = "esm_id" if outer_type == "whole_esm" else "scenario"
        test = observations[column].eq(outer_id).to_numpy()
        train = ~test
        selected = select_lambdas(observations, response, n_cells, outer_type, outer_id, lambdas)
        matrix, penalty = design_matrix(observations, train)
        for feature_index, feature in enumerate(FEATURES):
            block = slice(feature_index * n_cells, (feature_index + 1) * n_cells)
            y_train, y_test = response[train, block], response[test, block]
            prediction = ridge_predict(matrix[train], y_train, matrix[test], penalty, selected[feature_index])
            benchmark = np.broadcast_to(y_train.mean(axis=0), y_test.shape)
            rmse = float(np.sqrt(np.mean((prediction - y_test) ** 2)))
            benchmark_rmse = float(np.sqrt(np.mean((benchmark - y_test) ** 2)))
            require(benchmark_rmse > 0, "cell-mean benchmark RMSE is zero")
            nonnegative = feature != "tmean_c"
            bounded_unit = feature.startswith("stage") or feature in {"precipitation_timing_centroid", "precipitation_concentration_hhi"}
            rows.append({
                "holdout_type": outer_type, "holdout_id": outer_id, "feature_family": feature,
                "selected_lambda": selected[feature_index], "n_test_values": int(y_test.size),
                "rmse": rmse, "benchmark_rmse": benchmark_rmse,
                "rmse_ratio_to_cell_mean": rmse / benchmark_rmse,
                "negative_prediction_count": int((prediction < 0).sum()) if nonnegative else 0,
                "above_one_prediction_count": int((prediction > 1).sum()) if bounded_unit else 0,
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
    observations, response, n_cells = prepare_training(frame)
    lambdas = [float(value) for value in config["regularization"]["lambda_grid"]]
    holdouts = evaluate(observations, response, n_cells, lambdas)
    args.holdouts_out.parent.mkdir(parents=True, exist_ok=True)
    holdouts.to_csv(args.holdouts_out, index=False)
    ratios = holdouts.rmse_ratio_to_cell_mean
    criteria = {
        "maximum_rmse_ratio_passed": bool(ratios.max() <= float(config["promotion"]["maximum_outer_holdout_rmse_ratio_to_cell_mean"])),
        "median_rmse_ratio_passed": bool(ratios.median() <= float(config["promotion"]["median_outer_holdout_rmse_ratio_to_cell_mean"])),
        "every_feature_both_holdout_types_passed": bool((holdouts.groupby(["holdout_type", "feature_family"]).rmse_ratio_to_cell_mean.max() <= 1).all()),
        "physical_prediction_bounds_passed": bool((holdouts.negative_prediction_count == 0).all() and (holdouts.above_one_prediction_count == 0).all()),
    }
    audit = {
        "schema": "isimip3b_structural_feature_response_holdout_audit_v1",
        "status": "evaluated_not_promoted",
        "contract": contract_receipt["config"],
        "implementation": {"path": Path(__file__).resolve().relative_to(args.root.resolve()).as_posix(), "sha256": sha256(Path(__file__))},
        "training": {"path": config["training_artifact"], "sha256": sha256(training_path), "input_rows": len(frame), "retained_observations": len(observations), "cells": n_cells, "response_values": int(response.size)},
        "holdouts": {"artifact_name": args.holdouts_out.name, "sha256": sha256(args.holdouts_out), "comparisons": len(holdouts)},
        "results": {
            "gmst_model_better_than_cell_mean_count": int((ratios < 1).sum()),
            "median_rmse_ratio_to_cell_mean": float(ratios.median()),
            "maximum_rmse_ratio_to_cell_mean": float(ratios.max()),
            "negative_prediction_count": int(holdouts.negative_prediction_count.sum()),
            "above_one_prediction_count": int(holdouts.above_one_prediction_count.sum()),
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
    print(f"structural feature response: {len(holdouts)} comparisons, improved {(ratios < 1).sum()}, median ratio {ratios.median():.6f}, max {ratios.max():.6f}")


if __name__ == "__main__":
    main()
