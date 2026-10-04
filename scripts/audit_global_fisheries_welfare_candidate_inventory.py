#!/usr/bin/env python3
"""Audit a real-candidate inventory without validating data or estimating welfare.

This is an admission/deficiency audit only.  It checks the seven requested
components and their provenance metadata, but deliberately does not validate
response, incidence, or welfare rows.  It never authorizes coefficient
transfer, fitting, damages, aggregation, discounting, or an SCC.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any

from validate_global_fisheries_welfare_bridge_contract import (
    COMPONENT_ROLES,
    CONTRACT_VERSION,
    OVERLAP_FLAGS,
    REQUEST_COMPONENTS,
    validate_schema_identity,
)


ROOT = Path(__file__).resolve().parents[1]
SOURCE_FIELDS = {"source_id", "role", "version", "uri", "sha256", "license"}
LICENSE_FIELDS = {"spdx_id", "redistribution_allowed", "derivatives_allowed"}
FORBIDDEN_LICENSE_IDS = {"", "UNSET", "NOASSERTION", "NONE"}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_json_sha256(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def license_defects(value: Any) -> list[str]:
    if not isinstance(value, dict) or set(value) != LICENSE_FIELDS:
        return ["license_fields_incomplete_or_changed"]
    defects: list[str] = []
    spdx_id = value.get("spdx_id")
    if not isinstance(spdx_id, str) or spdx_id.strip().upper() in FORBIDDEN_LICENSE_IDS:
        defects.append("explicit_spdx_license_missing")
    if value.get("redistribution_allowed") is not True:
        defects.append("redistribution_not_explicitly_allowed")
    if value.get("derivatives_allowed") is not True:
        defects.append("derivative_use_not_explicitly_allowed")
    return defects


def source_defects(source: Any, valid_roles: set[str]) -> list[str]:
    if not isinstance(source, dict) or set(source) != SOURCE_FIELDS:
        return ["source_fields_incomplete_or_changed"]
    defects: list[str] = []
    if not isinstance(source.get("source_id"), str) or not source["source_id"].strip():
        defects.append("source_id_missing")
    if source.get("role") not in valid_roles:
        defects.append("source_role_unknown")
    if not isinstance(source.get("version"), str) or not source["version"].strip():
        defects.append("source_version_missing")
    if not isinstance(source.get("uri"), str) or not source["uri"].strip():
        defects.append("source_uri_missing")
    if not isinstance(source.get("sha256"), str) or re.fullmatch(r"[0-9a-f]{64}", source["sha256"]) is None:
        defects.append("source_sha256_invalid")
    defects.extend(license_defects(source.get("license")))
    return defects


def audit_inventory(
    inventory: dict[str, Any],
    schema: dict[str, Any],
    inventory_path: Path,
    schema_path: Path,
) -> dict[str, Any]:
    """Return a fail-closed metadata audit for a non-synthetic candidate."""
    validate_schema_identity(schema)
    require(isinstance(inventory, dict), "inventory must be a JSON object")
    require(set(inventory) == set(schema["required"]), "inventory top-level fields changed or are incomplete")
    require(inventory.get("contract_version") == CONTRACT_VERSION, "wrong contract version")
    require(inventory.get("synthetic_only") is False, "candidate audit accepts non-synthetic inventories only")
    require(
        inventory.get("authorization") == {
            "purpose": "candidate_inventory_only_no_validation_or_estimation",
            "coefficient_transfer": False,
            "fit": False,
            "damage": False,
            "scc": False,
        },
        "candidate authorization must forbid transfer, fit, damage, and SCC",
    )
    require(
        isinstance(inventory.get("bundle_id"), str)
        and re.fullmatch(r"candidate:[A-Za-z0-9._-]+", inventory["bundle_id"]) is not None,
        "bundle_id must use a nonblank candidate: namespace",
    )

    for name in ("sources", "request_components", "responses", "incidence", "welfare"):
        require(isinstance(inventory.get(name), list), f"{name} must be a list")

    valid_roles = set().union(*COMPONENT_ROLES.values())
    source_by_id: dict[str, dict[str, Any]] = {}
    source_audits: dict[str, list[str]] = {}
    duplicate_source_ids: set[str] = set()
    for index, source in enumerate(inventory["sources"]):
        defects = source_defects(source, valid_roles)
        source_id = source.get("source_id") if isinstance(source, dict) else None
        audit_id = source_id if isinstance(source_id, str) and source_id else f"<source[{index}]>"
        if audit_id in source_by_id:
            duplicate_source_ids.add(audit_id)
            defects.append("source_id_duplicated")
            source_audits[audit_id].append("source_id_duplicated")
        else:
            if isinstance(source, dict):
                source_by_id[audit_id] = source
            source_audits[audit_id] = defects

    components = inventory["request_components"]
    require(len(components) == 7, "exactly seven request components are required")
    component_by_id: dict[str, dict[str, Any]] = {}
    for component in components:
        require(
            isinstance(component, dict)
            and set(component) == {"component_id", "provided", "source_ids"},
            "request component fields changed or are incomplete",
        )
        component_id = component["component_id"]
        require(component_id in REQUEST_COMPONENTS, f"unknown request component: {component_id}")
        require(component_id not in component_by_id, f"duplicated request component: {component_id}")
        require(isinstance(component["provided"], bool), f"{component_id} provided must be boolean")
        require(isinstance(component["source_ids"], list), f"{component_id} source_ids must be a list")
        component_by_id[component_id] = component
    require(set(component_by_id) == REQUEST_COMPONENTS, "seven-part request is incomplete")

    component_results: list[dict[str, Any]] = []
    for component_id in sorted(REQUEST_COMPONENTS):
        component = component_by_id[component_id]
        refs = component["source_ids"]
        defects: list[str] = []
        if component["provided"] is not True:
            defects.append("component_not_provided")
        if not refs:
            defects.append("no_source_references")
        if len(refs) != len(set(refs)):
            defects.append("duplicate_source_reference")
        if not all(isinstance(ref, str) and ref for ref in refs):
            defects.append("invalid_source_reference")
        unknown_refs = sorted({ref for ref in refs if ref not in source_by_id})
        if unknown_refs:
            defects.append("unknown_source_reference")
        referenced_sources = [source_by_id[ref] for ref in refs if ref in source_by_id]
        observed_roles = {source.get("role") for source in referenced_sources}
        if not COMPONENT_ROLES[component_id].issubset(observed_roles):
            defects.append("required_source_role_missing")
        if any(ref in duplicate_source_ids or source_audits.get(ref) for ref in refs):
            defects.append("referenced_source_provenance_incomplete")
        component_results.append({
            "component_id": component_id,
            "metadata_status": "ready_for_scientific_review" if not defects else "blocked",
            "defects": sorted(set(defects)),
            "source_ids": refs,
        })

    bundle_license_defects = license_defects(inventory.get("license"))
    coverage = inventory.get("coverage")
    coverage_declared = coverage == {
        "scope": "global_declared_support",
        "complete": True,
        "missing_semantics": "explicit_no_imputation_or_renormalization",
    }
    pulse = inventory.get("pulse")
    pulse_declared = (
        isinstance(pulse, dict)
        and pulse.get("gas") == "CO2"
        and isinstance(pulse.get("mass"), (int, float))
        and not isinstance(pulse.get("mass"), bool)
        and math.isfinite(float(pulse["mass"]))
        and float(pulse["mass"]) == 1.0
        and pulse.get("mass_unit") == "tCO2"
        and pulse.get("counterfactual") == "same_realization_baseline"
        and isinstance(pulse.get("pulse_id"), str)
        and bool(pulse["pulse_id"])
    )
    overlap = inventory.get("overlap")
    overlap_declared = (
        isinstance(overlap, dict)
        and overlap.get("review_status") == "passed"
        and isinstance(overlap.get("accounting_boundary_id"), str)
        and bool(overlap["accounting_boundary_id"])
        and isinstance(overlap.get("trade_closure_id"), str)
        and bool(overlap["trade_closure_id"])
        and all(overlap.get(flag) is False for flag in OVERLAP_FLAGS)
    )
    all_components_ready = all(item["metadata_status"] == "ready_for_scientific_review" for item in component_results)
    all_sources_clean = bool(source_by_id) and not duplicate_source_ids and not any(source_audits.values())
    metadata_ready = (
        all_components_ready
        and not bundle_license_defects
        and all_sources_clean
        and coverage_declared
        and pulse_declared
        and overlap_declared
    )

    return {
        "audit_kind": "candidate_inventory_metadata_only_no_scientific_validation",
        "contract_version": CONTRACT_VERSION,
        "bundle_id": inventory["bundle_id"],
        "provenance": {
            "inventory_path": str(inventory_path.resolve()),
            "inventory_file_sha256": file_sha256(inventory_path),
            "audited_json_canonical_sha256": canonical_json_sha256(inventory),
            "schema_path": str(schema_path.resolve()),
            "schema_sha256": file_sha256(schema_path),
        },
        "component_summary": {
            "total": len(component_results),
            "ready_for_scientific_review": sum(item["metadata_status"] == "ready_for_scientific_review" for item in component_results),
            "blocked": sum(item["metadata_status"] == "blocked" for item in component_results),
        },
        "components": component_results,
        "source_summary": {
            "count": len(inventory["sources"]),
            "all_provenance_complete": all_sources_clean,
            "defects_by_source_id": source_audits,
        },
        "declaration_gates": {
            "bundle_license_reuse_declared": not bundle_license_defects,
            "global_coverage_and_missingness_declared": coverage_declared,
            "marginal_pulse_manifest_declared": pulse_declared,
            "overlap_boundary_declared": overlap_declared,
        },
        "declaration_defects": {
            "bundle_license": bundle_license_defects,
            "coverage": [] if coverage_declared else ["global_complete_support_or_missingness_semantics_not_declared"],
            "pulse": [] if pulse_declared else ["one_tCO2_same_realization_pulse_manifest_not_declared"],
            "overlap": [] if overlap_declared else ["passed_separable_accounting_boundary_not_declared"],
        },
        "unchecked_scientific_rows": {
            "responses": len(inventory["responses"]),
            "incidence": len(inventory["incidence"]),
            "welfare": len(inventory["welfare"]),
        },
        "metadata_status": "ready_for_separate_scientific_review" if metadata_ready else "incomplete_candidate_inventory",
        "authorizations": {
            "scientific_validation": False,
            "coefficient_transfer": False,
            "fit": False,
            "damage": False,
            "aggregation": False,
            "discounting": False,
            "scc": False,
        },
        "constraint": "Metadata readiness is not scientific validity; row semantics, matching, conservation, units, coverage, and overlap still require a separately authorized production validator.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inventory", type=Path)
    parser.add_argument(
        "--schema",
        type=Path,
        default=ROOT / "config/global_fisheries_welfare_bridge_input_contract_v1.schema.json",
    )
    args = parser.parse_args()
    schema = json.loads(args.schema.read_text(encoding="utf-8"))
    inventory = json.loads(args.inventory.read_text(encoding="utf-8"))
    print(json.dumps(audit_inventory(inventory, schema, args.inventory, args.schema), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
