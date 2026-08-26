#!/usr/bin/env python3
"""Source-bound manifests for historical crop-stage scPDSI tables."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any


PARTITION_CONTRACT_ID = "crop_stage_scpdsi_partition_source_bound_v1"
COMBINED_CONTRACT_ID = "crop_stage_scpdsi_combined_source_bound_v1"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def manifest_path_for(table_path: Path) -> Path:
    return Path(f"{table_path}.manifest.json")


def require_sha256(value: object, label: str) -> str:
    text = str(value)
    if not SHA256_RE.fullmatch(text):
        raise ValueError(f"{label} must be a lowercase SHA-256 digest")
    return text


def read_manifest(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Manifest must be a JSON object: {path}")
    return value


def write_manifest(path: Path, manifest: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def same_path(recorded: object, actual: Path) -> bool:
    try:
        return Path(str(recorded)).resolve() == actual.resolve()
    except (OSError, RuntimeError, ValueError):
        return False


def validate_combined_manifest(
    manifest_path: Path,
    table_path: Path,
    *,
    scpdsi_path: Path,
    calendar_path: Path,
    expected_crop: str,
    expected_irrigation: str,
    expected_year_start: int,
    expected_year_end: int,
    expected_stages: int,
    expected_threshold: float,
) -> dict[str, Any]:
    """Validate a combined table against both current raw source objects."""
    manifest = read_manifest(manifest_path)
    if manifest.get("contract_id") != COMBINED_CONTRACT_ID:
        raise ValueError("Unexpected combined stage-scPDSI manifest contract")
    if not same_path(manifest.get("output_file"), table_path):
        raise ValueError("Combined stage-scPDSI manifest points to another output")
    if require_sha256(manifest.get("output_sha256"), "output_sha256") != sha256_file(table_path):
        raise ValueError("Combined stage-scPDSI output hash differs from its manifest")
    if not same_path(manifest.get("scpdsi_source_file"), scpdsi_path):
        raise ValueError("Combined manifest scPDSI path differs from the declared raw source")
    if not same_path(manifest.get("calendar_source_file"), calendar_path):
        raise ValueError("Combined manifest calendar path differs from the declared source")
    if require_sha256(manifest.get("scpdsi_source_sha256"), "scpdsi_source_sha256") != sha256_file(scpdsi_path):
        raise ValueError("Current raw scPDSI hash differs from the combined manifest")
    if require_sha256(manifest.get("calendar_source_sha256"), "calendar_source_sha256") != sha256_file(calendar_path):
        raise ValueError("Current crop-calendar hash differs from the combined manifest")
    expected = {
        "crop": expected_crop,
        "irrigation": expected_irrigation,
        "year_start": int(expected_year_start),
        "year_end": int(expected_year_end),
        "expected_stages": int(expected_stages),
    }
    for field, value in expected.items():
        if manifest.get(field) != value:
            raise ValueError(f"Combined stage-scPDSI manifest {field} differs from expectation")
    if abs(float(manifest.get("threshold")) - float(expected_threshold)) > 1e-12:
        raise ValueError("Combined stage-scPDSI manifest threshold differs from expectation")
    if manifest.get("partition_source_manifests_validated") is not True:
        raise ValueError("Combined manifest lacks the partition source-validation gate")
    if manifest.get("complete_latitude_partition_coverage") is not True:
        raise ValueError("Combined manifest lacks complete latitude-partition coverage")
    return manifest
