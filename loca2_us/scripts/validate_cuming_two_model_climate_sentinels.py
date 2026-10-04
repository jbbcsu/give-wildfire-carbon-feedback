#!/usr/bin/env python3
"""Independently audit the saved two-GCM Cuming climate-only summary."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[2]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    candidate_path = args.candidate if args.candidate.is_absolute() else ROOT / args.candidate
    output = args.output if args.output.is_absolute() else ROOT / args.output
    require(not output.exists(), "fresh output required")
    candidate = json.loads(candidate_path.read_text())
    require(candidate["status"] == "pass", "candidate failed")
    require(candidate["models"] == ["GFDL-ESM4", "IPSL-CM6A-LR"], "model order changed")
    require(candidate["weighting"] == "equal_GCM", "weighting changed")
    require(candidate["support"]["outcome_columns_read"] is False, "outcome gate opened")
    require(candidate["support"]["paired_year_scoring"] is False, "paired-year gate opened")
    for gate in ("multi_model_validation", "multi_county_validation", "outcome_response", "causal_damage", "SCC"):
        require(candidate["claim_gates"][gate] is False, f"claim gate opened: {gate}")

    source_receipts = {}
    for model in candidate["models"]:
        matches = [
            (ROOT / path, metadata)
            for path, metadata in candidate["source_files"].items()
            if metadata["role"] == f"{model}_receipt"
        ]
        require(len(matches) == 1, f"receipt identity missing: {model}")
        path, metadata = matches[0]
        require(digest(path) == metadata["sha256"], f"source receipt hash changed: {model}")
        receipt = json.loads(path.read_text())
        require(receipt["source"]["source_id"] == model, f"source model differs: {model}")
        require(receipt["support"] == candidate["support"], f"support differs: {model}")
        source_receipts[model] = receipt

    checks = 0
    maximum_difference = 0.0
    require(set(candidate["metrics"]) == set(source_receipts["GFDL-ESM4"]["comparisons"]), "feature set changed")
    for feature, saved in candidate["metrics"].items():
        observed = []
        means = []
        biases = []
        qrmse = []
        for model in candidate["models"]:
            item = source_receipts[model]["comparisons"][feature]
            observed.append(float(item["observed_mean"]))
            means.append(float(item["model_mean"]))
            biases.append(float(item["climatology_bias_model_minus_observed"]))
            qrmse.append(float(item["quantile_rmse"]))
            for key in ("model_mean", "climatology_bias_model_minus_observed", "standard_deviation_ratio", "quantile_rmse"):
                difference = abs(float(saved["models"][model][key]) - float(item[key]))
                maximum_difference = max(maximum_difference, difference)
                require(difference <= 1e-12, f"model metric differs: {model}/{feature}/{key}")
                checks += 1
        recomputed = {
            "observed_mean": observed[0],
            "equal_gcm_mean_model_climatology": float(np.mean(means)),
            "equal_gcm_mean_climatology_bias": float(np.mean(biases)),
            "model_bias_minimum": float(np.min(biases)),
            "model_bias_maximum": float(np.max(biases)),
            "equal_gcm_mean_of_model_quantile_rmse": float(np.mean(qrmse)),
        }
        require(abs(observed[0] - observed[1]) <= 1e-12, f"observed mean differs: {feature}")
        for key, value in recomputed.items():
            difference = abs(float(saved[key]) - value)
            maximum_difference = max(maximum_difference, difference)
            require(difference <= 1e-12, f"aggregate metric differs: {feature}/{key}")
            checks += 1

    result = {
        "schema": "loca2_us_cuming_two_model_climate_sentinels_validation/v1",
        "status": "pass",
        "checks": checks,
        "maximum_absolute_saved_precision_difference": maximum_difference,
        "candidate": {"path": str(candidate_path.relative_to(ROOT)), "sha256": digest(candidate_path)},
        "models": candidate["models"],
        "support": candidate["support"],
        "claim_gates": candidate["claim_gates"],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": "pass", "checks": checks, "maximum_difference": maximum_difference}, sort_keys=True))


if __name__ == "__main__":
    main()
