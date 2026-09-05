#!/usr/bin/env python3
from __future__ import annotations

import copy
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from snapshot_isimip3b_rimex_catalogue_track_feasibility import evaluate, query_urls
import tomllib


root = Path(__file__).resolve().parents[1]
config_path = root / "config/isimip3b_rimex_catalogue_track_feasibility_v1.toml"
preregistration_path = root / "data/provenance/isimip3b_rimex_catalogue_track_feasibility_preregistration_20260905.json"
config = tomllib.loads(config_path.read_text(encoding="utf-8"))


def dataset(esm: str, member: str, scenario: str, variable: str, index: int) -> dict:
    files = []
    blocks = [(2015, 2020)] + [(year, year + 9) for year in range(2021, 2100, 10)]
    for block_index, (start, end) in enumerate(blocks):
        files.append({
            "id": f"file-{index}-{scenario}-{variable}-{block_index}",
            "name": f"{esm}_{member}_w5e5_{scenario}_{variable}_global_daily_{start}_{end}.nc",
            "version": "20210512", "size": 100 + block_index,
            "checksum_type": "sha512", "checksum": f"{index + block_index:0128x}"[-128:],
            "file_url": f"https://files.isimip.org/{esm}/{scenario}/{variable}/{start}_{end}.nc",
        })
    return {
        "id": f"dataset-{index}-{scenario}-{variable}",
        "name": f"{esm}_{member}_w5e5_{scenario}_{variable}_global_daily",
        "version": "20210512", "size": sum(item["size"] for item in files),
        "public": True, "restricted": False, "rights": {"short": "CC0 1.0"},
        "resources": [{"doi": "10.48364/ISIMIP.842396.1"}], "files": files,
        "specifiers": {
            "simulation_round": "ISIMIP3b", "product": "InputData", "region": "global",
            "time_step": "daily", "bias_adjustment": "w5e5", "climate_forcing": esm,
            "ensemble_member": member, "climate_scenario": scenario, "climate_variable": variable,
        },
    }


tracks = [(f"esm-{index}", "r1i1p1f1") for index in range(1, 6)]
payloads = {}
for scenario in config["screen"]["scenarios"]:
    for variable in config["screen"]["variables"]:
        results = [dataset(esm, member, scenario, variable, index) for index, (esm, member) in enumerate(tracks, 1)]
        payloads[(scenario, variable)] = {"count": len(results), "next": None, "results": results}


def fetch(url: str) -> dict:
    query = parse_qs(urlparse(url).query)
    assert "climate_forcing" not in query
    assert "ensemble_member" not in query
    return copy.deepcopy(payloads[(query["climate_scenario"][0], query["climate_variable"][0])])


urls = query_urls(config)
assert len(urls) == 6
rows, audit = evaluate(config_path, preregistration_path, root, fetch)
assert audit["status"] == "catalogue_track_gate_failed_insufficient_complete_tracks"
assert audit["eligible_complete_track_count"] == 5
assert audit["eligible_esm_family_count"] == 5
assert audit["balanced_dataset_count"] == 30
assert audit["unique_required_source_file_count"] == 270
assert audit["climate_payload_bytes_downloaded"] == 0
assert audit["final_ensemble_selected"] is False
assert len(rows) == 270

expanded_payloads = copy.deepcopy(payloads)
for scenario in config["screen"]["scenarios"]:
    for variable in config["screen"]["variables"]:
        extra = [dataset(f"esm-{index}", "r1i1p1f1", scenario, variable, index) for index in (6, 7)]
        expanded_payloads[(scenario, variable)]["results"].extend(extra)
        expanded_payloads[(scenario, variable)]["count"] = 7


def fetch_expanded(url: str) -> dict:
    query = parse_qs(urlparse(url).query)
    return copy.deepcopy(expanded_payloads[(query["climate_scenario"][0], query["climate_variable"][0])])


expanded_rows, expanded_audit = evaluate(config_path, preregistration_path, root, fetch_expanded)
assert expanded_audit["status"] == "metadata_feasible_only_no_ensemble_selected"
assert expanded_audit["eligible_complete_track_count"] == 7
assert expanded_audit["eligible_track_capacity_after_two_member_family_cap"] == 7
assert expanded_audit["final_ensemble_selected"] is False
assert len(expanded_rows) == 378

tampered = copy.deepcopy(payloads)
tampered[("ssp585", "tas")]["results"][0]["rights"]["short"] = "unknown"


def fetch_tampered(url: str) -> dict:
    query = parse_qs(urlparse(url).query)
    return copy.deepcopy(tampered[(query["climate_scenario"][0], query["climate_variable"][0])])


try:
    evaluate(config_path, preregistration_path, root, fetch_tampered)
except ValueError as error:
    assert "rights changed" in str(error)
else:
    raise AssertionError("changed rights passed")

print("ISIMIP3b catalogue track-feasibility snapshot tests passed")
