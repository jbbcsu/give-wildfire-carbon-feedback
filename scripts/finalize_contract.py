#!/usr/bin/env python3
"""Hash evidence and emit a machine-readable fail-closed readiness receipt."""
import csv, hashlib, json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config/heat_morbidity_contract_v1.json"

def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    cfg = json.loads(CONFIG.read_text())
    evidence = ROOT / cfg["sources"]["lay_2018"]["reported_evidence"]
    with evidence.open(newline="", encoding="utf-8") as f: rows = list(csv.DictReader(f))
    if len(rows) != 4: raise ValueError("expected four published Lay et al. scenario/year rows")
    actual = digest(evidence)
    expected = cfg["sources"]["lay_2018"]["sha256"]
    if expected != "PENDING" and expected != actual: raise ValueError("reported evidence hash mismatch")
    cfg["sources"]["lay_2018"]["sha256"] = actual
    CONFIG.write_text(json.dumps(cfg, indent=2, sort_keys=True) + "\n")
    receipt = {
        "schema": "heat_morbidity_readiness_receipt/v1", "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": cfg["status"], "numeric_scc_produced": False, "give_addition_authorized": False,
        "evidence_sha256": actual, "reported_rows": len(rows),
        "highest_value_next_step": "Request released fitted response objects from Gould et al. and Lay et al.; otherwise secure HCAI access and re-estimate."
    }
    out = ROOT / "provenance/heat_morbidity_readiness_receipt_v1.json"
    out.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps(receipt, indent=2)); return 0

if __name__ == "__main__": raise SystemExit(main())
