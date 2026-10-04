#!/usr/bin/env python3
"""Hash-bind and validate the LOCA2 manuscript's outcome-blind sentinel claims."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "loca2_us/data/provenance/loca2_cuming_gfdl_historical_climate_sentinel_2001_2012_20261003.json"
INDEPENDENT = ROOT / "loca2_us/data/provenance/loca2_cuming_gfdl_historical_climate_sentinel_validation_20261003.json"
JOB = ROOT / "loca2_us/data/provenance/loca2_cuming_gfdl_historical_climate_sentinel_job_v4_20261003.json"
MAIN = ROOT / "loca2_us/manuscript/MAIN_MANUSCRIPT.md"
METHODS = ROOT / "loca2_us/manuscript/METHODS_SUPPORTING_INFORMATION.md"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def validate() -> dict[str, object]:
    source = json.loads(SOURCE.read_text())
    independent = json.loads(INDEPENDENT.read_text())
    job = json.loads(JOB.read_text())
    main = MAIN.read_text()
    methods = METHODS.read_text()

    require(source["status"] == independent["status"] == "pass", "sentinel receipt failed")
    require(job["status"] == "completed" and job["returncode"] == 0, "sentinel job failed")
    require(independent["checks"] == 400, "independent check count changed")
    require(independent["maximum_absolute_saved_precision_difference"] == 0.0, "saved precision differs")
    require(source["support"]["years"] == list(range(2001, 2013)), "sentinel years changed")
    require(source["support"]["outcome_columns_read"] is False, "outcome-read gate opened")
    require(source["support"]["paired_year_scoring"] is False, "paired-year scoring gate opened")
    require(job["sampled_peak_group_rss_bytes"] < 512 * 1024**2, "memory guard failed")
    for gate in ("multi_model_validation", "outcome_response", "causal_damage", "SCC"):
        require(source["claim_gates"][gate] is False, f"claim gate opened: {gate}")

    expected = {
        "precip_mm": ("432.15", "461.58", "-29.44", "0.931", "60.02 mm"),
        "cdd_max_days": ("22.22", "18.19", "+4.03", "0.870", "4.52 days"),
        "rx5day_mm": ("84.24", "84.67", "-0.43", "0.953", "5.84 mm"),
        "tmean_c": ("20.29", "19.41", "+0.89", "0.750", "0.82 C"),
    }
    for values in expected.values():
        require(all(value in main for value in values), f"manuscript table lacks {values}")
    require("400 saved arithmetic and\nsupport checks" in main, "main manuscript lacks independent-check statement")
    require("484,589,568 bytes (462.14 MiB)" in main, "main manuscript lacks exact memory receipt")
    require("paired-year RMSE, correlation, or trend agreement" in methods, "methods lacks free-running boundary")
    require(
        "multi-model,\nmulti-county, outcome-response, causal-damage, and SCC gates remain closed" in methods,
        "methods lacks closed claim gates",
    )
    require("county aggregation and climate validation remain open" not in main, "stale status remains")
    require("include bias, RMSE, correlation, trend difference" not in methods, "stale paired-year metrics remain")

    machine = {}
    for feature in expected:
        item = source["comparisons"][feature]
        machine[feature] = {
            key: item[key]
            for key in (
                "model_mean",
                "observed_mean",
                "climatology_bias_model_minus_observed",
                "standard_deviation_ratio",
                "quantile_rmse",
            )
        }
    return {
        "schema": "loca2_us_manuscript_sentinel_evidence_validation/v1",
        "status": "pass",
        "role": "outcome_blind_manuscript_evidence_reconciliation_only",
        "source_receipts": {str(path.relative_to(ROOT)): sha256(path) for path in (SOURCE, INDEPENDENT, JOB)},
        "manuscripts": {str(path.relative_to(ROOT)): sha256(path) for path in (MAIN, METHODS)},
        "support": source["support"],
        "machine_values": machine,
        "independent_checks": independent["checks"],
        "peak_rss_bytes": job["sampled_peak_group_rss_bytes"],
        "claim_gates": source["claim_gates"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = validate()
    output = args.output if args.output.is_absolute() else ROOT / args.output
    require(not output.exists(), "fresh output required")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            {
                "status": "pass",
                "independent_checks": result["independent_checks"],
                "peak_rss_bytes": result["peak_rss_bytes"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
