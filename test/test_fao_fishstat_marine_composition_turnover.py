#!/usr/bin/env python3
"""Synthetic tests for the FAO marine-capture composition-turnover audit."""

from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path
import tempfile


SCRIPT = Path(__file__).parents[1] / "scripts" / "audit_fao_fishstat_marine_composition_turnover.py"
SPEC = importlib.util.spec_from_file_location("marine_turnover", SCRIPT)
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


def capture(path: Path) -> None:
    fields = ["environment_class", "measure_code", *MODULE.DIMENSIONS]
    fields += [field for year in MODULE.YEARS for field in (f"value_{year}", f"status_{year}")]
    rows = []
    for iso3, species, area, values in (
        ("AAA", "001", "1", (80.0, 50.0, 20.0, 0.0)),
        ("BBB", "002", "2", (20.0, 50.0, 80.0, 100.0)),
    ):
        row = {"environment_class": "marine", "measure_code": "Q_tlw", "country_iso3": iso3, "species_asfis_code": species, "fao_area_code": area}
        for year, value in zip(MODULE.YEARS, values):
            row[f"value_{year}"] = value
            row[f"status_{year}"] = "A"
        rows.append(row)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


with tempfile.TemporaryDirectory() as folder:
    root = Path(folder)
    contract_path = root / "contract.toml"
    validation_path = root / "validation.json"
    csv_path = root / "capture.csv"
    contract(contract_path)
    capture(csv_path)
    validation_path.write_text(json.dumps({
        "schema": "fao_fishstat_capture_headless_export_validation_v1",
        "status": "wide_export_reconciled_value_and_status_pairs_preserved",
        "contract": {"sha256": MODULE.sha256(contract_path)},
        "export": {"sha256": MODULE.sha256(csv_path), "bytes": csv_path.stat().st_size},
    }), encoding="utf-8")
    result = MODULE.audit(contract_path, validation_path, csv_path)
    first = result["comparisons"][0]["dimensions"]["country_iso3"]
    assert abs(first["composition_total_variation"] - 0.3) < 1e-12
    assert first["positive_group_jaccard"] == 1.0
    last = result["comparisons"][-1]["dimensions"]["country_iso3"]
    assert last["positive_group_jaccard"] == 0.5
    assert abs(last["composition_total_variation"] - 0.2) < 1e-12

    bad = json.loads(validation_path.read_text(encoding="utf-8"))
    bad["export"]["sha256"] = "0" * 64
    validation_path.write_text(json.dumps(bad), encoding="utf-8")
    try:
        MODULE.audit(contract_path, validation_path, csv_path)
    except ValueError as error:
        assert "hash" in str(error)
    else:
        raise AssertionError("mismatched CSV hash was accepted")

print("FAO marine-capture composition-turnover tests passed")
