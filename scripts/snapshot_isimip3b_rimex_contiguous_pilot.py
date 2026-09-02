#!/usr/bin/env python3
"""Pin the outcome-blind contiguous ISIMIP3b RIME-X pilot from the official API."""
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
SCHEMA = "isimip3b_rimex_contiguous_pilot_contract_v1"
ROLE = "outcome_blind_contiguous_daily_support_pilot_not_feature_response_damage_or_scc_input"
PERIOD_RE = re.compile(r"_(\d{4})_(\d{4})\.nc$")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(url: str) -> dict:
    request = urllib.request.Request(url, headers={"User-Agent": "GIVE-ISIMIP-contiguous-metadata-audit/1"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def validate_contract(contract: dict) -> None:
    require(contract.get("schema") == SCHEMA and contract.get("role") == ROLE, "contract identity changed")
    require(contract.get("primary_climate_route") == "direct_isimip3b_daily_feature_response", "primary route changed")
    require(contract.get("fallback_climate_route") == "mesmer_m_tp_plus_published_daily_generator", "fallback route changed")
    source = contract.get("source", {})
    require(source.get("dataset_version") == "20210512", "dataset version changed")
    require(source.get("resource_doi") == "10.48364/ISIMIP.842396.1", "resource DOI changed")
    require(source.get("rights") == "CC0 1.0", "rights changed")
    selection = contract.get("selection", {})
    require(selection.get("esm_id") == "gfdl-esm4", "pilot ESM changed")
    require(selection.get("member_id") == "r1i1p1f1", "pilot member changed")
    require(selection.get("scenario") == "ssp126", "pilot scenario changed")
    require(selection.get("variables") == ["pr", "tas"], "pilot variables changed")
    require(selection.get("file_periods") == ["2031_2040", "2041_2050", "2051_2060"], "pilot periods changed")
    require(selection.get("daily_support_end_year") - selection.get("daily_support_start_year") + 1 == 30, "daily support is not 30 years")
    require(selection.get("crop_feature_end_year") - selection.get("crop_feature_start_year") + 1 == 28, "crop-feature support is not 28 years")
    require(selection.get("running_mean_years") == 21, "published running mean changed")
    require(selection.get("smoothed_feature_start_year") == 2042 and selection.get("smoothed_feature_end_year") == 2049, "smoothed output years changed")
    design = contract.get("design", {})
    require(design.get("expected_dataset_count") == 2 and design.get("expected_file_count") == 6, "expected matrix changed")
    require(design.get("expected_smoothed_feature_years") == 8, "expected smoothed-year count changed")
    require(design.get("whole_esm_or_scenario_promotion_allowed_from_pilot") is False, "pilot promotion gate opened")
    limitations = contract.get("limitations", {})
    for gate in (
        "metadata_pinned", "all_six_files_acquired", "all_six_files_content_validated",
        "contiguous_features_built", "joint_dependence_preserved", "real_rimex_fit_authorized",
        "fair_feature_response_authorized", "production_emulator_authorized", "damage_or_scc_authorized",
    ):
        require(limitations.get(gate) is False, f"closed gate changed: {gate}")
    datasets = contract.get("datasets", [])
    require([(item.get("variable"), item.get("dataset_id")) for item in datasets] == [
        ("pr", "24cb1007-3c96-4b59-a0dc-42d94a8cff8c"),
        ("tas", "f741da2d-9d21-4c86-be9b-484396303e33"),
    ], "pinned dataset identities changed")


def build_snapshot(contract: dict, fetch_json: Callable[[str], dict] = load_json) -> tuple[list[dict], dict]:
    validate_contract(contract)
    source = contract["source"]
    selection = contract["selection"]
    periods = selection["file_periods"]
    rows: list[dict] = []
    api = source["catalogue_api"].rstrip("/")
    for selected in contract["datasets"]:
        dataset = fetch_json(f"{api}/{selected['dataset_id']}/")
        require(dataset.get("id") == selected["dataset_id"], "dataset ID changed")
        require(dataset.get("version") == source["dataset_version"], "dataset version changed")
        require(dataset.get("public") is True and dataset.get("restricted") is False, "dataset is not public and unrestricted")
        require(dataset.get("rights", {}).get("short") == source["rights"], "dataset rights changed")
        resource_dois = {resource.get("doi") for resource in dataset.get("resources", [])}
        require(source["resource_doi"] in resource_dois, "dataset resource DOI changed")
        spec = dataset.get("specifiers", {})
        expected_spec = {
            "simulation_round": "ISIMIP3b", "product": "InputData", "region": "global",
            "time_step": "daily", "climate_forcing": selection["esm_id"],
            "ensemble_member": selection["member_id"], "climate_scenario": selection["scenario"],
            "climate_variable": selected["variable"],
        }
        require(all(spec.get(key) == value for key, value in expected_spec.items()), "dataset specifiers changed")
        files_by_period: dict[str, dict] = {}
        for file_info in dataset.get("files", []):
            match = PERIOD_RE.search(str(file_info.get("name", "")))
            if match:
                period = f"{match.group(1)}_{match.group(2)}"
                require(period not in files_by_period, f"duplicate file period: {period}")
                files_by_period[period] = file_info
        for period in periods:
            require(period in files_by_period, f"missing file period: {selected['variable']}/{period}")
            file_info = files_by_period[period]
            checksum = str(file_info.get("checksum", ""))
            require(file_info.get("version") == source["dataset_version"], "file version changed")
            require(file_info.get("checksum_type") == "sha512" and len(checksum) == 128, "file checksum changed")
            require(int(file_info.get("size", 0)) > 0, "file byte size is invalid")
            require(str(file_info.get("file_url", "")).startswith("https://files.isimip.org/"), "file URL host changed")
            start_year, end_year = map(int, period.split("_"))
            rows.append({
                "esm_id": selection["esm_id"], "member_id": selection["member_id"],
                "scenario": selection["scenario"], "variable": selected["variable"],
                "start_year": start_year, "end_year": end_year, "dataset_id": dataset["id"],
                "file_id": file_info["id"], "file_name": file_info["name"],
                "version": file_info["version"], "size_bytes": int(file_info["size"]),
                "sha512": checksum, "file_url": file_info["file_url"], "rights": dataset["rights"]["short"],
                "public": str(dataset["public"]).lower(), "restricted": str(dataset["restricted"]).lower(),
            })
    require(len(rows) == 6 and len({row["file_id"] for row in rows}) == 6, "pilot file matrix is incomplete")
    audit = {
        "schema": "isimip3b_rimex_contiguous_pilot_metadata_audit_v1",
        "role": contract["role"],
        "registered_utc_date": contract["registered_utc_date"],
        "status": "passed_exact_metadata_selection_not_new_content_or_feature_validation",
        "dataset_count": len({row["dataset_id"] for row in rows}),
        "file_count": len(rows),
        "total_bytes": sum(row["size_bytes"] for row in rows),
        "periods": periods,
        "daily_support_years": 30,
        "crop_feature_years": 28,
        "centered_21_year_output_years": list(range(2042, 2050)),
        "all_public_unrestricted_cc0": all(row["public"] == "true" and row["restricted"] == "false" and row["rights"] == "CC0 1.0" for row in rows),
        "new_files_acquired": False,
        "new_files_content_validated": False,
        "contiguous_features_built": False,
        "joint_dependence_preserved": False,
        "real_rimex_fit_authorized": False,
        "fair_feature_response_authorized": False,
        "damage_or_scc_authorized": False,
    }
    return rows, audit


def write_outputs(rows: list[dict], audit: dict, csv_path: Path, audit_path: Path, contract_path: Path) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    result = dict(audit)
    result["contract"] = {"path": contract_path.relative_to(ROOT).as_posix(), "sha256": sha256(contract_path)}
    result["implementation"] = {"path": Path(__file__).relative_to(ROOT).as_posix(), "sha256": sha256(Path(__file__))}
    result["plan"] = {"path": csv_path.relative_to(ROOT).as_posix(), "sha256": sha256(csv_path)}
    audit_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--audit", type=Path, required=True)
    args = parser.parse_args()
    contract_path = args.contract.resolve()
    contract = tomllib.loads(contract_path.read_text(encoding="utf-8"))
    rows, audit = build_snapshot(contract)
    write_outputs(rows, audit, args.output.resolve(), args.audit.resolve(), contract_path)
    print(f"Pinned {len(rows)} contiguous-pilot files ({audit['total_bytes']} bytes); metadata gate passed")


if __name__ == "__main__":
    main()
