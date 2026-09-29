#!/usr/bin/env python3
"""Validate synthetic inputs against the global fisheries welfare bridge contract.

This validator deliberately rejects non-synthetic bundles. It performs no fit,
damage calculation, discounting, aggregation into GIVE, or SCC calculation.
"""

from __future__ import annotations

import argparse
import json
import math
import re
from collections import defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_VERSION = "global_fisheries_welfare_bridge_input_v1"
SCHEMA_ID = "https://give.local/contracts/global-fisheries-welfare-bridge-input-v1.schema.json"
REQUEST_COMPONENTS = {
    "license_and_reuse",
    "raw_model_inputs",
    "executable_model_and_dependency_lock",
    "incidence_and_geographic_keys",
    "consumer_and_producer_surplus",
    "matched_marginal_pulse",
    "overlap_accounting_boundary",
}
COMPONENT_ROLES = {
    "license_and_reuse": {"license"},
    "raw_model_inputs": {"raw_input"},
    "executable_model_and_dependency_lock": {"model_code", "dependency_lock"},
    "incidence_and_geographic_keys": {"incidence"},
    "consumer_and_producer_surplus": {"demand", "producer_cost"},
    "matched_marginal_pulse": {"pulse"},
    "overlap_accounting_boundary": {"overlap_review"},
}
OVERLAP_FLAGS = (
    "includes_aquaculture",
    "includes_terrestrial_food_market_welfare",
    "includes_nutrition_or_mortality",
    "includes_coral_or_reef_services",
    "includes_biodiversity_nonuse_value",
    "includes_ciam_coastal_impacts",
    "includes_indirect_or_induced_output",
    "uses_gross_revenue_as_welfare",
)
MATCHED_IDENTIFIERS = (
    "climate_model_id",
    "ecosystem_model_id",
    "management_scenario",
    "socioeconomic_scenario",
    "harvest_unit",
    "coverage_status",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def finite_number(value: Any, label: str, nonnegative: bool = False) -> float:
    require(isinstance(value, (int, float)) and not isinstance(value, bool), f"{label} must be numeric")
    number = float(value)
    require(math.isfinite(number), f"{label} must be finite")
    if nonnegative:
        require(number >= 0, f"{label} must be nonnegative")
    return number


def validate_license(value: Any, label: str) -> None:
    require(isinstance(value, dict), f"{label} must be an object")
    require(set(value) == {"spdx_id", "redistribution_allowed", "derivatives_allowed"}, f"{label} fields changed")
    require(isinstance(value["spdx_id"], str) and value["spdx_id"].strip() not in {"", "NOASSERTION", "NONE"}, f"{label} lacks an explicit SPDX license")
    require(value["redistribution_allowed"] is True, f"{label} does not allow redistribution")
    require(value["derivatives_allowed"] is True, f"{label} does not allow derivative use")


def validate_schema_identity(schema: dict[str, Any]) -> None:
    require(schema.get("$schema") == "https://json-schema.org/draft/2020-12/schema", "unexpected JSON Schema dialect")
    require(schema.get("$id") == SCHEMA_ID, "contract schema id changed")
    properties = schema.get("properties", {})
    require(properties.get("contract_version", {}).get("const") == CONTRACT_VERSION, "contract version changed")
    request_enum = set(schema["$defs"]["request_component"]["properties"]["component_id"]["enum"])
    require(request_enum == REQUEST_COMPONENTS, "seven-part request component set changed")


def validate_object_shape(value: Any, schema: dict[str, Any], definition: str, label: str) -> None:
    require(isinstance(value, dict), f"{label} must be an object")
    rule = schema["$defs"][definition]
    require(set(value) == set(rule["required"]), f"{label} fields changed or are incomplete")


def validate_bundle(bundle: dict[str, Any], schema: dict[str, Any], tolerance: float = 1e-9) -> dict[str, Any]:
    validate_schema_identity(schema)
    require(isinstance(bundle, dict), "bundle must be a JSON object")
    expected_top = set(schema["required"])
    require(set(bundle) == expected_top, "bundle top-level fields changed or are incomplete")
    require(bundle["contract_version"] == CONTRACT_VERSION, "wrong contract version")
    require(bundle["synthetic_only"] is True, "current validator accepts synthetic contract tests only")
    require(isinstance(bundle["bundle_id"], str) and re.fullmatch(r"synthetic:[A-Za-z0-9._-]+", bundle["bundle_id"]), "bundle_id must use the synthetic: namespace")

    authorization = bundle["authorization"]
    require(authorization == {
        "purpose": "synthetic_contract_test_only",
        "coefficient_transfer": False,
        "fit": False,
        "damage": False,
        "scc": False,
    }, "authorization must forbid transfer, fit, damage, and SCC")
    validate_license(bundle["license"], "bundle license")

    coverage = bundle["coverage"]
    require(coverage == {
        "scope": "global_declared_support",
        "complete": True,
        "missing_semantics": "explicit_no_imputation_or_renormalization",
    }, "global coverage or missingness contract is not closed")

    pulse = bundle["pulse"]
    require(set(pulse) == set(schema["properties"]["pulse"]["required"]), "pulse fields changed or are incomplete")
    require(pulse.get("gas") == "CO2" and pulse.get("mass_unit") == "tCO2", "pulse must use tCO2")
    require(finite_number(pulse.get("mass"), "pulse mass") == 1.0, "pulse mass must be exactly one tCO2")
    require(pulse.get("counterfactual") == "same_realization_baseline", "pulse requires the same-realization baseline")
    require(isinstance(pulse.get("pulse_id"), str) and pulse["pulse_id"], "pulse_id must be nonblank")

    sources = bundle["sources"]
    require(isinstance(sources, list) and sources, "sources must be nonempty")
    source_ids: set[str] = set()
    source_roles: dict[str, str] = {}
    for index, source in enumerate(sources):
        label = f"source[{index}]"
        require(isinstance(source, dict), f"{label} must be an object")
        required = {"source_id", "role", "version", "uri", "sha256", "license"}
        require(set(source) == required, f"{label} fields changed")
        require(source["source_id"] not in source_ids and source["source_id"], f"{label} source_id is blank or duplicated")
        source_ids.add(source["source_id"])
        require(source["role"] in {"license", "raw_input", "model_code", "dependency_lock", "incidence", "demand", "producer_cost", "pulse", "overlap_review"}, f"{label} has unknown role")
        source_roles[source["source_id"]] = source["role"]
        require(isinstance(source["version"], str) and source["version"], f"{label} version must be nonblank")
        require(isinstance(source["uri"], str) and source["uri"].startswith("synthetic://"), f"{label} must use a synthetic URI")
        require(isinstance(source["sha256"], str) and re.fullmatch(r"[0-9a-f]{64}", source["sha256"]), f"{label} sha256 is invalid")
        validate_license(source["license"], f"{label} license")

    components = bundle["request_components"]
    require(isinstance(components, list) and len(components) == 7, "exactly seven request components are required")
    observed_components: set[str] = set()
    for component in components:
        require(set(component) == {"component_id", "provided", "source_ids"}, "request component fields changed")
        component_id = component["component_id"]
        require(component_id in REQUEST_COMPONENTS and component_id not in observed_components, "request component is unknown or duplicated")
        observed_components.add(component_id)
        require(component["provided"] is True, f"request component {component_id} is not provided")
        refs = component["source_ids"]
        require(isinstance(refs, list) and refs and len(refs) == len(set(refs)), f"request component {component_id} needs unique source references")
        require(set(refs).issubset(source_ids), f"request component {component_id} references an unknown source")
        require(COMPONENT_ROLES[component_id].issubset({source_roles[source_id] for source_id in refs}), f"request component {component_id} lacks its required source role")
    require(observed_components == REQUEST_COMPONENTS, "seven-part request is incomplete")

    responses = bundle["responses"]
    require(isinstance(responses, list) and responses, "responses must be nonempty")
    response_groups: dict[tuple[Any, ...], dict[str, dict[str, Any]]] = defaultdict(dict)
    for index, row in enumerate(responses):
        validate_object_shape(row, schema, "response", f"response[{index}]")
        require(row.get("pulse_id") == pulse["pulse_id"], "response pulse_id does not match manifest")
        require(row.get("scenario") in {"baseline", "pulse"}, "response scenario must be baseline or pulse")
        require(row.get("coverage_status") == "complete", "response coverage must be complete; no imputation is allowed")
        require(row.get("harvest_unit") == "tonne_wet_weight", "response harvest unit must be tonne_wet_weight")
        finite_number(row.get("harvest_or_availability"), "harvest_or_availability", nonnegative=True)
        require(isinstance(row.get("year"), int) and not isinstance(row.get("year"), bool) and 1900 <= row["year"] <= 2300, "response year is invalid")
        key = (row.get("draw_id"), row.get("pulse_id"), row.get("year"), row.get("stock_id"), row.get("source_area_id"))
        require(all(value is not None and value != "" for value in key), "response key is incomplete")
        scenario = row["scenario"]
        require(scenario not in response_groups[key], f"duplicate response {scenario} row for {key}")
        response_groups[key][scenario] = row
    for key, pair in response_groups.items():
        require(set(pair) == {"baseline", "pulse"}, f"response key {key} lacks a matched baseline/pulse pair")
        for name in MATCHED_IDENTIFIERS:
            require(pair["baseline"].get(name) == pair["pulse"].get(name) and pair["baseline"].get(name) not in {None, ""}, f"response key {key} has unmatched {name}")

    incidence = bundle["incidence"]
    require(isinstance(incidence, list) and incidence, "incidence must be nonempty")
    incidence_groups: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    incidence_keys: set[tuple[Any, ...]] = set()
    for index, row in enumerate(incidence):
        validate_object_shape(row, schema, "incidence", f"incidence[{index}]")
        require(row.get("coverage_status") == "complete", "incidence coverage must be complete")
        require(re.fullmatch(r"[A-Z]{3}", str(row.get("producer_country_iso3", ""))) is not None, "producer country must be ISO3")
        require(re.fullmatch(r"[A-Z]{3}", str(row.get("consumer_country_iso3", ""))) is not None, "consumer country must be ISO3")
        require(isinstance(row.get("year"), int) and not isinstance(row.get("year"), bool) and 1900 <= row["year"] <= 2300, "incidence year is invalid")
        group = (row.get("draw_id"), row.get("year"), row.get("stock_id"), row.get("source_area_id"))
        market_key = group + (row.get("market_id"),)
        require(all(value is not None and value != "" for value in market_key), "incidence key is incomplete")
        require(market_key not in incidence_keys, f"duplicate incidence market key {market_key}")
        incidence_keys.add(market_key)
        for name in ("harvest_fraction", "landing_fraction", "consumption_fraction"):
            value = finite_number(row.get(name), name, nonnegative=True)
            require(value <= 1.0, f"{name} exceeds one")
        incidence_groups[group].append(row)
    require(set(incidence_groups) == {(key[0], key[2], key[3], key[4]) for key in response_groups}, "incidence and response support differ")
    for key, rows in incidence_groups.items():
        for name in ("harvest_fraction", "landing_fraction", "consumption_fraction"):
            require(abs(sum(float(row[name]) for row in rows) - 1.0) <= tolerance, f"{name} does not conserve for {key}")

    welfare = bundle["welfare"]
    require(isinstance(welfare, list) and welfare, "welfare rows must be nonempty")
    welfare_groups: dict[tuple[Any, ...], dict[str, dict[str, Any]]] = defaultdict(dict)
    for index, row in enumerate(welfare):
        validate_object_shape(row, schema, "welfare", f"welfare[{index}]")
        require(not any("revenue" in str(name).lower() for name in row), "revenue fields are forbidden in direct-welfare inputs")
        require(row.get("pulse_id") == pulse["pulse_id"], "welfare pulse_id does not match manifest")
        require(row.get("scenario") in {"baseline", "pulse"}, "welfare scenario must be baseline or pulse")
        require(row.get("coverage_status") == "complete", "welfare coverage must be complete")
        require(row.get("welfare_unit") == "USD_2020", "welfare unit must be USD_2020")
        require(row.get("consumer_welfare_semantics") == "consumer_surplus", "consumer welfare must be direct consumer surplus")
        require(row.get("producer_welfare_semantics") == "producer_surplus", "producer welfare must be direct producer surplus")
        require(isinstance(row.get("valuation_method_id"), str) and row["valuation_method_id"], "valuation_method_id must be nonblank")
        require(isinstance(row.get("year"), int) and not isinstance(row.get("year"), bool) and 1900 <= row["year"] <= 2300, "welfare year is invalid")
        finite_number(row.get("consumer_surplus"), "consumer_surplus")
        finite_number(row.get("producer_surplus"), "producer_surplus")
        incidence_key = (row.get("draw_id"), row.get("year"), row.get("stock_id"), row.get("source_area_id"), row.get("market_id"))
        require(incidence_key in incidence_keys, "welfare row lacks an incidence mapping")
        response_key = (row.get("draw_id"), row.get("pulse_id"), row.get("year"), row.get("stock_id"), row.get("source_area_id"))
        require(response_key in response_groups, "welfare row lacks a response pair")
        key = response_key + (row.get("market_id"),)
        scenario = row["scenario"]
        require(scenario not in welfare_groups[key], f"duplicate welfare {scenario} row for {key}")
        welfare_groups[key][scenario] = row
    require({key[:-1] + (key[-1],) for key in welfare_groups} == {(key[0], pulse["pulse_id"], key[1], key[2], key[3], key[4]) for key in incidence_keys}, "welfare and incidence market support differ")
    for key, pair in welfare_groups.items():
        require(set(pair) == {"baseline", "pulse"}, f"welfare key {key} lacks a matched baseline/pulse pair")
        for name in ("welfare_unit", "consumer_welfare_semantics", "producer_welfare_semantics", "valuation_method_id", "coverage_status"):
            require(pair["baseline"].get(name) == pair["pulse"].get(name), f"welfare key {key} has unmatched {name}")

    overlap = bundle["overlap"]
    validate_object_shape(overlap, schema, "overlap", "overlap")
    require(overlap.get("review_status") == "passed", "overlap review has not passed")
    require(isinstance(overlap.get("accounting_boundary_id"), str) and overlap["accounting_boundary_id"], "accounting boundary must be identified")
    require(isinstance(overlap.get("trade_closure_id"), str) and overlap["trade_closure_id"], "trade closure must be identified")
    for name in OVERLAP_FLAGS:
        require(overlap.get(name) is False, f"overlap exclusion failed: {name}")

    return {
        "contract_version": CONTRACT_VERSION,
        "bundle_id": bundle["bundle_id"],
        "synthetic_only": True,
        "request_components": len(components),
        "sources": len(sources),
        "matched_response_pairs": len(response_groups),
        "incidence_markets": len(incidence_keys),
        "matched_welfare_pairs": len(welfare_groups),
        "status": "synthetic_contract_valid_no_estimation_authorized",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    parser.add_argument(
        "--schema", type=Path,
        default=ROOT / "config/global_fisheries_welfare_bridge_input_contract_v1.schema.json",
    )
    parser.add_argument("--tolerance", type=float, default=1e-9)
    args = parser.parse_args()
    require(args.tolerance >= 0, "tolerance must be nonnegative")
    schema = json.loads(args.schema.read_text(encoding="utf-8"))
    bundle = json.loads(args.bundle.read_text(encoding="utf-8"))
    result = validate_bundle(bundle, schema, args.tolerance)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
