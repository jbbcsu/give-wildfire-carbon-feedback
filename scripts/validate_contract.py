#!/usr/bin/env python3
"""Validate the reported table and fail-closed integration gates."""
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main() -> int:
    cfg = json.loads((ROOT / "config/freshwater_angling_contract_v1.json").read_text())
    table = ROOT / cfg["reported_benchmark"]["path"]
    registry = ROOT / cfg["evidence_registry"]["path"]
    with table.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    reported = {(r["gcm"], r["endpoint"], r["rcp"]): float(r["cumulative_change_million_2015usd"]) for r in rows}
    results = ROOT / "results"
    checks = {
        "blocked_status": cfg["status"] == "BLOCKED_NO_MATCHED_MARGINAL_PATH_AND_RECREATION_OVERLAP_UNRESOLVED",
        "give_gate_closed": cfg["scope"]["give_addition_authorized"] is False,
        "global_transfer_closed": cfg["scope"]["global_transfer_authorized"] is False,
        "reported_table_hash": digest(table) == cfg["reported_benchmark"]["sha256"],
        "evidence_registry_hash": digest(registry) == cfg["evidence_registry"]["sha256"],
        "table_has_24_rows": len(rows) == 24,
        "published_all_fishing_means_match": reported[("five_gcm_average", "all_fishing", "RCP8.5")] == -45000 and reported[("five_gcm_average", "all_fishing", "RCP4.5")] == -38000,
        "one_reported_all_fishing_gain_retained": reported[("GISS-E2-R", "all_fishing", "RCP8.5")] == 680,
        "overlap_and_pulse_gates_closed": cfg["claim_gates"]["water_quality_recreation_overlap_resolved"] is False and cfg["claim_gates"]["matched_marginal_pulse_available"] is False,
        "no_scc_results": not (results.exists() and any(results.iterdir()))
    }
    report = {"schema": "freshwater_angling_contract_validation/v1", "status": "PASS" if all(checks.values()) else "FAIL", "checks": checks}
    out = ROOT / "provenance/freshwater_angling_validation_v1.json"
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if all(checks.values()) else 1

if __name__ == "__main__":
    raise SystemExit(main())
