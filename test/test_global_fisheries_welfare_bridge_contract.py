#!/usr/bin/env python3
"""Focused synthetic tests for the global fisheries welfare bridge contract."""

from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts/validate_global_fisheries_welfare_bridge_contract.py"
SCHEMA_PATH = ROOT / "config/global_fisheries_welfare_bridge_input_contract_v1.schema.json"
SPEC = importlib.util.spec_from_file_location("validate_global_fisheries_welfare_bridge_contract", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)
SCHEMA = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def license_record() -> dict:
    return {"spdx_id": "CC0-1.0", "redistribution_allowed": True, "derivatives_allowed": True}


def source(source_id: str, role: str, digit: str) -> dict:
    return {
        "source_id": source_id,
        "role": role,
        "version": "synthetic-v1",
        "uri": f"synthetic://{source_id}",
        "sha256": digit * 64,
        "license": license_record(),
    }


def valid_bundle() -> dict:
    sources = [
        source("license", "license", "1"),
        source("raw", "raw_input", "2"),
        source("code", "model_code", "3"),
        source("lock", "dependency_lock", "4"),
        source("incidence", "incidence", "5"),
        source("demand", "demand", "6"),
        source("cost", "producer_cost", "7"),
        source("pulse", "pulse", "8"),
        source("overlap", "overlap_review", "9"),
    ]
    component_sources = {
        "license_and_reuse": ["license"],
        "raw_model_inputs": ["raw"],
        "executable_model_and_dependency_lock": ["code", "lock"],
        "incidence_and_geographic_keys": ["incidence"],
        "consumer_and_producer_surplus": ["demand", "cost"],
        "matched_marginal_pulse": ["pulse"],
        "overlap_accounting_boundary": ["overlap"],
    }
    response = {
        "draw_id": "draw-1", "pulse_id": "pulse-1t", "year": 2050,
        "stock_id": "stock-1", "source_area_id": "area-1",
        "climate_model_id": "climate-1", "ecosystem_model_id": "ecosystem-1",
        "management_scenario": "management-1", "socioeconomic_scenario": "ssp-1",
        "harvest_or_availability": 100.0, "harvest_unit": "tonne_wet_weight",
        "coverage_status": "complete",
    }
    incidence = {
        "draw_id": "draw-1", "year": 2050, "stock_id": "stock-1",
        "source_area_id": "area-1", "market_id": "market-1",
        "producer_country_iso3": "USA", "consumer_country_iso3": "CAN",
        "harvest_fraction": 1.0, "landing_fraction": 1.0,
        "consumption_fraction": 1.0, "coverage_status": "complete",
    }
    welfare = {
        "draw_id": "draw-1", "pulse_id": "pulse-1t", "year": 2050,
        "stock_id": "stock-1", "source_area_id": "area-1", "market_id": "market-1",
        "consumer_surplus": 20.0, "producer_surplus": 10.0,
        "welfare_unit": "USD_2020", "consumer_welfare_semantics": "consumer_surplus",
        "producer_welfare_semantics": "producer_surplus", "valuation_method_id": "synthetic-method-1",
        "coverage_status": "complete",
    }
    return {
        "contract_version": MODULE.CONTRACT_VERSION,
        "bundle_id": "synthetic:valid-v1",
        "synthetic_only": True,
        "authorization": {"purpose": "synthetic_contract_test_only", "coefficient_transfer": False, "fit": False, "damage": False, "scc": False},
        "license": license_record(),
        "coverage": {"scope": "global_declared_support", "complete": True, "missing_semantics": "explicit_no_imputation_or_renormalization"},
        "pulse": {"pulse_id": "pulse-1t", "gas": "CO2", "mass": 1.0, "mass_unit": "tCO2", "counterfactual": "same_realization_baseline"},
        "request_components": [
            {"component_id": component_id, "provided": True, "source_ids": source_ids}
            for component_id, source_ids in component_sources.items()
        ],
        "sources": sources,
        "responses": [dict(response, scenario="baseline"), dict(response, scenario="pulse", harvest_or_availability=99.5)],
        "incidence": [incidence],
        "welfare": [dict(welfare, scenario="baseline"), dict(welfare, scenario="pulse", consumer_surplus=19.5, producer_surplus=9.8)],
        "overlap": {
            "accounting_boundary_id": "capture_direct_market_surplus_v1",
            "review_status": "passed", "trade_closure_id": "synthetic-trade-v1",
            "includes_aquaculture": False,
            "includes_terrestrial_food_market_welfare": False,
            "includes_nutrition_or_mortality": False,
            "includes_coral_or_reef_services": False,
            "includes_biodiversity_nonuse_value": False,
            "includes_ciam_coastal_impacts": False,
            "includes_indirect_or_induced_output": False,
            "uses_gross_revenue_as_welfare": False,
        },
    }


def fails(mutator) -> None:
    bundle = valid_bundle()
    mutator(bundle)
    try:
        MODULE.validate_bundle(bundle, SCHEMA)
    except ValueError:
        return
    raise AssertionError("invalid synthetic bundle passed")


result = MODULE.validate_bundle(valid_bundle(), SCHEMA)
assert result["status"] == "synthetic_contract_valid_no_estimation_authorized"
assert result["request_components"] == 7
assert result["matched_response_pairs"] == 1
assert result["matched_welfare_pairs"] == 1

with tempfile.TemporaryDirectory() as directory:
    bundle_path = Path(directory) / "synthetic-bundle.json"
    bundle_path.write_text(json.dumps(valid_bundle()), encoding="utf-8")
    completed = subprocess.run(
        ["python3", str(MODULE_PATH), str(bundle_path)],
        text=True,
        capture_output=True,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    cli_result = json.loads(completed.stdout)
    assert cli_result["status"] == "synthetic_contract_valid_no_estimation_authorized"

fails(lambda b: b.update(synthetic_only=False))
fails(lambda b: b["license"].update(redistribution_allowed=False))
fails(lambda b: b["sources"][0]["license"].update(derivatives_allowed=False))
fails(lambda b: b["request_components"].pop())
fails(lambda b: b["request_components"][4].update(source_ids=["license"]))
fails(lambda b: b["welfare"][0].update(consumer_welfare_semantics="gross_revenue"))
fails(lambda b: b["welfare"][0].update(producer_welfare_semantics="profit_multiplier"))
fails(lambda b: b["responses"].pop())
fails(lambda b: b["responses"][1].update(climate_model_id="unmatched-climate"))
fails(lambda b: b["incidence"][0].update(consumption_fraction=0.9))
fails(lambda b: b["welfare"][0].update(market_id="unmapped-market"))
fails(lambda b: b["overlap"].update(includes_nutrition_or_mortality=True))
fails(lambda b: b["overlap"].update(review_status="pending"))
fails(lambda b: b["responses"][0].update(harvest_unit="kg"))
fails(lambda b: b["welfare"][0].update(welfare_unit="USD_2015"))
fails(lambda b: b["pulse"].update(mass=1000000000.0))
fails(lambda b: b["welfare"][0].update(gross_revenue=100.0))

print("Global fisheries welfare bridge contract tests passed")
