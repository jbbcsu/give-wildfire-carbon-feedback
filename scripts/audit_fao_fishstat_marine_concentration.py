#!/usr/bin/env python3
"""Audit concentration of reported FAO marine capture support over time."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import tomllib
from collections import defaultdict
from pathlib import Path


YEARS = (1950, 1970, 1990, 2014)
EXPECTED_SCHEMA = "fao_fishstat_capture_headless_export_contract_v1"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def concentration(values: dict[str, float]) -> dict[str, float | int]:
    positive = sorted((value for value in values.values() if value > 0), reverse=True)
    total = sum(positive)
    require(total > 0, "concentration denominator is zero")
    shares = [value / total for value in positive]
    return {
        "positive_groups": len(positive),
        "top1_share": shares[0],
        "top5_share": sum(shares[:5]),
        "herfindahl_index": sum(value * value for value in shares),
    }


def audit(contract_path: Path, csv_path: Path) -> dict[str, object]:
    contract = tomllib.loads(contract_path.read_text(encoding="utf-8"))
    require(contract.get("schema") == EXPECTED_SCHEMA, "headless export schema changed")
    require(contract["source"]["annual_start_year"] <= min(YEARS), "requested years precede the export")
    require(contract["source"]["annual_end_year"] >= max(YEARS), "requested years exceed the export")
    required_status = set(contract["export"]["required_status_codes"])
    missing_status = set(contract["export"]["missing_status_codes"])

    totals = {year: 0.0 for year in YEARS}
    blank_iso3 = {year: 0.0 for year in YEARS}
    groups = {
        year: {"country_iso3": defaultdict(float), "species_asfis_code": defaultdict(float), "fao_area_code": defaultdict(float)}
        for year in YEARS
    }
    records = 0
    with csv_path.open("r", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        required_columns = {
            "environment_class", "measure_code", "country_iso3",
            "species_asfis_code", "fao_area_code",
        } | {column for year in YEARS for column in (f"value_{year}", f"status_{year}")}
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
                totals[year] += value
                if not row["country_iso3"]:
                    blank_iso3[year] += value
                else:
                    groups[year]["country_iso3"][row["country_iso3"]] += value
                groups[year]["species_asfis_code"][row["species_asfis_code"]] += value
                groups[year]["fao_area_code"][row["fao_area_code"]] += value
    require(records > 0, "marine capture slice is empty")

    results = []
    for year in YEARS:
        require(totals[year] > 0, f"{year}: no positive marine tonnage")
        results.append({
            "year": year,
            "reported_positive_tonnes": totals[year],
            "blank_iso3_share": blank_iso3[year] / totals[year],
            "concentration_excluding_blank_iso3": {
                dimension: concentration(groups[year][dimension])
                for dimension in ("country_iso3", "species_asfis_code", "fao_area_code")
            },
        })
    return {
        "schema": "fao_fishstat_marine_concentration_audit_v1",
        "role": "descriptive_reported_capture_concentration_not_allocation_calibration_welfare_damage_or_scc",
        "input": {"contract_sha256": sha256(contract_path), "csv_sha256": sha256(csv_path)},
        "filter": "environment_class=marine; measure_code=Q_tlw; positive reported tonnage only",
        "records": records,
        "results": results,
        "fishstat_gui_menu_export_reconciled": False,
        "country_or_eez_allocation_authorized": False,
        "fishmip_observed_calibration_authorized": False,
        "welfare_translation_authorized": False,
        "damage_or_scc_authorized": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--csv", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.contract, args.csv)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("FAO marine-capture concentration audit passed")


if __name__ == "__main__":
    main()
