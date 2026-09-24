#!/usr/bin/env python3
"""Reconstruct the status ledger directly from the reconciled full export."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import Counter, defaultdict
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
    parser.add_argument("--ledger-receipt", type=Path, required=True)
    parser.add_argument("--panel-receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), "fresh output required")
    ledger = json.loads(args.ledger_receipt.read_text(encoding="utf-8"))
    panel = json.loads(args.panel_receipt.read_text(encoding="utf-8"))
    require(ledger["schema"] == "fao_fishstat_marine_status_ledger/v1", "ledger receipt differs")
    full_source = Path(panel["sources"]["input"]["path"])
    require(digest(full_source) == panel["sources"]["input"]["sha256"], "full source hash differs")
    ledger_path = Path(ledger["output"]["path"])
    require(digest(ledger_path) == ledger["output"]["sha256"], "ledger hash differs")
    years = list(range(ledger["support"]["years"][0], ledger["support"]["years"][1] + 1))
    values: dict[tuple[int, str], list[float]] = defaultdict(list)
    cells: Counter[tuple[int, str]] = Counter()
    positive: Counter[tuple[int, str]] = Counter()
    selected = 0
    with full_source.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row["environment_class"] != "marine" or row["measure_code"] != "Q_tlw":
                continue
            selected += 1
            for year in years:
                status = row[f"status_{year}"]
                value = float(row[f"value_{year}"])
                values[(year, status)].append(value)
                cells[(year, status)] += 1
                positive[(year, status)] += value > 0
    require(selected == ledger["support"]["records"], "selected record count differs")
    compared = 0
    with ledger_path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            key = (int(row["year"]), row["status_code"])
            require(int(row["cells"]) == cells[key], f"cell count differs at {key}")
            require(int(row["positive_cells"]) == positive[key], f"positive count differs at {key}")
            require(float(row["tonnes_live_weight"]) == math.fsum(values[key]), f"tonnage differs at {key}")
            compared += 1
    require(compared == ledger["support"]["ledger_rows"], "ledger row count differs")
    result = {
        "schema": "fao_fishstat_marine_status_ledger_validation/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "pass",
        "scope": "independent reconstruction from the exact marine Q_tlw subsequence of the full reconciled export",
        "source": {"ledger_receipt": str(args.ledger_receipt), "ledger_receipt_sha256": digest(args.ledger_receipt), "full_export": str(full_source), "full_export_sha256": digest(full_source)},
        "validation": {"records_selected": selected, "ledger_rows_compared": compared, "cell_counts_exact": True, "positive_counts_exact": True, "tonnage_sums_exact": True},
        "claim_boundary": "status-ledger integrity only; no calibration selection, welfare, damage, or SCC gate is opened",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
