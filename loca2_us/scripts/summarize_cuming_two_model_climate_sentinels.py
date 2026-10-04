#!/usr/bin/env python3
"""Validate and summarize two outcome-blind Cuming LOCA2 climate sentinels."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
MODELS = {
    "GFDL-ESM4": {
        "receipt": ROOT / "loca2_us/data/provenance/loca2_cuming_gfdl_historical_climate_sentinel_2001_2012_20261003.json",
        "validation": ROOT / "loca2_us/data/provenance/loca2_cuming_gfdl_historical_climate_sentinel_validation_20261003.json",
        "job": ROOT / "loca2_us/data/provenance/loca2_cuming_gfdl_historical_climate_sentinel_job_v4_20261003.json",
    },
    "IPSL-CM6A-LR": {
        "receipt": ROOT / "loca2_us/data/provenance/loca2_cuming_ipsl_historical_climate_sentinel_2001_2012_20261004.json",
        "validation": ROOT / "loca2_us/data/provenance/loca2_cuming_ipsl_historical_climate_sentinel_validation_20261004.json",
        "job": ROOT / "loca2_us/data/provenance/loca2_cuming_ipsl_historical_climate_sentinel_job_20261004.json",
    },
}
HEADLINE = ("precip_mm", "cdd_max_days", "rx5day_mm", "tmean_c")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def summarize(receipts: dict[str, dict]) -> dict[str, dict]:
    require(set(receipts) == set(MODELS), "model set changed")
    features = set(receipts["GFDL-ESM4"]["comparisons"])
    require(features == set(receipts["IPSL-CM6A-LR"]["comparisons"]), "feature sets differ")
    result = {}
    for feature in sorted(features):
        observed_means = [receipts[model]["comparisons"][feature]["observed_mean"] for model in MODELS]
        observed_quantiles = [receipts[model]["comparisons"][feature]["observed_quantiles"] for model in MODELS]
        require(np.allclose(observed_means, observed_means[0], rtol=0, atol=1e-12), f"observed mean differs: {feature}")
        require(np.allclose(observed_quantiles, observed_quantiles[0], rtol=0, atol=1e-12), f"observed quantiles differ: {feature}")
        model_rows = {}
        for model in MODELS:
            item = receipts[model]["comparisons"][feature]
            model_rows[model] = {
                key: item[key]
                for key in (
                    "model_mean", "climatology_bias_model_minus_observed",
                    "standard_deviation_ratio", "quantile_rmse",
                )
            }
        means = [row["model_mean"] for row in model_rows.values()]
        biases = [row["climatology_bias_model_minus_observed"] for row in model_rows.values()]
        qrmse = [row["quantile_rmse"] for row in model_rows.values()]
        result[feature] = {
            "observed_mean": observed_means[0],
            "models": model_rows,
            "equal_gcm_mean_model_climatology": float(np.mean(means)),
            "equal_gcm_mean_climatology_bias": float(np.mean(biases)),
            "model_bias_minimum": float(np.min(biases)),
            "model_bias_maximum": float(np.max(biases)),
            "equal_gcm_mean_of_model_quantile_rmse": float(np.mean(qrmse)),
        }
    return result


def validate_and_summarize() -> dict[str, object]:
    receipts = {}
    source_files = {}
    support = None
    peak = 0
    for model, paths in MODELS.items():
        receipt = json.loads(paths["receipt"].read_text())
        validation = json.loads(paths["validation"].read_text())
        job = json.loads(paths["job"].read_text())
        require(receipt["status"] == validation["status"] == "pass", f"failed source/validation: {model}")
        require(receipt["source"]["source_id"] == model, f"source identity differs: {model}")
        require(receipt["source"]["variant_label"] == "r1i1p1f1", f"variant differs: {model}")
        require(validation["checks"] == 400 and validation["maximum_absolute_saved_precision_difference"] == 0.0,
                f"independent validation differs: {model}")
        require(job["status"] == "completed" and job["returncode"] == 0, f"bounded job failed: {model}")
        require(job["sampled_peak_group_rss_bytes"] < 512 * 1024**2, f"memory gate failed: {model}")
        require(receipt["support"]["outcome_columns_read"] is False, f"outcome gate opened: {model}")
        require(receipt["support"]["paired_year_scoring"] is False, f"paired scoring opened: {model}")
        for gate in ("multi_model_validation", "outcome_response", "causal_damage", "SCC"):
            require(receipt["claim_gates"][gate] is False, f"claim gate opened: {model}/{gate}")
        if support is None:
            support = receipt["support"]
        else:
            require(receipt["support"] == support, "model supports differ")
        receipts[model] = receipt
        peak = max(peak, int(job["sampled_peak_group_rss_bytes"]))
        for label, path in paths.items():
            source_files[str(path.relative_to(ROOT))] = {"role": f"{model}_{label}", "sha256": digest(path)}

    metrics = summarize(receipts)
    return {
        "schema": "loca2_us_cuming_two_model_climate_sentinels/v1",
        "status": "pass",
        "role": "outcome_blind_two_GCM_climate_distribution_sentinel_not_generalized_validation",
        "models": list(MODELS),
        "weighting": "equal_GCM",
        "support": support,
        "metrics": metrics,
        "headline_features": list(HEADLINE),
        "source_files": source_files,
        "maximum_sampled_peak_group_rss_bytes": peak,
        "claim_gates": {
            "second_GCM_sentinel": True,
            "multi_model_validation": False,
            "multi_county_validation": False,
            "outcome_response": False,
            "causal_damage": False,
            "SCC": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = validate_and_summarize()
    output = args.output if args.output.is_absolute() else ROOT / args.output
    require(not output.exists(), "fresh output required")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    headline = {
        feature: {
            "equal_gcm_bias": result["metrics"][feature]["equal_gcm_mean_climatology_bias"],
            "model_bias_range": [
                result["metrics"][feature]["model_bias_minimum"],
                result["metrics"][feature]["model_bias_maximum"],
            ],
        }
        for feature in HEADLINE
    }
    print(json.dumps({"status": "pass", "headline": headline}, indent=2))


if __name__ == "__main__":
    main()
