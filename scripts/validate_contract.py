#!/usr/bin/env python3
"""Validate that the wetland feedback scaffold remains fail closed."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    cfg = json.loads((ROOT / "config/wetland_methane_feedback_contract_v1.json").read_text())
    bench = cfg["magicc_2026_benchmark"]
    checks = {
        "status_is_blocked": cfg["status"].startswith("BLOCKED_"),
        "integration_not_authorized": not cfg["scope"]["give_integration_authorized"],
        "scc_not_authorized": not cfg["scope"]["scc_adjustment_authorized"],
        "source_hash_matches": hashlib.sha256((ROOT / bench["source_path"]).read_bytes()).hexdigest() == bench["source_sha256"],
        "license_hash_matches": hashlib.sha256((ROOT / bench["license_path"]).read_bytes()).hexdigest() == bench["license_sha256"],
        "natural_not_fossil_target": "never fossil" in cfg["unit_contract"]["target_input"],
        "baseline_partition_gate_closed": not cfg["claim_gates"]["wetland_share_of_give_natural_baseline_identified"],
        "biogenic_gate_closed": not cfg["claim_gates"]["biogenic_methane_oxidation_routing_validated"]
    }
    receipt = {"schema": "wetland_methane_feedback_validation/v1", "checks": checks, "valid": all(checks.values())}
    (ROOT / "provenance/wetland_methane_validation_v1.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0 if receipt["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

