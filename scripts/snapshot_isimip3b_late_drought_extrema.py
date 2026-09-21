#!/usr/bin/env python3
"""Freeze exact ISIMIP3b 2091--2100 tasmin/tasmax object identities."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "data/provenance/isimip3b_daily_catalog_selection.csv"
API = "https://data.isimip.org/api/v1/datasets/{dataset_id}/"
ESMS = ("gfdl-esm4", "ipsl-cm6a-lr", "mpi-esm1-2-hr", "mri-esm2-0", "ukesm1-0-ll")
SCENARIOS = ("ssp126", "ssp370", "ssp585")
VARIABLES = ("tasmin", "tasmax")
MEMBERS = {
    "gfdl-esm4": "r1i1p1f1", "ipsl-cm6a-lr": "r1i1p1f1",
    "mpi-esm1-2-hr": "r1i1p1f1", "mri-esm2-0": "r1i1p1f1",
    "ukesm1-0-ll": "r1i1p1f2",
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fetch_json(url: str) -> dict:
    request = Request(url, headers={"User-Agent": "GIVE-precipitation-research/1.0"})
    with urlopen(request, timeout=60) as response:
        payload = response.read()
    return json.loads(payload)


def validate_dataset(row: dict[str, str], dataset: dict) -> dict:
    esm, scenario, variable = row["forcing"], row["scenario"], row["variable"]
    expected_specifiers = {
        "region": "global", "product": "InputData", "category": "climate",
        "time_step": "daily", "subcategory": "atmosphere", "bias_adjustment": "w5e5",
        "climate_forcing": esm, "ensemble_member": MEMBERS[esm],
        "climate_scenario": scenario, "climate_variable": variable,
        "simulation_round": "ISIMIP3b",
    }
    if (dataset.get("id") != row["dataset_id"] or dataset.get("version") != "20210512"
            or dataset.get("public") is not True or dataset.get("restricted") is not False
            or dataset.get("rights", {}).get("short") != "CC0 1.0"
            or dataset.get("specifiers") != expected_specifiers):
        raise ValueError(f"dataset identity or access changed: {esm}/{scenario}/{variable}")
    expected_name = f"{esm}_{MEMBERS[esm]}_w5e5_{scenario}_{variable}_global_daily_2091_2100.nc"
    matches = [item for item in dataset.get("files", []) if item.get("name") == expected_name]
    if len(matches) != 1:
        raise ValueError(f"exact decade object missing or duplicated: {expected_name}")
    item = matches[0]
    checksum = item.get("checksum", "")
    if (item.get("version") != "20210512" or item.get("checksum_type") != "sha512"
            or len(checksum) != 128 or not all(c in "0123456789abcdef" for c in checksum)
            or not isinstance(item.get("size"), int) or item["size"] <= 0
            or not item.get("file_url", "").startswith("https://files.isimip.org/")):
        raise ValueError(f"file identity incomplete: {expected_name}")
    resources = dataset.get("resources", [])
    if not any(resource.get("doi") == "10.48364/ISIMIP.842396.1" for resource in resources):
        raise ValueError("source DOI changed")
    return {
        "esm": esm, "member": MEMBERS[esm], "scenario": scenario, "variable": variable,
        "dataset_id": dataset["id"], "dataset_url": dataset["url"],
        "dataset_version": dataset["version"], "file_id": item["id"],
        "file_name": item["name"], "file_url": item["file_url"],
        "bytes": item["size"], "sha512": checksum,
        "rights": dataset["rights"]["short"], "resource_doi": "10.48364/ISIMIP.842396.1",
    }


def build_snapshot(rows: list[dict[str, str]], fetch=fetch_json) -> dict:
    selected = [row for row in rows if row["forcing"] in ESMS
                and row["scenario"] in SCENARIOS and row["variable"] in VARIABLES]
    expected = {(esm, scenario, variable) for esm in ESMS for scenario in SCENARIOS for variable in VARIABLES}
    keys = {(row["forcing"], row["scenario"], row["variable"]) for row in selected}
    if len(selected) != len(expected) or keys != expected:
        raise ValueError("frozen catalog does not contain the exact 30-dataset extrema matrix")
    objects = [validate_dataset(row, fetch(API.format(dataset_id=row["dataset_id"])))
               for row in sorted(selected, key=lambda x: (x["forcing"], x["scenario"], x["variable"]))]
    return {
        "schema": "isimip3b_five_esm_late_drought_extrema_manifest_v1",
        "status": "source_metadata_frozen_not_downloaded_not_drought_response_damage_or_scc",
        "source_catalog": str(CATALOG.relative_to(ROOT)),
        "source_catalog_sha256": sha(CATALOG),
        "api": "https://data.isimip.org/api/v1/datasets/",
        "period": "2091-2100", "esms": list(ESMS), "scenarios": list(SCENARIOS),
        "variables": list(VARIABLES), "objects": objects,
        "object_count": len(objects), "total_bytes": sum(item["bytes"] for item in objects),
        "all_public_unrestricted_cc0": True,
        "raw_objects_downloaded_by_snapshot": False,
        "scientific_gates": {"drought_projection": False, "yield_response": False,
                             "damage": False, "scc": False},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("fresh output required")
    rows = list(csv.DictReader(CATALOG.open(newline="", encoding="utf-8")))
    output = build_snapshot(rows)
    output["implementation"] = {"path": str(Path(__file__).resolve().relative_to(ROOT)),
                                "sha256": sha(Path(__file__).resolve())}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": output["status"], "object_count": output["object_count"],
                      "total_bytes": output["total_bytes"]}))


if __name__ == "__main__":
    main()
