#!/usr/bin/env python3
import csv
import json
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def rows(path):
    with (ROOT / path).open() as stream: return list(csv.DictReader(stream))


def main():
    c = json.loads((ROOT / "config/conflict_crime_benchmark_v1.json").read_text())
    a, g, s = rows(c["outputs"]["annual"]), rows(c["outputs"]["by_gcm"]), rows(c["outputs"]["summary"])
    assert len(a) == 3312 and len(g) == 12 and len(s) == 6
    assert {row["impact_type"] for row in a} == {"Property", "Violent"}
    assert all(row["additive_to_give"] == "false" for row in s)
    assert all(row["uses_response_extrapolation"] == "false" for row in a if int(row["year"]) <= 2092)
    full = next(row for row in s if row["horizon"] == "2300" and row["component"] == "Total")
    bounded = next(row for row in s if row["horizon"] == "2092" and row["component"] == "Total")
    assert abs(Decimal(full["mean_2020usd_per_tco2"]) - Decimal("0.0192652745")) < Decimal("1e-9")
    assert abs(Decimal(bounded["mean_2020usd_per_tco2"]) - Decimal("0.0129063795")) < Decimal("1e-9")
    assert c["scope"]["organized_armed_conflict"] == "BLOCKED_NO_SCC"
    result = {"schema": "crime_partial_scc_validation/v1", "status": "PASS", "checks": {"annual_rows": 3312, "gcm_rows": 12, "summary_rows": 6, "numeric_sentinel": True, "nonadditivity_gate": True, "armed_conflict_gate": True}}
    (ROOT / c["outputs"]["validation"]).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2)); return 0


if __name__ == "__main__": raise SystemExit(main())
