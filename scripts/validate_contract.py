#!/usr/bin/env python3
"""Validate provenance and fail-closed claim gates."""
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main() -> int:
    cfg = json.loads((ROOT / "config/education_heat_contract_v1.json").read_text(encoding="utf-8"))
    evidence = ROOT / cfg["sources"]["evidence_registry"]["path"]
    with evidence.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    result_files = list((ROOT / "results").glob("*")) if (ROOT / "results").exists() else []
    checks = {
        "blocked_status": cfg["status"] == "BLOCKED_NO_DEFENSIBLE_VALUATION_OR_MATCHED_CLIMATE_LINK",
        "give_gate_closed": cfg["scope"]["give_addition_authorized"] is False,
        "global_gate_closed": cfg["scope"]["global_extrapolation_authorized"] is False,
        "earnings_conversion_forbidden": cfg["scope"]["lifetime_income_conversion_authorized"] is False,
        "evidence_hash": digest(evidence) == cfg["sources"]["evidence_registry"]["sha256"],
        "four_primary_studies": len(rows) == 4,
        "all_studies_have_doi": all(row["doi"] for row in rows),
        "critical_overlap_gates_closed": all(cfg["claim_gates"][key] is False for key in (
            "labor_productivity_overlap_resolved", "macroeconomic_growth_overlap_resolved",
            "adaptation_costs_separable_from_give_energy")),
        "no_result_output": not result_files
    }
    report = {"schema": "education_heat_contract_validation/v1", "status": "PASS" if all(checks.values()) else "FAIL", "checks": checks}
    out = ROOT / "provenance/education_heat_validation_v1.json"
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if all(checks.values()) else 1

if __name__ == "__main__":
    raise SystemExit(main())
