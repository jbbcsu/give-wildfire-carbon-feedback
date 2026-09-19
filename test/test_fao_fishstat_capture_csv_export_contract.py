#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))

from scripts.validate_fao_fishstat_capture_csv_export_contract import validate


contract = root / "data/provenance/fao_fishstat_capture_csv_export_v1.toml"
result = validate(contract, root)
receipt = json.loads((root / "data/provenance/fao_fishstat_capture_csv_export_preregistration_20260902.json").read_text())
assert result == receipt
assert result["status"] == "preregistered_before_record_export"
assert result["column_count"] == 154
assert result["columns"][:6] == ["COUNTRY", "SPECIES", "AREA", "MEASURE", "VALUE_Y1950", "SYMBOL_Y1950"]
assert result["columns"][-2:] == ["VALUE_Y2024", "SYMBOL_Y2024"]
assert result["fishmip_calibration_authorized"] is False

with tempfile.TemporaryDirectory() as temporary:
    tampered = Path(temporary) / "contract.toml"
    tampered.write_text(contract.read_text().replace("annual_end_year = 2024", "annual_end_year = 2023"), encoding="utf-8")
    try:
        validate(tampered, root)
    except ValueError as error:
        assert "annual range" in str(error)
    else:
        raise AssertionError("changed annual range was accepted")

print("FishStat CSV export contract tests passed")
