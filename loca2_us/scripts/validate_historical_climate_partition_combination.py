#!/usr/bin/env python3
"""Independently validate a combined LOCA2 historical climate sentinel."""

from __future__ import annotations

import argparse
import hashlib
import json
import tomllib
from pathlib import Path

import numpy as np
import pandas as pd

from build_historical_climate_sentinel import FEATURES, compare_distributions, read_observed, require


ROOT = Path(__file__).resolve().parents[2]


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def resolve(path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else ROOT / candidate


def assert_nested_close(actual: object, expected: object, label: str) -> tuple[int, float]:
    if isinstance(expected, dict):
        require(isinstance(actual, dict) and set(actual) == set(expected), f"keys differ: {label}")
        checks, maximum = 0, 0.0
        for key in sorted(expected):
            child_checks, child_maximum = assert_nested_close(actual[key], expected[key], f"{label}/{key}")
            checks += child_checks
            maximum = max(maximum, child_maximum)
        return checks, maximum
    if isinstance(expected, list):
        require(isinstance(actual, list) and len(actual) == len(expected), f"list differs: {label}")
        checks, maximum = 0, 0.0
        for index, expected_value in enumerate(expected):
            child_checks, child_maximum = assert_nested_close(actual[index], expected_value, f"{label}/{index}")
            checks += child_checks
            maximum = max(maximum, child_maximum)
        return checks, maximum
    if isinstance(expected, (int, float)) and not isinstance(expected, bool):
        difference = abs(float(actual) - float(expected))
        require(np.isclose(float(actual), float(expected), rtol=0, atol=1e-12), f"value differs: {label}")
        return 1, difference
    require(actual == expected, f"value differs: {label}")
    return 1, 0.0


def validate(record: dict) -> dict:
    require(record["schema"] == "loca2_us_historical_climate_partition_combination/v1", "wrong schema")
    require(record["status"] == "pass", "combination did not pass")
    require(len(record["partitions"]) >= 2, "at least two partitions required")
    combined_path = resolve(record["output"]["path"])
    require(digest(combined_path) == record["output"]["sha256"], "combined output changed")
    combined = pd.read_parquet(combined_path).sort_values("harvest_year").reset_index(drop=True)

    model_frames: list[pd.DataFrame] = []
    observed_frames: list[pd.DataFrame] = []
    partition_years: list[int] = []
    checks = 1
    for partition in record["partitions"]:
        receipt_path = resolve(partition["receipt"])
        require(digest(receipt_path) == partition["receipt_sha256"], "partition receipt changed")
        source_record = json.loads(receipt_path.read_text())
        require(source_record["status"] == "pass", "partition did not pass")
        require(source_record["support"]["outcome_columns_read"] is False, "partition read outcomes")
        require(source_record["support"]["paired_year_scoring"] is False, "partition used paired scoring")
        config_path = resolve(source_record["config"]["path"])
        feature_path = resolve(source_record["output"]["path"])
        require(digest(config_path) == source_record["config"]["sha256"], "partition config changed")
        require(digest(feature_path) == source_record["output"]["sha256"], "partition output changed")
        config = tomllib.loads(config_path.read_text())
        frame = pd.read_parquet(feature_path).sort_values("harvest_year").reset_index(drop=True)
        require(frame.harvest_year.tolist() == source_record["support"]["years"], "partition years differ")
        model_frames.append(frame)
        observed_frames.append(read_observed(ROOT, config))
        partition_years.extend(source_record["support"]["years"])
        checks += 7

    require(len(partition_years) == len(set(partition_years)), "partition years overlap")
    rebuilt = pd.concat(model_frames, ignore_index=True).sort_values("harvest_year").reset_index(drop=True)
    observed = pd.concat(observed_frames, ignore_index=True).sort_values("harvest_year").reset_index(drop=True)
    expected_years = record["support"]["years"]
    require(rebuilt.harvest_year.tolist() == expected_years, "rebuilt years differ")
    require(observed.harvest_year.tolist() == expected_years, "observed years differ")
    require(list(combined.columns) == list(rebuilt.columns), "combined columns differ")
    for column in combined.columns:
        if column == "harvest_year":
            require(combined[column].tolist() == rebuilt[column].tolist(), "combined year values differ")
        else:
            require(np.allclose(combined[column], rebuilt[column], rtol=0, atol=0), f"combined values differ: {column}")
        checks += 1

    for frame, label in ((combined, "modeled"), (observed, "observed")):
        require(
            np.allclose(frame[["stage1_precip_mm", "stage2_precip_mm", "stage3_precip_mm"]].sum(axis=1), frame.precip_mm, rtol=0, atol=1e-8),
            f"{label} stage precipitation does not reconcile",
        )
        require(
            np.allclose(frame[["stage1_precip_share", "stage2_precip_share", "stage3_precip_share"]].sum(axis=1), 1.0, rtol=0, atol=1e-10),
            f"{label} precipitation shares do not reconcile",
        )
        checks += 2 * len(frame)

    recomputed = compare_distributions(combined, observed)
    comparison_checks, maximum_difference = assert_nested_close(recomputed, record["comparisons"], "comparisons")
    checks += comparison_checks
    require(set(FEATURES) == set(recomputed), "feature set differs")
    require(record["claim_gates"]["multi_county_validation"] is False, "multi-county gate must stay closed")
    require(record["claim_gates"]["outcome_response"] is False, "outcome gate must stay closed")
    require(record["claim_gates"]["causal_damage"] is False, "damage gate must stay closed")
    require(record["claim_gates"]["SCC"] is False, "SCC gate must stay closed")
    return {"checks": checks + 5, "maximum_absolute_saved_precision_difference": maximum_difference}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = resolve(args.output)
    require(not output.exists(), "fresh validation output required")
    receipt_path = resolve(args.receipt)
    record = json.loads(receipt_path.read_text())
    result = validate(record)
    result.update(
        {
            "schema": "loca2_us_historical_climate_partition_combination_validation/v1",
            "status": "pass",
            "source_receipt": {"path": str(receipt_path.relative_to(ROOT)), "sha256": digest(receipt_path)},
            "support": record["support"],
            "claim_gates": record["claim_gates"],
        }
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": "pass", **{key: result[key] for key in ("checks", "maximum_absolute_saved_precision_difference")}}, indent=2))


if __name__ == "__main__":
    main()
