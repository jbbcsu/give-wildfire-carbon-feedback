#!/usr/bin/env python3
"""Independent 2012-2016 confirmation of two frozen rainfed model families."""
from __future__ import annotations

import argparse
import gc
import hashlib
import json
import os
import resource
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.dataset as ds
import pyarrow.parquet as pq

from evaluate_crop_response_models import KEYS, LABELS, make_first_differences
from evaluate_multicrop_rainfed_distribution_diagnostic import (
    _fit_predict_masks,
    _source_columns,
    sha256_path,
)
from evaluate_multicrop_rainfed_distribution_geographic_audit import (
    geographic_cluster_codes,
    holm_adjust,
    summarize_losses,
)
from evaluate_precipitation_distribution_diagnostic import _expand_models
from make_validation_folds import stable_fold


PROJECT = Path(__file__).resolve().parents[1]
CONFIG_DEFAULT = PROJECT / "config" / "rainfed_distribution_later_period_confirmation_v1.toml"
CONTRACT_ID = "rainfed_distribution_later_period_external_confirmation_v1"
STATUS = "validated_noncausal_later_period_rainfed_distribution_confirmation_not_scc_eligible"


def resolve(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else PROJECT / path


def load_config(path: Path) -> tuple[dict[str, Any], str, dict[str, list[str]]]:
    raw = path.read_bytes()
    config = tomllib.loads(raw.decode("utf-8"))
    if config.get("schema_version") != 1 or config.get("contract_id") != CONTRACT_ID:
        raise ValueError("Unexpected later-period confirmation contract")
    if config.get("reference_model") != "seasonal_quantity":
        raise ValueError("Reference model changed")
    confirmations = config.get("confirmations", [])
    frozen = {(row["crop"], row["candidate_model"]) for row in confirmations}
    if frozen != {
        ("mai", "quantity_plus_timing_concentration"),
        ("soy", "quantity_plus_all_distribution"),
    }:
        raise ValueError("Frozen confirmation family changed")
    unavailable = config.get("unavailable", [])
    if len(unavailable) != 1 or unavailable[0].get("crop") != "swh":
        raise ValueError("Spring-wheat availability record changed")
    unavailable_path = resolve(unavailable[0]["expected_source_path"])
    if unavailable_path.exists():
        raise ValueError("Spring-wheat source is now present; unavailable contract must be revised")
    for field in ("selection_audit", "feature_spec"):
        artifact = resolve(config[f"{field}_path"])
        if sha256_path(artifact) != config[f"{field}_sha256"]:
            raise ValueError(f"{field} hash differs")
    selection = json.loads(resolve(config["selection_audit_path"]).read_text(encoding="utf-8"))
    selected_pairs = {(row["crop"], row["candidate_model"]) for row in selection["results"]}
    if not frozen.issubset(selected_pairs):
        raise ValueError("A frozen comparison is absent from the selection audit")
    specification = tomllib.loads(resolve(config["feature_spec_path"]).read_text(encoding="utf-8"))
    models = _expand_models(specification)
    for crop, candidate in frozen:
        if candidate not in models or config["reference_model"] not in models:
            raise ValueError(f"Frozen model absent from feature registry for {crop}")
    for source in confirmations:
        source_path = resolve(source["source_path"])
        if sha256_path(source_path) != source["source_sha256"]:
            raise ValueError(f"Later rainfed source hash differs for {source['crop']}")
        if pq.ParquetFile(source_path).metadata.num_rows != int(source["expected_rows"]):
            raise ValueError(f"Later rainfed source row count differs for {source['crop']}")
    authorization = config["authorization"]
    if authorization.get("independent_period_predictive_confirmation_authorized") is not True:
        raise ValueError("Predictive confirmation authorization missing")
    forbidden = [
        key for key in authorization if key != "independent_period_predictive_confirmation_authorized"
    ]
    if any(authorization[key] is not False for key in forbidden):
        raise ValueError("A forbidden claim gate is open")
    return config, hashlib.sha256(raw).hexdigest(), models


def build_observed_levels(
    source: dict[str, Any], models: dict[str, list[str]], config: dict[str, Any]
) -> tuple[pd.DataFrame, dict[str, float]]:
    crop = str(source["crop"])
    candidate = str(source["candidate_model"])
    required_models = [str(config["reference_model"]), candidate]
    requested = _source_columns(models)
    scanner = ds.Scanner.from_dataset(
        ds.dataset(resolve(source["source_path"]), format="parquet"),
        columns=requested,
        filter=ds.field("yield_observed") == True,  # noqa: E712
        batch_size=8192,
        batch_readahead=1,
        fragment_readahead=1,
        use_threads=False,
    )
    table = scanner.to_table()
    if table.num_rows != int(source["expected_observed_outcomes"]):
        raise ValueError(f"Observed outcome count differs for {crop}")
    if not bool(pc.all(pc.equal(table["crop"], crop)).as_py()):
        raise ValueError(f"Crop differs for {crop}")
    if not bool(pc.all(pc.equal(table["irrigation"], source["expected_irrigation"])).as_py()):
        raise ValueError(f"Irrigation regime differs for {crop}")
    frame = table.to_pandas()
    del table
    gc.collect()
    pa.default_memory_pool().release_unused()
    years = pd.to_numeric(frame["harvest_year"], errors="raise").astype(int)
    if years.min() != int(source["expected_year_start"]) or years.max() != int(source["expected_year_end"]):
        raise ValueError(f"Year coverage differs for {crop}")
    if (frame["yield_t_ha"] <= 0).any() or frame.duplicated(KEYS).any():
        raise ValueError(f"Invalid or duplicate observed outcomes for {crop}")

    stage_days = [f"stage{stage}_stage_days" for stage in (1, 2, 3)]
    stage_precip = [f"stage{stage}_precip_mm" for stage in (1, 2, 3)]
    stage_wet = [f"stage{stage}_wet_days_n" for stage in (1, 2, 3)]
    differences = {
        "stage_days": float((frame[stage_days].sum(axis=1) - frame["season_days"]).abs().max()),
        "stage_precip_mm": float((frame[stage_precip].sum(axis=1) - frame["precip_mm"]).abs().max()),
        "stage_wet_days": float((frame[stage_wet].sum(axis=1) - frame["wet_days_n"]).abs().max()),
    }
    if differences["stage_days"] != 0 or differences["stage_wet_days"] != 0 or differences["stage_precip_mm"] > 1e-3:
        raise ValueError(f"Stage reconciliation differs for {crop}: {differences}")

    frame["log1p_precip_mm"] = np.log1p(frame["precip_mm"].to_numpy(dtype=float))
    totals = frame["precip_mm"].to_numpy(dtype=float)
    stage_values = frame[stage_precip].to_numpy(dtype=float)
    shares = np.divide(stage_values, totals[:, None], out=np.zeros_like(stage_values), where=totals[:, None] > 0)
    frame["precipitation_concentration_hhi"] = np.square(shares).sum(axis=1)
    frame["precipitation_timing_centroid"] = (
        shares * ((np.arange(3, dtype=float) + 0.5) / 3.0)
    ).sum(axis=1)
    for stage in (1, 2, 3):
        prefix = f"stage{stage}_"
        days = frame[f"{prefix}stage_days"].to_numpy(dtype=float)
        wet = frame[f"{prefix}wet_days_n"].to_numpy(dtype=float)
        precip = frame[f"{prefix}precip_mm"].to_numpy(dtype=float)
        cdd = frame[f"{prefix}cdd_max_days"].to_numpy(dtype=float)
        frame[f"{prefix}wet_day_frequency"] = wet / days
        frame[f"{prefix}mean_wet_day_intensity_mm"] = np.divide(
            precip, wet, out=np.zeros_like(precip), where=wet > 0
        )
        frame[f"{prefix}cdd_fraction"] = cdd / days

    validation = config["spatial_validation"]
    block_degrees = float(validation["block_degrees"])
    lat_block = np.floor((frame["lat"].to_numpy(dtype=float) + 90.0) / block_degrees).astype(int)
    lon_block = np.floor(frame["lon_360"].to_numpy(dtype=float) / block_degrees).astype(int)
    block_ids = pd.Series(lat_block.astype(str)) + "_" + pd.Series(lon_block.astype(str))
    frame["spatial_fold"] = block_ids.map(
        lambda value: stable_fold(value, int(validation["folds"]), str(validation["seed"]))
    ).to_numpy()
    frame["is_temporal_holdout"] = False
    frame["is_climate_extreme"] = False
    if frame["spatial_fold"].nunique() != int(validation["folds"]):
        raise ValueError(f"Not all spatial folds populated for {crop}")
    feature_columns = list(
        dict.fromkeys(feature for model in required_models for feature in models[model])
    )
    if not np.isfinite(frame[feature_columns].to_numpy(dtype=float)).all():
        raise ValueError(f"Nonfinite constructed features for {crop}")
    keep = KEYS + LABELS + ["yield_t_ha", "yield_observed", *feature_columns]
    frame.drop(columns=[column for column in frame.columns if column not in keep], inplace=True)
    return frame, differences


def run_worker(crop: str, config_path: Path, seed_offset: int) -> dict[str, Any]:
    config, _, models = load_config(config_path)
    sources = {row["crop"]: row for row in config["confirmations"]}
    if crop not in sources:
        raise ValueError(f"Unregistered confirmation crop {crop}")
    source = sources[crop]
    levels, reconciliation = build_observed_levels(source, models, config)
    reference = str(config["reference_model"])
    candidate = str(source["candidate_model"])
    all_features = list(dict.fromkeys(models[reference] + models[candidate]))
    pairs = make_first_differences(levels, all_features)
    observed_levels = len(levels)
    del levels
    gc.collect()
    pa.default_memory_pool().release_unused()
    observed = pairs["delta_log_yield"].to_numpy(dtype=float)
    folds = pairs["spatial_fold"].to_numpy(dtype=int)
    clusters = geographic_cluster_codes(
        pairs["lat"].to_numpy(dtype=float),
        pairs["lon_360"].to_numpy(dtype=float),
        int(config["geographic_clusters"]["latitude_degrees"]),
        int(config["geographic_clusters"]["longitude_degrees"]),
    )
    scores: dict[str, np.ndarray] = {}
    for model in (reference, candidate):
        prediction = np.empty(len(pairs), dtype=float)
        for fold in range(int(config["spatial_validation"]["folds"])):
            test = pairs["spatial_fold"].eq(fold)
            values, _ = _fit_predict_masks(pairs, ~test, test, models[model], 100, 100)
            prediction[test.to_numpy()] = values
        if not np.isfinite(prediction).all():
            raise ValueError(f"Nonfinite OOF scores for {crop}/{model}")
        scores[model] = prediction
    summary_config = {
        "reference_model": reference,
        "candidate_models": [candidate],
        "spatial_folds": int(config["spatial_validation"]["folds"]),
        "geographic_clusters": config["geographic_clusters"],
        "uncertainty": config["uncertainty"],
    }
    rows, support = summarize_losses(
        crop, observed, folds, clusters, scores, summary_config, seed_offset
    )
    return {
        "crop": crop,
        "observed_levels": observed_levels,
        "consecutive_pairs": len(pairs),
        "stage_reconciliation_maximum_absolute_differences": reconciliation,
        "result": rows[0],
        "geographic_support": support,
        "maximum_rss_bytes": int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss),
    }


