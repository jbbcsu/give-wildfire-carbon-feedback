#!/usr/bin/env python3
"""Ensure the blank real-candidate inventory remains blank and fail-closed."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "templates/global_fisheries_welfare_bridge_candidate_inventory_v1.json"
VALIDATOR = ROOT / "scripts/validate_global_fisheries_welfare_bridge_contract.py"
EXPECTED_COMPONENTS = {
    "license_and_reuse",
    "raw_model_inputs",
    "executable_model_and_dependency_lock",
    "incidence_and_geographic_keys",
    "consumer_and_producer_surplus",
    "matched_marginal_pulse",
    "overlap_accounting_boundary",
}


inventory = json.loads(TEMPLATE.read_text(encoding="utf-8"))
assert inventory["contract_version"] == "global_fisheries_welfare_bridge_input_v1"
assert inventory["synthetic_only"] is False
assert inventory["authorization"]["purpose"] == "candidate_inventory_only_no_validation_or_estimation"
assert not any(inventory["authorization"][key] for key in ("coefficient_transfer", "fit", "damage", "scc"))
assert {item["component_id"] for item in inventory["request_components"]} == EXPECTED_COMPONENTS
assert all(item["provided"] is False and item["source_ids"] == [] for item in inventory["request_components"])
assert inventory["sources"] == []
assert inventory["responses"] == []
assert inventory["incidence"] == []
assert inventory["welfare"] == []

result = subprocess.run(
    ["python3", str(VALIDATOR), str(TEMPLATE)],
    text=True,
    capture_output=True,
)
assert result.returncode != 0
assert "current validator accepts synthetic contract tests only" in result.stderr

print("Global fisheries candidate inventory template remains blank and fail-closed")
