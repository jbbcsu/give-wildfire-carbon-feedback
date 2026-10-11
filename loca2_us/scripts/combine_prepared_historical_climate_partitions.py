#!/usr/bin/env python3
"""Combine validated nonoverlapping LOCA2 partitions and score distributions."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import tomllib
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
BUILDER_PATH = ROOT / "loca2_us/scripts/build_historical_climate_sentinel.py"
SPEC = importlib.util.spec_from_file_location("loca2_historical_builder_for_combination", BUILDER_PATH)
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
    parser.add_argument("--configs", nargs=2, type=Path, required=True)
    parser.add_argument("--validations", nargs=2, type=Path, required=True)
    parser.add_argument("--features-out", type=Path, required=True)
    parser.add_argument("--receipt-out", type=Path, required=True)
    args = parser.parse_args()
    config_paths = [path if path.is_absolute() else ROOT / path for path in args.configs]
    validation_paths = [path if path.is_absolute() else ROOT / path for path in args.validations]
    features_out = args.features_out if args.features_out.is_absolute() else ROOT / args.features_out
    receipt_out = args.receipt_out if args.receipt_out.is_absolute() else ROOT / args.receipt_out
    require(not features_out.exists() and not receipt_out.exists(), "fresh combined outputs required")

    configs = [tomllib.loads(path.read_text()) for path in config_paths]
    validations = [json.loads(path.read_text()) for path in validation_paths]
    require(all(item["status"] == "pass" and item["checks"] == 352 for item in validations), "partition validation failed")
    identity_fields = ("store", "precipitation_version", "source_id", "experiment_id", "variant_label", "variables")
    require(all(configs[0]["source"][key] == configs[1]["source"][key] for key in identity_fields), "source identity differs")
    require(configs[0]["sample"]["county_geoid"] == configs[1]["sample"]["county_geoid"], "county differs")
    require(configs[0]["sample"]["crop"] == configs[1]["sample"]["crop"], "crop differs")
    require(configs[0]["sample"]["outcome_columns_read"] is False and configs[1]["sample"]["outcome_columns_read"] is False, "outcome gate opened")
    require(configs[0]["sample"]["paired_year_scoring"] is False and configs[1]["sample"]["paired_year_scoring"] is False, "paired scoring gate opened")

    modeled_parts = [pd.read_parquet(ROOT / config["outputs"]["features"]) for config in configs]
    observed_parts = [BUILDER.read_prepared_local_inputs(ROOT, path, config)[1] for path, config in zip(config_paths, configs, strict=True)]
    modeled = pd.concat(modeled_parts, ignore_index=True).sort_values("harvest_year").reset_index(drop=True)
    observed = pd.concat(observed_parts, ignore_index=True).sort_values("harvest_year").reset_index(drop=True)
    expected_years = list(range(2001, 2013))
    require(modeled.harvest_year.astype(int).tolist() == expected_years, "modeled partitions overlap or omit years")
    require(observed.harvest_year.astype(int).tolist() == expected_years, "reference partitions overlap or omit years")
    comparisons = BUILDER.compare_distributions(modeled, observed)
    features_out.parent.mkdir(parents=True, exist_ok=True)
    modeled.to_parquet(features_out, index=False)
    source_paths = [*config_paths, *validation_paths, BUILDER_PATH]
    for config in configs:
        source_paths.extend((ROOT / config["outputs"]["receipt"], ROOT / config["outputs"]["features"]))
    result = {
        "schema": "loca2_us_combined_historical_climate_sentinel/v1",
        "status": "pass",
        "role": "free_running_second_county_climate_distribution_validation_not_paired_year_prediction",
        "source": {key: configs[0]["source"][key] for key in identity_fields},
        "support": {"county_geoid": configs[0]["sample"]["county_geoid"], "crop": configs[0]["sample"]["crop"], "years": expected_years, "outcome_columns_read": False, "paired_year_scoring": False},
        "comparisons": comparisons,
        "output": {"path": str(features_out.relative_to(ROOT)), "bytes": features_out.stat().st_size, "sha256": sha256(features_out)},
        "sources": {str(path.relative_to(ROOT)): sha256(path) for path in source_paths},
        "claim_gates": {"second_county_climate_sentinel": True, "multi_county_validation": False, "outcome_response": False, "causal_damage": False, "SCC": False},
    }
    receipt_out.parent.mkdir(parents=True, exist_ok=True)
    receipt_out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    headline = {feature: {key: comparisons[feature][key] for key in ("model_mean", "observed_mean", "climatology_bias_model_minus_observed", "standard_deviation_ratio", "quantile_rmse")} for feature in ("precip_mm", "cdd_max_days", "rx5day_mm", "tmean_c")}
    print(json.dumps({"status": "pass", "years": expected_years, "headline": headline}, indent=2))


if __name__ == "__main__":
    main()
