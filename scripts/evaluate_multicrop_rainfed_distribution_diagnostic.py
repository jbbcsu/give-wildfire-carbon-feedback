#!/usr/bin/env python3
"""Stream a six-crop rainfed precipitation-distribution predictive diagnostic.

The hash-locked source contains all crop-grid-year rows.  This evaluator reads
only positive observed-yield rows for one crop at a time, constructs the same
registered direct-pattern features used by the maize/soybean screen, and then
runs endpoint-disjoint spatial, temporal, and high-tail predictive holdouts.
Coefficients are transient and are never returned or written.
"""
from __future__ import annotations

import argparse
import gc
import hashlib
import json
import math
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
import pyarrow.compute as pc
import pyarrow.dataset as ds
import pyarrow.parquet as pq

from evaluate_crop_response_models import (
    KEYS,
    LABELS,
    _metrics,
    make_first_differences,
)
from evaluate_precipitation_distribution_diagnostic import (
    NONSPATIAL_SPLIT_CONTRACT,
    SPEC_DEFAULT,
    _expand_models,
    assert_coefficients_suppressed,
)


PROJECT = Path(__file__).resolve().parents[1]
LOCK_DEFAULT = PROJECT / "config" / "multicrop_rainfed_distribution_diagnostic_v1.lock.toml"
CONTRACT_ID = "gdhy_multicrop_rainfed_distribution_predictive_diagnostic_v1"
STATUS = "validated_noncausal_multicrop_rainfed_distribution_predictive_diagnostic_not_scc_eligible"
HOLDOUTS = ("spatial_block", "temporal", "climate_extreme")
STAGES = (1, 2, 3)


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else PROJECT / path


def load_contract(spec_path: Path, lock_path: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, list[str]], str, str]:
    spec_raw = spec_path.read_bytes()
    lock_raw = lock_path.read_bytes()
    spec = tomllib.loads(spec_raw.decode("utf-8"))
    lock = tomllib.loads(lock_raw.decode("utf-8"))
    spec_hash = hashlib.sha256(spec_raw).hexdigest()
    lock_hash = hashlib.sha256(lock_raw).hexdigest()
    if lock.get("schema_version") != 1 or lock.get("diagnostic_contract_id") != CONTRACT_ID:
        raise ValueError("Unrecognized multicrop diagnostic lock")
    if lock.get("spec_sha256") != spec_hash:
        raise ValueError("Diagnostic specification hash differs from the multicrop lock")
    models = _expand_models(spec)
    boundary = lock.get("boundary", {})
    required_true = (
        "source_artifacts_are_ignored",
        "observed_rows_only_in_memory",
        "held_out_predictive_fit_authorized",
        "coefficients_suppressed",
    )
    required_false = (
        "causal_interpretation_authorized",
        "production_model_selection_authorized",
        "response_draw_export_authorized",
        "scc_use_authorized",
    )
    if any(boundary.get(name) is not True for name in required_true):
        raise ValueError("Multicrop diagnostic true boundary gate differs")
    if any(boundary.get(name) is not False for name in required_false):
        raise ValueError("Multicrop diagnostic false boundary gate differs")
    return spec, lock, models, spec_hash, lock_hash


def _source_columns(models: dict[str, list[str]]) -> list[str]:
    columns = set(KEYS + ["yield_t_ha", "yield_observed"])
    columns.update(["season_days", "precip_mm", "wet_days_n", "cdd_max_days", "rx1day_mm", "rx5day_mm"])
    for stage in STAGES:
        prefix = f"stage{stage}_"
        columns.update(
            {
                f"{prefix}stage_days",
                f"{prefix}tmean_c",
                f"{prefix}precip_mm",
                f"{prefix}wet_days_n",
                f"{prefix}cdd_max_days",
                f"{prefix}rx1day_mm",
                f"{prefix}rx5day_mm",
            }
        )
    # This also guards against a future model registry requiring an unbuilt
    # feature: only model features constructed below may be requested.
    expected = {feature for features in models.values() for feature in features}
    constructed = {
        "log1p_precip_mm",
        "precipitation_timing_centroid",
        "precipitation_concentration_hhi",
    }
    for stage in STAGES:
        prefix = f"stage{stage}_"
        constructed.update(
            {
                f"{prefix}tmean_c",
                f"{prefix}wet_day_frequency",
                f"{prefix}mean_wet_day_intensity_mm",
                f"{prefix}cdd_fraction",
                f"{prefix}rx1day_mm",
                f"{prefix}rx5day_mm",
            }
        )
    if expected != constructed:
        raise ValueError("Registered diagnostic features differ from the streamed construction")
    return sorted(columns)


