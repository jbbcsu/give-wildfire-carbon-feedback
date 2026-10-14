#!/usr/bin/env python3
"""Freeze the deterministic 15-case acquisition/reduction queue for 11 bridge cells."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXTREMA = ROOT / "data/provenance/isimip3b_five_esm_late_drought_extrema_20260921.json"
HISTORICAL_DIR = ROOT / "data/interim/us_county/us_spei_bridge_historical_cells_v2_20261013"
PAIR_ROOT = ROOT / "data/interim/five_esm_late_drought_20260921"
MODELS = ("gfdl-esm4", "ipsl-cm6a-lr", "mpi-esm1-2-hr", "mri-esm2-0", "ukesm1-0-ll")
SCENARIOS = ("ssp126", "ssp370", "ssp585")


def digest(path: Path, algorithm: str = "sha256") -> str:
    value = hashlib.new(algorithm)
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output if args.output.is_absolute() else ROOT / args.output
    require(not output.exists(), "fresh queue manifest required")
    extrema = json.loads(EXTREMA.read_text())
    require(extrema["object_count"] == 30 and extrema["all_public_unrestricted_cc0"], "extrema registry changed")
    historical_result_path = HISTORICAL_DIR / "result.json"
    historical_validation_path = HISTORICAL_DIR / "validation.json"
    historical_result = json.loads(historical_result_path.read_text())
    historical_validation = json.loads(historical_validation_path.read_text())
    require(historical_validation["status"] == "passed"
            and historical_validation["result"]["sha256"] == digest(historical_result_path),
            "historical 11-cell artifact is not independently validated")
    cases = []
    for case_number, (model, scenario) in enumerate(((m, s) for m in MODELS for s in SCENARIOS), start=1):
        slug = f"{model}_{scenario}"
        prior_result_path = PAIR_ROOT / slug / "result.json"
        prior_validation_path = PAIR_ROOT / slug / "validation.json"
        prior_result, prior_validation = json.loads(prior_result_path.read_text()), json.loads(prior_validation_path.read_text())
        require(prior_result["support_cells"] == 31208 and prior_validation["status"] == "passed"
                and prior_validation["pair_result_sha256"] == digest(prior_result_path), "prior case binding changed")
        retained = {item["variable"]: item for item in prior_result["sources"] if item["variable"] in {"pr", "tas"}}
        require(set(retained) == {"pr", "tas"}, "retained future source set changed")
        for item in retained.values():
            path = ROOT / item["path"]
            require(path.is_file() and path.stat().st_size == item["bytes"], "retained future source unavailable")
        needed = [item for item in extrema["objects"]
                  if item["esm"] == model and item["scenario"] == scenario]
        require(len(needed) == 2 and {item["variable"] for item in needed} == {"tasmin", "tasmax"},
                "future extrema pair changed")
        needed = sorted(needed, key=lambda item: item["variable"], reverse=True)
        case_root = f"data/interim/us_county/us_spei_bridge_future_11_cells_20261013/{slug}"
        acquire_commands = [
            f"./.venv/bin/python scripts/run_bounded_job.py --receipt data/interim/us_county/{slug}_{item['variable']}_bridge_acquire.resource.json --log data/interim/us_county/{slug}_{item['variable']}_bridge_acquire.log --max-mib 512 --min-free-gib 130 -- ./.venv/bin/python scripts/acquire_us_spei_bridge_future_extrema.py --esm {model} --scenario {scenario} --variable {item['variable']}"
            for item in needed
        ]
        cases.append({
            "case_number": case_number, "esm": model, "scenario": scenario, "slug": slug,
            "retained_sources": retained, "extrema": needed,
            "prior_case": {"result_path": str(prior_result_path.relative_to(ROOT)),
                           "result_sha256": digest(prior_result_path),
                           "validation_path": str(prior_validation_path.relative_to(ROOT)),
                           "validation_sha256": digest(prior_validation_path)},
            "commands": {
                "acquire_sequentially": acquire_commands,
                "reduce": f"./.venv/bin/python scripts/run_bounded_job.py --receipt {case_root}.resource.json --log {case_root}.log --max-mib 512 --min-free-gib 130 -- ./.venv/bin/python scripts/build_us_spei_bridge_future_case.py --esm {model} --scenario {scenario} --historical-dir data/interim/us_county/us_spei_bridge_historical_cells_v2_20261013 --output-dir {case_root}",
                "validate": f"./.venv/bin/python scripts/run_bounded_job.py --receipt {case_root}.validation.resource.json --log {case_root}.validation.log --max-mib 512 --min-free-gib 130 -- ./.venv/bin/python scripts/validate_us_spei_bridge_future_case.py --case-dir {case_root} --output {case_root}/validation.json",
                "evict_after_validation": f"./.venv/bin/python scripts/evict_validated_late_drought_extrema_pair.py --pair-dir {case_root} --validation {case_root}/validation.json --receipt data/provenance/{slug}_us_spei_bridge_extrema_eviction_20261013.json",
            },
            "output_dir": case_root,
        })
    manifest = {
        "schema": "us_spei_bridge_future_11_cell_queue_v1", "status": "ready_for_sequential_execution",
        "role": "climate_only_acquisition_and_reduction_plan_no_county_panel_or_outcome_fit",
        "order": "model_order_then_ssp126_ssp370_ssp585_one_case_at_a_time",
        "case_count": len(cases), "extrema_object_count": sum(len(case["extrema"]) for case in cases),
        "total_extrema_bytes": sum(item["bytes"] for case in cases for item in case["extrema"]),
        "historical_fit": {"result_path": str(historical_result_path.relative_to(ROOT)),
                           "result_sha256": digest(historical_result_path),
                           "validation_path": str(historical_validation_path.relative_to(ROOT)),
                           "validation_sha256": digest(historical_validation_path),
                           "cells": 11, "fits": 396},
        "extrema_registry": {"path": str(EXTREMA.relative_to(ROOT)), "sha256": digest(EXTREMA),
                             "rights": "CC0 1.0", "resource_doi": "10.48364/ISIMIP.842396.1"},
        "cases": cases,
        "execution_rules": {"maximum_resident_extrema_pairs": 1, "memory_limit_mib_per_job": 512,
                            "minimum_free_disk_gib": 130,
                            "evict_only_after_independent_validation": True,
                            "retain_precipitation_and_mean_temperature": True,
                            "stop_on_first_failure": True},
        "gates": {name: False for name in ("future_exact_361_county_support", "future_county_spei_panel",
                  "bridge_to_nass_response", "fit_outcomes", "future_yield_projection", "causal_claim", "damage", "scc")},
        "implementation": {"path": str(Path(__file__).resolve().relative_to(ROOT)),
                           "sha256": digest(Path(__file__).resolve())},
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": manifest["status"], "cases": len(cases),
                      "extrema_objects": manifest["extrema_object_count"],
                      "total_extrema_bytes": manifest["total_extrema_bytes"],
                      "first_command": cases[0]["commands"]["acquire_sequentially"][0]}))


if __name__ == "__main__":
    main()
