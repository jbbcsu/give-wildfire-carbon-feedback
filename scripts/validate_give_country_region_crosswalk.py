#!/usr/bin/env python3
"""Validate the frozen baseline GIVE country-to-FUND region crosswalk."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import tomllib
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG_SCHEMA = "give_country_fund_region_crosswalk_config_v1"
CONFIG_ROLE = "baseline_give_country_to_fund_region_aggregation_crosswalk_not_welfare_damage_or_scc"
FIELDNAMES = ["country_id", "country_name", "give_region_id", "mapping_version"]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        return list(reader.fieldnames or []), list(reader)


def validate_rows(fieldnames: list[str], rows: list[dict[str, str]], config: dict) -> dict[str, object]:
    if config.get("schema") != CONFIG_SCHEMA or config.get("role") != CONFIG_ROLE:
        raise ValueError("crosswalk config identity changed")
    if fieldnames != FIELDNAMES:
        raise ValueError("crosswalk columns or order changed")
    expected_count = int(config["expected_country_rows"])
    if len(rows) != expected_count:
        raise ValueError("crosswalk country count changed")
    mapping_version = str(config["mapping_version"])
    expected_regions = set(map(str, config["expected_regions"]))
    expected_region_counts = {str(key): int(value) for key, value in config["expected_region_counts"].items()}
    if expected_regions != set(expected_region_counts):
        raise ValueError("expected region identities and counts disagree")

    countries: set[str] = set()
    region_counts: Counter[str] = Counter()
    for row in rows:
        country = row["country_id"].strip()
        name = row["country_name"].strip()
        region = row["give_region_id"].strip()
        version = row["mapping_version"].strip()
        if not re.fullmatch(r"[A-Z]{3}", country) or country in countries:
            raise ValueError("country IDs are invalid or duplicated")
        if not name:
            raise ValueError("country name is blank")
        if region not in expected_regions:
            raise ValueError("country maps to an undeclared GIVE region")
        if version != mapping_version:
            raise ValueError("mapping version changed within the crosswalk")
        countries.add(country)
        region_counts[region] += 1
    if dict(region_counts) != expected_region_counts:
        raise ValueError("per-region country counts changed")
    return {
        "country_rows": len(rows),
        "region_count": len(region_counts),
        "region_country_counts": dict(sorted(region_counts.items())),
        "mapping_version": mapping_version,
    }


def audit(config_path: Path) -> dict[str, object]:
    config = tomllib.loads(config_path.read_text(encoding="utf-8"))
    crosswalk_path = ROOT / str(config["derived_crosswalk"])
    observed_hash = sha256(crosswalk_path)
    if observed_hash != str(config["derived_sha256"]):
        raise ValueError("derived crosswalk SHA-256 changed")
    fieldnames, rows = read_rows(crosswalk_path)
    summary = validate_rows(fieldnames, rows, config)
    limitations = config.get("limitations", {})
    if any(limitations.get(name) is not False for name in (
        "country_welfare_coverage_validated",
        "fishmip_to_country_allocation_validated",
        "trade_or_incidence_model_selected",
        "welfare_estimated",
        "damage_or_scc_authorized",
    )):
        raise ValueError("crosswalk config improperly opens a downstream gate")
    return {
        "schema": "give_country_fund_region_crosswalk_audit_v1",
        "role": config["role"],
        "status": "validated_aggregation_crosswalk_only",
        **summary,
        "source": {
            "description": config["source"],
            "path_at_acquisition": config["source_path_at_acquisition"],
            "sha256": config["source_sha256"],
            "license_note": config["source_license_note"],
        },
        "crosswalk": {
            "path": str(crosswalk_path.relative_to(ROOT)),
            "sha256": observed_hash,
        },
        "config": {
            "path": str(config_path.relative_to(ROOT)),
            "sha256": sha256(config_path),
        },
        "aggregator_schema_compatible": True,
        "country_welfare_coverage_validated": False,
        "fishmip_to_country_allocation_validated": False,
        "trade_or_incidence_model_selected": False,
        "welfare_estimated": False,
        "damage_or_scc_authorized": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=ROOT / "config/give_country_fund_region_crosswalk_v1.toml")
    parser.add_argument("--out", type=Path, default=ROOT / "data/provenance/give_country_fund_region_crosswalk_audit_20260828.json")
    args = parser.parse_args()
    config_path = args.config.resolve()
    result = audit(config_path)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.out.with_suffix(args.out.suffix + ".partial")
    temporary.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(args.out)
    print(f"GIVE fisheries crosswalk passed: {result['country_rows']} countries in {result['region_count']} regions")


if __name__ == "__main__":
    main()