def _label_columns() -> list[str]:
    return sorted(set(KEYS + LABELS + ["yield_observed", "validation_design"]))


def _finite(frame: pd.DataFrame, columns: list[str], label: str) -> None:
    # Validate one column at a time: materializing the complete numeric block
    # twice pushes the largest crop above the 512 MiB worker contract.
    for column in columns:
        numeric = pd.to_numeric(frame[column], errors="coerce")
        if not np.isfinite(numeric.to_numpy(dtype=float, copy=False)).all():
            raise ValueError(f"{label} contains nonfinite values in {column}")
        if not pd.api.types.is_numeric_dtype(frame[column]):
            frame[column] = numeric


def read_observed_crop_batches(
    panel_path: Path,
    columns: list[str],
    crop: str,
    *,
    batch_size: int = 8192,
    expected_irrigation: str = "noirr",
    expected_validation_design: str | None = None,
) -> pd.DataFrame:
    """Read one crop's observed rows without materializing a Parquet row group.

    The source has million-row row groups, so a predicate pushdown read can
    transiently decode far more than the retained crop.  Fixed-size record
    batches make the memory bound explicit before conversion to pandas.
    """
    dataset = ds.dataset(panel_path, format="parquet")
    scanner = ds.Scanner.from_dataset(
        dataset,
        columns=columns,
        filter=(ds.field("crop") == crop) & (ds.field("yield_observed") == True),  # noqa: E712
        batch_size=batch_size,
        batch_readahead=1,
        fragment_readahead=1,
        use_threads=False,
    )
    retained = scanner.to_table()
    if not retained.num_rows:
        raise ValueError(f"No observed rows found for {crop}")
    if not bool(pc.all(pc.equal(retained["irrigation"], expected_irrigation)).as_py()):
        raise ValueError(f"Irrigation regime differs for {crop}")
    if expected_validation_design is not None and not bool(
        pc.all(pc.equal(retained["validation_design"], expected_validation_design)).as_py()
    ):
        raise ValueError(f"Validation design differs for {crop}")
    drop = ["crop", "irrigation", "yield_observed"]
    if "validation_design" in retained.column_names:
        drop.append("validation_design")
    output = retained.drop_columns(drop).to_pandas()
    del retained
    gc.collect()
    pa.default_memory_pool().release_unused()
    output["crop"] = crop
    output["irrigation"] = expected_irrigation
    output["yield_observed"] = True
    if expected_validation_design is not None:
        output["validation_design"] = expected_validation_design
    return output


