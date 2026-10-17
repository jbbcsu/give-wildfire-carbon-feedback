#!/usr/bin/env python3
"""Fail-closed validation of winter-recreation benchmark outputs."""
import csv, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def read(path):
    with path.open(newline="", encoding="utf-8") as f: return list(csv.DictReader(f))

def main():
    cfg = json.loads((ROOT / "config/winter_recreation_benchmark_v1.json").read_text())
    annual = read(ROOT / cfg["outputs"]["annual"]); by_gcm = read(ROOT / cfg["outputs"]["by_gcm"]); summary = read(ROOT / cfg["outputs"]["summary"])
    checks = {
        "annual_rows_4968": len(annual) == 276 * 6 * 3,
        "by_gcm_rows_12": len(by_gcm) == 12,
        "summary_rows_8": len(summary) == 8,
        "activities_complete": {r["activity"] for r in annual} == {"Alpine", "XC", "Snowmobiling"},
        "years_complete": {int(r["year"]) for r in annual} == set(range(2025, 2301)),
        "finite_summary": all(abs(float(r["mean_2020usd_per_tco2"])) < 100 for r in summary),
        "nonadditive_gate": all(r["additive_to_give"] == "false" for r in summary),
        "claim_gate": cfg["scope"]["additivity_to_give_authorized"] is False and cfg["scope"]["consumer_surplus"] == "NOT_ESTIMATED"
    }
    out = {"schema": "winter_recreation_validation/v1", "status": "PASS" if all(checks.values()) else "FAIL", "checks": checks}
    path = ROOT / cfg["outputs"]["validation"]; path.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    print(json.dumps(out, indent=2)); return 0 if all(checks.values()) else 1

if __name__ == "__main__": raise SystemExit(main())
