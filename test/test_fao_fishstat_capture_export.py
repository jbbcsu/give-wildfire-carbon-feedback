#!/usr/bin/env python3
"""Synthetic failure gates for the FAO FishStat capture export validator."""
from __future__ import annotations

import csv
import hashlib
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.validate_fao_fishstat_capture_export import validate


root = Path(__file__).resolve().parents[1]
base_contract = (root / "data/provenance/fao_fishstat_capture_headless_export_v1.toml").read_text(encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


with tempfile.TemporaryDirectory() as temporary:
    temp = Path(temporary)
    contract = temp / "contract.toml"
    contract.write_text(base_contract.replace("wide_record_count = 30918", "wide_record_count = 1"), encoding="utf-8")
    csv_path = temp / "export.csv"
    years = range(1950, 2025)
    fixed = [
        "source_record_id", "country_un_m49", "country_iso3", "country_name",
        "species_asfis_code", "species_scientific_name", "species_name",
        "fao_area_code", "fao_area_name", "environment_class",
        "measure_code", "measure_name", "unit", "unit_multiplier",
    ]
    header = fixed + [item for year in years for item in (f"value_{year}", f"status_{year}")]
    row = ["00000001", "516", "NAM", "Namibia", "GLS", "Galatheidae", "Squat lobsters nei", "47", "Atlantic, Southeast", "marine", "Q_tlw", "Tonnes - live weight", "t", "1"]
    for _ in years:
        row.extend(["0.0", "O"])
    with csv_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n", quoting=csv.QUOTE_ALL)
        writer.writerow(header)
        writer.writerow(row)
    audit = temp / "audit.json"
    audit.write_text(json.dumps({
        "schema": "fao_fishstat_capture_headless_source_audit_v1",
        "source_table": "FISHSTAT.TSD_CAPTURE_QUANTITY",
        "years": [1950, 2024],
        "output": {"bytes": csv_path.stat().st_size, "sha256": sha256(csv_path)},
        "counts": {"wide_records": 1, "annual_cells": 75, "value_null_cells": 0, "status_blank_cells": 0, "positive_value_cells": 0, "zero_value_cells": 75, "environment_records": {"inland": 0, "marine": 1}, "measure_records": {"Q_tlw": 1}, "status_cells": {"O": 75}},
    }), encoding="utf-8")
    result = validate(contract, csv_path, audit, root)
    assert result["records"] == 1 and result["annual_cells"] == 75

    bad = list(row)
    bad[-1] = "Q"
    with csv_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n", quoting=csv.QUOTE_ALL)
        writer.writerow(header)
        writer.writerow(bad)
    try:
        validate(contract, csv_path, audit, root)
    except ValueError as error:
        assert "byte count" in str(error) or "SHA-256" in str(error)
    else:
        raise AssertionError("tampered CSV was accepted")

    opened = base_contract.replace("fishstat_gui_menu_export_reconciled = false", "fishstat_gui_menu_export_reconciled = true")
    contract.write_text(opened.replace("wide_record_count = 30918", "wide_record_count = 1"), encoding="utf-8")
    try:
        validate(contract, csv_path, audit, root)
    except ValueError as error:
        assert "closed boundary" in str(error)
    else:
        raise AssertionError("premature downstream authorization was accepted")

print("FAO FishStat capture export synthetic tests passed")
