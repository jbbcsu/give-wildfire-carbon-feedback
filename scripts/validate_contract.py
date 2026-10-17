#!/usr/bin/env python3
"""Validate fail-closed Amazon feedback integration claims."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    cfg = json.loads((ROOT / "config/amazon_dieback_feedback_contract_v1.json").read_text())
    checks = {
        "status_is_blocked": cfg["status"].startswith("BLOCKED_"),
        "integration_not_authorized": not cfg["scope"]["give_integration_authorized"],
        "scc_not_authorized": not cfg["scope"]["scc_adjustment_authorized"],
        "all_unlock_gates_not_accidentally_open": not all(cfg["claim_gates"].values()),
        "meta_source_hash_matches": hashlib.sha256((ROOT / cfg["meta_2021"]["source_path"]).read_bytes()).hexdigest() == cfg["meta_2021"]["source_sha256"],
        "combined_epa_scalar_forbidden": any("combined EPA" in item for item in cfg["forbidden_claims"])
    }
    receipt = {"schema": "amazon_dieback_feedback_validation/v1", "checks": checks, "valid": all(checks.values())}
    (ROOT / "provenance/amazon_feedback_validation_v1.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0 if receipt["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

