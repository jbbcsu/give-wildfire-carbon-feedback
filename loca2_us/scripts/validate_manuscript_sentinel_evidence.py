#!/usr/bin/env python3
"""Hash-bind and validate the LOCA2 manuscript's outcome-blind sentinel claims."""

from __future__ import annotations

import argparse
import hashlib
import json
import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "loca2_us/data/provenance/loca2_cuming_gfdl_historical_climate_sentinel_2001_2012_20261003.json"
INDEPENDENT = ROOT / "loca2_us/data/provenance/loca2_cuming_gfdl_historical_climate_sentinel_validation_20261003.json"
JOB = ROOT / "loca2_us/data/provenance/loca2_cuming_gfdl_historical_climate_sentinel_job_v4_20261003.json"
TWO_MODEL = ROOT / "loca2_us/data/provenance/loca2_cuming_two_model_climate_sentinels_20261004.json"
BOX_BUTTE_WEIGHTS = ROOT / "loca2_us/data/provenance/loca2_box_butte_tiger2019_weights_20261004.json"
BOX_BUTTE_JOB = ROOT / "loca2_us/data/provenance/loca2_box_butte_tiger2019_weights_job_20261004.json"
BOX_BUTTE_PREFLIGHT = ROOT / "loca2_us/data/provenance/loca2_box_butte_gfdl_historical_chunk_preflight_20261004.json"
BOX_BUTTE_PREFLIGHT_JOB = ROOT / "loca2_us/data/provenance/loca2_box_butte_gfdl_historical_chunk_preflight_job_20261004.json"
BOX_BUTTE_PART_CONFIGS = (
    ROOT / "loca2_us/config/loca2_us_box_butte_gfdl_historical_2001_2006_v1.toml",
    ROOT / "loca2_us/config/loca2_us_box_butte_gfdl_historical_2007_2012_v1.toml",
)
BOX_BUTTE_PART_PREFLIGHTS = (
    ROOT / "loca2_us/data/provenance/loca2_box_butte_gfdl_historical_2001_2006_preflight_20261004.json",
    ROOT / "loca2_us/data/provenance/loca2_box_butte_gfdl_historical_2007_2012_preflight_20261004.json",
)
BOX_BUTTE_PART_PREFLIGHT_JOBS = (
    ROOT / "loca2_us/data/provenance/loca2_box_butte_gfdl_historical_2001_2006_preflight_job_20261004.json",
    ROOT / "loca2_us/data/provenance/loca2_box_butte_gfdl_historical_2007_2012_preflight_job_20261004.json",
)
BOX_BUTTE_PART1_JOB = ROOT / "loca2_us/data/provenance/loca2_box_butte_gfdl_historical_2001_2006_job_20261004.json"
BOX_BUTTE_LOW_MEMORY_CONFIG = ROOT / "loca2_us/config/loca2_us_box_butte_gfdl_historical_2001_2006_spatial_chunk_v1.toml"
BOX_BUTTE_LOW_MEMORY_PREFLIGHT = ROOT / "loca2_us/data/provenance/loca2_box_butte_gfdl_historical_2001_2006_spatial_chunk_v1_preflight_20261004.json"
BOX_BUTTE_LOW_MEMORY_PREFLIGHT_JOB = ROOT / "loca2_us/data/provenance/loca2_box_butte_gfdl_historical_2001_2006_spatial_chunk_v1_preflight_job_20261004.json"
BOX_BUTTE_LOW_MEMORY_JOB = ROOT / "loca2_us/data/provenance/loca2_box_butte_gfdl_historical_2001_2006_spatial_chunk_v1_job_20261004.json"
BOX_BUTTE_LOW_MEMORY_ABSENT = (
    ROOT / "loca2_us/data/interim/box_butte_gfdl_historical_2001_2006_spatial_chunk_v1_corn_features.parquet",
    ROOT / "loca2_us/data/provenance/loca2_box_butte_gfdl_historical_climate_sentinel_2001_2006_spatial_chunk_v1_20261004.json",
)
BOX_BUTTE_EXPECTED_ABSENT = (
    ROOT / "loca2_us/data/interim/box_butte_gfdl_historical_2001_2006_corn_features.parquet",
    ROOT / "loca2_us/data/provenance/loca2_box_butte_gfdl_historical_climate_sentinel_2001_2006_20261004.json",
    ROOT / "loca2_us/data/interim/box_butte_gfdl_historical_2007_2012_corn_features.parquet",
    ROOT / "loca2_us/data/provenance/loca2_box_butte_gfdl_historical_climate_sentinel_2007_2012_20261004.json",
)
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
    two_model = json.loads(TWO_MODEL.read_text())
    box_butte_weights = json.loads(BOX_BUTTE_WEIGHTS.read_text())
    box_butte_job = json.loads(BOX_BUTTE_JOB.read_text())
    box_butte_preflight = json.loads(BOX_BUTTE_PREFLIGHT.read_text())
    box_butte_preflight_job = json.loads(BOX_BUTTE_PREFLIGHT_JOB.read_text())
    part_configs = [tomllib.loads(path.read_text()) for path in BOX_BUTTE_PART_CONFIGS]
    part_preflights = [json.loads(path.read_text()) for path in BOX_BUTTE_PART_PREFLIGHTS]
    part_preflight_jobs = [json.loads(path.read_text()) for path in BOX_BUTTE_PART_PREFLIGHT_JOBS]
    part1_job = json.loads(BOX_BUTTE_PART1_JOB.read_text())
    low_memory_config = tomllib.loads(BOX_BUTTE_LOW_MEMORY_CONFIG.read_text())
    low_memory_preflight = json.loads(BOX_BUTTE_LOW_MEMORY_PREFLIGHT.read_text())
    low_memory_preflight_job = json.loads(BOX_BUTTE_LOW_MEMORY_PREFLIGHT_JOB.read_text())
    low_memory_job = json.loads(BOX_BUTTE_LOW_MEMORY_JOB.read_text())
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
    require(two_model["status"] == "pass", "two-model sentinel failed")
    require(two_model["models"] == ["GFDL-ESM4", "IPSL-CM6A-LR"], "two-model identities changed")
    require(two_model["weighting"] == "equal_GCM", "two-model weighting changed")
    require(two_model["support"] == source["support"], "two-model support changed")
    for gate in ("multi_model_validation", "multi_county_validation", "outcome_response", "causal_damage", "SCC"):
        require(two_model["claim_gates"][gate] is False, f"two-model claim gate opened: {gate}")
    require(box_butte_weights["status"] == "pass", "Box Butte weights failed")
    require(box_butte_weights["audit"]["county_geoid"] == "31013", "Box Butte GEOID changed")
    require(box_butte_weights["audit"]["positive_grid_cells"] == 100, "Box Butte cell count changed")
    require(box_butte_job["status"] == "completed" and box_butte_job["returncode"] == 0, "Box Butte weights job failed")
    require(box_butte_job["sampled_peak_group_rss_bytes"] < 512 * 1024**2, "Box Butte weights memory guard failed")
    require(box_butte_preflight["status"] == "blocked_remote_chunk_plan_exceeds_cap", "Box Butte preflight did not fail closed")
    require(box_butte_preflight["inspection"] == {"climate_values_read": False, "outcome_columns_read": False}, "Box Butte preflight opened a data gate")
    require(box_butte_preflight["plan"]["compressed_bytes"] == 1206323507, "Box Butte chunk bytes changed")
    require(box_butte_preflight["plan"]["remote_objects"] == 60, "Box Butte chunk count changed")
    require(box_butte_preflight_job["status"] == "completed" and box_butte_preflight_job["returncode"] == 0, "Box Butte preflight job failed")
    require(box_butte_preflight_job["sampled_peak_group_rss_bytes"] < 512 * 1024**2, "Box Butte preflight memory guard failed")
    for gate in ("second_county_climate_sentinel", "multi_county_validation", "outcome_response", "causal_damage", "SCC"):
        require(box_butte_preflight["claim_gates"][gate] is False, f"Box Butte claim gate opened: {gate}")
    part_years = [
        set(range(config["sample"]["year_min"], config["sample"]["year_max"] + 1))
        for config in part_configs
    ]
    require(not part_years[0] & part_years[1] and part_years[0] | part_years[1] == set(range(2001, 2013)), "Box Butte partitions overlap or omit years")
    require([item["plan"]["compressed_bytes"] for item in part_preflights] == [602729539, 724320234], "Box Butte partition plans changed")
    for config, preflight, preflight_job in zip(part_configs, part_preflights, part_preflight_jobs, strict=True):
        require(config["sample"]["outcome_columns_read"] is False and config["sample"]["paired_year_scoring"] is False, "Box Butte partition read/scoring gate opened")
        require(all(value is False for value in config["claim_gates"].values()), "Box Butte partition claim gate opened")
        require(preflight["status"] == "pass_metadata_only_plan_within_cap", "Box Butte partition preflight failed")
        require(preflight["inspection"] == {"climate_values_read": False, "outcome_columns_read": False}, "Box Butte partition preflight opened a data gate")
        require(preflight_job["status"] == "completed" and preflight_job["returncode"] == 0, "Box Butte partition preflight job failed")
        require(preflight_job["sampled_peak_group_rss_bytes"] < 512 * 1024**2, "Box Butte partition preflight memory guard failed")
    require(part1_job["status"] == "memory_budget_exceeded" and part1_job["returncode"] == -9, "Box Butte execution did not fail closed")
    require(part1_job["sampled_peak_group_rss_bytes"] == 560070656, "Box Butte execution peak changed")
    require(part1_job["sampled_peak_group_rss_bytes"] > 512 * 1024**2, "Box Butte memory gate was not exceeded")
    require(all(not path.exists() for path in BOX_BUTTE_EXPECTED_ABSENT), "Box Butte failed/stopped execution left a promoted artifact")
    require(low_memory_config["resources"]["spatial_accumulator"] == "one_source_spatial_chunk_at_a_time_v1", "Box Butte low-memory strategy changed")
    require(low_memory_config["sample"]["outcome_columns_read"] is False and low_memory_config["sample"]["paired_year_scoring"] is False, "Box Butte low-memory read/scoring gate opened")
    require(all(value is False for value in low_memory_config["claim_gates"].values()), "Box Butte low-memory claim gate opened")
    require(low_memory_preflight["status"] == "pass_metadata_only_plan_within_cap", "Box Butte low-memory preflight failed")
    require(low_memory_preflight["plan"]["compressed_bytes"] == 602729539, "Box Butte low-memory plan changed")
    require(low_memory_preflight["inspection"] == {"climate_values_read": False, "outcome_columns_read": False}, "Box Butte low-memory preflight opened a data gate")
    require(low_memory_preflight_job["status"] == "completed" and low_memory_preflight_job["returncode"] == 0, "Box Butte low-memory preflight job failed")
    require(low_memory_preflight_job["sampled_peak_group_rss_bytes"] == 182190080, "Box Butte low-memory preflight peak changed")
    require(low_memory_job["status"] == "memory_budget_exceeded" and low_memory_job["returncode"] == -9, "Box Butte low-memory retry did not fail closed")
    require(low_memory_job["sampled_peak_group_rss_bytes"] == 546308096, "Box Butte low-memory retry peak changed")
    require(all(not path.exists() for path in BOX_BUTTE_LOW_MEMORY_ABSENT), "Box Butte low-memory failure left a promoted artifact")

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
    for value in ("+4.90 mm", "+0.73 days", "-4.32 mm", "+1.34 C", "-12.27 mm", "+2.38 days", "-2.38 mm", "+1.11 C"):
        require(value in main, f"main manuscript lacks two-model value: {value}")
    require("483,278,848\nbytes" in methods, "methods lacks IPSL memory receipt")
    require("general multi-model validation gate" in methods, "methods lacks two-model gate boundary")
    for value in ("59 counties", "520.4337 km", "1,206,323,507", "1,150.44 MiB", "1,024 MiB"):
        require(value in main and value in methods, f"manuscripts lack geographic-preflight value: {value}")
    require("execution therefore fails closed" in methods, "methods lacks fail-closed boundary")
    require(all(value in main and value in methods for value in ("185,270,272", "176.69 MiB")), "manuscripts lack preflight memory receipt")
    for value in ("602,729,539", "574.81 MiB", "724,320,234", "690.77 MiB", "560,070,656", "534.13 MiB"):
        require(value in main and value in methods, f"manuscripts lack Box Butte split-gate value: {value}")
    require("No\nfeature file or successful sentinel receipt was written" in methods, "methods lacks absent-artifact boundary")
    require("The second partition and concatenation\nwere not run" in main, "main lacks stopped-execution boundary")
    for value in ("one_source_spatial_chunk_at_a_time_v1", "546,308,096", "521.00 MiB"):
        require(value in methods, f"methods lack low-memory retry value: {value}")
    require("bit-for-bit\nsynthetic equivalence" in main, "main lacks exact-equivalence boundary")
    require("Part 2 and\nconcatenation were not run" in methods, "methods lacks low-memory stop boundary")
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
        "source_receipts": {
            str(path.relative_to(ROOT)): sha256(path)
            for path in (
                SOURCE, INDEPENDENT, JOB, TWO_MODEL, BOX_BUTTE_WEIGHTS,
                BOX_BUTTE_JOB, BOX_BUTTE_PREFLIGHT, BOX_BUTTE_PREFLIGHT_JOB,
                *BOX_BUTTE_PART_PREFLIGHTS, *BOX_BUTTE_PART_PREFLIGHT_JOBS,
                BOX_BUTTE_PART1_JOB, BOX_BUTTE_LOW_MEMORY_PREFLIGHT,
                BOX_BUTTE_LOW_MEMORY_PREFLIGHT_JOB, BOX_BUTTE_LOW_MEMORY_JOB,
            )
        },
        "design_configs": {
            str(path.relative_to(ROOT)): sha256(path)
            for path in (*BOX_BUTTE_PART_CONFIGS, BOX_BUTTE_LOW_MEMORY_CONFIG)
        },
        "box_butte_split_gate": {
            "partition_plan_bytes": [item["plan"]["compressed_bytes"] for item in part_preflights],
            "execution_status": part1_job["status"],
            "execution_peak_rss_bytes": part1_job["sampled_peak_group_rss_bytes"],
            "expected_absent_outputs": [str(path.relative_to(ROOT)) for path in BOX_BUTTE_EXPECTED_ABSENT],
        },
        "box_butte_low_memory_gate": {
            "strategy": low_memory_config["resources"]["spatial_accumulator"],
            "preflight_bytes": low_memory_preflight["plan"]["compressed_bytes"],
            "execution_status": low_memory_job["status"],
            "execution_peak_rss_bytes": low_memory_job["sampled_peak_group_rss_bytes"],
            "expected_absent_outputs": [str(path.relative_to(ROOT)) for path in BOX_BUTTE_LOW_MEMORY_ABSENT],
        },
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
