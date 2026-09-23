#!/usr/bin/env python3
"""Reconcile the independent FishStatJ GUI export with the headless extract."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sqlite3
import tempfile
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path


YEARS = list(range(1950, 2025))
DISPLAY_SYMBOL = {
    "A": "",
    "O": "...",
    "N": "N",
    "I": "I",
    "E": "E",
    "Q": "Q",
    "X": "X",
    "P": "P",
}


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def require_gui_precision(text: str) -> None:
    require(text != "", "blank GUI numeric value")
    fractional = text.partition(".")[2]
    require(len(fractional) <= 2, f"GUI value has more than two decimals: {text}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gui", type=Path, required=True)
    parser.add_argument("--headless", type=Path, required=True)
    parser.add_argument("--headless-validation", type=Path, required=True)
    parser.add_argument("--scratch-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.scratch_dir.mkdir(parents=True, exist_ok=True)

    expected_header = [
        "Country (Name)", "ASFIS species (Name)",
        "FAO major fishing area (Name)", "Unit (Name)", "Unit",
    ] + [item for year in YEARS for item in (f"[{year}]", "S")]
    gui_rows = 0
    totals: dict[str, list[str]] = {}
    citation = None
    gui_status_counts: Counter[str] = Counter()

    with tempfile.TemporaryDirectory(prefix="fishstat_gui_reconcile_", dir=args.scratch_dir) as temporary:
        database = sqlite3.connect(Path(temporary) / "gui.sqlite")
        database.execute(
            "CREATE TABLE gui (country TEXT, species TEXT, area TEXT, measure TEXT, payload TEXT, "
            "PRIMARY KEY (country, species, area, measure)) WITHOUT ROWID"
        )
        with args.gui.open("r", encoding="utf-8-sig", newline="") as stream:
            reader = csv.reader(stream)
            header = next(reader)
            require(header == expected_header, "GUI export header changed")
            for row in reader:
                require(row, "blank GUI export row")
                if row[0].startswith("Totals - "):
                    require(len(row) == len(expected_header), "GUI total row width changed")
                    measure = row[0].removeprefix("Totals - ")
                    require(measure not in totals, "duplicate GUI total row")
                    totals[measure] = [row[5 + 2 * index] for index in range(len(YEARS))]
                    continue
                if row[0].startswith("FAO. "):
                    require(citation is None and len(row) == 1, "GUI citation row changed")
                    citation = row[0]
                    continue
                require(len(row) == len(expected_header), "GUI data row width changed")
                require(row[4] == "TLW, Number", "GUI selected-unit annotation changed")
                key = tuple(row[:4])
                payload = row[5:]
                for index in range(len(YEARS)):
                    require(payload[2 * index] != "", "GUI annual value is blank")
                    gui_status_counts[payload[2 * index + 1]] += 1
                try:
                    database.execute("INSERT INTO gui VALUES (?, ?, ?, ?, ?)", (*key, json.dumps(payload)))
                except sqlite3.IntegrityError as error:
                    raise ValueError(f"duplicate GUI key: {key}") from error
                gui_rows += 1
        database.commit()

        require(set(totals) == {"Tonnes - live weight", "Number"}, "GUI total rows changed")
        require(citation is not None and "Licence: CC-BY-4.0" in citation, "GUI citation/license row changed")

        headless_rows = 0
        matched_cells = 0
        scientific_name_fallback_records = 0
        rounded_value_cells = 0
        maximum_absolute_display_rounding = Decimal(0)
        headless_status_counts: Counter[str] = Counter()
        status_display_crosswalk: Counter[tuple[str, str]] = Counter()
        headless_totals = {measure: [Decimal(0) for _ in YEARS] for measure in totals}
        with args.headless.open("r", encoding="utf-8", newline="") as stream:
            reader = csv.DictReader(stream)
            for row in reader:
                species_display = row["species_name"]
                if not species_display:
                    species_display = f"[{row['species_scientific_name']}]"
                    scientific_name_fallback_records += 1
                key = (row["country_name"], species_display, row["fao_area_name"], row["measure_name"])
                found = database.execute(
                    "SELECT payload FROM gui WHERE country=? AND species=? AND area=? AND measure=?", key
                ).fetchone()
                require(found is not None, f"headless key missing from GUI export: {key}")
                payload = json.loads(found[0])
                for index, year in enumerate(YEARS):
                    headless_value = Decimal(row[f"value_{year}"])
                    gui_text = payload[2 * index]
                    require_gui_precision(gui_text)
                    gui_value = Decimal(gui_text)
                    rounding = abs(headless_value - gui_value)
                    require(rounding <= Decimal("0.005"), f"display-value mismatch for {key}, {year}")
                    rounded_value_cells += rounding != 0
                    maximum_absolute_display_rounding = max(maximum_absolute_display_rounding, rounding)
                    status = row[f"status_{year}"]
                    symbol = payload[2 * index + 1]
                    require(status in DISPLAY_SYMBOL, f"unregistered headless status {status}")
                    require(symbol == DISPLAY_SYMBOL[status], f"symbol mismatch for {key}, {year}: {status}/{symbol}")
                    headless_status_counts[status] += 1
                    status_display_crosswalk[status, symbol] += 1
                    headless_totals[row["measure_name"]][index] += headless_value
                    matched_cells += 1
                database.execute(
                    "DELETE FROM gui WHERE country=? AND species=? AND area=? AND measure=?", key
                )
                headless_rows += 1
        require(database.execute("SELECT COUNT(*) FROM gui").fetchone()[0] == 0, "GUI has unmatched data rows")
        database.close()

    for measure, values in totals.items():
        for index, year in enumerate(YEARS):
            require_gui_precision(values[index])
            require(abs(Decimal(values[index]) - headless_totals[measure][index]) <= Decimal("0.005"),
                    f"display-total mismatch: {measure}, {year}")

    reference = json.loads(args.headless_validation.read_text())
    require(reference["records"] == gui_rows == headless_rows == 30918, "record-count reconciliation failed")
    require(reference["annual_cells"] == matched_cells == 2318850, "annual-cell reconciliation failed")
    require(reference["status_cells"] == dict(sorted(headless_status_counts.items())), "headless status receipt changed")

    result = {
        "schema": "fao_fishstat_gui_headless_reconciliation_v1",
        "status": "independent_gui_export_exactly_reconciled",
        "validated_at_utc": datetime.now(timezone.utc).isoformat(),
        "gui_export": {"path": str(args.gui), "bytes": args.gui.stat().st_size, "sha256": digest(args.gui)},
        "headless_export": {"path": str(args.headless), "bytes": args.headless.stat().st_size, "sha256": digest(args.headless)},
        "headless_validation": {"path": str(args.headless_validation), "sha256": digest(args.headless_validation)},
        "records": gui_rows,
        "scientific_name_fallback_records": scientific_name_fallback_records,
        "annual_value_status_pairs": matched_cells,
        "value_reconciliation": {
            "rule": "FishStatJ GUI exports at most two displayed decimals; every displayed value and total is within 0.005 of the source-precision headless value",
            "exact_unrounded_cells": matched_cells - rounded_value_cells,
            "display_rounded_cells": rounded_value_cells,
            "maximum_absolute_display_rounding": str(maximum_absolute_display_rounding),
        },
        "years": [YEARS[0], YEARS[-1]],
        "gui_footer_rows": 3,
        "gui_status_symbol_counts": dict(sorted(gui_status_counts.items())),
        "headless_status_counts": dict(sorted(headless_status_counts.items())),
        "status_display_crosswalk": [
            {"headless_status": status, "gui_symbol": symbol, "cells": count}
            for (status, symbol), count in sorted(status_display_crosswalk.items())
        ],
        "total_rows_reconciled": sorted(totals),
        "claim_gates": {
            "fishstat_gui_menu_export_reconciled": True,
            "observed_capture_record_integrity_validated": True,
            "marine_tonnage_filter_authorized": False,
            "country_or_eez_allocation_authorized": False,
            "fishmip_observed_calibration_authorized": False,
            "welfare_translation_authorized": False,
            "damage_or_scc_authorized": False,
        },
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result["claim_gates"], sort_keys=True))


if __name__ == "__main__":
    main()
