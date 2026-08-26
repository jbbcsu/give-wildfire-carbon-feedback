#!/usr/bin/env python3
"""Synthetic fail-closed tests for bounded FAOSTAT value acquisition."""
from __future__ import annotations

import csv
import importlib.util
from pathlib import Path
import tempfile


PROJECT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "acquire_faostat_qv_maize_soy",
    PROJECT / "scripts" / "acquire_faostat_qv_maize_soy.py",
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

assert "item_code=56" in MODULE.query_url(56)
assert "sql_url=" in MODULE.query_url(56)


def row(year: int, item_code: int = 56, item: str = "Maize (corn)") -> dict[str, str]:
    result = {field: "" for field in MODULE.REQUIRED_COLUMNS}
    result.update(
        {
            "faostat": "231",
            "m49_code": "840",
            "country_name_en": "United States of America",
            "item_code": str(item_code),
            "item": item,
            "year": str(year),
            MODULE.CONSTANT_USD: "1000.0",
            MODULE.CONSTANT_USD_FLAG: "Estimated value",
            MODULE.CURRENT_USD: "900.0",
            MODULE.CURRENT_USD_FLAG: "Official value",
        }
    )
    return result


with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    path = root / "response.csv"
    fixture = [row(1961), row(1999), row(2000), row(2001), row(2024)]
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=MODULE.REQUIRED_COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(fixture)
    rows, audit = MODULE.validate_response(path, 56)
    assert len(rows) == 5
    assert audit["year_min"] == 1961 and audit["year_max"] == 2024
    assert audit["baseline_1999_2001_constant_usd_nonmissing_rows"] == 3
    canonical = MODULE.write_canonical(rows, root / "canonical.csv")
    assert canonical["rows"] == 5 and canonical["size_bytes"] > 0

    fixture.append(row(2000))
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=MODULE.REQUIRED_COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(fixture)
    try:
        MODULE.validate_response(path, 56)
    except ValueError as error:
        assert "Duplicate" in str(error)
    else:
        raise AssertionError("Duplicate M49-item-year key was accepted")

    bad = [row(1961), row(2024)]
    bad[1][MODULE.CONSTANT_USD] = "-1"
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=MODULE.REQUIRED_COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(bad)
    try:
        MODULE.validate_response(path, 56)
    except ValueError as error:
        assert "negative" in str(error)
    else:
        raise AssertionError("Negative production value was accepted")

print("FAOSTAT QV acquisition tests passed")
