#!/usr/bin/env python3
"""Independently verify the marine panel is the exact filtered source subsequence."""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
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
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), "fresh validation output required")
    receipt = json.loads(args.receipt.read_text(encoding="utf-8"))
    require(receipt["schema"] == "fao_fishstat_marine_tonnage_panel/v1", "receipt differs")
    source_path = Path(receipt["sources"]["input"]["path"])
    panel_path = Path(receipt["output"]["path"])
    require(digest(source_path) == receipt["sources"]["input"]["sha256"], "source hash differs")
    require(digest(panel_path) == receipt["output"]["sha256"], "panel hash differs")

    selected = 0
    with source_path.open("r", encoding="utf-8", newline="") as source, gzip.open(panel_path, "rt", encoding="utf-8", newline="") as panel:
        source_reader = csv.DictReader(source)
        panel_reader = csv.DictReader(panel)
        require(source_reader.fieldnames == panel_reader.fieldnames, "header differs")
        panel_iterator = iter(panel_reader)
        for row in source_reader:
            if row["environment_class"] == "marine" and row["measure_code"] == "Q_tlw":
                observed = next(panel_iterator, None)
                require(observed is not None and observed == row, f"filtered row differs at {selected}")
                selected += 1
        require(next(panel_iterator, None) is None, "panel has extra rows")
    require(selected == receipt["support"]["records"], "record count differs")

    result = {
        "schema": "fao_fishstat_marine_tonnage_panel_validation/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "pass",
        "scope": "Every output field and row matches the exact ordered marine Q_tlw subsequence of the reconciled headless export.",
        "source": {"path": str(args.receipt), "sha256": digest(args.receipt)},
        "validation": {"records_compared": selected, "header_exact": True, "field_values_exact": True, "order_exact": True, "no_extra_rows": True},
        "claim_boundary": "source-panel integrity only; no allocation, calibration, welfare, damage, or SCC gate is opened",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
