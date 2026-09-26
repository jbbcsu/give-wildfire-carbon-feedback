#!/usr/bin/env python3
"""Paired geographic stability audit for six-crop distribution predictions.

Only aggregate fixed spatial out-of-fold losses are emitted. Coefficients,
row predictions, bootstrap draws, and geographic impact labels are suppressed.
"""
from __future__ import annotations

import argparse
import gc
import hashlib
import json
import os
import resource
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow as pa

from evaluate_crop_response_models import make_first_differences
from evaluate_multicrop_rainfed_distribution_diagnostic import (
    STATUS as PARENT_STATUS,
    _fit_predict_masks,
    load_contract,
    sha256_path,
)


PROJECT = Path(__file__).resolve().parents[1]
CONFIG_DEFAULT = PROJECT / "config" / "multicrop_rainfed_distribution_geographic_audit_v1.toml"
STATUS = "validated_noncausal_multicrop_geographic_paired_predictive_loss_audit_not_scc_eligible"
CONTRACT_ID = "multicrop_rainfed_distribution_geographic_paired_loss_audit_v1"


def resolve(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else PROJECT / path


def load_config(path: Path) -> tuple[dict[str, Any], str]:
    raw = path.read_bytes()
    config = tomllib.loads(raw.decode("utf-8"))
    if config.get("schema_version") != 1 or config.get("contract_id") != CONTRACT_ID:
        raise ValueError("Unexpected geographic audit contract")
    if config.get("reference_model") != "seasonal_quantity":
        raise ValueError("Reference model changed")
    if len(config.get("candidate_models", [])) != 5 or len(config.get("crops", [])) != 6:
        raise ValueError("Registered crop/model family changed")
    if config.get("spatial_folds") != 5:
        raise ValueError("Spatial fold count changed")
    clusters = config["geographic_clusters"]
    if clusters["latitude_degrees"] != 10 or clusters["longitude_degrees"] != 10:
        raise ValueError("Geographic cluster grid changed")
    uncertainty = config["uncertainty"]
    if uncertainty["replicates"] != 5000 or uncertainty["seed"] != 20260925:
        raise ValueError("Bootstrap contract changed")
    authorization = config["authorization"]
    if authorization.get("predictive_geographic_audit_authorized") is not True:
        raise ValueError("Predictive audit authorization missing")
    forbidden = [key for key in authorization if key != "predictive_geographic_audit_authorized"]
    if any(authorization[key] is not False for key in forbidden):
        raise ValueError("A forbidden claim gate is open")
    for field in ("parent_result", "parent_lock", "parent_spec", "parent_evaluator"):
        artifact = resolve(config[f"{field}_path"])
        if sha256_path(artifact) != config[f"{field}_sha256"]:
            raise ValueError(f"{field} hash differs")
    parent = json.loads(resolve(config["parent_result_path"]).read_text(encoding="utf-8"))
    if parent.get("status") != PARENT_STATUS:
        raise ValueError("Parent diagnostic status differs")
    return config, hashlib.sha256(raw).hexdigest()


def geographic_cluster_codes(
    lat: np.ndarray, lon: np.ndarray, latitude_degrees: int, longitude_degrees: int
) -> np.ndarray:
    lat = np.asarray(lat, dtype=float)
    lon = np.asarray(lon, dtype=float)
    if not np.isfinite(lat).all() or not np.isfinite(lon).all():
        raise ValueError("Nonfinite coordinates")
    if (lat < -90).any() or (lat >= 90).any() or (lon < 0).any() or (lon >= 360).any():
        raise ValueError("Coordinates outside registered cluster grid")
    lat_bin = np.floor((lat + 90.0) / latitude_degrees).astype(np.int64)
    lon_bin = np.floor(lon / longitude_degrees).astype(np.int64)
    return lat_bin * (360 // longitude_degrees) + lon_bin


def holm_adjust(p_values: list[float]) -> list[float]:
    order = np.argsort(np.asarray(p_values, dtype=float), kind="stable")
    adjusted = np.empty(len(p_values), dtype=float)
    running = 0.0
    total = len(p_values)
    for rank, index in enumerate(order):
        running = max(running, min(1.0, (total - rank) * float(p_values[index])))
        adjusted[index] = running
    return adjusted.tolist()


def summarize_losses(
    crop: str,
    observed: np.ndarray,
    folds: np.ndarray,
    cluster_codes: np.ndarray,
    scores: dict[str, np.ndarray],
    config: dict[str, Any],
    crop_seed_offset: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    unique, inverse = np.unique(cluster_codes, return_inverse=True)
    cluster_count = len(unique)
    counts = np.bincount(inverse, minlength=cluster_count).astype(np.int64)
    pair_count = int(counts.sum())
    cluster_config = config["geographic_clusters"]
    if cluster_count < int(cluster_config["minimum_occupied_clusters_per_crop"]):
        raise ValueError(f"Insufficient occupied clusters for {crop}")
    maximum_share = float((counts / pair_count).max())
    if maximum_share > float(cluster_config["maximum_pair_share"]):
        raise ValueError(f"A geographic cluster dominates {crop}")

    sse: dict[str, np.ndarray] = {}
    for model, prediction in scores.items():
        residual = observed - prediction
        sse[model] = np.bincount(inverse, weights=residual * residual, minlength=cluster_count)

    uncertainty = config["uncertainty"]
    replicates = int(uncertainty["replicates"])
    rng = np.random.default_rng(int(uncertainty["seed"]) + crop_seed_offset)
    draw_counts = rng.multinomial(
        cluster_count, np.full(cluster_count, 1.0 / cluster_count), size=replicates
    )
    draw_n = np.sum(draw_counts * counts[None, :], axis=1)
    if (draw_n <= 0).any():
        raise AssertionError("Empty bootstrap replicate")
    reference = str(config["reference_model"])
    reference_draw_sse = np.sum(draw_counts * sse[reference][None, :], axis=1)
    reference_rmse = float(np.sqrt(sse[reference].sum() / pair_count))
    quantiles = list(uncertainty["interval_probabilities"])
    summaries: list[dict[str, Any]] = []
    for candidate in config["candidate_models"]:
        candidate_draw_sse = np.sum(draw_counts * sse[candidate][None, :], axis=1)
        rmse_draw = np.sqrt(candidate_draw_sse / draw_n) - np.sqrt(reference_draw_sse / draw_n)
        interval = np.quantile(rmse_draw, quantiles, method="linear")
        lower_tail = (int(np.count_nonzero(rmse_draw <= 0)) + 1) / (replicates + 1)
        upper_tail = (int(np.count_nonzero(rmse_draw >= 0)) + 1) / (replicates + 1)
        tail_probability = min(1.0, 2.0 * min(lower_tail, upper_tail))
        candidate_rmse = float(np.sqrt(sse[candidate].sum() / pair_count))
        cluster_mean_delta = (sse[candidate] - sse[reference]) / counts
        fold_differences: list[dict[str, Any]] = []
        for fold in range(int(config["spatial_folds"])):
            mask = folds == fold
            candidate_fold = float(np.sqrt(np.mean((observed[mask] - scores[candidate][mask]) ** 2)))
            reference_fold = float(np.sqrt(np.mean((observed[mask] - scores[reference][mask]) ** 2)))
            fold_differences.append(
                {
                    "fold": fold,
                    "test_rows": int(mask.sum()),
                    "candidate_minus_reference_rmse": candidate_fold - reference_fold,
                    "candidate_has_lower_rmse": candidate_fold < reference_fold,
                }
            )
        summaries.append(
            {
                "crop": crop,
                "candidate_model": candidate,
                "reference_model": reference,
                "sign_convention": "candidate_minus_reference_negative_favors_candidate",
                "pair_count": pair_count,
                "occupied_10degree_clusters": cluster_count,
                "candidate_oof_rmse": candidate_rmse,
                "reference_oof_rmse": reference_rmse,
                "candidate_minus_reference_rmse": candidate_rmse - reference_rmse,
                "paired_cluster_bootstrap_rmse_difference_quantiles": {
                    "p2_5": float(interval[0]),
                    "p50": float(interval[1]),
                    "p97_5": float(interval[2]),
                },
                "two_sided_bootstrap_tail_probability": tail_probability,
                "clusters_with_lower_candidate_mean_squared_loss": int(
                    np.count_nonzero(cluster_mean_delta < 0)
                ),
                "cluster_share_with_lower_candidate_mean_squared_loss": float(
                    np.mean(cluster_mean_delta < 0)
                ),
                "median_cluster_candidate_minus_reference_mean_squared_loss": float(
                    np.median(cluster_mean_delta)
                ),
                "spatial_fold_differences": fold_differences,
                "all_five_spatial_folds_have_lower_candidate_rmse": bool(
                    all(row["candidate_has_lower_rmse"] for row in fold_differences)
                ),
            }
        )
    diagnostics = {
        "crop": crop,
        "pair_count": pair_count,
        "occupied_10degree_clusters": cluster_count,
        "maximum_cluster_pair_share": maximum_share,
        "effective_cluster_count_from_pair_shares": float(
            1.0 / np.square(counts / pair_count).sum()
        ),
    }
    return summaries, diagnostics


def run_crop_worker(
    crop: str, level_extract: Path, config_path: Path, crop_seed_offset: int
) -> dict[str, Any]:
    config, _ = load_config(config_path)
    _, _, models, _, _ = load_contract(
        resolve(config["parent_spec_path"]), resolve(config["parent_lock_path"])
    )
    required_models = [config["reference_model"], *config["candidate_models"]]
    if any(model not in models for model in required_models):
        raise ValueError("Geographic audit model absent from parent registry")
    levels = pd.read_parquet(level_extract)
    all_features = list(
        dict.fromkeys(feature for model in required_models for feature in models[model])
    )
    pairs = make_first_differences(levels, all_features)
    del levels
    gc.collect()
    pa.default_memory_pool().release_unused()
    observed = pairs["delta_log_yield"].to_numpy(dtype=float)
    fold_values = pairs["spatial_fold"].to_numpy(dtype=int)
    cluster_codes = geographic_cluster_codes(
        pairs["lat"].to_numpy(dtype=float),
        pairs["lon_360"].to_numpy(dtype=float),
        int(config["geographic_clusters"]["latitude_degrees"]),
        int(config["geographic_clusters"]["longitude_degrees"]),
    )
    scores: dict[str, np.ndarray] = {}
    for model in required_models:
        prediction = np.empty(len(pairs), dtype=float)
        for fold in range(int(config["spatial_folds"])):
            test = pairs["spatial_fold"].eq(fold)
            fit, _ = _fit_predict_masks(
                pairs,
                ~test,
                test,
                models[model],
                100,
                100,
            )
            prediction[test.to_numpy()] = fit
        if not np.isfinite(prediction).all():
            raise ValueError("Nonfinite spatial OOF prediction")
        scores[model] = prediction
    summaries, diagnostics = summarize_losses(
        crop, observed, fold_values, cluster_codes, scores, config, crop_seed_offset
    )
    return {
        "crop": crop,
        "summaries": summaries,
        "diagnostics": diagnostics,
        "maximum_rss_bytes": int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss),
    }


def run_audit(config_path: Path = CONFIG_DEFAULT) -> dict[str, Any]:
    config, config_hash = load_config(config_path)
    _, lock, _, _, _ = load_contract(
        resolve(config["parent_spec_path"]), resolve(config["parent_lock_path"])
    )
    crop_locks = {row["crop"]: row for row in lock["crops"]}
    all_rows: list[dict[str, Any]] = []
    diagnostics: list[dict[str, Any]] = []
    worker_rss: dict[str, dict[str, int]] = {}
    environment = os.environ.copy()
    environment.update({"OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1"})
    parent_evaluator = resolve(config["parent_evaluator_path"])
    with tempfile.TemporaryDirectory(prefix="multicrop_geo_audit_") as directory:
        scratch = Path(directory)
        for offset, crop in enumerate(config["crops"]):
            if crop not in crop_locks:
                raise ValueError(f"Unregistered crop {crop}")
            stage_path = scratch / f"{crop}_stage.parquet"
            level_path = scratch / f"{crop}_levels.parquet"
            extract = subprocess.run(
                [sys.executable, str(parent_evaluator), "--extract-stage-crop", crop,
                 "--stage-extract", str(stage_path)],
                check=True, capture_output=True, text=True, env=environment,
            )
            level = subprocess.run(
                [sys.executable, str(parent_evaluator), "--build-level-crop", crop,
                 "--stage-extract", str(stage_path), "--level-extract", str(level_path)],
                check=True, capture_output=True, text=True, env=environment,
            )
            worker = subprocess.run(
                [sys.executable, str(Path(__file__).resolve()), "--config", str(config_path),
                 "--worker-crop", crop, "--level-extract", str(level_path),
                 "--crop-seed-offset", str(offset)],
                check=False, capture_output=True, text=True, env=environment,
            )
            if worker.returncode:
                raise RuntimeError(f"Geographic worker failed for {crop}: {worker.stderr}")
            extract_receipt = json.loads(extract.stdout)
            level_receipt = json.loads(level.stdout)
            fragment = json.loads(worker.stdout)
            all_rows.extend(fragment["summaries"])
            diagnostics.append(fragment["diagnostics"])
            worker_rss[crop] = {
                "stage_extract": int(extract_receipt["maximum_rss_bytes"]),
                "level_build": int(level_receipt["maximum_rss_bytes"]),
                "paired_loss_audit": int(fragment["maximum_rss_bytes"]),
            }
    adjusted = holm_adjust([row["two_sided_bootstrap_tail_probability"] for row in all_rows])
    alpha = float(config["uncertainty"]["familywise_alpha"])
    supported: list[dict[str, str]] = []
    for row, value in zip(all_rows, adjusted):
        row["holm_adjusted_tail_probability_30_tests"] = value
        row["passes_prespecified_descriptive_predictive_support_gate"] = bool(
            row["paired_cluster_bootstrap_rmse_difference_quantiles"]["p97_5"] < 0
            and value <= alpha
            and row["all_five_spatial_folds_have_lower_candidate_rmse"]
            and row["cluster_share_with_lower_candidate_mean_squared_loss"] > 0.5
        )
        if row["passes_prespecified_descriptive_predictive_support_gate"]:
            supported.append({"crop": row["crop"], "candidate_model": row["candidate_model"]})
    maximum_rss = max(value for crop in worker_rss.values() for value in crop.values())
    result = {
        "status": STATUS,
        "contract_id": CONTRACT_ID,
        "config_sha256": config_hash,
        "parent_result_path": config["parent_result_path"],
        "parent_result_sha256": config["parent_result_sha256"],
        "comparison_count": len(all_rows),
        "spatial_oof_only": True,
        "training_reestimated_within_bootstrap": False,
        "row_predictions_exported": False,
        "bootstrap_draws_exported": False,
        "results": all_rows,
        "crop_geographic_support": diagnostics,
        "comparisons_passing_descriptive_predictive_support_gate": supported,
        "coefficients_suppressed": True,
        "causal_interpretation_authorized": False,
        "economic_winner_loser_interpretation_authorized": False,
        "production_model_selection_authorized": False,
        "response_draw_export_authorized": False,
        "damage_calculation_authorized": False,
        "scc_use_authorized": False,
        "runtime": {
            "maximum_worker_rss_bytes": maximum_rss,
            "worker_memory_bytes_maximum": int(config["resources"]["worker_memory_bytes_maximum"]),
            "worker_rss_bytes": worker_rss,
        },
        "warning": (
            "Lower held-out predictive loss in a geographic block is not a causal crop benefit, "
            "an economic winner, a damage estimate, or evidence authorized for GIVE/SCC use."
        ),
    }
    if maximum_rss > int(config["resources"]["worker_memory_bytes_maximum"]):
        raise MemoryError("Geographic audit worker exceeded memory contract")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=CONFIG_DEFAULT)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--worker-crop")
    parser.add_argument("--level-extract", type=Path)
    parser.add_argument("--crop-seed-offset", type=int)
    args = parser.parse_args()
    if args.worker_crop:
        if args.out or args.level_extract is None or args.crop_seed_offset is None:
            raise ValueError("Worker requires crop, level extract, and seed offset")
        print(json.dumps(run_crop_worker(
            args.worker_crop, args.level_extract, args.config, args.crop_seed_offset
        ), sort_keys=True))
        return
    if args.out is None or args.level_extract is not None or args.crop_seed_offset is not None:
        raise ValueError("Full audit requires --out only")
    result = run_audit(args.config)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in result.items() if key != "results"}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
