#!/usr/bin/env python3
"""Audit time variation in reported FAO marine-capture composition."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import tomllib
from collections import defaultdict
from pathlib import Path


YEARS = (1950, 1970, 1990, 2014)
PAIRS = tuple(zip(YEARS[:-1], YEARS[1:]))
DIMENSIONS = ("country_iso3", "species_asfis_code", "fao_area_code")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def shares(values: dict[str, float]) -> dict[str, float]:
    positive = {key: value for key, value in values.items() if value > 0}
    total = sum(positive.values())
    require(total > 0, "composition denominator is zero")
    return {key: value / total for key, value in positive.items()}


def compare(first: dict[str, float], second: dict[str, float]) -> dict[str, float | int]:
    left, right = shares(first), shares(second)
    union = set(left) | set(right)
    left_positive, right_positive = set(left), set(right)
    left_top5 = set(sorted(left, key=lambda key: (-left[key], key))[:5])
    right_top5 = set(sorted(right, key=lambda key: (-right[key], key))[:5])
    return {
        "first_positive_groups": len(left_positive),
        "second_positive_groups": len(right_positive),
        "positive_group_jaccard": len(left_positive & right_positive) / len(left_positive | right_positive),
        "composition_total_variation": 0.5 * sum(abs(left.get(key, 0.0) - right.get(key, 0.0)) for key in union),
        "top5_members_retained": len(left_top5 & right_top5),
        "first_top5_share_of_second_tonnage": sum(right.get(key, 0.0) for key in left_top5),
        "second_top5_share_of_first_tonnage": sum(left.get(key, 0.0) for key in right_top5),
    }


def audit(contract_path: Path, validation_path: Path, csv_path: Path) -> dict[str, object]:
    contract = tomllib.loads(contract_path.read_text(encoding="utf-8"))
    require(contract.get("schema") == "fao_fishstat_capture_headless_export_contract_v1", "headless export schema changed")
    require(contract["source"]["annual_start_year"] <= min(YEARS), "requested years precede export")
    require(contract["source"]["annual_end_year"] >= max(YEARS), "requested years exceed export")
    required_status = set(contract["export"]["required_status_codes"])
    missing_status = set(contract["export"]["missing_status_codes"])
    validation = json.loads(validation_path.read_text(encoding="utf-8"))
    require(validation.get("schema") == "fao_fishstat_capture_headless_export_validation_v1", "validation schema changed")
    require(validation.get("status") == "wide_export_reconciled_value_and_status_pairs_preserved", "headless export validation did not pass")
    require(validation.get("contract", {}).get("sha256") == sha256(contract_path), "contract hash changed")
    csv_hash = sha256(csv_path)
    require(validation.get("export", {}).get("sha256") == csv_hash, "capture CSV hash changed")
    require(validation.get("export", {}).get("bytes") == csv_path.stat().st_size, "capture CSV size changed")

    grouped = {year: {dimension: defaultdict(float) for dimension in DIMENSIONS} for year in YEARS}
    records = 0
    with csv_path.open("r", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        required_columns = {"environment_class", "measure_code", *DIMENSIONS} | {
            field for year in YEARS for field in (f"value_{year}", f"status_{year}")
        }
        require(reader.fieldnames is not None and required_columns <= set(reader.fieldnames), "capture CSV schema is incomplete")
        for row in reader:
            if row["environment_class"] != "marine" or row["measure_code"] != "Q_tlw":
                continue
            records += 1
            for year in YEARS:
                value = float(row[f"value_{year}"])
                status = row[f"status_{year}"]
                require(value >= 0, "negative capture value")
                require(status in required_status, "unknown capture status")
                require(not (status in missing_status and value > 0), "missing-status cell carries positive tonnage")
                if value <= 0:
                    continue
                for dimension in DIMENSIONS:
                    key = row[dimension]
                    if dimension == "country_iso3" and not key:
                        continue
                    require(bool(key), f"positive marine record has blank {dimension}")
                    grouped[year][dimension][key] += value
    require(records > 0, "marine capture slice is empty")

    comparisons = []
    for first_year, second_year in PAIRS:
        comparisons.append({
            "first_year": first_year,
            "second_year": second_year,
            "dimensions": {
                dimension: compare(grouped[first_year][dimension], grouped[second_year][dimension])
                for dimension in DIMENSIONS
            },
        })
    return {
        "schema": "fao_fishstat_marine_composition_turnover_audit_v1",
        "role": "descriptive_reported_capture_composition_turnover_not_allocation_calibration_welfare_damage_or_scc",
        "input": {
            "contract_sha256": sha256(contract_path),
            "validation_sha256": sha256(validation_path),
            "csv_sha256": csv_hash,
        },
        "filter": "environment_class=marine; measure_code=Q_tlw; positive reported tonnage only; blank ISO3 excluded from country shares",
        "records": records,
        "comparisons": comparisons,
        "fishstat_gui_menu_export_reconciled": False,
        "country_or_eez_allocation_authorized": False,
        "fishmip_observed_calibration_authorized": False,
        "welfare_translation_authorized": False,
        "damage_or_scc_authorized": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--validation", type=Path, required=True)
    parser.add_argument("--csv", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.contract, args.validation, args.csv)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("FAO marine-capture composition-turnover audit passed")


if __name__ == "__main__":
    main()
