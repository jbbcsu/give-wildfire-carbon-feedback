#!/usr/bin/env python3
"""Pin the complete contiguous RIME-X ESM × scenario file matrix from ISIMIP."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import re
import tomllib
import urllib.request
from typing import Callable


PERIOD_RE = re.compile(r"_(\d{4})_(\d{4})\.nc$")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def fetch_json(url: str) -> dict:
    request = urllib.request.Request(url, headers={"User-Agent": "GIVE-RIMEX-contiguous-matrix/1"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


def load_contract(path: Path, root: Path) -> tuple[dict, list[dict[str, str]]]:
    config = tomllib.loads(path.read_text(encoding="utf-8"))
    require(config.get("schema") == "isimip3b_rimex_contiguous_holdout_matrix_contract_v1", "schema changed")
    require(config.get("primary_climate_route") == "direct_isimip3b_daily_feature_response", "primary route changed")
    require(config.get("fallback_climate_route") == "mesmer_m_tp_plus_published_daily_generator", "fallback route changed")
    source = config.get("source", {})
    catalog = root / str(source["catalog_snapshot"])
    require(sha256(catalog) == source.get("catalog_snapshot_sha256"), "catalog snapshot changed")
    selection = config.get("selection", {})
    require(selection.get("esms") == ["gfdl-esm4", "ipsl-cm6a-lr", "mpi-esm1-2-hr", "mri-esm2-0", "ukesm1-0-ll"], "ESM matrix changed")
    require(selection.get("scenarios") == ["ssp126", "ssp370", "ssp585"], "scenario matrix changed")
    require(selection.get("variables") == ["pr", "tas"] and selection.get("file_periods") == ["2031_2040", "2041_2050", "2051_2060"], "variable/period matrix changed")
    require((selection.get("feature_year_start"), selection.get("feature_year_end"), selection.get("centered_window_years"), selection.get("center_year_start"), selection.get("center_year_end")) == (2032, 2059, 21, 2042, 2049), "feature support changed")
    design = config.get("design", {})
    require((design.get("expected_datasets"), design.get("expected_files"), design.get("expected_complete_templates")) == (30, 90, 120), "matrix counts changed")
    require(design.get("minimum_joint_templates") == 51 and design.get("whole_esm_holdout_templates") == 96 and design.get("whole_scenario_holdout_templates") == 80, "holdout template counts changed")
    require(design.get("all_12_crop_regime_cells_required_per_template") is True and design.get("held_out_templates_excluded_from_training") is True, "template integrity gate changed")
    for gate in ("metadata_matrix_pinned", "all_files_acquired", "all_files_content_validated", "all_features_built", "joint_dependence_validated", "whole_esm_holdouts_passed", "whole_scenario_holdouts_passed", "fair_feature_response_authorized", "damage_or_scc_authorized"):
        require(config.get("limitations", {}).get(gate) is False, f"closed gate changed: {gate}")
    with catalog.open(newline="", encoding="utf-8") as stream:
        rows = [row for row in csv.DictReader(stream) if row["forcing"] in selection["esms"] and row["scenario"] in selection["scenarios"] and row["variable"] in selection["variables"]]
    require(len(rows) == 30, "catalog does not contain the exact selected dataset matrix")
    require(len({(row["forcing"], row["scenario"], row["variable"]) for row in rows}) == 30, "catalog matrix has duplicate cells")
    for row in rows:
        require(row["version"] == source["dataset_version"] and row["rights"] == source["rights"], "catalog version/rights changed")
        require(row["public"] == "true" and row["restricted"] == "false" and row["resource_doi"] == source["resource_doi"], "catalog access/resource gate changed")
    return config, sorted(rows, key=lambda row: (row["forcing"], row["scenario"], row["variable"]))


def build(config: dict, datasets: list[dict[str, str]], fetch: Callable[[str], dict] = fetch_json) -> tuple[list[dict], dict]:
    source, selection = config["source"], config["selection"]
    output = []
    for selected in datasets:
        dataset = fetch(f"{source['catalogue_api'].rstrip('/')}/{selected['dataset_id']}/")
        require(dataset.get("id") == selected["dataset_id"] and dataset.get("version") == source["dataset_version"], "dataset identity/version changed")
        spec = dataset.get("specifiers", {})
        expected = {"simulation_round": "ISIMIP3b", "product": "InputData", "region": "global", "time_step": "daily", "climate_forcing": selected["forcing"], "ensemble_member": selected["member"], "climate_scenario": selected["scenario"], "climate_variable": selected["variable"]}
        require(all(spec.get(key) == value for key, value in expected.items()), "dataset specifiers changed")
        require(dataset.get("public") is True and dataset.get("restricted") is False and dataset.get("rights", {}).get("short") == source["rights"], "dataset access changed")
        require(source["resource_doi"] in {resource.get("doi") for resource in dataset.get("resources", [])}, "resource DOI changed")
        files = {}
        for item in dataset.get("files", []):
            match = PERIOD_RE.search(str(item.get("name", "")))
            if match:
                files[f"{match.group(1)}_{match.group(2)}"] = item
        for period in selection["file_periods"]:
            require(period in files, f"selected period missing: {selected['forcing']}/{selected['scenario']}/{selected['variable']}/{period}")
            item = files[period]
            checksum = str(item.get("checksum", ""))
            require(item.get("version") == source["dataset_version"] and item.get("checksum_type") == "sha512" and len(checksum) == 128, "file version/checksum changed")
            require(int(item.get("size", 0)) > 0 and str(item.get("file_url", "")).startswith("https://files.isimip.org/"), "file size/URL changed")
            start, end = map(int, period.split("_"))
            output.append({
                "esm_id": selected["forcing"], "member_id": selected["member"], "scenario": selected["scenario"], "variable": selected["variable"],
                "start_year": start, "end_year": end, "dataset_id": selected["dataset_id"], "file_id": item["id"], "file_name": item["name"],
                "version": item["version"], "size_bytes": int(item["size"]), "sha512": checksum, "file_url": item["file_url"],
                "rights": source["rights"], "public": "true", "restricted": "false",
            })
    require(len(output) == 90 and len({row["file_id"] for row in output}) == 90, "file matrix is incomplete")
    audit = {
        "schema": "isimip3b_rimex_contiguous_holdout_matrix_metadata_audit_v1",
        "status": "passed_exact_metadata_matrix_not_content_feature_or_holdout_validation",
        "dataset_count": 30, "file_count": 90, "total_bytes": sum(row["size_bytes"] for row in output),
        "complete_templates_if_all_content_passes": 120,
        "training_templates_after_whole_esm_holdout": 96,
        "training_templates_after_whole_scenario_holdout": 80,
        "minimum_joint_templates": 51,
        "all_public_unrestricted_cc0": True,
        "new_files_acquired": False, "all_files_content_validated": False, "all_features_built": False,
        "whole_esm_holdouts_passed": False, "whole_scenario_holdouts_passed": False,
        "fair_feature_response_authorized": False, "damage_or_scc_authorized": False,
    }
    return output, audit


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--audit", type=Path, required=True)
    args = parser.parse_args()
    root, contract_path = args.root.resolve(), args.contract.resolve()
    config, datasets = load_contract(contract_path, root)
    rows, audit = build(config, datasets)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n"); writer.writeheader(); writer.writerows(rows)
    audit["contract"] = {"path": contract_path.relative_to(root).as_posix(), "sha256": sha256(contract_path)}
    audit["implementation"] = {"path": Path(__file__).resolve().relative_to(root).as_posix(), "sha256": sha256(Path(__file__))}
    audit["plan"] = {"path": args.output.resolve().relative_to(root).as_posix(), "sha256": sha256(args.output.resolve())}
    args.audit.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"pinned {len(rows)} contiguous holdout-matrix files; metadata gate passed")


if __name__ == "__main__":
    main()