def build_observed_levels(
    crop: str,
    crop_lock: dict[str, Any],
    source: dict[str, Any],
    models: dict[str, list[str]],
    stage_extract: Path | None = None,
) -> tuple[pd.DataFrame, dict[str, float]]:
    stage_path = resolve_path(str(crop_lock["stage_panel_path"]))
    label_path = resolve_path(str(crop_lock["label_panel_path"]))
    expected_irrigation = str(source["expected_irrigation"])
    expected_design = str(source["validation_design"])
    labels = read_observed_crop_batches(
        label_path,
        _label_columns(),
        crop,
        expected_irrigation=expected_irrigation,
        expected_validation_design=expected_design,
    )
    if stage_extract is None:
        frame = read_observed_crop_batches(
            stage_path,
            _source_columns(models),
            crop,
            expected_irrigation=expected_irrigation,
        )
    else:
        frame = pd.read_parquet(stage_extract)
    expected_observed = int(crop_lock["expected_observed_outcomes"])
    if (
        len(frame) != expected_observed
        or len(labels) != expected_observed
        or not frame["yield_observed"].eq(True).all()
        or not labels["yield_observed"].eq(True).all()
    ):
        raise ValueError(f"Observed outcome count differs for {crop}")
    labels = labels.drop(columns=["yield_observed"])
    frame = frame.merge(labels, on=KEYS, how="left", validate="one_to_one")
    if frame[LABELS + ["validation_design"]].isna().any().any():
        raise ValueError(f"Validation labels failed to join for {crop}")
    if set(frame["crop"].astype(str)) != {crop}:
        raise ValueError(f"Crop filter differs for {crop}")
    if set(frame["irrigation"].astype(str)) != {str(source["expected_irrigation"])}:
        raise ValueError(f"Irrigation regime differs for {crop}")
    if frame.duplicated(KEYS).any():
        raise ValueError(f"Duplicate outcome key for {crop}")
    if set(frame["validation_design"].astype(str)) != {expected_design}:
        raise ValueError(f"Validation design differs for {crop}")
    for label in LABELS[1:]:
        if not pd.api.types.is_bool_dtype(frame[label]) or frame[label].isna().any():
            raise ValueError(f"{label} is not Boolean for {crop}")
    years = pd.to_numeric(frame["harvest_year"], errors="raise").astype(int)
    if years.min() != int(source["expected_year_start"]) or years.max() != int(source["expected_year_end"]):
        raise ValueError(f"Observed year coverage differs for {crop}")
    if frame["spatial_fold"].nunique() != 5:
        raise ValueError(f"Spatial folds differ for {crop}")
    if not frame.groupby(KEYS[:-1], observed=True)["spatial_fold"].nunique().eq(1).all():
        raise ValueError(f"Spatial fold changes within a cell for {crop}")

    season = ["season_days", "precip_mm", "wet_days_n", "cdd_max_days", "rx1day_mm", "rx5day_mm"]
    stage_columns: list[str] = []
    for stage in STAGES:
        prefix = f"stage{stage}_"
        stage_columns.extend(
            [
                f"{prefix}stage_days",
                f"{prefix}tmean_c",
                f"{prefix}precip_mm",
                f"{prefix}wet_days_n",
                f"{prefix}cdd_max_days",
                f"{prefix}rx1day_mm",
                f"{prefix}rx5day_mm",
            ]
        )
    _finite(frame, season + stage_columns + ["yield_t_ha"], f"{crop} source")
    if (frame["yield_t_ha"] <= 0).any() or (frame["precip_mm"] < 0).any() or (frame["season_days"] <= 0).any():
        raise ValueError(f"Invalid yield, precipitation, or duration for {crop}")

    stage_days = [f"stage{stage}_stage_days" for stage in STAGES]
    stage_precip = [f"stage{stage}_precip_mm" for stage in STAGES]
    stage_wet = [f"stage{stage}_wet_days_n" for stage in STAGES]
    differences = {
        "stage_days": float((frame[stage_days].sum(axis=1) - frame["season_days"]).abs().max()),
        "stage_precip_mm": float((frame[stage_precip].sum(axis=1) - frame["precip_mm"]).abs().max()),
        "stage_wet_days": float((frame[stage_wet].sum(axis=1) - frame["wet_days_n"]).abs().max()),
    }
    if differences["stage_days"] != 0 or differences["stage_wet_days"] != 0 or differences["stage_precip_mm"] > 1e-3:
        raise ValueError(f"Stage/season reconciliation fails for {crop}: {differences}")

    frame["log1p_precip_mm"] = np.log1p(frame["precip_mm"])
    totals = frame["precip_mm"].to_numpy(dtype=float)
    stage_values = frame[stage_precip].to_numpy(dtype=float)
    shares = np.divide(stage_values, totals[:, None], out=np.zeros_like(stage_values), where=totals[:, None] > 0)
    midpoints = (np.arange(len(STAGES), dtype=float) + 0.5) / len(STAGES)
    frame["precipitation_concentration_hhi"] = np.square(shares).sum(axis=1)
    frame["precipitation_timing_centroid"] = (shares * midpoints).sum(axis=1)
    for index, stage in enumerate(STAGES):
        prefix = f"stage{stage}_"
        days = frame[f"{prefix}stage_days"].to_numpy(dtype=float)
        wet = frame[f"{prefix}wet_days_n"].to_numpy(dtype=float)
        precip = frame[f"{prefix}precip_mm"].to_numpy(dtype=float)
        cdd = frame[f"{prefix}cdd_max_days"].to_numpy(dtype=float)
        rx1 = frame[f"{prefix}rx1day_mm"].to_numpy(dtype=float)
        rx5 = frame[f"{prefix}rx5day_mm"].to_numpy(dtype=float)
        if np.any(days <= 0) or np.any(wet < 0) or np.any(wet > days) or np.any(cdd < 0) or np.any(cdd > days):
            raise ValueError(f"Stage count bounds fail for {crop}/{stage}")
        if np.any(rx1 < 0) or np.any(rx5 + 1e-12 < rx1) or np.any(rx5 > precip + 1e-3):
            raise ValueError(f"Stage precipitation-extreme bounds fail for {crop}/{stage}")
        frame[f"{prefix}wet_day_frequency"] = wet / days
        frame[f"{prefix}mean_wet_day_intensity_mm"] = np.divide(
            precip, wet, out=np.zeros_like(precip), where=wet > 0
        )
        frame[f"{prefix}cdd_fraction"] = cdd / days
    feature_columns = list(dict.fromkeys(feature for features in models.values() for feature in features))
    if not np.isfinite(frame[feature_columns].to_numpy(dtype=float)).all():
        raise ValueError(f"Constructed distribution features are nonfinite for {crop}")
    retained_columns = KEYS + LABELS + ["yield_t_ha", "yield_observed", *feature_columns]
    frame.drop(columns=[column for column in frame.columns if column not in retained_columns], inplace=True)
    del labels
    gc.collect()
    pa.default_memory_pool().release_unused()
    return frame, differences


