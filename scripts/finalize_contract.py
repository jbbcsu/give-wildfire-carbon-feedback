#!/usr/bin/env python3
"""Write a deterministic receipt for the fail-closed education audit."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main() -> int:
    cfg_path = ROOT / "config/education_heat_contract_v1.json"
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    evidence = ROOT / cfg["sources"]["evidence_registry"]["path"]
    receipt = {
        "schema": "education_heat_readiness_receipt/v1",
        "status": cfg["status"],
        "give_addition_authorized": cfg["scope"]["give_addition_authorized"],
        "lifetime_income_conversion_authorized": cfg["scope"]["lifetime_income_conversion_authorized"],
        "evidence_registry_sha256": digest(evidence),
        "failed_gates": sorted(k for k, value in cfg["claim_gates"].items() if value is False),
        "scc_output_created": False
    }
    out = ROOT / "provenance/education_heat_readiness_receipt_v1.json"
    out.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
