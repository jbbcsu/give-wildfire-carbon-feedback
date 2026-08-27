#!/usr/bin/env python3
"""Paired cluster-bootstrap sensitivity for spatial out-of-fold losses.

The script refits the existing five spatial-fold models only to reconstruct
their held-out scores in memory. It never writes row scores, row losses,
regression parameters, or bootstrap draws. The bootstrap resamples fixed
out-of-fold loss aggregates, so it does not include training-sample
re-estimation uncertainty.
"""
from __future__ import annotations

import argparse
import json
import os
import tomllib
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from allocate_outcome_exposures import read_table
from build_direct_scpdsi_diagnostic_inputs import (
    COMMON_OUTPUT_FEATURES,
    DIRECT_OUTPUT_FEATURES,
    FALSE_GATES,
    KEYS,
    MODEL_IDS,
    OUTCOME,
    SCPDSI_OUTPUT_FEATURES,
    sha256_file,
)
from evaluate_direct_scpdsi_predictive_diagnostic import (
    _masks,
    _metrics,
    _reject_forbidden_result_keys,
    validate_view_frames,
)
from validate_direct_scpdsi_predictive_diagnostic import (
    _check_result_structure,
    validate_diagnostic,
)


CONTRACT_ID = "global_direct_scpdsi_paired_loss_uncertainty_v1"
EXPECTED_COMPARISONS = [
    ("direct_quantity_minus_controls", "direct_quantity", "controls_only"),
    ("scpdsi_mean_minus_controls", "scpdsi_mean", "controls_only"),
    (
        "scpdsi_seasonal_summary_minus_controls",
        "scpdsi_seasonal_summary",
        "controls_only",
    ),
    ("scpdsi_stage_means_minus_controls", "scpdsi_stage_means", "controls_only"),
    ("scpdsi_mean_minus_direct_quantity", "scpdsi_mean", "direct_quantity"),
    (
        "scpdsi_seasonal_summary_minus_direct_quantity",
        "scpdsi_seasonal_summary",
        "direct_quantity",
    ),
    (
        "scpdsi_stage_means_minus_direct_quantity",
        "scpdsi_stage_means",
        "direct_quantity",
    ),
]
BASE_PATH_FIELDS = [
    "base_config",
    "base_input_audit",
    "base_direct_view",
    "base_scpdsi_view",
    "base_common_view",
    "base_split_view",
    "base_result",
    "base_validation",
]