def extract_observed_stage_rows(
    crop: str,
    crop_lock: dict[str, Any],
    source: dict[str, Any],
    models: dict[str, list[str]],
    output: Path,
) -> dict[str, Any]:
    stage_path = resolve_path(str(crop_lock["stage_panel_path"]))
    dataset = ds.dataset(stage_path, format="parquet")
    scanner = ds.Scanner.from_dataset(
        dataset,
        columns=_source_columns(models),
        filter=(ds.field("crop") == crop) & (ds.field("yield_observed") == True),  # noqa: E712
        batch_size=8192,
        batch_readahead=1,
        fragment_readahead=1,
        use_threads=False,
    )
    table = scanner.to_table()
    if table.num_rows != int(crop_lock["expected_observed_outcomes"]):
        raise ValueError(f"Stage extract row count differs for {crop}")
    if not bool(pc.all(pc.equal(table["irrigation"], str(source["expected_irrigation"]))).as_py()):
        raise ValueError(f"Stage extract irrigation differs for {crop}")
    output.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, output, compression="zstd")
    return {
        "crop": crop,
        "rows": int(table.num_rows),
        "sha256": sha256_path(output),
        "maximum_rss_bytes": int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss),
    }


def extract_observed_levels(
    crop: str,
    crop_lock: dict[str, Any],
    source: dict[str, Any],
    models: dict[str, list[str]],
    stage_extract: Path,
    output: Path,
) -> dict[str, Any]:
    levels, reconciliations = build_observed_levels(
        crop, crop_lock, source, models, stage_extract=stage_extract
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    levels.to_parquet(output, index=False, compression="zstd")
    return {
        "crop": crop,
        "rows": int(len(levels)),
        "maximum_reconciliation_differences": reconciliations,
        "sha256": sha256_path(output),
        "maximum_rss_bytes": int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss),
    }


def _fit_predict_masks(
    pairs: pd.DataFrame,
    train_mask: pd.Series,
    test_mask: pd.Series,
    features: list[str],
    minimum_train_rows: int,
    minimum_test_rows: int,
) -> tuple[np.ndarray, dict[str, Any]]:
    train_rows = int(train_mask.sum())
    test_rows = int(test_mask.sum())
    if train_rows < minimum_train_rows or test_rows < minimum_test_rows:
        raise ValueError(
            f"Insufficient split rows: train={train_rows}, test={test_rows}, "
            f"required={minimum_train_rows}/{minimum_test_rows}"
        )
    columns = [f"delta__{feature}" for feature in features]
    train_x = pairs.loc[train_mask, columns].to_numpy(dtype=float)
    test_x = pairs.loc[test_mask, columns].to_numpy(dtype=float)
    scale = train_x.std(axis=0, ddof=0)
    if np.any(scale <= 0) or not np.isfinite(scale).all():
        raise ValueError("Zero/nonfinite training variation")
    center = train_x.mean(axis=0)
    design = np.empty((train_rows, len(features) + 1), dtype=float)
    design[:, 0] = 1.0
    design[:, 1:] = (train_x - center) / scale
    del train_x
    outcome = pairs.loc[train_mask, "delta_log_yield"].to_numpy(dtype=float)
    coefficients, _, rank, singular = np.linalg.lstsq(design, outcome, rcond=1e-12)
    del design, outcome
    prediction = coefficients[0] + ((test_x - center) / scale) @ coefficients[1:]
    if not np.isfinite(prediction).all():
        raise ValueError("Predictions are nonfinite")
    return prediction, {
        "train_rows": train_rows,
        "test_rows": test_rows,
        "matrix_rank": int(rank),
        "condition_number": float(singular[0] / singular[-1]),
    }


