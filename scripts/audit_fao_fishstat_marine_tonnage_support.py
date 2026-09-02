#!/usr/bin/env python3
"""Describe annual marine-tonnage support without opening calibration gates."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import tomllib
from pathlib import Path


EXPECTED_SCHEMA = "fao_fishstat_capture_headless_export_contract_v1"
EXPECTED_ROLE = "observed_capture_record_integrity_gate_not_fishmip_calibration_allocation_welfare_damage_or_scc"
SELECTED_YEARS = (1950, 1960, 1970, 1980, 1990, 2000, 2010, 2014)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def empty_year() -> dict[str, object]:
    return {
        "reported_positive_tonnes": 0.0,
        "positive_cells": 0,
        "missing_cells": 0,
        "suppressed_cells": 0,
        "not_significant_cells": 0,
        "active_iso3": set(),
        "active_areas": set(),
        "active_species": set(),
        "blank_iso3_positive_tonnes": 0.0,
    }


def audit(contract_path: Path, csv_path: Path) -> dict[str, object]:
    contract = tomllib.loads(contract_path.read_text(encoding="utf-8"))
    require(contract.get("schema") == EXPECTED_SCHEMA, "headless export schema changed")
    require(contract.get("role") == EXPECTED_ROLE, "headless export role changed")
    require(contract["source"]["annual_start_year"] == 1950, "capture start year changed")
    require(contract["source"]["annual_end_year"] >= 2014, "FishMIP overlap is incomplete")
    require(contract["export"]["not_significant_status_code"] == "N", "not-significant code changed")
    require(set(contract["export"]["missing_status_codes"]) == {"L", "M", "O", "Q"}, "missing codes changed")
    for gate, value in contract["boundaries"].items():
        require(value is False, f"closed boundary changed: {gate}")

    years = list(range(1950, 2015))
    annual = {year: empty_year() for year in years}
    records = 0
    with csv_path.open("r", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        required = {
            "source_record_id", "country_iso3", "species_asfis_code", "fao_area_code",
            "environment_class", "measure_code",
        } | {item for year in years for item in (f"value_{year}", f"status_{year}")}
        require(reader.fieldnames is not None and required <= set(reader.fieldnames), "capture CSV schema is incomplete")
        for row in reader:
            if row["environment_class"] != "marine" or row["measure_code"] != "Q_tlw":
                continue
            records += 1
            for year in years:
                value = float(row[f"value_{year}"])
                status = row[f"status_{year}"]
                require(value >= 0, "negative capture value")
                require(status in contract["export"]["required_status_codes"], "unknown capture status")
                summary = annual[year]
                if status in {"L", "M", "O"}:
                    summary["missing_cells"] += 1
                elif status == "Q":
                    summary["suppressed_cells"] += 1
                elif status == "N":
                    summary["not_significant_cells"] += 1
                if value > 0:
                    summary["reported_positive_tonnes"] += value
                    summary["positive_cells"] += 1
                    if row["country_iso3"]:
                        summary["active_iso3"].add(row["country_iso3"])
                    else:
                        summary["blank_iso3_positive_tonnes"] += value
                    summary["active_areas"].add(row["fao_area_code"])
                    summary["active_species"].add(row["species_asfis_code"])

    require(records > 0, "marine-tonnage support is empty")
    for summary in annual.values():
        for field in ("active_iso3", "active_areas", "active_species"):
            summary[field] = len(summary[field])
        total = summary["reported_positive_tonnes"]
        summary["blank_iso3_positive_tonnes_share"] = (
            summary["blank_iso3_positive_tonnes"] / total if total else None
        )

    minimum_year = min(years, key=lambda year: annual[year]["reported_positive_tonnes"])
    maximum_year = max(years, key=lambda year: annual[year]["reported_positive_tonnes"])
    blank_year = max(years, key=lambda year: annual[year]["blank_iso3_positive_tonnes_share"] or 0.0)
    return {
        "schema": "fao_fishstat_marine_tonnage_support_audit_v1",
        "role": "post_export_descriptive_support_not_filter_authorization_allocation_calibration_welfare_damage_or_scc",
        "input": {"contract_sha256": sha256(contract_path), "csv_sha256": sha256(csv_path)},
        "filter_description": "environment_class=marine and measure_code=Q_tlw; positive values summed; status retained separately",
        "records": records,
        "years": [years[0], years[-1]],
        "minimum_reported_positive_tonnes": {"year": minimum_year, "value": annual[minimum_year]["reported_positive_tonnes"]},
        "maximum_reported_positive_tonnes": {"year": maximum_year, "value": annual[maximum_year]["reported_positive_tonnes"]},
        "maximum_blank_iso3_positive_tonnes_share": {"year": blank_year, "value": annual[blank_year]["blank_iso3_positive_tonnes_share"]},
        "years_with_suppressed_cells": [year for year in years if annual[year]["suppressed_cells"]],
        "selected_years": {str(year): annual[year] for year in SELECTED_YEARS},
        "fishstat_gui_menu_export_reconciled": False,
        "marine_tonnage_filter_authorized": False,
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
    result = audit(args.contract.resolve(), args.csv.resolve())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("FAO marine-tonnage descriptive support audit passed")


if __name__ == "__main__":
    main()
