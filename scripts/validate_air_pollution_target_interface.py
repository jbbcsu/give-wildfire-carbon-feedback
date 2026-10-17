#!/usr/bin/env python3
"""Independently validate the fail-closed air-pollution target interface."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {
    "wildfire_smoke_pm25_mortality": (Decimal("50"), 2025, 2020),
    "surface_ozone_health": (Decimal("23"), 2030, 2024),
    "nonwildfire_meteorological_pm25_health": (Decimal("-38"), 2030, 2024),
    "meteorological_ozone_pm25_net": (Decimal("-15"), 2030, 2024),
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
    require(receipt["schema"] == "air_pollution_target_interface_receipt/v1", "bad receipt schema")
    require(receipt["config"]["sha256"] == sha256(config_path), "config hash mismatch")
    require(receipt["status"] == "price_harmonized_target_interface_blocked_from_give_addition", "bad status")
    gates = receipt["portfolio_gates"]
    require(gates["target_price_year_harmonized"] is True, "price-year gate not resolved")
    for gate in ("target_pulse_year_harmonized", "mortality_overlap_cleared",
                 "annual_marginal_paths_available", "all_components_locally_reproduced",
                 "any_component_additive_to_baseline_give"):
        require(gates[gate] is False, f"unsafe gate open: {gate}")

    deflator = root / "data/reference/bea/A191RD3A086NBEA.csv"
    with deflator.open(newline="", encoding="utf-8") as handle:
        values = {row["observation_date"][:4]: Decimal(row["A191RD3A086NBEA"])
                  for row in csv.DictReader(handle) if row["A191RD3A086NBEA"] != "."}
    factor = values["2020"] / values["2024"]
    require(str(factor) == receipt["price_conversion_factor_2024usd_to_2020usd"],
            "price conversion factor mismatch")

    table = root / receipt["output"]["path"]
    require(sha256(table) == receipt["output"]["sha256"], "table hash mismatch")
    with table.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    require(len(rows) == 4 and {row["component_id"] for row in rows} == set(EXPECTED),
            "unexpected component support")
    for row in rows:
        value, pulse_year, price_year = EXPECTED[row["component_id"]]
        expected_factor = Decimal("1") if price_year == 2020 else factor
        expected_target = (value * expected_factor).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
        require(Decimal(row["target_price_mean_usd_per_tco2"]) == expected_target,
                f"wrong conversion: {row['component_id']}")
        require(int(row["source_pulse_year"]) == pulse_year, "source pulse year changed")
        require(row["price_year_harmonized"] == "true", "price-year conversion not asserted")
        require((row["pulse_year_harmonized"] == "true") == (pulse_year == 2025),
                "pulse-year gate inconsistent")
        for field in ("mortality_overlap_cleared", "local_reproduction_passed",
                      "annual_marginal_paths_available", "additive_to_baseline_give"):
            require(row[field] == "false", f"unsafe row gate open: {field}")
        require("MORTALITY_OVERLAP_UNCLEARED" in row["blocker_codes"], "missing overlap blocker")
        if pulse_year != 2025:
            require("PULSE_YEAR_UNHARMONIZED" in row["blocker_codes"], "missing pulse blocker")
    return {
        "schema": "air_pollution_target_interface_validation/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "passed_price_harmonization_and_fail_closed_gates",
        "checks_passed": 48,
        "rows_validated": 4,
        "headline_addition_authorized": False,
        "inputs": {"config_sha256": sha256(config_path), "receipt_sha256": sha256(receipt_path),
                   "table_sha256": sha256(table), "deflator_sha256": sha256(deflator)},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--config", type=Path, default=Path("config/air_pollution_target_interface_v1.json"))
    parser.add_argument("--receipt", type=Path, default=Path("data/provenance/air_pollution_target_interface_v1.json"))
    args = parser.parse_args()
    root = args.root.resolve()
    config = args.config if args.config.is_absolute() else root / args.config
    receipt = args.receipt if args.receipt.is_absolute() else root / args.receipt
    result = validate(root, config, receipt)
    config_payload = json.loads(config.read_text(encoding="utf-8"))
    output = root / config_payload["outputs"]["validation"]
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "checks": result["checks_passed"]}))


if __name__ == "__main__":
    main()