def _numeric_endpoint_ids(pairs: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    cells, _ = pd.factorize(pd.MultiIndex.from_frame(pairs[["lat", "lon_360"]]), sort=False)
    cells = cells.astype(np.int64, copy=False)
    return (
        cells * 10000 + pairs["pair_start_year"].to_numpy(dtype=np.int64),
        cells * 10000 + pairs["pair_end_year"].to_numpy(dtype=np.int64),
    )


def _purged_masks_low_memory(
    pairs: pd.DataFrame,
) -> dict[str, tuple[pd.Series, pd.Series, dict[str, Any]]]:
    start_id, end_id = _numeric_endpoint_ids(pairs)
    temporal_test = pairs["is_temporal_holdout"].astype(bool)
    test_start = int(pairs.loc[temporal_test, "pair_end_year"].min())
    temporal_candidate = ~temporal_test
    temporal_train = temporal_candidate & pairs["pair_end_year"].le(test_start - 2)
    temporal_overlap = np.intersect1d(
        np.concatenate([start_id[temporal_train], end_id[temporal_train]]),
        np.concatenate([start_id[temporal_test], end_id[temporal_test]]),
        assume_unique=False,
    ).size
    if temporal_overlap:
        raise AssertionError("Purged temporal split retains shared yield endpoints")

    extreme_test = pairs["pair_is_climate_extreme"].astype(bool)
    extreme_candidate = ~extreme_test
    extreme_test_endpoints = np.unique(
        np.concatenate([start_id[extreme_test], end_id[extreme_test]])
    )
    keep = ~np.isin(start_id, extreme_test_endpoints) & ~np.isin(end_id, extreme_test_endpoints)
    extreme_train = extreme_candidate & keep
    extreme_overlap = np.intersect1d(
        np.concatenate([start_id[extreme_train], end_id[extreme_train]]),
        extreme_test_endpoints,
        assume_unique=False,
    ).size
    if extreme_overlap:
        raise AssertionError("Purged climate-extreme split retains shared yield endpoints")
    splits = {
        "temporal": (
            temporal_train,
            temporal_test,
            {
                "purge_rule": "drop_training_pairs_sharing_either_yield_endpoint_with_temporal_test",
                "purged_train_rows": int((temporal_candidate & ~temporal_train).sum()),
                "endpoint_overlap_count": 0,
            },
        ),
        "climate_extreme": (
            extreme_train,
            extreme_test,
            {
                "purge_rule": "drop_training_pairs_sharing_either_yield_endpoint_with_extreme_test",
                "purged_train_rows": int((extreme_candidate & ~extreme_train).sum()),
                "endpoint_overlap_count": 0,
            },
        ),
    }
    return splits


def evaluate_pairs_low_memory(
    pairs: pd.DataFrame,
    models: dict[str, list[str]],
    minimum_train_rows: int,
    minimum_test_rows: int,
) -> tuple[list[dict[str, Any]], int]:
    folds = sorted(int(value) for value in pairs["spatial_fold"].unique())
    if len(folds) < 2:
        raise ValueError("Spatial validation requires at least two populated folds")
    # A fold is constant within each crop/grid cell, so cell-disjointness is a
    # sufficient and much smaller endpoint-overlap check than materializing all
    # yield endpoint tuples repeatedly for every model.
    cell_folds = pairs[["lat", "lon_360", "spatial_fold"]].drop_duplicates()
    if cell_folds.duplicated(["lat", "lon_360"]).any():
        raise ValueError("Spatial fold changes within a crop/grid cell")
    split_masks = _purged_masks_low_memory(pairs)
    pairs.drop(columns=["crop", "irrigation", "lat", "lon_360"], inplace=True)
    del cell_folds
    gc.collect()
    results: list[dict[str, Any]] = []
    for model, features in models.items():
        spatial_observed: list[np.ndarray] = []
        spatial_predicted: list[np.ndarray] = []
        fold_audits: list[dict[str, Any]] = []
        for fold in folds:
            test_mask = pairs["spatial_fold"].eq(fold)
            train_mask = ~test_mask
            prediction, fit = _fit_predict_masks(
                pairs, train_mask, test_mask, features, minimum_train_rows, minimum_test_rows
            )
            spatial_observed.append(pairs.loc[test_mask, "delta_log_yield"].to_numpy(dtype=float))
            spatial_predicted.append(prediction)
            fold_audits.append({"fold": fold, "endpoint_overlap_count": 0, **fit})
        observed = np.concatenate(spatial_observed)
        predicted = np.concatenate(spatial_predicted)
        results.append(
            {
                "model": model,
                "holdout": "spatial_block",
                "feature_count": len(features),
                "folds": fold_audits,
                "test_rows": int(len(observed)),
                **_metrics(observed, predicted),
            }
        )
        for holdout, (train_mask, test_mask, purge) in split_masks.items():
            prediction, fit = _fit_predict_masks(
                pairs, train_mask, test_mask, features, minimum_train_rows, minimum_test_rows
            )
            fit.update(_metrics(pairs.loc[test_mask, "delta_log_yield"].to_numpy(dtype=float), prediction))
            fit.update(purge)
            results.append(
                {"model": model, "holdout": holdout, "feature_count": len(features), **fit}
            )
    return results, int(len(pairs))


def run_crop_fragment(
    crop: str,
    level_extract: Path,
    spec_path: Path,
    lock_path: Path,
) -> dict[str, Any]:
    spec, lock, models, _, _ = load_contract(spec_path, lock_path)
    source = lock["source"]
    crop_locks = {str(row["crop"]): row for row in lock["crops"]}
    if crop not in crop_locks:
        raise ValueError(f"Unregistered crop {crop}")
    levels = pd.read_parquet(level_extract)
    observed_level_rows = int(len(levels))
    if observed_level_rows != int(crop_locks[crop]["expected_observed_outcomes"]):
        raise ValueError(f"Level extract row count differs for {crop}")
    all_features = list(dict.fromkeys(feature for features in models.values() for feature in features))
    pairs = make_first_differences(levels, all_features)
    del levels
    gc.collect()
    pa.default_memory_pool().release_unused()
    results, pair_count = evaluate_pairs_low_memory(
        pairs,
        models,
        int(spec["minimum_train_rows"]),
        int(spec["minimum_test_rows"]),
    )
    for row in results:
        row["crop"] = crop
    return {
        "crop": crop,
        "source_rows": int(crop_locks[crop]["expected_rows"]),
        "observed_level_rows_loaded": observed_level_rows,
        "consecutive_pairs": pair_count,
        "results": results,
        "maximum_rss_bytes": int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss),
    }


