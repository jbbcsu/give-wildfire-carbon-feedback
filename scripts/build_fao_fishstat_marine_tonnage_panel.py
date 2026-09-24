#!/usr/bin/env python3
"""Build the lossless marine live-weight subset of the reconciled FAO export."""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import json
import tomllib
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--headless-validation", type=Path, required=True)
    parser.add_argument("--gui-reconciliation", type=Path, required=True)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists() and not args.receipt.exists(), "fresh outputs required")
    contract = tomllib.loads(args.contract.read_text(encoding="utf-8"))
    headless = json.loads(args.headless_validation.read_text(encoding="utf-8"))
    gui = json.loads(args.gui_reconciliation.read_text(encoding="utf-8"))
    require(contract["schema"] == "fao_fishstat_capture_headless_export_contract_v1", "contract differs")
    require(headless["schema"] == "fao_fishstat_capture_headless_export_validation_v1", "headless validation differs")
    require(gui["schema"] == "fao_fishstat_gui_headless_reconciliation_v1", "GUI reconciliation differs")
    require(gui["claim_gates"]["observed_capture_record_integrity_validated"], "record-integrity gate closed")
    require(gui["headless_export"]["sha256"] == headless["export"]["sha256"] == digest(args.input), "input identity differs")
    require(contract["export"]["allowed_environment_classes"] == ["inland", "marine"], "environment registry differs")
    require("Q_tlw" in contract["export"]["allowed_measure_codes"], "tonnage measure absent")

    rows = 0
    status_counts: Counter[str] = Counter()
    positive_cells = 0
    years = list(range(contract["source"]["annual_start_year"], contract["source"]["annual_end_year"] + 1))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.input.open("r", encoding="utf-8", newline="") as source, args.output.open("wb") as raw:
        reader = csv.DictReader(source)
        require(reader.fieldnames is not None, "input header absent")
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed, io.TextIOWrapper(compressed, encoding="utf-8", newline="") as text:
            writer = csv.DictWriter(text, fieldnames=reader.fieldnames, lineterminator="\n")
            writer.writeheader()
            for row in reader:
                if row["environment_class"] != "marine" or row["measure_code"] != "Q_tlw":
                    continue
                require(row["measure_name"] == "Tonnes - live weight" and row["unit"] == "t", "tonnage units differ")
                for year in years:
                    value = float(row[f"value_{year}"])
                    status = row[f"status_{year}"]
                    require(value >= 0 and status in contract["export"]["required_status_codes"], "invalid annual pair")
                    status_counts[status] += 1
                    positive_cells += value > 0
                writer.writerow(row)
                rows += 1
    require(rows == 27_625, "marine-tonnage record count differs")
    require(sum(status_counts.values()) == rows * len(years), "annual pair count differs")

    result = {
        "schema": "fao_fishstat_marine_tonnage_panel/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "lossless_reconciled_marine_live_weight_source_panel",
        "filter": {"environment_class": "marine", "measure_code": "Q_tlw", "measure_name": "Tonnes - live weight", "unit": "t"},
        "sources": {
            "input": {"path": str(args.input), "sha256": digest(args.input)},
            "contract": {"path": str(args.contract), "sha256": digest(args.contract)},
            "headless_validation": {"path": str(args.headless_validation), "sha256": digest(args.headless_validation)},
            "gui_reconciliation": {"path": str(args.gui_reconciliation), "sha256": digest(args.gui_reconciliation)},
        },
        "support": {"records": rows, "years": [years[0], years[-1]], "annual_value_status_pairs": rows * len(years), "positive_value_cells": positive_cells, "status_cells": dict(sorted(status_counts.items()))},
        "output": {"path": str(args.output), "bytes": args.output.stat().st_size, "sha256": digest(args.output), "compression": "gzip_mtime_zero"},
        "claim_gates": {"marine_tonnage_source_panel": True, "missing_statuses_preserved": True, "country_or_eez_allocation": False, "fishmip_calibration": False, "welfare": False, "damage_or_scc": False},
        "limitations": [
            "Country is primarily vessel flag rather than harvest EEZ or consumer incidence.",
            "Nominal landings exclude discards and do not identify effort, management, or climate causation.",
            "All source value/status pairs are preserved; this artifact does not recode missing values as zero or select admissible calibration statuses.",
        ],
        "implementation": {"path": str(Path(__file__).resolve().relative_to(Path(__file__).resolve().parents[1])), "sha256": digest(Path(__file__).resolve())},
    }
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "support": result["support"], "output": result["output"]}, indent=2))


if __name__ == "__main__":
    main()
