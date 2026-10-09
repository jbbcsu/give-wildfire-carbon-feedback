#!/usr/bin/env python3
"""Fail-closed structural checks for the Moore et al. published GTAP arrays."""

from __future__ import annotations

import csv
import hashlib
import json
import math
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT
    / "vendor"
    / "moore_2026"
    / "lrennels-paper-2026-give-labor-ag-5d034e7"
)
GTAP = SOURCE / "data" / "gtap_output"
OUT = ROOT / "data" / "provenance" / "published_damage_array_validation_20261009.json"
DEGREES = {1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_rows(path: Path) -> list[dict[str, str]]:
    # The published CSVs contain Latin-1/Windows-1252 country-name glyphs.
    with path.open(newline="", encoding="cp1252") as stream:
        return list(csv.DictReader(stream))


def finite(row: dict[str, str], columns: tuple[str, ...]) -> bool:
    return all(math.isfinite(float(row[column])) for column in columns)


def validate_agriculture(path: Path) -> dict[str, object]:
    rows = read_rows(path)
    keys = [(r["Country"], r["Degrees"], r["Percentile"]) for r in rows]
    countries = {r["Country"] for r in rows}
    degrees = {float(r["Degrees"]) for r in rows}
    percentiles = {r["Percentile"] for r in rows}
    counts = Counter(r["Country"] for r in rows)
    checks = {
        "rows_equal_160x7x3": len(rows) == 160 * 7 * 3,
        "countries_equal_160": len(countries) == 160,
        "degrees_match_knots": degrees == DEGREES,
        "percentiles_match": percentiles == {"2.50%", "50.00%", "97.50%"},
        "keys_unique": len(keys) == len(set(keys)),
        "balanced_panel": set(counts.values()) == {21},
        "numeric_values_finite": all(
            finite(
                row,
                (
                    "Welfare_in_M_USD",
                    "Valueadded_in_M_USD",
                    "Initial_Income_in_M_USD",
                ),
            )
            for row in rows
        ),
    }
    return {
        "path": str(path.relative_to(ROOT)),
        "sha256": sha256(path),
        "rows": len(rows),
        "countries": len(countries),
        "degrees": sorted(degrees),
        "percentiles": sorted(percentiles),
        "checks": checks,
    }


def validate_labor(path: Path, expected_shock: str) -> dict[str, object]:
    rows = read_rows(path)
    keys = [(r["Country"], r["Degrees"], r["GCM"]) for r in rows]
    countries = {r["Country"] for r in rows}
    degrees = {float(r["Degrees"]) for r in rows}
    gcms = {r["GCM"] for r in rows}
    counts = Counter(r["Country"] for r in rows)
    max_decomposition_error = max(
        abs(
            float(r["Welfare_in_M_USD"])
            - float(r["ST_AG_Welfare_in_M_USD"])
            - float(r["ST_NONAG_Welfare_in_M_USD"])
        )
        for r in rows
    )
    checks = {
        "rows_equal_160x7x16": len(rows) == 160 * 7 * 16,
        "countries_equal_160": len(countries) == 160,
        "degrees_match_knots": degrees == DEGREES,
        "gcms_equal_16": len(gcms) == 16,
        "keys_unique": len(keys) == len(set(keys)),
        "balanced_panel": set(counts.values()) == {112},
        "labor_shock_matches_file": {r["Labor Shock"] for r in rows}
        == {expected_shock},
        "numeric_values_finite": all(
            finite(
                row,
                (
                    "ST_AG_Welfare_in_M_USD",
                    "ST_NONAG_Welfare_in_M_USD",
                    "Welfare_in_M_USD",
                    "Valueadded_in_M_USD",
                    "Initial_Income_in_M_USD",
                ),
            )
            for row in rows
        ),
    }
    return {
        "path": str(path.relative_to(ROOT)),
        "sha256": sha256(path),
        "rows": len(rows),
        "countries": len(countries),
        "degrees": sorted(degrees),
        "gcms": sorted(gcms),
        "max_welfare_decomposition_error_musd": max_decomposition_error,
        "decomposition_note": (
            "Diagnostic only: the published loader uses the ST_AG and ST_NONAG "
            "columns directly and does not use Welfare_in_M_USD. Exact additivity "
            "is therefore not imposed as a validation gate."
        ),
        "checks": checks,
    }


def main() -> None:
    results = {
        "schema": "published_damage_array_validation/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_doi": "10.5281/zenodo.21483095",
        "agriculture": validate_agriculture(
            GTAP / "202505_Plants_People_Agriculture.csv"
        ),
        "labor_iso": validate_labor(
            GTAP / "20260428_Plants_People_results_v4_ISO_Revision.csv", "ISO"
        ),
        "labor_lancet": validate_labor(
            GTAP / "20260428_Plants_People_results_v4_Lancet_Revision.csv",
            "Lancet",
        ),
    }
    all_checks = [
        value
        for section in ("agriculture", "labor_iso", "labor_lancet")
        for value in results[section]["checks"].values()
    ]
    results["status"] = "pass" if all(all_checks) else "fail"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(results, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": results["status"], "checks": len(all_checks)}))
    if results["status"] != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