def _canonical_path(config_path: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else config_path.resolve().parents[1] / path


def load_sensitivity_config(config_path: Path) -> dict[str, Any]:
    config = tomllib.loads(config_path.read_text(encoding="utf-8"))
    expected_fields = {
        "schema_version",
        "contract_id",
        "description",
        *BASE_PATH_FIELDS,
        "score_basis",
        "resampling_scheme",
        "resampling_unit",
        "cluster_latitude_degrees",
        "cluster_longitude_degrees",
        "bootstrap_replicates",
        "random_seed",
        "interval_probabilities",
        "minimum_occupied_clusters_per_crop",
        "maximum_cluster_pair_share",
        "training_reestimated_within_bootstrap",
        "loss_metrics",
        "observation_weighting",
        "model_selection_rule",
        "diagnostic_fit_authorized",
        *FALSE_GATES,
        "comparisons",
    }
    if set(config) != expected_fields:
        raise ValueError(
            "Sensitivity config schema differs: "
            f"missing={sorted(expected_fields - set(config))}, "
            f"extra={sorted(set(config) - expected_fields)}"
        )
    if config["schema_version"] != 1 or config["contract_id"] != CONTRACT_ID:
        raise ValueError("Unexpected paired-loss sensitivity contract")
    for field in BASE_PATH_FIELDS:
        if not isinstance(config[field], str) or not config[field]:
            raise ValueError(f"{field} must name a nonempty base artifact path")
    locked = {
        "score_basis": "existing_five_fold_spatial_oof_scores_recomputed_in_memory",
        "resampling_scheme": "paired_pairs_cluster_bootstrap_fixed_oof_losses",
        "resampling_unit": "crop_by_10degree_lat_lon_cell_with_all_pairs_and_episodes_together",
        "cluster_latitude_degrees": 10,
        "cluster_longitude_degrees": 10,
        "bootstrap_replicates": 5000,
        "random_seed": 20260826,
        "interval_probabilities": [0.025, 0.975],
        "minimum_occupied_clusters_per_crop": 30,
        "maximum_cluster_pair_share": 0.10,
        "training_reestimated_within_bootstrap": False,
        "loss_metrics": ["rmse_difference", "mae_difference"],
        "observation_weighting": "equal_crop_grid_year_pair_weighting_not_area_production_or_welfare_weighted",
        "model_selection_rule": "none_nonproduction_sensitivity_reports_all_registered_comparisons",
        "diagnostic_fit_authorized": True,
    }
    for field, expected in locked.items():
        if config[field] != expected:
            raise ValueError(f"Sensitivity config {field} differs from its locked value")
    for gate in FALSE_GATES:
        if config[gate] is not False:
            raise ValueError(f"Sensitivity config {gate} must be exactly false")
    observed_comparisons = [
        (
            item.get("id"),
            item.get("candidate_model_id"),
            item.get("reference_model_id"),
        )
        for item in config["comparisons"]
    ]
    if observed_comparisons != EXPECTED_COMPARISONS or any(
        set(item) != {"id", "candidate_model_id", "reference_model_id"}
        for item in config["comparisons"]
    ):
        raise ValueError("Registered paired model comparisons differ")
    return config


def _base_paths(config_path: Path, config: dict[str, Any]) -> dict[str, Path]:
    return {field: _canonical_path(config_path, config[field]) for field in BASE_PATH_FIELDS}


def _load_validated_base(
    config_path: Path, config: dict[str, Any]
) -> tuple[dict[str, pd.DataFrame], dict[str, Any], dict[str, Path]]:
    paths = _base_paths(config_path, config)
    missing = [str(path) for path in paths.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Required validated base artifact is missing: {missing}")
    declared_view_paths = {
        "direct": Path(config["base_direct_view"]),
        "scpdsi": Path(config["base_scpdsi_view"]),
        "common": Path(config["base_common_view"]),
        "split": Path(config["base_split_view"]),
    }
    stored_audit = json.loads(paths["base_input_audit"].read_text(encoding="utf-8"))
    for name, declared_path in declared_view_paths.items():
        if stored_audit.get("output_files", {}).get(name, {}).get("path") != str(declared_path):
            raise ValueError(f"Sensitivity view path for {name} differs from the base audit literal")
    # The base audit intentionally binds the literal relative output paths.
    # Validate from the project root so those literals remain unchanged while
    # still allowing this sensitivity config itself to be passed absolutely.
    project_root = config_path.resolve().parents[1]
    previous_directory = Path.cwd()
    try:
        os.chdir(project_root)
        recomputed_receipt = validate_diagnostic(
            Path(config["base_config"]),
            Path(config["base_input_audit"]),
            declared_view_paths,
            Path(config["base_result"]),
        )
    finally:
        os.chdir(previous_directory)
    stored_receipt = json.loads(paths["base_validation"].read_text(encoding="utf-8"))
    if stored_receipt != recomputed_receipt:
        raise ValueError("Stored base validation differs from exact current recomputation")
    view_paths = {
        "direct": paths["base_direct_view"],
        "scpdsi": paths["base_scpdsi_view"],
        "common": paths["base_common_view"],
        "split": paths["base_split_view"],
    }
    views = {name: read_table(path) for name, path in view_paths.items()}
    validate_view_frames(views)
    base_result = json.loads(paths["base_result"].read_text(encoding="utf-8"))
    _check_result_structure(base_result)
    return views, base_result, paths


def _merge_views(views: dict[str, pd.DataFrame]) -> pd.DataFrame:
    split_columns = [
        "spatial_block_5deg",
        "spatial_fold",
        "temporal_role",
        "stress_direct_dry",
        "stress_direct_wet",
        "stress_scpdsi_drought",
        "stress_heat",
        "stress_union",
        "start_endpoint_id",
        "end_endpoint_id",
        "train_eligible_stress_direct_dry",
        "train_eligible_stress_direct_wet",
        "train_eligible_stress_scpdsi_drought",
        "train_eligible_stress_heat",
        "train_eligible_stress_union",
    ]
    return (
        views["common"][KEYS + [OUTCOME] + COMMON_OUTPUT_FEATURES]
        .merge(views["direct"][KEYS + DIRECT_OUTPUT_FEATURES], on=KEYS, validate="one_to_one")
        .merge(views["scpdsi"][KEYS + SCPDSI_OUTPUT_FEATURES], on=KEYS, validate="one_to_one")
        .merge(views["split"][KEYS + split_columns], on=KEYS, validate="one_to_one")
    )


def _internal_spatial_oof_scores(
    crop_data: pd.DataFrame,
    features: list[str],
    base_rows: dict[str, dict[str, Any]],
) -> np.ndarray:
    """Reconstruct held-out scores and require exact base fold metrics."""
    scores = np.full(len(crop_data), np.nan, dtype=float)
    for fold in range(5):
        holdout = f"spatial_fold_{fold}"
        train, test = _masks(crop_data, holdout)
        x_train = crop_data.loc[train, features].to_numpy(dtype=float)
        x_test = crop_data.loc[test, features].to_numpy(dtype=float)
        y_train = crop_data.loc[train, OUTCOME].to_numpy(dtype=float)
        y_test = crop_data.loc[test, OUTCOME].to_numpy(dtype=float)
        if features:
            means = x_train.mean(axis=0)
            scales = x_train.std(axis=0, ddof=0)
            if (
                not np.isfinite(means).all()
                or not np.isfinite(scales).all()
                or (scales <= 1e-12).any()
            ):
                raise ValueError("OOF reconstruction found a zero or nonfinite training scale")
            x_train = (x_train - means) / scales
            x_test = (x_test - means) / scales
        x_train = np.column_stack([np.ones(len(x_train)), x_train])
        x_test = np.column_stack([np.ones(len(x_test)), x_test])
        if len(y_train) <= x_train.shape[1] or np.linalg.matrix_rank(x_train) != x_train.shape[1]:
            raise ValueError("OOF reconstruction design is underidentified or rank deficient")
        condition_number = float(np.linalg.cond(x_train))
        if not np.isfinite(condition_number) or condition_number > 1e10:
            raise ValueError("OOF reconstruction design is numerically ill conditioned")
        internal_solution = np.linalg.lstsq(x_train, y_train, rcond=None)[0]
        with np.errstate(over="raise", invalid="raise", divide="raise"):
            fold_scores = np.sum(x_test * internal_solution[None, :], axis=1)
        if not np.isfinite(internal_solution).all() or not np.isfinite(fold_scores).all():
            raise ValueError("OOF reconstruction produced nonfinite internal values")
        scores[test.to_numpy()] = fold_scores
        pooled = _metrics(y_test, fold_scores)
        episode_values = crop_data.loc[test, "episode"].to_numpy()
        by_episode = {
            episode: _metrics(
                y_test[episode_values == episode], fold_scores[episode_values == episode]
            )
            for episode in sorted(set(episode_values))
        }
        base_row = base_rows[holdout]
        if pooled != base_row["pooled_metrics"] or by_episode != base_row["metrics_by_episode"]:
            raise ValueError(f"Reconstructed {holdout} metrics differ from the validated base")
    if not np.isfinite(scores).all():
        raise ValueError("Every row must receive exactly one finite spatial OOF score")
    return scores


def _cluster_codes(
    frame: pd.DataFrame, latitude_degrees: int, longitude_degrees: int
) -> np.ndarray:
    lat = frame["lat"].to_numpy(dtype=float)
    lon = frame["lon_360"].to_numpy(dtype=float)
    if (
        not np.isfinite(lat).all()
        or not np.isfinite(lon).all()
        or (lat < -90).any()
        or (lat >= 90).any()
        or (lon < 0).any()
        or (lon >= 360).any()
    ):
        raise ValueError("Coordinates fall outside the registered 10-degree cluster grid")
    lat_bin = np.floor((lat + 90.0) / latitude_degrees).astype(np.int64)
    lon_bin = np.floor(lon / longitude_degrees).astype(np.int64)
    _, codes = np.unique(np.column_stack([lat_bin, lon_bin]), axis=0, return_inverse=True)
    return codes


def summarize_fixed_oof_losses(
    observed: np.ndarray,
    scores_by_model: dict[str, np.ndarray],
    cluster_codes: np.ndarray,
    comparisons: list[dict[str, str]],
    bootstrap_replicates: int,
    random_seed: int,
    interval_probabilities: list[float],
    minimum_clusters: int,
    maximum_cluster_pair_share: float,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Return only aggregate paired-loss summaries; no row data or draws."""
    observed = np.asarray(observed, dtype=float)
    cluster_codes = np.asarray(cluster_codes)
    if (
        observed.ndim != 1
        or cluster_codes.shape != observed.shape
        or not np.isfinite(observed).all()
    ):
        raise ValueError("Observed outcomes and cluster codes must be finite aligned vectors")
    if set(scores_by_model) != set(MODEL_IDS):
        raise ValueError("OOF score registry differs from the five locked models")
    for model_id, scores in scores_by_model.items():
        values = np.asarray(scores, dtype=float)
        if values.shape != observed.shape or not np.isfinite(values).all():
            raise ValueError(f"OOF scores for {model_id} are nonfinite or misaligned")
    unique_codes, inverse = np.unique(cluster_codes, return_inverse=True)
    cluster_count = len(unique_codes)
    if cluster_count < minimum_clusters:
        raise ValueError("Occupied cluster count is below the prespecified minimum")
    cluster_n = np.bincount(inverse, minlength=cluster_count).astype(np.int64)
    pair_count = int(cluster_n.sum())
    shares = cluster_n / pair_count
    max_share = float(shares.max())
    if max_share > maximum_cluster_pair_share:
        raise ValueError("A geographic cluster exceeds the prespecified maximum pair share")
    effective_count = float(1.0 / np.dot(shares, shares))

    squared_by_model: dict[str, np.ndarray] = {}
    absolute_by_model: dict[str, np.ndarray] = {}
    for model_id, scores in scores_by_model.items():
        residual = observed - np.asarray(scores, dtype=float)
        squared_by_model[model_id] = np.bincount(
            inverse, weights=residual * residual, minlength=cluster_count
        )
        absolute_by_model[model_id] = np.bincount(
            inverse, weights=np.abs(residual), minlength=cluster_count
        )

    rng = np.random.default_rng(random_seed)
    cluster_draw_counts = rng.multinomial(
        cluster_count,
        np.full(cluster_count, 1.0 / cluster_count),
        size=bootstrap_replicates,
    )
    # Explicit elementwise reductions avoid platform BLAS floating-status
    # noise while preserving the exact cluster-weighted arithmetic.
    draw_n = np.sum(cluster_draw_counts * cluster_n[None, :], axis=1)
    if (draw_n <= 0).any():
        raise AssertionError("A cluster bootstrap replicate has empty support")

    summaries: list[dict[str, Any]] = []
    lower_probability, upper_probability = interval_probabilities
    for comparison in comparisons:
        candidate = comparison["candidate_model_id"]
        reference = comparison["reference_model_id"]
        candidate_sse = squared_by_model[candidate]
        reference_sse = squared_by_model[reference]
        candidate_sae = absolute_by_model[candidate]
        reference_sae = absolute_by_model[reference]
        candidate_rmse = float(np.sqrt(candidate_sse.sum() / pair_count))
        reference_rmse = float(np.sqrt(reference_sse.sum() / pair_count))
        candidate_mae = float(candidate_sae.sum() / pair_count)
        reference_mae = float(reference_sae.sum() / pair_count)
        candidate_sse_draws = np.sum(
            cluster_draw_counts * candidate_sse[None, :], axis=1
        )
        reference_sse_draws = np.sum(
            cluster_draw_counts * reference_sse[None, :], axis=1
        )
        candidate_sae_draws = np.sum(
            cluster_draw_counts * candidate_sae[None, :], axis=1
        )
        reference_sae_draws = np.sum(
            cluster_draw_counts * reference_sae[None, :], axis=1
        )
        rmse_draws = np.sqrt(candidate_sse_draws / draw_n) - np.sqrt(
            reference_sse_draws / draw_n
        )
        mae_draws = candidate_sae_draws / draw_n - reference_sae_draws / draw_n
        rmse_interval = np.quantile(
            rmse_draws, [lower_probability, upper_probability], method="linear"
        )
        mae_interval = np.quantile(
            mae_draws, [lower_probability, upper_probability], method="linear"
        )
        summaries.append(
            {
                "comparison_id": comparison["id"],
                "candidate_model_id": candidate,
                "reference_model_id": reference,
                "sign_convention": "candidate_minus_reference_negative_favors_candidate_on_loss",
                "pair_count": pair_count,
                "candidate_oof_rmse": candidate_rmse,
                "reference_oof_rmse": reference_rmse,
                "rmse_difference": candidate_rmse - reference_rmse,
                "rmse_interval": {
                    "lower": float(rmse_interval[0]),
                    "upper": float(rmse_interval[1]),
                },
                "candidate_oof_mae": candidate_mae,
                "reference_oof_mae": reference_mae,
                "mae_difference": candidate_mae - reference_mae,
                "mae_interval": {
                    "lower": float(mae_interval[0]),
                    "upper": float(mae_interval[1]),
                },
            }
        )
    diagnostics = {
        "pair_count": pair_count,
        "occupied_cluster_count": cluster_count,
        "effective_cluster_count_inverse_herfindahl": effective_count,
        "maximum_cluster_pair_share": max_share,
        "minimum_cluster_pair_count": int(cluster_n.min()),
        "median_cluster_pair_count": float(np.median(cluster_n)),
        "maximum_cluster_pair_count": int(cluster_n.max()),
    }
    return summaries, diagnostics


def evaluate_sensitivity(config_path: Path) -> dict[str, Any]:
    config = load_sensitivity_config(config_path)
    views, base_result, paths = _load_validated_base(config_path, config)
    data = _merge_views(views)
    model_specs = {model["id"]: model for model in base_result["models"]}
    base_rows = {
        (row["crop"], row["model_id"], row["holdout_id"]): row
        for row in base_result["results"]
    }
    all_summaries: list[dict[str, Any]] = []
    crop_diagnostics: dict[str, Any] = {}
    for crop_index, crop in enumerate(("mai", "soy")):
        crop_data = data.loc[data["crop"].eq(crop)].reset_index(drop=True)
        if crop_data.empty:
            raise ValueError(f"No validated base support for crop {crop}")
        scores_by_model: dict[str, np.ndarray] = {}
        for model_id in MODEL_IDS:
            features = [
                *COMMON_OUTPUT_FEATURES,
                *model_specs[model_id]["candidate_features"],
            ]
            rows_for_model = {
                f"spatial_fold_{fold}": base_rows[(crop, model_id, f"spatial_fold_{fold}")]
                for fold in range(5)
            }
            scores_by_model[model_id] = _internal_spatial_oof_scores(
                crop_data, features, rows_for_model
            )
        cluster_codes = _cluster_codes(
            crop_data,
            config["cluster_latitude_degrees"],
            config["cluster_longitude_degrees"],
        )
        summaries, diagnostics = summarize_fixed_oof_losses(
            crop_data[OUTCOME].to_numpy(dtype=float),
            scores_by_model,
            cluster_codes,
            config["comparisons"],
            config["bootstrap_replicates"],
            config["random_seed"] + crop_index,
            config["interval_probabilities"],
            config["minimum_occupied_clusters_per_crop"],
            config["maximum_cluster_pair_share"],
        )
        all_summaries.extend({"crop": crop, **summary} for summary in summaries)
        crop_diagnostics[crop] = {
            **diagnostics,
            "crop_seed": config["random_seed"] + crop_index,
        }

    result: dict[str, Any] = {
        "schema_version": 1,
        "contract_id": CONTRACT_ID,
        "status": "completed_nonproduction_paired_loss_uncertainty_sensitivity",
        "config_file": str(config_path),
        "config_sha256": sha256_file(config_path),
        "base_artifacts": {
            field: {"path": config[field], "sha256": sha256_file(path)}
            for field, path in sorted(paths.items())
        },
        "base_diagnostic_validation_recomputed": True,
        "all_five_fold_metrics_match_base": True,
        "score_basis": config["score_basis"],
        "resampling_scheme": config["resampling_scheme"],
        "resampling_unit": config["resampling_unit"],
        "cluster_latitude_degrees": config["cluster_latitude_degrees"],
        "cluster_longitude_degrees": config["cluster_longitude_degrees"],
        "bootstrap_replicates": config["bootstrap_replicates"],
        "random_seed": config["random_seed"],
        "interval_probabilities": config["interval_probabilities"],
        "training_refit_within_bootstrap": False,
        "bootstrap_draws_emitted": False,
        "row_scores_emitted": False,
        "row_losses_emitted": False,
        "observation_weighting": config["observation_weighting"],
        "model_selection_rule": config["model_selection_rule"],
        "crop_cluster_diagnostics": crop_diagnostics,
        "comparisons": all_summaries,
        "comparison_count": len(all_summaries),
        "uncertainty_scope": (
            "paired empirical variation across occupied 10-degree crop-grid cells, "
            "conditional on the observed panel, fixed feature construction, fold assignment, "
            "and fitted five-fold OOF scores"
        ),
        "unsupported_inference": (
            "not training-sample or model-selection uncertainty; not a population-randomization, "
            "causal, structural-response, future-climate, damage, welfare, or SCC interval"
        ),
        "dependence_boundary": (
            "keeps all pairs and episodes within a 10-degree cell together but does not model "
            "dependence beyond or across cell boundaries"
        ),
        "diagnostic_fit_authorized": True,
        "families_stacked": False,
        "coefficients_emitted": False,
        "predictions_emitted": False,
        **{gate: False for gate in FALSE_GATES},
    }
    if result["comparison_count"] != 2 * len(EXPECTED_COMPARISONS):
        raise AssertionError("Complete crop-by-comparison product was not emitted")
    _reject_forbidden_result_keys(result)
    return result


def evaluate_file(config_path: Path, result_path: Path) -> dict[str, Any]:
    result = evaluate_sensitivity(config_path)
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(
        json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--result-out", required=True)
    args = parser.parse_args()
    result = evaluate_file(Path(args.config), Path(args.result_out))
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
