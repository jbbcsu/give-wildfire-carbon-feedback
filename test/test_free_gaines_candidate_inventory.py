#!/usr/bin/env python3
"""Cross-check the partial Free/Gaines inventory against the pinned source audit."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "scripts"
AUDITOR_PATH = SCRIPT_DIR / "audit_global_fisheries_welfare_candidate_inventory.py"
SCHEMA_PATH = ROOT / "config/global_fisheries_welfare_bridge_input_contract_v1.schema.json"
INVENTORY_PATH = ROOT / "data/provenance/free_gaines_welfare_bridge_candidate_inventory_20261004.json"
SOURCE_AUDIT_PATH = ROOT / "data/provenance/alternative_global_fisheries_welfare_audit_20260928.json"
sys.path.insert(0, str(SCRIPT_DIR))
spec = importlib.util.spec_from_file_location("candidate_inventory_audit", AUDITOR_PATH)
assert spec and spec.loader
auditor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(auditor)


schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
inventory = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
source_audit = json.loads(SOURCE_AUDIT_PATH.read_text(encoding="utf-8"))
candidate_source = inventory["sources"][0]
pinned_audit = source_audit["closest_candidate_source_audit"]
pinned_script = pinned_audit["pinned_files"]["format_script"]

# No metadata value is inferred: the immutable version and digest must match
# the earlier audit of the real repository checkout exactly.
assert candidate_source["version"] == pinned_audit["commit"]
assert candidate_source["sha256"] == pinned_script["sha256"]
assert pinned_script["path"] == "code/Step1_format_gaines_data.R"
assert candidate_source["uri"].endswith(
    f"/{pinned_audit['commit']}/{pinned_script['path']}"
)
assert pinned_audit["root_license_files"] == []

# The one evidenced script is only downstream formatting code.  It is not
# promoted to a complete executable-model component, and absent material is
# left absent rather than fabricated.
executable_component = next(
    component for component in inventory["request_components"]
    if component["component_id"] == "executable_model_and_dependency_lock"
)
assert executable_component == {
    "component_id": "executable_model_and_dependency_lock",
    "provided": False,
    "source_ids": [candidate_source["source_id"]],
}
assert inventory["responses"] == []
assert inventory["incidence"] == []
assert inventory["welfare"] == []

result = auditor.audit_inventory(inventory, schema, INVENTORY_PATH, SCHEMA_PATH)
assert result["component_summary"] == {
    "total": 7,
    "ready_for_scientific_review": 0,
    "blocked": 7,
}
assert result["metadata_status"] == "incomplete_candidate_inventory"
assert result["source_summary"]["count"] == 1
assert set(result["source_summary"]["defects_by_source_id"][candidate_source["source_id"]]) == {
    "explicit_spdx_license_missing",
    "redistribution_not_explicitly_allowed",
    "derivative_use_not_explicitly_allowed",
}
executable_result = next(
    component for component in result["components"]
    if component["component_id"] == "executable_model_and_dependency_lock"
)
assert set(executable_result["defects"]) == {
    "component_not_provided",
    "required_source_role_missing",
    "referenced_source_provenance_incomplete",
}
assert all(value is False for value in result["declaration_gates"].values())
assert all(value is False for value in result["authorizations"].values())

print("Free/Gaines partial candidate inventory remains evidence-pinned and fail-closed")
