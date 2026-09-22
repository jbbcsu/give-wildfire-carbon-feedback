#!/usr/bin/env python3
"""Independently summarize and validate the complete weekly USDM vector archive."""
from __future__ import annotations

import argparse
import hashlib
import json
import tomllib
from datetime import date, timedelta
from pathlib import Path

from download_usdm_weekly_shapefiles import manifest_identities, validate_archive


def configured_dates(contract: dict[str, object]) -> list[date]:
    current = date.fromisoformat(str(contract["first_map_date"]))
    end = date.fromisoformat(str(contract["last_map_date"]))
    frequency = int(contract["frequency_days"])
    values = []
    while current <= end:
        values.append(current)
        current += timedelta(days=frequency)
    if len(values) != int(contract["expected_archives"]):
        raise ValueError("configured date sequence has unexpected length")
    return values


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--shape-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    arguments = parser.parse_args()

    contract = tomllib.loads(arguments.config.read_text(encoding="utf-8"))
    dates = configured_dates(contract)
    manifest = arguments.shape_dir / "MANIFEST.jsonl"
    identities = manifest_identities(manifest)
    expected_names = {f"USDM_{value:%Y%m%d}_M.zip" for value in dates}
    if set(identities) != expected_names:
        raise ValueError("manifest file support differs from configured weekly sequence")
    actual_names = {path.name for path in arguments.shape_dir.glob("USDM_*_M.zip")}
    if actual_names != expected_names:
        raise ValueError("raw archive file support differs from configured weekly sequence")

    combined = hashlib.sha256()
    total_bytes = 0
    total_records = 0
    minimum_records = None
    maximum_records = 0
    missing_severity_weeks = {str(level): 0 for level in range(5)}
    for number, map_date in enumerate(dates, 1):
        name = f"USDM_{map_date:%Y%m%d}_M.zip"
        path = arguments.shape_dir / name
        payload = path.read_bytes()
        byte_count = len(payload)
        sha512 = hashlib.sha512(payload).hexdigest()
        if (byte_count, sha512) not in identities[name]:
            raise ValueError(f"archive identity differs from manifest for {name}")
        validation = validate_archive(payload, map_date)
        records = int(validation["records"])
        severities = set(map(int, validation["severity_values"]))
        total_bytes += byte_count
        total_records += records
        minimum_records = records if minimum_records is None else min(minimum_records, records)
        maximum_records = max(maximum_records, records)
        for level in range(5):
            missing_severity_weeks[str(level)] += level not in severities
        combined.update(f"{name}\t{byte_count}\t{sha512}\n".encode())
        if number % 50 == 0 or number == len(dates):
            print(f"validated {number}/{len(dates)} weekly USDM archives", flush=True)

    line_count = sum(bool(line.strip()) for line in manifest.read_text(encoding="utf-8").splitlines())
    result = {
        "schema": "usdm_weekly_shapefile_archive_validation_v1",
        "passed": True,
        "config": str(arguments.config),
        "shape_directory": str(arguments.shape_dir),
        "first_map_date": dates[0].isoformat(),
        "last_map_date": dates[-1].isoformat(),
        "archives": len(dates),
        "total_bytes": total_bytes,
        "total_polygon_records": total_records,
        "minimum_records_per_archive": minimum_records,
        "maximum_records_per_archive": maximum_records,
        "weeks_without_severity_class": missing_severity_weeks,
        "canonical_identity_list_sha256": combined.hexdigest(),
        "raw_manifest_lines": line_count,
        "duplicate_manifest_lines": line_count - len(identities),
        "source": "official U.S. Drought Monitor weekly vector archive",
        "claim_boundary": "source and geometry validation only; not response, damage, or SCC",
    }
    arguments.out.parent.mkdir(parents=True, exist_ok=True)
    arguments.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