def run_confirmation(config_path: Path = CONFIG_DEFAULT) -> dict[str, Any]:
    config, config_hash, _ = load_config(config_path)
    environment = os.environ.copy()
    environment.update({"OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1"})
    fragments: list[dict[str, Any]] = []
    for offset, source in enumerate(config["confirmations"]):
        process = subprocess.run(
            [sys.executable, str(Path(__file__).resolve()), "--config", str(config_path),
             "--worker-crop", source["crop"], "--seed-offset", str(offset)],
            check=False, capture_output=True, text=True, env=environment,
        )
        if process.returncode:
            raise RuntimeError(f"Confirmation worker failed for {source['crop']}: {process.stderr}")
        fragments.append(json.loads(process.stdout))
    rows = [fragment["result"] for fragment in fragments]
    adjusted = holm_adjust([row["two_sided_bootstrap_tail_probability"] for row in rows])
    alpha = float(config["uncertainty"]["familywise_alpha"])
    for row, value in zip(rows, adjusted):
        row["holm_adjusted_tail_probability_two_tests"] = value
        row["passes_prespecified_later_period_confirmation_gate"] = bool(
            row["candidate_minus_reference_rmse"] < 0
            and row["paired_cluster_bootstrap_rmse_difference_quantiles"]["p97_5"] < 0
            and value <= alpha
            and row["all_five_spatial_folds_have_lower_candidate_rmse"]
            and row["cluster_share_with_lower_candidate_mean_squared_loss"] > 0.5
        )
    family_pass = all(row["passes_prespecified_later_period_confirmation_gate"] for row in rows)
    maximum_rss = max(fragment["maximum_rss_bytes"] for fragment in fragments)
    memory_cap = int(config["resources"]["worker_memory_bytes_maximum"])
    if maximum_rss > memory_cap:
        raise MemoryError("Later-period confirmation exceeds worker memory contract")
    result = {
        "status": STATUS,
        "contract_id": CONTRACT_ID,
        "config_sha256": config_hash,
        "selection_audit_path": config["selection_audit_path"],
        "selection_audit_sha256": config["selection_audit_sha256"],
        "selection_period": config["selection_period"],
        "confirmation_period": config["confirmation_period"],
        "confirmation_scope": config["confirmation_scope"],
        "comparison_count": 2,
        "results": rows,
        "available_crop_receipts": [
            {key: value for key, value in fragment.items() if key not in {"result", "maximum_rss_bytes"}}
            for fragment in fragments
        ],
        "unavailable_crops": config["unavailable"],
        "both_available_confirmations_pass": family_pass,
        "predictive_family_level_promotion_authorized": family_pass,
        "coefficients_suppressed": True,
        "row_predictions_exported": False,
        "bootstrap_draws_exported": False,
        "causal_interpretation_authorized": False,
        "economic_winner_loser_interpretation_authorized": False,
        "production_model_selection_authorized": False,
        "response_draw_export_authorized": False,
        "damage_calculation_authorized": False,
        "scc_use_authorized": False,
        "runtime": {
            "maximum_worker_rss_bytes": maximum_rss,
            "worker_memory_bytes_maximum": memory_cap,
            "worker_rss_bytes": {fragment["crop"]: fragment["maximum_rss_bytes"] for fragment in fragments},
        },
        "warning": (
            "This confirms or rejects predictive model families after refitting on independent later outcomes. "
            "It does not transport early-period coefficients or identify causal, economic, damage, or SCC effects."
        ),
    }
    if family_pass:
        result["predictive_family_level_promotion_authorized"] = True
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=CONFIG_DEFAULT)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--worker-crop")
    parser.add_argument("--seed-offset", type=int)
    args = parser.parse_args()
    if args.worker_crop:
        if args.out or args.seed_offset is None:
            raise ValueError("Worker requires crop and seed offset")
        print(json.dumps(run_worker(args.worker_crop, args.config, args.seed_offset), sort_keys=True))
        return
    if args.out is None or args.seed_offset is not None:
        raise ValueError("Full confirmation requires --out only")
    result = run_confirmation(args.config)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in result.items() if key != "results"}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
