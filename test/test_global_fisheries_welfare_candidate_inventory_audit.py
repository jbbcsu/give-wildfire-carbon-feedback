#!/usr/bin/env python3
"""Focused tests for the non-synthetic candidate-inventory metadata audit."""

from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "scripts"
AUDITOR_PATH = SCRIPT_DIR / "audit_global_fisheries_welfare_candidate_inventory.py"
SCHEMA_PATH = ROOT / "config/global_fisheries_welfare_bridge_input_contract_v1.schema.json"
TEMPLATE_PATH = ROOT / "templates/global_fisheries_welfare_bridge_candidate_inventory_v1.json"
sys.path.insert(0, str(SCRIPT_DIR))
spec = importlib.util.spec_from_file_location("candidate_inventory_audit", AUDITOR_PATH)
assert spec and spec.loader
auditor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(auditor)


schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
template = json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))


blank_result = auditor.audit_inventory(template, schema, TEMPLATE_PATH, SCHEMA_PATH)
assert blank_result["metadata_status"] == "incomplete_candidate_inventory"
assert blank_result["component_summary"] == {
    "total": 7,
    "ready_for_scientific_review": 0,
    "blocked": 7,
}
assert blank_result["source_summary"]["count"] == 0
assert all(value is False for value in blank_result["authorizations"].values())
assert "explicit_spdx_license_missing" in blank_result["declaration_defects"]["bundle_license"]
assert len(blank_result["provenance"]["inventory_file_sha256"]) == 64
assert len(blank_result["provenance"]["audited_json_canonical_sha256"]) == 64
assert all(
    "component_not_provided" in component["defects"]
    and "no_source_references" in component["defects"]
    for component in blank_result["components"]
)


test_only_partial = copy.deepcopy(template)
test_only_partial["bundle_id"] = "candidate:test-only-partial-metadata"
test_only_partial["sources"] = [{
    "source_id": "test-only-license-source",
    "role": "license",
    "version": "test-only-v1",
    "uri": "https://example.invalid/test-only-license",
    "sha256": "0" * 64,
    "license": {
        "spdx_id": "CC0-1.0",
        "redistribution_allowed": True,
        "derivatives_allowed": True,
    },
}]
license_component = next(
    item for item in test_only_partial["request_components"]
    if item["component_id"] == "license_and_reuse"
)
license_component["provided"] = True
license_component["source_ids"] = ["test-only-license-source"]
partial_result = auditor.audit_inventory(test_only_partial, schema, TEMPLATE_PATH, SCHEMA_PATH)
assert partial_result["component_summary"] == {
    "total": 7,
    "ready_for_scientific_review": 1,
    "blocked": 6,
}
assert partial_result["metadata_status"] == "incomplete_candidate_inventory"
assert all(value is False for value in partial_result["authorizations"].values())


bad_license = copy.deepcopy(test_only_partial)
bad_license["sources"][0]["license"]["spdx_id"] = "NOASSERTION"
bad_result = auditor.audit_inventory(bad_license, schema, TEMPLATE_PATH, SCHEMA_PATH)
assert bad_result["component_summary"]["ready_for_scientific_review"] == 0
assert "referenced_source_provenance_incomplete" in next(
    item for item in bad_result["components"]
    if item["component_id"] == "license_and_reuse"
)["defects"]


synthetic = copy.deepcopy(template)
synthetic["synthetic_only"] = True
try:
    auditor.audit_inventory(synthetic, schema, TEMPLATE_PATH, SCHEMA_PATH)
except ValueError as error:
    assert "non-synthetic inventories only" in str(error)
else:
    raise AssertionError("synthetic inventory was not rejected")


duplicate = copy.deepcopy(template)
duplicate["request_components"][1]["component_id"] = duplicate["request_components"][0]["component_id"]
try:
    auditor.audit_inventory(duplicate, schema, TEMPLATE_PATH, SCHEMA_PATH)
except ValueError as error:
    assert "duplicated request component" in str(error)
else:
    raise AssertionError("duplicated component was not rejected")


print("Global fisheries candidate inventory audit tests passed")
