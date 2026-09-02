#!/usr/bin/env python3
"""Validate the official FAO FishStat global-capture workspace source gate."""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import tomllib
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path


SCHEMA = "fao_fishstat_global_capture_source_contract_v1"
ROLE = "official_observed_capture_source_gate_not_fishmip_calibration_welfare_damage_or_scc"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha512(path: Path) -> str:
    digest = hashlib.sha512()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate(contract_path: Path, root: Path) -> dict[str, object]:
    contract = tomllib.loads(contract_path.read_text(encoding="utf-8"))
    require(contract.get("schema") == SCHEMA and contract.get("role") == ROLE, "contract identity changed")
    source = contract.get("source", {})
    require(source.get("provider") == "Food and Agriculture Organization of the United Nations", "provider changed")
    require(source.get("workspace_version") == "2026.1.0", "workspace version changed")
    require(source.get("capture_dataset_title") == "FishStat: Global capture production 1950-2024", "capture title changed")
    require(source.get("license") == "CC-BY-4.0", "license changed")
    path = root / str(source["local_path"])
    require(path.is_file(), "registered FAO workspace is missing")
    require(path.stat().st_size == int(source["content_length_bytes"]), "workspace byte size changed")
    require(sha512(path) == source["sha512"], "workspace SHA-512 changed")

    content = contract.get("content", {})
    with zipfile.ZipFile(path) as archive:
        require(archive.testzip() is None, "workspace ZIP integrity failed")
        names = archive.namelist()
        require(len(names) == len(set(names)) == int(content["expected_archive_members"]), "workspace member inventory changed")
        require(content["workspace_xml"] in names and content["capture_notes"] in names, "required workspace metadata is missing")
        workspace_xml = archive.read(content["workspace_xml"])
        capture_notes = archive.read(content["capture_notes"]).decode("utf-8-sig")

    workspace = ET.fromstring(workspace_xml)
    require(workspace.attrib.get("acronym") == "FAO_FI_GLOBAL_PROD", "workspace acronym changed")
    require(workspace.attrib.get("version") == source["workspace_version"], "embedded workspace version changed")
    require(workspace.attrib.get("compatibility") == "4.4.0", "workspace compatibility changed")
    phrases = [
        "GLOBAL CAPTURE PRODUCTION", "annual series of capture production from 1950",
        "nominal landings", "exclude discards", "expressed in live weight",
        "flag of the fishing vessel", "3 900 commercial species items",
        "19 major marine fishing areas", "1950-2024", "CC-BY-4.0",
        '" L " = Missing value', '" Q " = Missing value; suppressed',
    ]
    normalized = html.unescape(capture_notes).replace("\u00a0", " ").replace("\u2011", "-")
    for phrase in phrases:
        require(phrase in normalized, f"embedded capture note changed: {phrase}")
    validation = contract.get("validation", {})
    for gate in ("archive_integrity_required", "workspace_identity_required", "embedded_capture_notes_required", "missing_suppressed_flags_preserved"):
        require(validation.get(gate) is True, f"required gate changed: {gate}")
    for gate in (
        "record_export_completed", "marine_only_filter_validated", "country_iso3_crosswalk_validated",
        "fao_area_crosswalk_validated", "fishmip_grid_or_eez_allocation_validated",
        "effort_or_management_identified", "welfare_translation_authorized", "damage_or_scc_authorized",
    ):
        require(validation.get(gate) is False, f"closed gate changed: {gate}")

    return {
        "schema": "fao_fishstat_global_capture_source_validation_v1",
        "status": "validated_official_workspace_container_and_capture_metadata_record_export_pending",
        "contract": {"path": contract_path.resolve().relative_to(root.resolve()).as_posix(), "sha256": sha256(contract_path)},
        "implementation": {"path": Path(__file__).resolve().relative_to(root.resolve()).as_posix(), "sha256": sha256(Path(__file__))},
        "source": {"url": source["url"], "workspace_version": source["workspace_version"], "bytes": path.stat().st_size, "sha512": source["sha512"], "license": source["license"]},
        "archive_member_count": len(names),
        "capture_series_years": [content["annual_start_year"], content["annual_end_year"]],
        "observed_measure": "nominal_landings_live_weight_not_discard_adjusted_catch",
        "missing_and_suppressed_status_semantics_present": True,
        "record_export_completed": False,
        "marine_only_filter_validated": False,
        "country_or_eez_allocation_validated": False,
        "fishmip_observed_calibration_authorized": False,
        "welfare_translation_authorized": False,
        "damage_or_scc_authorized": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = validate(args.contract.resolve(), args.root.resolve())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("FAO FishStat global-capture source gate passed")


if __name__ == "__main__":
    main()
