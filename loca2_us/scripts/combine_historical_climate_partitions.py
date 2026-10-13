#!/usr/bin/env python3
"""Combine frozen nonoverlapping LOCA2 sentinel partitions and rescore climate distributions."""

from __future__ import annotations

import argparse
import hashlib
import json
import tomllib
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from build_historical_climate_sentinel import FEATURES, compare_distributions, read_observed, require


ROOT = Path(__file__).resolve().parents[2]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipts", type=Path, nargs="+", required=True)
    parser.add_argument("--expected-year-min", type=int, required=True)
    parser.add_argument("--expected-year-max", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists() and not args.receipt.exists(), "fresh outputs required")
    records, frames, observed_frames = [], [], []
    for receipt_path in args.receipts:
        record = json.loads(receipt_path.read_text())
        require(record["status"] == "pass" and record["schema"] == "loca2_us_historical_climate_sentinel/v1", "partition receipt failed")
        config_path = ROOT / record["config"]["path"]
        require(digest(config_path) == record["config"]["sha256"], "partition config changed")
        config = tomllib.loads(config_path.read_text())
        feature_path = ROOT / record["output"]["path"]
        require(digest(feature_path) == record["output"]["sha256"], "partition features changed")
        frame = pd.read_parquet(feature_path)
        require(frame.harvest_year.tolist() == record["support"]["years"], "partition years differ")
        frames.append(frame)
        observed_frames.append(read_observed(ROOT, config))
        records.append({"receipt": str(receipt_path), "receipt_sha256": digest(receipt_path), "config": record["config"], "output": record["output"], "source": record["source"], "support": record["support"]})
    reference = records[0]
    for record in records[1:]:
        for field in ("store", "source_id", "experiment_id", "variant_label", "ensemble_index", "precipitation_version", "spatial_accumulator"):
            require(record["source"][field] == reference["source"][field], f"partition source differs: {field}")
        for field in ("county_geoid", "crop", "grid_cells", "season_days_each", "outcome_columns_read", "paired_year_scoring"):
            require(record["support"][field] == reference["support"][field], f"partition support differs: {field}")
    combined = pd.concat(frames, ignore_index=True).sort_values("harvest_year").reset_index(drop=True)
    observed = pd.concat(observed_frames, ignore_index=True).sort_values("harvest_year").reset_index(drop=True)
    expected_years = list(range(args.expected_year_min, args.expected_year_max + 1))
    require(combined.harvest_year.tolist() == expected_years, "combined model years differ")
    require(observed.harvest_year.tolist() == expected_years, "combined observed years differ")
    require(not combined.harvest_year.duplicated().any() and set(FEATURES).issubset(combined.columns), "combined feature support differs")
    comparisons = compare_distributions(combined, observed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    combined.to_parquet(args.output, index=False)
    result = {
        "schema": "loca2_us_historical_climate_partition_combination/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "pass",
        "role": "one_county_one_model_free_running_climate_distribution_sentinel_not_outcome_or_damage_validation",
        "partitions": records,
        "support": {"county_geoid": reference["support"]["county_geoid"], "crop": reference["support"]["crop"], "years": combined.harvest_year.tolist(), "year_count": len(combined), "grid_cells": reference["support"]["grid_cells"]},
        "comparisons": comparisons,
        "output": {"path": str(args.output), "bytes": args.output.stat().st_size, "sha256": digest(args.output)},
        "validation": {"nonoverlapping_complete_years": True, "partition_hashes": True, "source_identity": True, "observed_calendar_rebuilt": True},
        "claim_gates": {"one_county_one_model_historical_climate_sentinel": True, "multi_county_validation": False, "multi_model_validation": False, "outcome_response": False, "causal_damage": False, "SCC": False},
        "implementation": {"path": str(Path(__file__).resolve()), "sha256": digest(Path(__file__).resolve())},
    }
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": "pass", "support": result["support"], "precip": comparisons["precip_mm"], "cdd": comparisons["cdd_max_days"]}, indent=2))


if __name__ == "__main__":
    main()
