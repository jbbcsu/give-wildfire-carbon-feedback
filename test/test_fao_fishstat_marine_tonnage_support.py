#!/usr/bin/env python3
"""Synthetic gates for the descriptive FAO marine-tonnage support audit."""
from __future__ import annotations

import csv
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.audit_fao_fishstat_marine_tonnage_support import audit


root = Path(__file__).resolve().parents[1]
base_contract = (root / "data/provenance/fao_fishstat_capture_headless_export_v1.toml").read_text(encoding="utf-8")
years = range(1950, 2025)
fixed = [
    "source_record_id", "country_iso3", "species_asfis_code", "fao_area_code",
    "environment_class", "measure_code",
]
header = fixed + [item for year in years for item in (f"value_{year}", f"status_{year}")]


def row(record_id: str, environment: str, measure: str, value: float, status: str) -> list[str]:
    result = [record_id, "USA", "COD", "21", environment, measure]
    for year in years:
        result.extend([str(value if year == 2014 else 0.0), status if year == 2014 else "O"])
    return result


with tempfile.TemporaryDirectory() as temporary:
    temp = Path(temporary)
    contract = temp / "contract.toml"
    contract.write_text(base_contract, encoding="utf-8")
    csv_path = temp / "capture.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(header)
        writer.writerow(row("1", "marine", "Q_tlw", 10.0, "A"))
        writer.writerow(row("2", "inland", "Q_tlw", 20.0, "A"))
        writer.writerow(row("3", "marine", "Q_no_1", 30.0, "A"))
    result = audit(contract, csv_path)
    assert result["records"] == 1
    assert result["selected_years"]["2014"]["reported_positive_tonnes"] == 10.0
    assert not result["marine_tonnage_filter_authorized"]

    opened = base_contract.replace("marine_tonnage_filter_authorized = false", "marine_tonnage_filter_authorized = true")
    contract.write_text(opened, encoding="utf-8")
    try:
        audit(contract, csv_path)
    except ValueError as error:
        assert "closed boundary" in str(error)
    else:
        raise AssertionError("premature marine-filter authorization was accepted")

print("FAO marine-tonnage support synthetic tests passed")