def summarize_comparisons(results: list[dict[str, Any]], models: dict[str, list[str]]) -> tuple[list[dict[str, Any]], dict[str, list[str]]]:
    rows = {(row["crop"], row["model"], row["holdout"]): row for row in results}
    comparisons: list[dict[str, Any]] = []
    stable: dict[str, list[str]] = {}
    crops = sorted({row["crop"] for row in results})
    distribution_models = [name for name in models if name.startswith("quantity_plus_")]
    for crop in crops:
        stable[crop] = [
            model
            for model in distribution_models
            if all(
                float(rows[(crop, "seasonal_quantity", holdout)]["rmse"])
                > float(rows[(crop, model, holdout)]["rmse"])
                for holdout in HOLDOUTS
            )
        ]
        for holdout in HOLDOUTS:
            quantity = float(rows[(crop, "seasonal_quantity", holdout)]["rmse"])
            candidates = sorted(
                (
                    (float(rows[(crop, model, holdout)]["rmse"]), list(models).index(model), model)
                    for model in distribution_models
                )
            )
            best_rmse, _, best_model = candidates[0]
            comparisons.append(
                {
                    "crop": crop,
                    "holdout": holdout,
                    "test_rows": int(rows[(crop, "seasonal_quantity", holdout)]["test_rows"]),
                    "zero_change_rmse": float(rows[(crop, "seasonal_quantity", holdout)]["zero_change_rmse"]),
                    "temperature_control_rmse": float(rows[(crop, "temperature_control", holdout)]["rmse"]),
                    "seasonal_quantity_rmse": quantity,
                    "best_distribution_model_descriptive_only": best_model,
                    "best_distribution_rmse": best_rmse,
                    "distribution_improvement_vs_seasonal_quantity": quantity - best_rmse,
                    "predictive_winner_vs_seasonal_quantity": bool(best_rmse < quantity),
                }
            )
    return comparisons, stable


