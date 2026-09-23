#!/usr/bin/env python3
"""Audit the old Hultgren impact archive without extracting it into memory."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import tomllib
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def hashes(path: Path) -> tuple[str, str]:
    sha256 = hashlib.sha256()
    git_sha1 = hashlib.sha1(b"blob " + str(path.stat().st_size).encode() + b"\0")
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            sha256.update(block)
            git_sha1.update(block)
    return sha256.hexdigest(), git_sha1.hexdigest()


def sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    config_path = args.config.resolve()
    config = tomllib.loads(config_path.read_text())
    archive = ROOT / config["local_path"]

    sha256, git_blob_sha1 = hashes(archive)
    checks = {
        "bytes": archive.stat().st_size,
        "sha256": sha256,
        "git_blob_sha1": git_blob_sha1,
    }
    for field, value in checks.items():
        if value != config[field]:
            raise ValueError(f"Archive {field} mismatch")

    with zipfile.ZipFile(archive) as bundle:
        members = bundle.infolist()
        names = {member.filename for member in members}
        total_uncompressed = sum(member.file_size for member in members)
        if len(members) != config["zip_members"]:
            raise ValueError("ZIP member count mismatch")
        if total_uncompressed != config["zip_uncompressed_bytes"]:
            raise ValueError("ZIP uncompressed byte total mismatch")
        required = config["audit"]["required_current_regression_member"]
        historical = config["audit"]["historical_maize_projection_member"]
        if historical not in names:
            raise ValueError("Expected historical maize projection is absent")
        with bundle.open(historical) as binary:
            reader = csv.reader(io.TextIOWrapper(binary, encoding="utf-8", newline=""))
            header = next(reader)
            rows = sum(1 for _ in reader)

    expected_historical_fields = {
        "region", "year", "gdd831", "kdd31", "pr", "prpoly2", "coeffpr",
        "coeffpr2", "seasonalpr", "irshare", "baseline",
    }
    if not expected_historical_fields.issubset(header):
        raise ValueError("Historical maize projection schema differs")

    receipt = {
        "schema_version": 1,
        "audited_at_utc": datetime.now(timezone.utc).isoformat(),
        "config": {"path": str(config_path.relative_to(ROOT)), "sha256": sha256_file(config_path)},
        "archive": {
            "local_path": config["local_path"],
            "source_repository": config["source_repository"],
            "historical_commit": config["historical_commit"],
            "repository_path": config["repository_path"],
            **checks,
            "zip_members": len(members),
            "zip_uncompressed_bytes": total_uncompressed,
            "license_status": config["license_status"],
            "version_warning": config["version_warning"],
        },
        "current_data_route": {
            "url": config["current_readme_data_url"],
            "checked": config["current_readme_data_url_checked"],
            "http_status": config["current_readme_data_url_http_status"],
        },
        "contents": {
            "required_current_regression_member": required,
            "required_current_regression_member_present": required in names,
            "historical_maize_projection_member": historical,
            "historical_maize_projection_rows": rows,
            "historical_maize_projection_columns": header,
        },
        "claim_gates": {
            "archive_identity_validated": True,
            "current_regression_data_recovered": required in names,
            "final_2025_model_version_match_validated": False,
            "future_precipitation_projection_validated": False,
            "damage_estimate_validated": False,
            "scc_estimate_validated": False,
        },
    }
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps(receipt["claim_gates"], sort_keys=True))


if __name__ == "__main__":
    main()
