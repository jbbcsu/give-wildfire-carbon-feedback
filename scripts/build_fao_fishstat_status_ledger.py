#!/usr/bin/env python3
"""Build an annual status-preserving ledger from the marine tonnage panel."""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import math
import tomllib
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
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--panel-receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists() and not args.receipt.exists(), "fresh outputs required")
    contract = tomllib.loads(args.contract.read_text(encoding="utf-8"))
    panel = json.loads(args.panel_receipt.read_text(encoding="utf-8"))
    require(contract["schema"] == "fao_fishstat_capture_headless_export_contract_v1", "contract differs")
    require(panel["schema"] == "fao_fishstat_marine_tonnage_panel/v1", "panel receipt differs")
    source = Path(panel["output"]["path"])
    require(digest(source) == panel["output"]["sha256"], "panel hash differs")
    years = list(range(panel["support"]["years"][0], panel["support"]["years"][1] + 1))
    allowed = contract["export"]["required_status_codes"]
    tonnage: dict[tuple[int, str], list[float]] = defaultdict(list)
    cells: Counter[tuple[int, str]] = Counter()
    positive: Counter[tuple[int, str]] = Counter()
    records = 0
    with gzip.open(source, "rt", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            require(row["environment_class"] == "marine" and row["measure_code"] == "Q_tlw", "panel scope differs")
            for year in years:
                status = row[f"status_{year}"]
                value = float(row[f"value_{year}"])
                require(status in allowed and value >= 0, "invalid annual pair")
                tonnage[(year, status)].append(value)
                cells[(year, status)] += 1
                positive[(year, status)] += value > 0
            records += 1
    require(records == panel["support"]["records"], "record count differs")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    present_statuses = sorted({status for _, status in cells})
    with args.output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["year", "status_code", "cells", "positive_cells", "tonnes_live_weight"])
        writer.writeheader()
        for year in years:
            for status in present_statuses:
                writer.writerow({"year": year, "status_code": status, "cells": cells[(year, status)], "positive_cells": positive[(year, status)], "tonnes_live_weight": repr(math.fsum(tonnage[(year, status)]))})

    totals = {status: {"cells": sum(cells[(year, status)] for year in years), "positive_cells": sum(positive[(year, status)] for year in years), "tonnes_live_weight": math.fsum(value for year in years for value in tonnage[(year, status)])} for status in present_statuses}
    result = {
        "schema": "fao_fishstat_marine_status_ledger/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "annual_source_status_ledger_complete",
        "source": {"path": str(source), "sha256": digest(source), "receipt": str(args.panel_receipt), "receipt_sha256": digest(args.panel_receipt), "contract": str(args.contract), "contract_sha256": digest(args.contract)},
        "support": {"records": records, "years": [years[0], years[-1]], "statuses_present": present_statuses, "ledger_rows": len(years) * len(present_statuses)},
        "status_totals": totals,
        "output": {"path": str(args.output), "bytes": args.output.stat().st_size, "sha256": digest(args.output)},
        "claim_gates": {"status_composition_described": True, "calibration_status_selection": False, "fishmip_calibration": False, "welfare": False, "damage_or_scc": False},
        "limitations": ["The ledger preserves source status codes and does not choose which codes belong in calibration.", "Missing, suppressed, and not-significant cells remain distinct and are never reinterpreted as observed absence.", "Tonnage remains nominal vessel-flag landings rather than effort-adjusted biomass or EEZ production."],
        "implementation": {"path": str(Path(__file__).resolve().relative_to(Path(__file__).resolve().parents[1])), "sha256": digest(Path(__file__).resolve())},
    }
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "support": result["support"], "status_totals": totals}, indent=2))


if __name__ == "__main__":
    main()
