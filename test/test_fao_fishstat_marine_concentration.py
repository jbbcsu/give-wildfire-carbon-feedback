#!/usr/bin/env python3
"""Synthetic tests for reported marine-capture concentration."""

from __future__ import annotations

import csv
import importlib.util
from pathlib import Path
import tempfile


SCRIPT = Path(__file__).parents[1] / "scripts" / "audit_fao_fishstat_marine_concentration.py"
SPEC = importlib.util.spec_from_file_location("marine_concentration", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def contract(path: Path) -> None:
    path.write_text(
        "schema = \"fao_fishstat_capture_headless_export_contract_v1\"\n"
        "[source]\nannual_start_year = 1950\nannual_end_year = 2024\n"
        "[export]\nrequired_status_codes = [\"A\", \"L\", \"M\", \"O\", \"Q\", \"N\"]\n"
        "missing_status_codes = [\"L\", \"M\", \"O\", \"Q\"]\n",
        encoding="utf-8",
    )


def capture(path: Path, invalid_missing: bool = False) -> None:
    fields = ["environment_class", "measure_code", "country_iso3", "species_asfis_code", "fao_area_code"]
    fields += [field for year in MODULE.YEARS for field in (f"value_{year}", f"status_{year}")]
    rows = []
    for iso3, species, area, value in (("AAA", "001", "1", 80.0), ("BBB", "002", "2", 20.0)):
        row = {"environment_class": "marine", "measure_code": "Q_tlw", "country_iso3": iso3, "species_asfis_code": species, "fao_area_code": area}
        for year in MODULE.YEARS:
            row[f"value_{year}"] = value
            row[f"status_{year}"] = "A"
        rows.append(row)
    if invalid_missing:
        rows[0]["status_1950"] = "M"
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


with tempfile.TemporaryDirectory() as folder:
    root = Path(folder)
    contract_path, csv_path = root / "contract.toml", root / "capture.csv"
    contract(contract_path)
    capture(csv_path)
    result = MODULE.audit(contract_path, csv_path)
    first = result["results"][0]["concentration_excluding_blank_iso3"]["country_iso3"]
    assert first["top1_share"] == 0.8
    assert first["top5_share"] == 1.0
    assert abs(first["herfindahl_index"] - 0.68) < 1e-12

    capture(csv_path, invalid_missing=True)
    try:
        MODULE.audit(contract_path, csv_path)
    except ValueError as error:
        assert "missing-status" in str(error)
    else:
        raise AssertionError("positive missing-status value was accepted")

print("FAO marine-capture concentration tests passed")
