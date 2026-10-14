"""Fail-closed validator for the municipal-water fast-route evidence screen.

This validates only audit structure and evidence bindings. It never downloads
model data, estimates damages, allocates multisector welfare, or computes SCC.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


SCREEN_SCHEMA = "municipal_water_fast_route_screen_v1"
RECEIPT_SCHEMA = "municipal_water_source_receipts_v1"
REQUIRED_GATES = {
    "climate_response",
    "annual_welfare_paths",
    "geographic_coverage",
    "uncertainty",
    "marginal_pulse_compatibility",
    "license",
    "overlap_boundary",
}
EXPECTED_INCLUDED = {
    "municipal_and_household_water_supply_reliability",
    "municipal_water_supply_treatment_pumping_storage_and_conveyance_cost",
}
EXPECTED_EXCLUDED = {
    "give_agriculture_crop_yield_and_market_damages",
    "give_energy_demand_and_supply_damages",
    "ciam_coastal_flooding_and_protection",
    "irrigation_and_livestock_water_impacts",
    "manufacturing_water_impacts",
    "primary_energy_and_electricity_water_impacts",
    "hydropower_impacts",
    "inland_flood_capital_and_displacement_impacts",
    "water_recreation_ecosystem_and_nonuse_values",
}
STATES = {"pass", "partial", "fail"}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def exact(value: Any, fields: set[str], label: str) -> dict[str, Any]:
    require(isinstance(value, dict), f"{label} must be an object")
    require(set(value) == fields, f"{label} fields changed or are incomplete")
    return value


def nonblank(value: Any, label: str) -> str:
    require(isinstance(value, str) and value.strip(), f"{label} must be nonblank")
    return value


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as stream:
        value = json.load(stream)
    require(isinstance(value, dict), f"{path} must contain an object")
    return value


def validate_receipts(receipts: dict[str, Any]) -> set[str]:
    exact(receipts, {"schema", "audit_date", "receipts", "network_scope"}, "receipt document")
    require(receipts["schema"] == RECEIPT_SCHEMA, "receipt schema changed")
    nonblank(receipts["audit_date"], "receipt audit_date")
    rows = receipts["receipts"]
    require(isinstance(rows, list) and rows, "source receipts are absent")
    evidence_ids: set[str] = set()
    for index, row in enumerate(rows):
        exact(
            row,
            {"evidence_id", "source_type", "title", "locator", "revision", "license", "verified_facts"},
            f"receipt[{index}]",
        )
        evidence_id = nonblank(row["evidence_id"], f"receipt[{index}].evidence_id")
        require(evidence_id not in evidence_ids, f"duplicate evidence ID {evidence_id}")
        evidence_ids.add(evidence_id)
        for field in ("source_type", "title", "locator", "revision", "license"):
            nonblank(row[field], f"receipt[{index}].{field}")
        require(
            row["source_type"] in {
                "peer_reviewed_primary",
                "official_author_repository",
                "official_repository_archive",
                "official_model_release",
                "official_model_documentation",
                "official_source_report",
            },
            f"receipt[{index}] is not a primary or official source type",
        )
        facts = row["verified_facts"]
        require(isinstance(facts, list) and facts, f"receipt[{index}] lacks verified facts")
        require(all(isinstance(item, str) and item.strip() for item in facts), f"receipt[{index}] has blank facts")

    scope = exact(receipts["network_scope"], {"metadata_and_small_text_only", "large_artifacts_downloaded", "model_runs_performed"}, "network_scope")
    require(scope == {"metadata_and_small_text_only": True, "large_artifacts_downloaded": False, "model_runs_performed": False}, "network scope exceeds a bounded screen")
    return evidence_ids


def validate_screen(screen: dict[str, Any], evidence_ids: set[str]) -> dict[str, Any]:
    exact(
        screen,
        {
            "schema", "audit_date", "authorization", "required_gates",
            "municipal_overlap_boundary", "candidate_order", "candidates", "decision",
        },
        "screen",
    )
    require(screen["schema"] == SCREEN_SCHEMA, "screen schema changed")
    nonblank(screen["audit_date"], "screen audit_date")

    authorization = exact(
        screen["authorization"],
        {
            "purpose", "download_large_artifacts", "estimate_coefficients",
            "impute_or_allocate", "calculate_damage_function", "calculate_or_promote_scc",
        },
        "authorization",
    )
    require(authorization["purpose"] == "source_and_transfer_feasibility_only", "audit purpose changed")
    require(all(authorization[field] is False for field in authorization if field != "purpose"), "audit authorizes estimation, allocation, download, or SCC")
    require(set(screen["required_gates"]) == REQUIRED_GATES and len(screen["required_gates"]) == len(REQUIRED_GATES), "seven transfer gates changed")

    boundary = exact(
        screen["municipal_overlap_boundary"],
        {"included", "excluded", "allocation_or_renormalization_allowed", "cross_sector_surplus_attribution_allowed"},
        "municipal_overlap_boundary",
    )
    require(set(boundary["included"]) == EXPECTED_INCLUDED, "municipal included boundary changed")
    require(set(boundary["excluded"]) == EXPECTED_EXCLUDED, "municipal overlap exclusions are incomplete")
    require(boundary["allocation_or_renormalization_allowed"] is False, "allocation or renormalization must be forbidden")
    require(boundary["cross_sector_surplus_attribution_allowed"] is False, "cross-sector surplus attribution must be forbidden")

    candidates = screen["candidates"]
    require(isinstance(candidates, list) and candidates, "candidate screen is empty")
    observed: dict[str, bool] = {}
    for index, candidate in enumerate(candidates):
        exact(
            candidate,
            {
                "candidate_id", "sector", "role", "release", "published_endpoint",
                "spatial_temporal_support", "gates", "ready_for_give",
                "exact_blocker", "forbidden_shortcut",
            },
            f"candidate[{index}]",
        )
        candidate_id = nonblank(candidate["candidate_id"], f"candidate[{index}].candidate_id")
        require(candidate_id not in observed, f"duplicate candidate {candidate_id}")
        for field in ("sector", "role", "published_endpoint", "spatial_temporal_support", "exact_blocker", "forbidden_shortcut"):
            nonblank(candidate[field], f"candidate[{index}].{field}")
        release = exact(candidate["release"], {"version", "revision", "license_summary"}, f"candidate[{index}].release")
        for field in release:
            nonblank(release[field], f"candidate[{index}].release.{field}")

        gates = candidate["gates"]
        require(isinstance(gates, dict) and set(gates) == REQUIRED_GATES, f"candidate {candidate_id} gate set changed")
        all_pass = True
        for gate_name, gate in gates.items():
            exact(gate, {"state", "evidence_ids", "reason"}, f"candidate {candidate_id}.{gate_name}")
            require(gate["state"] in STATES, f"candidate {candidate_id}.{gate_name} state is invalid")
            all_pass = all_pass and gate["state"] == "pass"
            bound_ids = gate["evidence_ids"]
            require(isinstance(bound_ids, list) and bound_ids, f"candidate {candidate_id}.{gate_name} lacks evidence")
            require(all(item in evidence_ids for item in bound_ids), f"candidate {candidate_id}.{gate_name} cites unknown evidence")
            nonblank(gate["reason"], f"candidate {candidate_id}.{gate_name}.reason")
        require(isinstance(candidate["ready_for_give"], bool), f"candidate {candidate_id} readiness must be boolean")
        require(candidate["ready_for_give"] == all_pass, f"candidate {candidate_id} readiness disagrees with its gates")
        observed[candidate_id] = all_pass

    order = screen["candidate_order"]
    require(isinstance(order, list) and order == list(observed), "candidate order must exactly match unique candidate records")

    decision = exact(
        screen["decision"],
        {"qualifying_candidate_count", "lead_candidate", "result", "fastest_defensible_next_step", "external_benchmark_only"},
        "decision",
    )
    qualifying = sum(observed.values())
    require(decision["qualifying_candidate_count"] == qualifying, "qualifying candidate count is inconsistent")
    require(decision["lead_candidate"] in observed, "lead candidate is unknown")
    require(decision["result"] == "no_transferable_municipal_water_or_inland_flood_module", "negative screen result changed")
    require(qualifying == 0, "this evidence version must not open a scientific or SCC gate")
    nonblank(decision["fastest_defensible_next_step"], "decision.fastest_defensible_next_step")
    nonblank(decision["external_benchmark_only"], "decision.external_benchmark_only")
    return {
        "schema": SCREEN_SCHEMA,
        "candidates": len(candidates),
        "qualifying_candidates": qualifying,
        "scc_calculated": False,
        "result": decision["result"],
    }


def validate_files(screen_path: Path, receipt_path: Path) -> dict[str, Any]:
    receipts = load_json(receipt_path)
    evidence_ids = validate_receipts(receipts)
    screen = load_json(screen_path)
    return validate_screen(screen, evidence_ids)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("screen", type=Path)
    parser.add_argument("receipts", type=Path)
    args = parser.parse_args()
    try:
        result = validate_files(args.screen, args.receipts)
    except (OSError, json.JSONDecodeError, ValueError) as error:
        print(json.dumps({"valid": False, "error": str(error)}, sort_keys=True))
        return 1
    print(json.dumps({"valid": True, **result}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
