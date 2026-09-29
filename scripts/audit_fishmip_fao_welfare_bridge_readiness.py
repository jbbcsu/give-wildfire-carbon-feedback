#!/usr/bin/env python3
"""Audit resident FishMIP/FAO readiness for a defensible welfare bridge."""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import re
import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG_SCHEMA = "fishmip_fao_welfare_bridge_readiness_config_v1"
CONFIG_ROLE = "source_pinned_biophysical_to_welfare_bridge_audit_and_external_data_request"
STATIC_FIELDS = [
    "source_record_id", "country_un_m49", "country_iso3", "country_name",
    "species_asfis_code", "species_scientific_name", "species_name",
    "fao_area_code", "fao_area_name", "environment_class", "measure_code",
    "measure_name", "unit", "unit_multiplier",
]
ECONOMIC_TERMS = (
    "price", "cost", "revenue", "profit", "elasticity", "demand", "supply",
    "trade", "consumer", "producer", "surplus", "effort", "management",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def scan_fao_panel(path: Path) -> dict[str, object]:
    with gzip.open(path, "rt", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        fields = list(reader.fieldnames or [])
        if fields[: len(STATIC_FIELDS)] != STATIC_FIELDS:
            raise ValueError("FAO panel static schema changed")
        dynamic = fields[len(STATIC_FIELDS):]
        value_years = [int(match.group(1)) for field in dynamic if (match := re.fullmatch(r"value_(\d{4})", field))]
        status_years = [int(match.group(1)) for field in dynamic if (match := re.fullmatch(r"status_(\d{4})", field))]
        if value_years != status_years or value_years != list(range(1950, 2025)):
            raise ValueError("FAO panel annual value/status pairs changed")
        records = sum(1 for _ in reader)
    economic = [field for field in STATIC_FIELDS if any(term in field.lower() for term in ECONOMIC_TERMS)]
    return {
        "records": records,
        "static_fields": len(STATIC_FIELDS),
        "years": len(value_years),
        "year_range": [value_years[0], value_years[-1]],
        "economic_static_fields": economic,
        "economic_static_field_count": len(economic),
        "species_identity_present": "species_asfis_code" in STATIC_FIELDS,
        "vessel_flag_country_present": "country_iso3" in STATIC_FIELDS,
        "fao_area_present": "fao_area_code" in STATIC_FIELDS,
    }


def audit(config_path: Path) -> dict[str, object]:
    config = tomllib.loads(config_path.read_text(encoding="utf-8"))
    if config.get("schema") != CONFIG_SCHEMA or config.get("role") != CONFIG_ROLE:
        raise ValueError("welfare-bridge config identity changed")
    paths: dict[str, Path] = {}
    for name, value in config["inputs"].items():
        if name.endswith("_sha256"):
            continue
        path = ROOT / str(value)
        if not path.is_file() or sha256(path) != config["inputs"][f"{name}_sha256"]:
            raise ValueError(f"source missing or hash changed: {name}")
        paths[name] = path

    catalog = tomllib.loads(paths["fishmip_catalog"].read_text(encoding="utf-8"))
    spatial = load_json(paths["fishmip_spatial"])
    prediction = load_json(paths["fishmip_fao_prediction"])
    fao_receipt = load_json(paths["fao_panel_receipt"])
    turnover = load_json(paths["fao_turnover"])
    eez = tomllib.loads(paths["eez_decision"].read_text(encoding="utf-8"))
    overlap = load_json(paths["give_overlap"])
    panel = scan_fao_panel(paths["fao_panel"])
    expected = config["expected"]

    if catalog["catalog_result_count"] != int(expected["fishmip_files"]):
        raise ValueError("FishMIP catalogue file count changed")
    if catalog["variable"]["name"] != "tc" or catalog["variable"]["description"] != "total catch density":
        raise ValueError("FishMIP variable identity changed")
    if len(spatial["results"]) != int(expected["fishmip_matrix_results"]):
        raise ValueError("FishMIP structural matrix changed")
    common_cells = {item["common_finite_grid_cells"] for item in spatial["results"]}
    if common_cells != {int(expected["fishmip_common_finite_cells"])}:
        raise ValueError("FishMIP common support changed")
    if len(spatial["inputs"]) != int(expected["fishmip_files"]):
        raise ValueError("FishMIP spatial receipt no longer binds all files")
    if spatial["matched_co2_pulse"] or spatial["welfare_estimated"] or spatial["damage_estimated"]:
        raise ValueError("FishMIP receipt improperly opens a downstream gate")

    for key in ("records", "years", "static_fields", "economic_static_field_count"):
        if panel[key] != int(expected[f"fao_{key}"]):
            raise ValueError(f"FAO panel result changed: {key}")
    if fao_receipt["filter"]["measure_code"] != "Q_tlw" or fao_receipt["filter"]["unit"] != "t":
        raise ValueError("FAO marine panel is no longer physical live-weight tonnage")
    if fao_receipt["claim_gates"]["welfare"] or fao_receipt["claim_gates"]["country_or_eez_allocation"]:
        raise ValueError("FAO receipt improperly opens welfare or allocation")

    contract_results = [
        item for item in prediction["results"]
        if item["status_family"] == "contract_observed_or_quality"
    ]
    beaten = sum(item["fishmip_beats_benchmark_relative_rmse"] for item in contract_results)
    if beaten != int(expected["contract_status_family_paths_beating_constant"]):
        raise ValueError("FishMIP/FAO blocked-prediction result changed")
    species_turnover = [
        item["dimensions"]["species_asfis_code"]["composition_total_variation"]
        for item in turnover["comparisons"]
    ]
    country_turnover = [
        item["dimensions"]["country_iso3"]["composition_total_variation"]
        for item in turnover["comparisons"]
    ]
    if eez["eez"]["acquired"] or eez["limitations"]["production_allocation_built"]:
        raise ValueError("EEZ allocation state changed")
    if overlap["claim_gates"]["published_market_additive_to_give"]:
        raise ValueError("GIVE overlap receipt improperly opens market additivity")

    requests = list(config["external_data_request"]["components"])
    if len(requests) != int(expected["request_components"]):
        raise ValueError("external data request component count changed")
    required_request_keys = {"id", "purpose", "required_keys", "required_variables", "requirements"}
    if len({item["id"] for item in requests}) != len(requests) or any(set(item) != required_request_keys for item in requests):
        raise ValueError("external data request schema is invalid or duplicated")
    forbidden = dict(config["forbidden_shortcuts"])
    if not forbidden or not all(forbidden.values()):
        raise ValueError("every registered shortcut must remain forbidden")
    gates = dict(config["claim_gates"])
    if any(gates.values()):
        raise ValueError("welfare-bridge config improperly opens a scientific gate")

    return {
        "schema": "fishmip_fao_welfare_bridge_readiness_audit_v1",
        "role": config["role"],
        "status": "blocked_precise_external_bioeconomic_bridge_bundle_required",
        "resident_evidence": {
            "fishmip": {
                "catalogue_files": catalog["catalog_result_count"],
                "variable": catalog["variable"],
                "units": catalog["content_validation"]["boats_gfdl_historical"]["units"],
                "common_finite_grid_cells": next(iter(common_cells)),
                "global_grid": [180, 360],
                "species_or_commodity_dimension": False,
                "biomass_variable_present_in_acquired_matrix": False,
                "matched_co2_pulse": False,
                "welfare_fields_present": False,
            },
            "fao": {
                **panel,
                "measure": fao_receipt["filter"],
                "country_semantics": "primarily_vessel_flag_not_harvest_eez_or_consumer_incidence",
                "climate_causation_identified": False,
            },
            "historical_bridge": {
                "contract_status_family_paths": len(contract_results),
                "paths_beating_constant_holdout_benchmark": beaten,
                "historical_fit_probability_weights_available": False,
                "species_composition_total_variation_range": [min(species_turnover), max(species_turnover)],
                "country_composition_total_variation_range": [min(country_turnover), max(country_turnover)],
                "fixed_species_or_country_share_bridge_authorized": False,
            },
            "allocation": {
                "eez_geometry_acquired": eez["eez"]["acquired"],
                "production_grid_allocation_built": eez["limitations"]["production_allocation_built"],
                "fleet_incidence_identified": eez["limitations"]["fleet_incidence_identified"],
                "trade_or_market_incidence_identified": eez["limitations"]["trade_or_market_incidence_identified"],
            },
            "overlap": {
                "market_additive_to_give": overlap["claim_gates"]["published_market_additive_to_give"],
                "nutrition_additive_to_give": overlap["claim_gates"]["published_nutrition_additive_to_give"],
            },
        },
        "decision": {
            "global_structural_catch_density_diagnostic_available": True,
            "globally_complete_welfare_ready_response_available": False,
            "resident_fao_supplies_prices_costs_elasticities_or_trade": False,
            "defensible_resident_coupling_available": False,
            "reason": "The acquired FishMIP matrix is aggregate scenario catch density without commodity, incidence, welfare, or pulse semantics; FAO supplies physical vessel-flag landings and species identities but no economic bridge. Allocation and overlap gates remain closed.",
        },
        "external_data_request": requests,
        "forbidden_shortcuts": forbidden,
        "claim_gates": gates,
        "provenance": {
            name: {"path": str(path.relative_to(ROOT)), "sha256": sha256(path)}
            for name, path in paths.items()
        },
        "config": {"path": str(config_path.relative_to(ROOT)), "sha256": sha256(config_path)},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config", type=Path,
        default=ROOT / "config/fishmip_fao_welfare_bridge_readiness_v1.toml",
    )
    parser.add_argument(
        "--out", type=Path,
        default=ROOT / "data/provenance/fishmip_fao_welfare_bridge_readiness_20260928.json",
    )
    args = parser.parse_args()
    result = audit(args.config.resolve())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.out.with_suffix(args.out.suffix + ".partial")
    temporary.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(args.out)
    print(result["status"])


if __name__ == "__main__":
    main()
