#!/usr/bin/env python3
"""Validate the source-bound Hultgren maize precipitation-method record."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import tempfile
import tomllib
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        type=Path,
        default=ROOT / "config/hultgren_maize_weather_method_v1.toml",
    )
    parser.add_argument(
        "--receipt",
        type=Path,
        default=ROOT / "data/provenance/hultgren_maize_weather_method_validation_20260923.json",
    )
    args = parser.parse_args()

    config_path = args.config.resolve()
    config = tomllib.loads(config_path.read_text())
    supplement = config["supplement"]
    archive_path = ROOT / supplement["archive_path"]
    require(archive_path.stat().st_size == supplement["archive_bytes"], "Supplement archive size differs")
    require(sha256_file(archive_path) == supplement["archive_sha256"], "Supplement archive hash differs")

    with zipfile.ZipFile(archive_path) as archive:
        member_info = archive.getinfo(supplement["member"])
        member_bytes = archive.read(member_info)
    require(member_info.file_size == supplement["member_bytes"], "Supplement PDF size differs")
    require(sha256_bytes(member_bytes) == supplement["member_sha256"], "Supplement PDF hash differs")

    with tempfile.NamedTemporaryFile(suffix=".pdf") as temporary_pdf:
        temporary_pdf.write(member_bytes)
        temporary_pdf.flush()
        pdfinfo = subprocess.run(
            ["pdfinfo", temporary_pdf.name],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        page_lines = [line for line in pdfinfo.splitlines() if line.startswith("Pages:")]
        require(len(page_lines) == 1, "Could not read supplement page count")
        pages = int(page_lines[0].split(":", 1)[1].strip())
        require(pages == supplement["pages"], "Supplement page count differs")
        completed = subprocess.run(
            ["pdftotext", "-layout", temporary_pdf.name, "-"],
            check=True,
            capture_output=True,
            text=True,
        )
    supplement_text = " ".join(completed.stdout.split())
    validation = config["validation"]
    missing_supplement_text = [
        text
        for text in validation["required_supplement_text"]
        if " ".join(text.split()) not in supplement_text
    ]
    require(not missing_supplement_text, f"Required supplement text missing: {missing_supplement_text}")

    code_config_path = ROOT / config["code"]["source_config"]
    code_config = tomllib.loads(code_config_path.read_text())
    require(code_config["source_commit"] == "3ccdffcd4e4ff6e55566ce76e2aac130ee86349a", "Source commit differs")
    code_paths = [
        ROOT / config["code"]["set_crop_variables"],
        ROOT / config["code"]["collapse_clim"],
    ]
    code_text = "\n".join(path.read_text() for path in code_paths)
    missing_code_text = [text for text in validation["required_code_text"] if text not in code_text]
    require(not missing_code_text, f"Required source-code text missing: {missing_code_text}")

    maize = config["maize"]
    require(maize["precipitation_phase_lengths_months"] == [1, 3, 6], "Unexpected maize phases")
    require(sum(maize["precipitation_phase_lengths_months"]) == maize["growing_season_months"], "Phases do not cover season")
    require(maize["precipitation_polynomial_order"] == 2, "Unexpected precipitation order")

    reproducibility = config["reproducibility"]
    require(reproducibility["published_estimate_available"], "Published estimate must be available")
    require(not reproducibility["required_regression_dataset_available"], "Missing dataset gate changed")
    require(not reproducibility["future_projection_ready"], "Future projection must remain blocked")
    require(not reproducibility["damage_ready"], "Damage gate must remain blocked")
    require(not reproducibility["scc_ready"], "SCC gate must remain blocked")

    receipt = {
        "schema_version": 1,
        "validated_at_utc": datetime.now(timezone.utc).isoformat(),
        "config": {"path": str(config_path.relative_to(ROOT)), "sha256": sha256_file(config_path)},
        "publication_doi": config["publication_doi"],
        "supplement": {
            "official_endpoint": supplement["official_endpoint"],
            "archive_path": supplement["archive_path"],
            "archive_bytes": archive_path.stat().st_size,
            "archive_sha256": sha256_file(archive_path),
            "member": supplement["member"],
            "member_bytes": member_info.file_size,
            "member_sha256": sha256_bytes(member_bytes),
            "pages": pages,
            "license": supplement["license"],
            "storage_rule": supplement["storage_rule"],
            "required_text_checks": len(validation["required_supplement_text"]),
        },
        "code": {
            "source_commit": code_config["source_commit"],
            "license_status": config["code"]["license_status"],
            "files": [
                {"path": str(path.relative_to(ROOT)), "sha256": sha256_file(path)}
                for path in code_paths
            ],
            "required_text_checks": len(validation["required_code_text"]),
        },
        "maize_method": maize,
        "method": config["method"],
        "claim_gates": {
            "source_identity_validated": True,
            "monthly_quantity_and_within_season_timing_documented": True,
            "published_maize_phase_structure_validated": True,
            "exact_historical_response_reproduced": False,
            "future_projection_validated": False,
            "damage_estimate_validated": False,
            "scc_estimate_validated": False,
        },
    }
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps(receipt["claim_gates"], sort_keys=True))


if __name__ == "__main__":
    main()
