#!/usr/bin/env python3
"""Validate source pins and fail-closed claim gates."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main() -> int:
    cfg = json.loads((ROOT / "config/permafrost_feedback_contract_v1.json").read_text())
    receipt = json.loads((ROOT / "provenance/permafrost_feedback_readiness_receipt_v1.json").read_text())
    give = cfg["give_audit"]
    results = ROOT / "results"
    checks = {
        "blocked_status": cfg["status"] == "BLOCKED_RECURSION_EMISSIONS_BOUNDARY_AND_ARTIFACT_GATES",
        "integration_gate_closed": cfg["scope"]["give_integration_authorized"] is False,
        "scc_gate_closed": cfg["scope"]["scc_adjustment_authorized"] is False,
        "vendored_sources_match": receipt["vendored_hashes_match"],
        "give_source_hashes_match": all(digest((ROOT / give[key]).resolve()) == give[key.replace("_path", "_sha256")] for key in ("co2_cycle_path", "ch4_cycle_path", "main_model_path")),
        "mechanical_checks_pass": all(receipt["mechanical_checks"].values()),
        "artifact_discrepancies_remain_explicit": receipt["parameter_count_reconciled"] is False and receipt["decay_argument_used_in_released_species_function"] is False,
        "critical_recursion_gates_closed": all(cfg["claim_gates"][key] is False for key in ("biogenic_ch4_routing_validated", "one_year_recursive_ordering_validated", "common_random_number_pulse_convergence_validated")),
        "no_result_output": not (results.exists() and any(results.iterdir()))
    }
    report = {"schema": "permafrost_feedback_contract_validation/v1", "status": "PASS" if all(checks.values()) else "FAIL", "checks": checks}
    out = ROOT / "provenance/permafrost_feedback_validation_v1.json"
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if all(checks.values()) else 1

if __name__ == "__main__":
    raise SystemExit(main())
