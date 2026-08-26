#!/usr/bin/env python3
"""Validate the bounded ISIMIP3b metadata/header smoke against provenance."""
from __future__ import annotations

import argparse
import csv
import json
import tomllib
from pathlib import Path


def validate(provenance_path: Path, selection_path: Path, sidecar_path: Path, header_path: Path) -> None:
    with provenance_path.open("rb") as handle:
        provenance = tomllib.load(handle)
    smoke = provenance["engineering_smoke"]
    if smoke.get("role") != "metadata_and_range_content_only_not_projection_acquisition":
        raise ValueError("Smoke role must prohibit a projection-acquisition claim")
    if smoke.get("result") != "passed" or not smoke.get("limitation"):
        raise ValueError("Smoke record must retain its passed result and explicit limitation")

    with sidecar_path.open(encoding="utf-8") as handle:
        sidecar = json.load(handle)
    expected_sidecar = {
        "path": smoke["file_path"],
        "size": smoke["file_size_bytes"],
        "checksum": smoke["file_checksum_sha512"],
        "checksum_type": "sha512",
    }
    for key, expected in expected_sidecar.items():
        if sidecar.get(key) != expected:
            raise ValueError(f"Sidecar {key} mismatch: expected {expected}, got {sidecar.get(key)}")
    spec = sidecar.get("specifiers", {})
    expected_spec = {
        "simulation_round": "ISIMIP3b",
        "product": "InputData",
        "region": "global",
        "time_step": "daily",
        "climate_scenario": "ssp370",
        "climate_forcing": "mri-esm2-0",
        "ensemble_member": "r1i1p1f1",
        "bias_adjustment": "w5e5",
        "climate_variable": "pr",
        "start_year": smoke["start_year"],
        "end_year": smoke["end_year"],
    }
    if any(spec.get(key) != value for key, value in expected_spec.items()):
        raise ValueError("Sidecar specifiers differ from the registered smoke file")

    header = header_path.read_bytes()
    expected_length = smoke["range_end"] - smoke["range_start"] + 1
    if len(header) != expected_length or len(header) != smoke["range_bytes_received"]:
        raise ValueError(f"Header byte count mismatch: expected {expected_length}, got {len(header)}")
    magic = bytes.fromhex(smoke["range_magic_hex"])
    if not header.startswith(magic):
        raise ValueError("Header does not have the registered HDF5 signature")
    if smoke["http_content_length"] != smoke["file_size_bytes"] or smoke["http_accept_ranges"] != "bytes":
        raise ValueError("HTTP metadata does not support the registered bounded range smoke")

    with selection_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    matches = [row for row in rows if row["dataset_id"] == smoke["source_dataset_id"]]
    if len(matches) != 1:
        raise ValueError("Smoke dataset must occur exactly once in the frozen selection")
    row = matches[0]
    expected_row = {
        "forcing": "mri-esm2-0",
        "member": "r1i1p1f1",
        "scenario": "ssp370",
        "variable": "pr",
        "dataset_name": smoke["source_dataset_name"],
        "version": smoke["source_dataset_version"],
        "rights": smoke["file_rights"],
    }
    if any(row.get(key) != str(value) for key, value in expected_row.items()):
        raise ValueError("Smoke dataset does not match its frozen selection row")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("provenance", type=Path)
    parser.add_argument("selection", type=Path)
    parser.add_argument("sidecar", type=Path)
    parser.add_argument("header", type=Path)
    args = parser.parse_args()
    validate(args.provenance, args.selection, args.sidecar, args.header)
    print("ISIMIP3b bounded engineering smoke metadata/header validation passed")


if __name__ == "__main__":
    main()
