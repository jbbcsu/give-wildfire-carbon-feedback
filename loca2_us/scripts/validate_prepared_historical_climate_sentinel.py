#!/usr/bin/env python3
"""Independently validate prepared local inputs and a completed LOCA2 sentinel."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import tomllib
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
BUILDER_PATH = ROOT / "loca2_us/scripts/build_historical_climate_sentinel.py"
SPEC = importlib.util.spec_from_file_location("loca2_historical_builder_for_validation", BUILDER_PATH)
if SPEC is None or SPEC.loader is None:
    raise ImportError(f"cannot load {BUILDER_PATH}")
BUILDER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILDER)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--job-receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    config_path = args.config if args.config.is_absolute() else ROOT / args.config
    job_path = args.job_receipt if args.job_receipt.is_absolute() else ROOT / args.job_receipt
    output_path = args.output if args.output.is_absolute() else ROOT / args.output
    require(not output_path.exists(), "fresh validation output required")
    config = tomllib.loads(config_path.read_text())
    receipt_path = ROOT / config["outputs"]["receipt"]
    feature_path = ROOT / config["outputs"]["features"]
    cache_path = ROOT / config["inputs"]["prepared_local_inputs"]
    cache_receipt_path = ROOT / config["inputs"]["prepared_local_inputs_receipt"]
    receipt = json.loads(receipt_path.read_text())
    cache_receipt = json.loads(cache_receipt_path.read_text())
    job = json.loads(job_path.read_text())
    require(receipt["status"] == cache_receipt["status"] == "pass", "source receipt failed")
    require(job["status"] == "completed" and job["returncode"] == 0, "bounded job failed")
    require(job["sampled_peak_group_rss_bytes"] < 512 * 1024**2, "memory ceiling failed")
    require(receipt["config"]["sha256"] == cache_receipt["config"]["sha256"] == sha256(config_path), "config binding failed")
    require(receipt["output"]["sha256"] == sha256(feature_path), "feature output changed")
    require(cache_receipt["output"]["sha256"] == sha256(cache_path), "prepared cache changed")

    original_weights = pd.read_parquet(
        ROOT / config["inputs"]["weights"],
        columns=["grid_lat_index", "grid_lon_index", "spatial_weight"],
    ).sort_values(["grid_lat_index", "grid_lon_index"]).reset_index(drop=True)
    original_observed = BUILDER.read_observed(ROOT, config)
    prepared_weights, prepared_observed, _ = BUILDER.read_prepared_local_inputs(ROOT, config_path, config)
    prepared_weights = prepared_weights.sort_values(["grid_lat_index", "grid_lon_index"]).reset_index(drop=True)
    pd.testing.assert_frame_equal(prepared_weights, original_weights, check_exact=True)
    pd.testing.assert_frame_equal(prepared_observed, original_observed, check_exact=True)

    modeled = pd.read_parquet(feature_path).sort_values("harvest_year").reset_index(drop=True)
    recomputed = BUILDER.compare_distributions(modeled, original_observed)
    checks = 0
    for feature in BUILDER.FEATURES:
        for key in (
            "model_mean", "observed_mean", "climatology_bias_model_minus_observed",
            "model_standard_deviation", "observed_standard_deviation",
            "standard_deviation_ratio", "quantile_rmse",
        ):
            require(recomputed[feature][key] == receipt["comparisons"][feature][key], f"comparison changed: {feature}/{key}")
            checks += 1
        for key in ("model_quantiles", "observed_quantiles", "quantile_differences_model_minus_observed"):
            require(recomputed[feature][key] == receipt["comparisons"][feature][key], f"quantiles changed: {feature}/{key}")
            checks += len(recomputed[feature][key])
    result = {
        "schema": "loca2_us_prepared_historical_climate_sentinel_validation/v1",
        "status": "pass",
        "role": "independent_local_cache_equivalence_and_saved_arithmetic_validation",
        "checks": checks,
        "memory": {"peak_group_rss_bytes": job["sampled_peak_group_rss_bytes"], "maximum_bytes": 512 * 1024**2},
        "support": receipt["support"],
        "claim_gates": receipt["claim_gates"],
        "sources": {
            str(path.relative_to(ROOT)): sha256(path)
            for path in (config_path, job_path, receipt_path, feature_path, cache_receipt_path, cache_path, BUILDER_PATH)
        },
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": "pass", "checks": checks, "peak_group_rss_bytes": job["sampled_peak_group_rss_bytes"]}))


if __name__ == "__main__":
    main()
