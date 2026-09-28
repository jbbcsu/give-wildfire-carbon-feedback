#!/usr/bin/env python3
"""Audit Blue-SCC market-coefficient coverage against the frozen GIVE universe.

The external coefficient table is read in place. The output contains only
aggregate overlap and FUND-region coverage counts, never coefficient values or
country-level source membership.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import subprocess
import tomllib
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG_SCHEMA = "blue_scc_give_country_transfer_config_v1"
CONFIG_ROLE = "country_key_and_coverage_transfer_audit_only_not_damage_or_scc"
SOURCE_FIELDS = {"country_iso3", "GDP_FractionChange_perC"}
GIVE_FIELDS = ["country_id", "country_name", "give_region_id", "mapping_version"]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        return list(reader.fieldnames or []), list(reader)


def country_keys(
    fieldnames: list[str], rows: list[dict[str, str]], key: str, required: set[str]
) -> set[str]:
    if not required.issubset(fieldnames):
        raise ValueError(f"required columns absent for {key}")
    countries: set[str] = set()
    for row in rows:
        country = row[key].strip()
        if not re.fullmatch(r"[A-Z]{3}", country) or country in countries:
            raise ValueError(f"invalid or duplicate country key in {key}")
        countries.add(country)
    return countries


def summarize_transfer(
    source_fields: list[str],
    source_rows: list[dict[str, str]],
    give_fields: list[str],
    give_rows: list[dict[str, str]],
    expected_regions: set[str],
) -> dict[str, object]:
    source = country_keys(source_fields, source_rows, "country_iso3", SOURCE_FIELDS)
    give = country_keys(give_fields, give_rows, "country_id", set(GIVE_FIELDS))
    if give_fields != GIVE_FIELDS:
        raise ValueError("GIVE crosswalk columns or order changed")

    region_total: Counter[str] = Counter()
    region_covered: Counter[str] = Counter()
    for row in give_rows:
        region = row["give_region_id"].strip()
        if region not in expected_regions:
            raise ValueError("GIVE row contains an undeclared region")
        region_total[region] += 1
        if row["country_id"].strip() in source:
            region_covered[region] += 1
    if set(region_total) != expected_regions:
        raise ValueError("GIVE crosswalk does not cover every declared region")

    by_region = {
        region: {
            "give_countries": region_total[region],
            "source_covered_countries": region_covered[region],
            "uncovered_countries": region_total[region] - region_covered[region],
            "complete": region_total[region] == region_covered[region],
        }
        for region in sorted(expected_regions)
    }
    overlap = len(source & give)
    return {
        "source_country_rows": len(source),
        "give_country_rows": len(give),
        "overlap_countries": overlap,
        "source_only_countries": len(source - give),
        "give_only_countries": len(give - source),
        "give_country_count_coverage_fraction": overlap / len(give),
        "complete_regions": sum(item["complete"] for item in by_region.values()),
        "incomplete_regions": sum(not item["complete"] for item in by_region.values()),
        "region_coverage": by_region,
    }


def git_head(root: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        check=True,
        text=True,
        capture_output=True,
    )
    return result.stdout.strip()


def audit(source_root: Path, config_path: Path) -> dict[str, object]:
    config = tomllib.loads(config_path.read_text(encoding="utf-8"))
    if config.get("schema") != CONFIG_SCHEMA or config.get("role") != CONFIG_ROLE:
        raise ValueError("transfer config identity changed")
    source = config["source"]
    if git_head(source_root) != source["repository_commit"]:
        raise ValueError("Blue-SCC repository commit changed")
    license_files = [
        path.name
        for path in source_root.iterdir()
        if path.is_file() and path.name.lower().startswith(("license", "copying"))
    ]
    if license_files:
        raise ValueError("root license state changed; review before reuse")
    source_path = source_root / source["coefficient_path"]
    if not source_path.is_file() or source_path.is_symlink():
        raise ValueError("pinned coefficient source is missing or not a regular file")
    if sha256(source_path) != source["coefficient_sha256"]:
        raise ValueError("pinned coefficient source hash changed")

    give_config_path = ROOT / config["give"]["crosswalk_config"]
    give_config = tomllib.loads(give_config_path.read_text(encoding="utf-8"))
    give_path = ROOT / give_config["derived_crosswalk"]
    if sha256(give_path) != give_config["derived_sha256"]:
        raise ValueError("frozen GIVE crosswalk hash changed")
    source_fields, source_rows = read_csv(source_path)
    give_fields, give_rows = read_csv(give_path)
    summary = summarize_transfer(
        source_fields,
        source_rows,
        give_fields,
        give_rows,
        set(map(str, give_config["expected_regions"])),
    )
    if summary["source_country_rows"] != int(source["expected_coefficient_rows"]):
        raise ValueError("source coefficient row count changed")
    if summary["give_country_rows"] != int(config["give"]["expected_country_rows"]):
        raise ValueError("GIVE country row count changed")
    if len(summary["region_coverage"]) != int(config["give"]["expected_region_count"]):
        raise ValueError("GIVE region count changed")
    for key in (
        "overlap_countries", "source_only_countries", "give_only_countries", "complete_regions"
    ):
        if summary[key] != int(config["expected"][key]):
            raise ValueError(f"registered transfer result changed: {key}")
    gates = dict(config["claim_gates"])
    if any(gates.values()):
        raise ValueError("transfer config improperly opens a scientific gate")

    return {
        "schema": "blue_scc_give_country_transfer_audit_v1",
        "role": config["role"],
        "status": "blocked_incomplete_country_coverage_and_unlicensed_source",
        "source": {
            "repository_url": source["repository_url"],
            "repository_commit": source["repository_commit"],
            "repository_license_status": source["repository_license_status"],
            "coefficient_path": source["coefficient_path"],
            "coefficient_sha256": source["coefficient_sha256"],
        },
        "give_crosswalk": {
            "mapping_version": give_config["mapping_version"],
            "path": str(give_path.relative_to(ROOT)),
            "sha256": give_config["derived_sha256"],
        },
        "coverage": summary,
        "interpretation": {
            "coverage_fraction_is_unweighted_country_count": True,
            "missing_countries_may_not_be_treated_as_zero": True,
            "complete_region_totals_available_under_current_contract": False,
            "coefficient_values_or_country_membership_embedded": False,
            "external_source_files_copied": False,
        },
        "claim_gates": gates,
        "config": {
            "path": str(config_path.relative_to(ROOT)),
            "sha256": sha256(config_path),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument(
        "--config", type=Path, default=ROOT / "config/blue_scc_give_country_transfer_v1.toml"
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / "data/provenance/blue_scc_give_country_transfer_audit_20260928.json",
    )
    args = parser.parse_args()
    result = audit(args.source_root.resolve(), args.config.resolve())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.out.with_suffix(args.out.suffix + ".partial")
    temporary.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(args.out)
    print(
        "Blue-SCC/GIVE country transfer blocked: "
        f"{result['coverage']['overlap_countries']}/"
        f"{result['coverage']['give_country_rows']} GIVE countries covered"
    )


if __name__ == "__main__":
    main()