def run_diagnostic(spec_path: Path = SPEC_DEFAULT, lock_path: Path = LOCK_DEFAULT) -> dict[str, Any]:
    spec, lock, models, spec_hash, lock_hash = load_contract(spec_path, lock_path)
    source = lock["source"]
    panel_path = resolve_path(str(source["panel_path"]))
    panel_audit_path = resolve_path(str(source["panel_audit_path"]))
    if sha256_path(panel_path) != source["panel_sha256"]:
        raise ValueError("Multicrop source panel hash differs")
    if sha256_path(panel_audit_path) != source["panel_audit_sha256"]:
        raise ValueError("Multicrop source audit hash differs")
    panel_audit = json.loads(panel_audit_path.read_text(encoding="utf-8"))
    crop_locks = {str(row["crop"]): row for row in lock["crops"]}
    if set(crop_locks) != set(panel_audit.get("crops", [])):
        raise ValueError("Locked crop set differs from source audit")
    source_rows = {str(row["crop"]): row for row in panel_audit.get("sources", [])}
    if set(source_rows) != set(crop_locks):
        raise ValueError("Source audit crop records differ")
    if int(panel_audit.get("n_rows", -1)) != int(source["expected_rows"]):
        raise ValueError("Total source row count differs")
    if int(panel_audit.get("n_observed_yields", -1)) != int(source["expected_observed_outcomes"]):
        raise ValueError("Total observed outcome count differs")

    all_results: list[dict[str, Any]] = []
    crop_summaries: list[dict[str, Any]] = []
    total_pairs = 0
    worker_rss: dict[str, dict[str, int]] = {}
    worker_env = os.environ.copy()
    worker_env.update({"OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1"})
    with tempfile.TemporaryDirectory(prefix="multicrop_distribution_") as directory:
        scratch = Path(directory)
        for crop in sorted(crop_locks):
            locked = crop_locks[crop]
            registered = source_rows[crop]
            if int(registered["n_rows"]) != int(locked["expected_rows"]):
                raise ValueError(f"Source total rows differ for {crop}")
            if int(registered["n_observed_yields"]) != int(locked["expected_observed_outcomes"]):
                raise ValueError(f"Source observed outcomes differ for {crop}")
            for field in ("stage_panel", "label_panel"):
                path = resolve_path(str(locked[f"{field}_path"]))
                if sha256_path(path) != locked[f"{field}_sha256"]:
                    raise ValueError(f"{field} hash differs for {crop}")

            extract_path = scratch / f"{crop}_observed_stage.parquet"
            level_path = scratch / f"{crop}_observed_levels.parquet"
            extract = subprocess.run(
                [
                    sys.executable,
                    str(Path(__file__).resolve()),
                    "--spec", str(spec_path),
                    "--lock", str(lock_path),
                    "--extract-stage-crop", crop,
                    "--stage-extract", str(extract_path),
                ],
                check=True,
                capture_output=True,
                text=True,
                env=worker_env,
            )
            extract_receipt = json.loads(extract.stdout)
            level_run = subprocess.run(
                [
                    sys.executable,
                    str(Path(__file__).resolve()),
                    "--spec", str(spec_path),
                    "--lock", str(lock_path),
                    "--build-level-crop", crop,
                    "--stage-extract", str(extract_path),
                    "--level-extract", str(level_path),
                ],
                check=True,
                capture_output=True,
                text=True,
                env=worker_env,
            )
            level_receipt = json.loads(level_run.stdout)
            fragment_run = subprocess.run(
                [
                    sys.executable,
                    str(Path(__file__).resolve()),
                    "--spec", str(spec_path),
                    "--lock", str(lock_path),
                    "--worker-crop", crop,
                    "--level-extract", str(level_path),
                ],
                check=True,
                capture_output=True,
                text=True,
                env=worker_env,
            )
            fragment = json.loads(fragment_run.stdout)
            all_results.extend(fragment.pop("results"))
            total_pairs += int(fragment["consecutive_pairs"])
            worker_rss[crop] = {
                "extract_maximum_rss_bytes": int(extract_receipt["maximum_rss_bytes"]),
                "level_build_maximum_rss_bytes": int(level_receipt["maximum_rss_bytes"]),
                "evaluate_maximum_rss_bytes": int(fragment.pop("maximum_rss_bytes")),
            }
            fragment["maximum_reconciliation_differences"] = level_receipt[
                "maximum_reconciliation_differences"
            ]
            crop_summaries.append(fragment)

    comparisons, stable = summarize_comparisons(all_results, models)
    maximum_rss = max(value for crop in worker_rss.values() for value in crop.values())
    audit = {
        "status": STATUS,
        "diagnostic_contract_id": CONTRACT_ID,
        "specification_id": spec["specification_id"],
        "specification_version": spec["specification_version"],
        "spec_sha256": spec_hash,
        "lock_sha256": lock_hash,
        "source_panel": str(source["panel_path"]),
        "source_panel_sha256": source["panel_sha256"],
        "source_panel_audit": str(source["panel_audit_path"]),
        "source_panel_audit_sha256": source["panel_audit_sha256"],
        "source_rows": int(source["expected_rows"]),
        "observed_level_rows": int(source["expected_observed_outcomes"]),
        "observed_rows_only_in_memory": True,
        "crops": sorted(crop_locks),
        "models": list(models),
        "model_feature_counts": {name: len(features) for name, features in models.items()},
        "holdouts": list(HOLDOUTS),
        "validation_design": source["validation_design"],
        "nonspatial_split_contract": NONSPATIAL_SPLIT_CONTRACT,
        "n_consecutive_pairs": total_pairs,
        "crop_summaries": crop_summaries,
        "comparisons": comparisons,
        "stable_distribution_extensions_improving_all_holdouts": stable,
        "results": all_results,
        "coefficients_suppressed": True,
        "causal_interpretation_authorized": False,
        "production_model_selection_authorized": False,
        "response_draw_export_authorized": False,
        "scc_use_authorized": False,
        "runtime": {
            "maximum_worker_rss_bytes": maximum_rss,
            "worker_rss_bytes": worker_rss,
            "worker_isolation": "separate stage extraction, level construction, and evaluation processes per crop",
        },
        "warning": (
            "Predictive winner/loser labels compare held-out RMSE only. They are not causal crop impacts, "
            "economic winners or losers, response coefficients, damages, or SCC inputs."
        ),
    }
    assert_coefficients_suppressed(audit)
    return audit


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, default=SPEC_DEFAULT)
    parser.add_argument("--lock", type=Path, default=LOCK_DEFAULT)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--extract-stage-crop")
    parser.add_argument("--build-level-crop")
    parser.add_argument("--worker-crop")
    parser.add_argument("--stage-extract", type=Path)
    parser.add_argument("--level-extract", type=Path)
    args = parser.parse_args()
    if args.extract_stage_crop:
        if args.worker_crop or args.build_level_crop or args.out or args.stage_extract is None or args.level_extract:
            raise ValueError("Stage extraction requires only --extract-stage-crop and --stage-extract")
        spec, lock, models, _, _ = load_contract(args.spec, args.lock)
        crops = {str(row["crop"]): row for row in lock["crops"]}
        if args.extract_stage_crop not in crops:
            raise ValueError("Unregistered extraction crop")
        print(json.dumps(extract_observed_stage_rows(
            args.extract_stage_crop,
            crops[args.extract_stage_crop],
            lock["source"],
            models,
            args.stage_extract,
        ), sort_keys=True))
        return
    if args.build_level_crop:
        if args.worker_crop or args.out or args.stage_extract is None or args.level_extract is None:
            raise ValueError("Level construction requires --build-level-crop, --stage-extract, and --level-extract")
        spec, lock, models, _, _ = load_contract(args.spec, args.lock)
        crops = {str(row["crop"]): row for row in lock["crops"]}
        if args.build_level_crop not in crops:
            raise ValueError("Unregistered level crop")
        print(json.dumps(extract_observed_levels(
            args.build_level_crop,
            crops[args.build_level_crop],
            lock["source"],
            models,
            args.stage_extract,
            args.level_extract,
        ), sort_keys=True))
        return
    if args.worker_crop:
        if args.out or args.stage_extract or args.level_extract is None or args.build_level_crop:
            raise ValueError("Crop worker requires only --worker-crop and --level-extract")
        print(json.dumps(run_crop_fragment(
            args.worker_crop,
            args.level_extract,
            args.spec,
            args.lock,
        ), sort_keys=True))
        return
    if args.out is None or args.stage_extract is not None or args.level_extract is not None:
        raise ValueError("Full diagnostic requires --out and no extracts")
    audit = run_diagnostic(args.spec, args.lock)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in audit.items() if key != "results"}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
