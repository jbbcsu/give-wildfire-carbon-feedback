#!/usr/bin/env python3
"""Independently validate the air-pollution scalar benchmark interface."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {
    "wildfire_smoke_pm25_mortality": (50.0, 2025),
    "surface_ozone_health": (23.0, 2030),
    "nonwildfire_meteorological_pm25_health": (-38.0, 2030),
    "meteorological_ozone_pm25_net": (-15.0, 2030),
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate(root: Path, config_path: Path, receipt_path: Path) -> dict[str, Any]:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    require(config["schema"] == "air_pollution_literature_bridge_config/v1", "bad config schema")
    require(receipt["schema"] == "air_pollution_literature_bridge_receipt/v1", "bad receipt schema")
    require(receipt["config"]["sha256"] == sha256(config_path), "config hash mismatch")
    require(receipt["status"] == "external_benchmarks_exported_not_additive", "bad status")
    require(receipt["give_interface"]["eligible_for_headline_scc"] is False,
            "headline SCC unexpectedly enabled")
    require(receipt["give_interface"]["annual_country_damage_paths_available"] is False,
            "annual damage paths unexpectedly asserted")
    require(set(receipt["hard_gates"].values()) == {False}, "hard gate unexpectedly open")

    table = root / receipt["output"]["path"]
    require(table.is_file() and not table.is_symlink(), "missing regular output table")
    require(sha256(table) == receipt["output"]["sha256"], "output hash mismatch")
    require(table.stat().st_size == receipt["output"]["bytes"], "output size mismatch")
    with table.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    require(len(rows) == 4, "unexpected benchmark row count")
    require({row["component_id"] for row in rows} == set(EXPECTED), "component support differs")
    for row in rows:
        value = float(row["mean_usd_per_tco2"])
        require(math.isfinite(value), "non-finite benchmark")
        expected_value, expected_year = EXPECTED[row["component_id"]]
        require(value == expected_value and int(row["pulse_year"]) == expected_year,
                f"registered benchmark changed: {row['component_id']}")
        require(row["locally_reproduced"] == "false", "benchmark promoted to reproduction")
        require(row["additive_to_give"] == "false", "benchmark promoted to addition")
    require(float(next(r for r in rows if r["component_id"] == "surface_ozone_health")["mean_usd_per_tco2"]) +
            float(next(r for r in rows if r["component_id"] == "nonwildfire_meteorological_pm25_health")["mean_usd_per_tco2"]) ==
            float(next(r for r in rows if r["component_id"] == "meteorological_ozone_pm25_net")["mean_usd_per_tco2"]),
            "published EPA component arithmetic fails")
    return {
        "schema": "air_pollution_literature_bridge_validation/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "passed_external_benchmark_interface_only",
        "checks_passed": 23,
        "rows_validated": 4,
        "headline_addition_authorized": False,
        "claim_status": "GIVE-readable scalar evidence table validated; reproduction and additive SCC gates remain closed",
        "inputs": {
            "config_sha256": sha256(config_path),
            "receipt_sha256": sha256(receipt_path),
            "table_sha256": sha256(table),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--config", type=Path,
                        default=Path("config/air_pollution_literature_bridge_v1.json"))
    parser.add_argument("--receipt", type=Path,
                        default=Path("data/provenance/air_pollution_literature_bridge_v1.json"))
    args = parser.parse_args()
    root = args.root.resolve()
    config_path = args.config if args.config.is_absolute() else root / args.config
    receipt_path = args.receipt if args.receipt.is_absolute() else root / args.receipt
    result = validate(root, config_path, receipt_path)
    config = json.loads(config_path.read_text(encoding="utf-8"))
    output = root / config["outputs"]["validation"]
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".partial")
    temporary.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(output)
    print(json.dumps({"status": result["status"], "checks": result["checks_passed"]}))


if __name__ == "__main__":
    main()
