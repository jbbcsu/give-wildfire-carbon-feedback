#!/usr/bin/env python3
"""Fail if the blocked morbidity evidence is mislabeled or an SCC result appears."""
import csv, hashlib, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    cfg = json.loads((ROOT / "config/heat_morbidity_contract_v1.json").read_text())
    evidence = ROOT / cfg["sources"]["lay_2018"]["reported_evidence"]
    with evidence.open(newline="", encoding="utf-8") as f: rows = list(csv.DictReader(f))
    forbidden = list((ROOT / "results").glob("*scc*.csv"))
    checks = {
        "blocked_status": cfg["status"] == "BLOCKED_NO_MARGINAL_SCC",
        "give_gate_closed": cfg["scope"]["give_addition_authorized"] is False,
        "evidence_hash": digest(evidence) == cfg["sources"]["lay_2018"]["sha256"],
        "reported_rows_exact": len(rows) == 4,
        "direct_cost_columns_only": "meps_direct_medical_cost_million_2015usd" in rows[0] and "wages" not in rows[0],
        "no_scc_output": not forbidden,
        "all_required_gates_explicit": all(k in cfg["claim_gates"] for k in ("marginal_climate_response_available", "direct_medical_cost_separable", "consumer_welfare_separable", "adaptation_scenario_available"))
    }
    result = {"schema": "heat_morbidity_contract_validation/v1", "status": "PASS" if all(checks.values()) else "FAIL", "checks": checks}
    path = ROOT / "provenance/heat_morbidity_validation_v1.json"; path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2)); return 0 if all(checks.values()) else 1

if __name__ == "__main__": raise SystemExit(main())
