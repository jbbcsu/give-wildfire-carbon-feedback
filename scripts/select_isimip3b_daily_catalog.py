#!/usr/bin/env python3
"""Freeze and validate the complete ISIMIP3b daily climate training matrix.

The script consumes saved responses from the official dataset API.  It never
downloads climate fields.  A snapshot row pins each selected dataset identity,
version, size, member, rights, and year coverage; file-level checksums remain a
mandatory acquisition-time check.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path


SCENARIOS = ("historical", "ssp126", "ssp370", "ssp585")
VARIABLES = ("pr", "tas", "tasmin", "tasmax")
EXPECTED_MEMBERS = {
    "gfdl-esm4": "r1i1p1f1",
    "ipsl-cm6a-lr": "r1i1p1f1",
    "mpi-esm1-2-hr": "r1i1p1f1",
    "mri-esm2-0": "r1i1p1f1",
    "ukesm1-0-ll": "r1i1p1f2",
}
EXPECTED_YEARS = {
    "historical": (1850, 2014),
    "ssp126": (2015, 2100),
    "ssp370": (2015, 2100),
    "ssp585": (2015, 2100),
}
FIELDNAMES = (
    "forcing",
    "member",
    "scenario",
    "variable",
    "dataset_id",
    "dataset_name",
    "version",
    "size_bytes",
    "file_count",
    "first_year",
    "last_year",
    "rights",
    "public",
    "restricted",
    "resource_doi",
)
YEAR_BLOCK = re.compile(r"_(\d{4})_(\d{4})\.nc$")


def _year_blocks(files: list[dict], dataset_name: str) -> tuple[int, int]:
    blocks: list[tuple[int, int]] = []
    for item in files:
        match = YEAR_BLOCK.search(str(item.get("name", "")))
        if match is None:
            raise ValueError(f"{dataset_name}: file lacks a closed year block: {item.get('name')}")
        start, end = map(int, match.groups())
        if start > end:
            raise ValueError(f"{dataset_name}: reversed file year block {start}-{end}")
        if item.get("checksum_type") != "sha512" or len(str(item.get("checksum", ""))) != 128:
            raise ValueError(f"{dataset_name}: every file must expose an API SHA-512")
        if item.get("version") is None or item.get("size", 0) <= 0:
            raise ValueError(f"{dataset_name}: every file needs a version and positive size")
        if not str(item.get("file_url", "")).startswith("https://files.isimip.org/"):
            raise ValueError(f"{dataset_name}: unexpected file URL")
        blocks.append((start, end))
    blocks.sort()
    for previous, current in zip(blocks, blocks[1:]):
        if current[0] != previous[1] + 1:
            raise ValueError(f"{dataset_name}: noncontiguous file years {previous} then {current}")
    return blocks[0][0], blocks[-1][1]


def validate_payloads(payloads: dict[tuple[str, str], dict]) -> list[dict[str, str]]:
    expected_keys = {(scenario, variable) for scenario in SCENARIOS for variable in VARIABLES}
    if set(payloads) != expected_keys:
        missing = sorted(expected_keys - set(payloads))
        extra = sorted(set(payloads) - expected_keys)
        raise ValueError(f"API payload matrix differs; missing={missing}, extra={extra}")

    rows: list[dict[str, str]] = []
    seen_ids: set[str] = set()
    for scenario in SCENARIOS:
        for variable in VARIABLES:
            payload = payloads[(scenario, variable)]
            results = payload.get("results", [])
            if payload.get("count") != len(EXPECTED_MEMBERS) or len(results) != len(EXPECTED_MEMBERS):
                raise ValueError(f"{scenario}/{variable}: expected exactly five complete candidates")
            found: set[str] = set()
            for dataset in results:
                spec = dataset.get("specifiers", {})
                forcing = spec.get("climate_forcing")
                member = spec.get("ensemble_member")
                if forcing not in EXPECTED_MEMBERS or member != EXPECTED_MEMBERS[forcing]:
                    raise ValueError(f"{scenario}/{variable}: unexpected forcing/member {forcing}/{member}")
                if forcing in found:
                    raise ValueError(f"{scenario}/{variable}: duplicate forcing {forcing}")
                found.add(forcing)
                required = {
                    "simulation_round": "ISIMIP3b",
                    "product": "InputData",
                    "region": "global",
                    "time_step": "daily",
                    "climate_scenario": scenario,
                    "climate_variable": variable,
                    "bias_adjustment": "w5e5",
                }
                if any(spec.get(key) != value for key, value in required.items()):
                    raise ValueError(f"{scenario}/{variable}/{forcing}: specifier mismatch")
                dataset_id = str(dataset.get("id", ""))
                if not dataset_id or dataset_id in seen_ids:
                    raise ValueError(f"{scenario}/{variable}/{forcing}: missing or duplicate dataset id")
                seen_ids.add(dataset_id)
                if not dataset.get("public") or dataset.get("restricted"):
                    raise ValueError(f"{scenario}/{variable}/{forcing}: dataset is not public/unrestricted")
                rights = dataset.get("rights", {}).get("short")
                if rights != "CC0 1.0":
                    raise ValueError(f"{scenario}/{variable}/{forcing}: expected CC0 1.0, got {rights}")
                version = str(dataset.get("version", ""))
                files = dataset.get("files", [])
                if not files or any(str(item.get("version", "")) != version for item in files):
                    raise ValueError(f"{scenario}/{variable}/{forcing}: inconsistent file versions")
                size = int(dataset.get("size", 0))
                if size <= 0 or sum(int(item.get("size", 0)) for item in files) != size:
                    raise ValueError(f"{scenario}/{variable}/{forcing}: file sizes do not sum to dataset size")
                first_year, last_year = _year_blocks(files, str(dataset.get("name", "")))
                if (first_year, last_year) != EXPECTED_YEARS[scenario]:
                    raise ValueError(
                        f"{scenario}/{variable}/{forcing}: expected years {EXPECTED_YEARS[scenario]}, "
                        f"got {(first_year, last_year)}"
                    )
                resources = dataset.get("resources", [])
                doi = resources[0].get("doi", "") if resources else ""
                if not doi:
                    raise ValueError(f"{scenario}/{variable}/{forcing}: missing dataset resource DOI")
                rows.append(
                    {
                        "forcing": forcing,
                        "member": member,
                        "scenario": scenario,
                        "variable": variable,
                        "dataset_id": dataset_id,
                        "dataset_name": str(dataset.get("name", "")),
                        "version": version,
                        "size_bytes": str(size),
                        "file_count": str(len(files)),
                        "first_year": str(first_year),
                        "last_year": str(last_year),
                        "rights": rights,
                        "public": "true",
                        "restricted": "false",
                        "resource_doi": doi,
                    }
                )
            if found != set(EXPECTED_MEMBERS):
                raise ValueError(f"{scenario}/{variable}: incomplete forcing coverage")
    return sorted(rows, key=lambda row: (row["forcing"], row["scenario"], row["variable"]))


def read_payloads(root: Path) -> dict[tuple[str, str], dict]:
    payloads = {}
    for scenario in SCENARIOS:
        for variable in VARIABLES:
            path = root / f"{scenario}_{variable}.json"
            with path.open(encoding="utf-8") as handle:
                payloads[(scenario, variable)] = json.load(handle)
    return payloads


def write_snapshot(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def compare_snapshot(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open(newline="", encoding="utf-8") as handle:
        stored = list(csv.DictReader(handle))
    if stored != rows:
        raise ValueError(f"Committed selection snapshot differs from validated API payloads: {path}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("api_json_dir", type=Path)
    parser.add_argument("snapshot", type=Path)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    rows = validate_payloads(read_payloads(args.api_json_dir))
    if args.write:
        write_snapshot(args.snapshot, rows)
    else:
        compare_snapshot(args.snapshot, rows)
    total_bytes = sum(int(row["size_bytes"]) for row in rows)
    print(f"validated {len(rows)} datasets across 5 ESMs; catalogue bytes={total_bytes}")


if __name__ == "__main__":
    main()
