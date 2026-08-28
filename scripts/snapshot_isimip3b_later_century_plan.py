#!/usr/bin/env python3
"""Pin the predeclared later-century ISIMIP3b file matrix from the official API."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import tomllib
import urllib.request
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
CONFIG_SCHEMA = "isimip3b_later_century_expansion_config_v1"
CONFIG_ROLE = "outcome_blind_metadata_pinned_later_century_daily_feature_support_expansion_not_acquired_not_emulator_damage_or_scc_input"
PERIOD_RE = re.compile(r"_(\d{4})_(\d{4})\.nc$")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(url: str) -> dict:
    request = urllib.request.Request(url, headers={"User-Agent": "GIVE-ISIMIP-metadata-audit/1"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


def validate_config(config: dict, config_path: Path) -> tuple[list[dict], list[str]]:
    if config.get("schema") != CONFIG_SCHEMA or config.get("role") != CONFIG_ROLE:
        raise ValueError("later-century config identity changed")
    source = config["source"]
    snapshot = ROOT / source["selection_snapshot"]
    if sha256(snapshot) != source["selection_snapshot_sha256"]:
        raise ValueError("frozen ISIMIP3b dataset selection snapshot hash changed")
    selection = config["selection"]
    esms = selection["esm_ids"]
    members = selection["member_ids"]
    if len(esms) != len(members) or len(esms) != len(set(esms)):
        raise ValueError("ESM/member registration must be one-to-one")
    periods = selection["file_periods"]
    if periods != ["2041_2050", "2091_2100"]:
        raise ValueError("registered later-century periods changed")
    rows = list(csv.DictReader(snapshot.open(newline="", encoding="utf-8")))
    wanted = []
    for esm, member in zip(esms, members, strict=True):
        for scenario in selection["scenarios"]:
            for variable in selection["variables"]:
                matches = [
                    row for row in rows
                    if row["forcing"] == esm and row["member"] == member
                    and row["scenario"] == scenario and row["variable"] == variable
                ]
                if len(matches) != 1:
                    raise ValueError(f"expected one frozen dataset for {esm}/{member}/{scenario}/{variable}")
                wanted.append(matches[0])
    expected = int(config["design"]["expected_dataset_count"])
    if len(wanted) != expected:
        raise ValueError(f"expected {expected} datasets, found {len(wanted)}")
    return wanted, periods


def build_snapshot(config: dict, fetch_json: Callable[[str], dict] = load_json) -> tuple[list[dict], dict]:
    datasets, periods = validate_config(config, ROOT / "config/isimip3b_later_century_expansion_v1.toml")
    output = []
    api = config["source"]["catalogue_api"].rstrip("/")
    for selected in datasets:
        dataset = fetch_json(f"{api}/{selected['dataset_id']}/")
        spec = dataset.get("specifiers", {})
        expected_spec = {
            "simulation_round": "ISIMIP3b",
            "product": "InputData",
            "region": "global",
            "time_step": "daily",
            "climate_forcing": selected["forcing"],
            "ensemble_member": selected["member"],
            "climate_scenario": selected["scenario"],
            "climate_variable": selected["variable"],
        }
        if dataset.get("id") != selected["dataset_id"] or dataset.get("version") != config["source"]["dataset_version"]:
            raise ValueError(f"dataset identity/version mismatch for {selected['dataset_id']}")
        if any(spec.get(key) != value for key, value in expected_spec.items()):
            raise ValueError(f"dataset specifier mismatch for {selected['dataset_id']}")
        if dataset.get("public") is not True or dataset.get("restricted") is not False:
            raise ValueError(f"dataset is not public and unrestricted: {selected['dataset_id']}")
        if dataset.get("rights", {}).get("short") != config["source"]["rights"]:
            raise ValueError(f"rights mismatch for {selected['dataset_id']}")
        files_by_period = {}
        for file_info in dataset.get("files", []):
            match = PERIOD_RE.search(str(file_info.get("name", "")))
            if match:
                period = f"{match.group(1)}_{match.group(2)}"
                if period in files_by_period:
                    raise ValueError(f"duplicate {period} file for {selected['dataset_id']}")
                files_by_period[period] = file_info
        for period in periods:
            if period not in files_by_period:
                raise ValueError(f"missing {period} file for {selected['dataset_id']}")
            file_info = files_by_period[period]
            checksum = str(file_info.get("checksum", ""))
            if file_info.get("version") != config["source"]["dataset_version"] or file_info.get("checksum_type") != "sha512" or len(checksum) != 128:
                raise ValueError(f"file version/checksum mismatch for {file_info.get('id')}")
            start_year, end_year = map(int, period.split("_"))
            output.append({
                "esm_id": selected["forcing"],
                "member_id": selected["member"],
                "scenario": selected["scenario"],
                "variable": selected["variable"],
                "start_year": start_year,
                "end_year": end_year,
                "dataset_id": dataset["id"],
                "file_id": file_info["id"],
                "file_name": file_info["name"],
                "version": file_info["version"],
                "size_bytes": int(file_info["size"]),
                "sha512": checksum,
                "file_url": file_info["file_url"],
                "rights": dataset["rights"]["short"],
                "public": str(dataset["public"]).lower(),
                "restricted": str(dataset["restricted"]).lower(),
            })
    expected_files = int(config["design"]["expected_file_count"])
    if len(output) != expected_files or len({row["file_id"] for row in output}) != expected_files:
        raise ValueError(f"expected {expected_files} unique files, found {len(output)}")
    audit = {
        "schema": "isimip3b_later_century_metadata_audit_v1",
        "role": config["role"],
        "registered_utc_date": config["registered_utc_date"],
        "result": "passed_metadata_selection_not_acquired",
        "dataset_count": len({row["dataset_id"] for row in output}),
        "file_count": len(output),
        "total_bytes": sum(row["size_bytes"] for row in output),
        "esm_count": len({row["esm_id"] for row in output}),
        "scenario_count": len({row["scenario"] for row in output}),
        "variables": sorted({row["variable"] for row in output}),
        "periods": periods,
        "all_public_unrestricted_cc0": all(row["public"] == "true" and row["restricted"] == "false" and row["rights"] == "CC0 1.0" for row in output),
        "acquired": False,
        "content_validated": False,
        "feature_response_fitted": False,
        "damage_or_scc_authorized": False,
    }
    return output, audit


def write_outputs(rows: list[dict], audit: dict, csv_path: Path, audit_path: Path) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0])
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    audit = dict(audit)
    audit["csv_path"] = str(csv_path.relative_to(ROOT))
    audit["csv_sha256"] = sha256(csv_path)
    audit_path.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/isimip3b_later_century_expansion_v1.toml")
    parser.add_argument("--output", default="data/provenance/isimip3b_later_century_plan.csv")
    parser.add_argument("--audit", default="data/provenance/isimip3b_later_century_plan_20260827.json")
    args = parser.parse_args()
    config = tomllib.loads((ROOT / args.config).read_text(encoding="utf-8"))
    rows, audit = build_snapshot(config)
    config_path = ROOT / args.config
    audit["config"] = {"path": args.config, "sha256": sha256(config_path)}
    audit["implementation"] = {
        "path": str(Path(__file__).resolve().relative_to(ROOT)),
        "sha256": sha256(Path(__file__).resolve()),
    }
    write_outputs(rows, audit, ROOT / args.output, ROOT / args.audit)
    print(f"Pinned {audit['file_count']} later-century files ({audit['total_bytes']} bytes); metadata gate passed")


if __name__ == "__main__":
    main()
