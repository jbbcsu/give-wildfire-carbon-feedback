#!/usr/bin/env python3
"""Fail-closed checks for the inland-flood benchmark outputs."""

import csv
import json
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def rows(path: str):
    with (ROOT / path).open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def main() -> int:
    config = json.loads((ROOT / "config/inland_flood_scc_v1.json").read_text())
    annual = rows(config["outputs"]["annual_national"])
    summary = rows(config["outputs"]["summary"])
    states = rows(config["outputs"]["by_state"])
    assert len(annual) == 276 and len(summary) == 3 and len(states) == 49
    assert [int(row["horizon"]) for row in summary] == [2092, 2246, 2300]
    state_sum = sum(Decimal(row["partial_scc_2020usd_per_tco2"]) for row in states)
    national = Decimal(summary[-1]["partial_scc_2020usd_per_tco2"])
    assert abs(state_sum - national) < Decimal("1e-10")
    assert all(row["uses_response_extrapolation"] == "false" for row in annual if int(row["year"]) <= 2246)
    assert any(row["uses_response_extrapolation"] == "true" for row in annual if int(row["year"]) > 2246)
    primary = Decimal(summary[-1]["partial_scc_2020usd_per_tco2"])
    assert Decimal("0.014") < primary < Decimal("0.015")
    exclusions = set(config["scope"]["excluded"])
    assert {"coastal surge and sea-level rise", "pluvial flooding and urban drainage", "roads and rail"} <= exclusions
    validation = {
        "schema": "inland_flood_partial_scc_validation/v1",
        "status": "PASS",
        "checks": {
            "annual_rows": len(annual), "jurisdictions": len(states),
            "state_sum_equals_national": True, "bounded_support_gate": True,
            "scope_exclusions_present": True, "primary_range_sentinel": True
        }
    }
    out = ROOT / config["outputs"]["validation"]
    out.write_text(json.dumps(validation, indent=2, sort_keys=True) + "\n")
    print(json.dumps(validation, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
