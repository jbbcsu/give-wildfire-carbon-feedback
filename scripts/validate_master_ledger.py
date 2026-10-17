#!/usr/bin/env python3
"""Independently validate the synthesis ledger, source hashes, and no-sum gate."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {
    "precip_maize_quantity": ("integrated_pair_tested", -0.0061017295490773385),
    "precip_full_replacement": ("blocked_nonadditive", None),
    "labor_heat_productivity": ("integrated_pair_tested", 40.56425698048089),
    "fisheries_market": ("external_sensitivity", 0.0617078215811978),
    "fisheries_combined_market_nutrition": ("external_sensitivity", 33.814859578185334),
    "wildfire_smoke_pm25": ("blocked_nonadditive", 50.04),
    "nonwildfire_air_pollution_net": ("blocked_nonadditive", -12.586136),
    "aggregate_water_resources": ("external_sensitivity", 2.283769899326),
    "conus_heat_roads_rail": ("bounded_regional_benchmark", 0.214477593749),
    "conus_grid_td_direct_cost": ("blocked_nonadditive", 0.066819238708),
    "conus_inland_riverine_flood": ("bounded_regional_benchmark", 0.014246408098),
    "conus_freshwater_quality": ("bounded_regional_benchmark", 0.016683906231),
    "global_ecosystem_services": ("blocked_nonadditive", None),
    "conus_temperature_crime": ("bounded_regional_benchmark", 0.019265274491),
    "organized_armed_conflict": ("blocked_nonadditive", None),
    "conus_winter_recreation_revenue": ("blocked_nonadditive", 0.023860501026),
    "heat_morbidity_direct_medical_costs": ("blocked_nonadditive", None),
    "tropical_cyclone_macro": ("external_sensitivity", 38.64485612123323),
    "dengue_nonfatal_morbidity": ("blocked_nonadditive", None),
    "noncoastal_climate_migration": ("blocked_nonadditive", None),
    "bilal_kaenzig_global_macro": ("mutually_exclusive_comparator", 1206.96927919086),
    "education_heat_learning": ("blocked_nonadditive", None),
    "freshwater_recreational_angling": ("blocked_nonadditive", None),
    "permafrost_carbon_feedback": ("blocked_nonadditive", None),
    "amazon_dieback_carbon_feedback": ("blocked_nonadditive", None),
    "global_forestry_market_welfare": ("external_sensitivity", -0.0769529710606),
    "wetland_methane_feedback": ("blocked_nonadditive", None),
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_rows(rows: list[dict[str, str]]) -> None:
    require(len(rows) == len(EXPECTED), "wrong ledger row count")
    require({row["component_id"] for row in rows} == set(EXPECTED), "unexpected ledger components")
    for row in rows:
        expected_category, expected_value = EXPECTED[row["component_id"]]
        require(row["category"] == expected_category, f"category drift: {row['component_id']}")
        require(row["master_total_eligible"] == "false", f"master-total gate open: {row['component_id']}")
        require(row["blocker"].strip() != "", f"missing claim boundary: {row['component_id']}")
        if expected_value is None:
            require(row["central_value"] == "", f"invented value: {row['component_id']}")
        else:
            require(math.isclose(float(row["central_value"]), expected_value, rel_tol=0, abs_tol=1e-12),
                    f"numeric value drift: {row['component_id']}")
    require(Counter(row["category"] for row in rows) == Counter({
        "integrated_pair_tested": 2, "external_sensitivity": 5,
        "bounded_regional_benchmark": 4, "blocked_nonadditive": 15,
        "mutually_exclusive_comparator": 1,
    }), "category counts changed")
    macro = next(row for row in rows if row["component_id"] == "bilal_kaenzig_global_macro")
    require(macro["value_role"] == "mutually exclusive top-down comparator only; not an omitted-sector residual",
            "macro comparator role changed")
    require(set(macro["incompatibility_codes"].split("|")) == {
        "DAMAGE_OBJECT", "PRICE_UNIT", "DISCOUNTING", "PULSE_AND_CLIMATE_MODULE", "SOCIOECONOMIC_BASELINE"
    }, "macro comparator incompatibility inventory changed")
    require(macro["units"] == "2024 international dollars per metric tonne CO2",
            "macro comparator unit changed")
    permafrost = next(row for row in rows if row["component_id"] == "permafrost_carbon_feedback")
    require(permafrost["central_value"] == "" and permafrost["statistic"] == "none",
            "permafrost value invented")
    require(set(permafrost["incompatibility_codes"].split("|")) == {
        "FAIR_FEEDBACK_BOUNDARY", "BIOGENIC_CH4_PORT", "RECURSIVE_BASELINE_PULSE", "SOURCE_ARTIFACT"
    }, "permafrost incompatibility inventory changed")
    require("9-50%" in permafrost["blocker"] and "prohibited" in permafrost["blocker"],
            "combined EPA uplift prohibition missing")
    amazon = next(row for row in rows if row["component_id"] == "amazon_dieback_carbon_feedback")
    require(amazon["central_value"] == "" and amazon["statistic"] == "none",
            "Amazon feedback value invented")
    require(set(amazon["incompatibility_codes"].split("|")) == {
        "FAIR_LAND_SINK_BOUNDARY", "BASELINE_LAND_USE_EMISSIONS", "HAZARD_DRIVER_INCOMPLETENESS",
        "RECURSIVE_BASELINE_PULSE", "SOURCE_STOCK_OVERSHOOT",
    }, "Amazon feedback incompatibility inventory changed")
    require("0.1%" in amazon["blocker"] and "prohibited" in amazon["blocker"],
            "META scalar prohibition missing")
    forestry = next(row for row in rows if row["component_id"] == "global_forestry_market_welfare")
    require(forestry["source_status"] == "external_legacy_benchmark_only",
            "forestry source status changed")
    require(forestry["statistic"] == "central_with_OAT_source_parameter_range_not_probability_interval",
            "forestry OAT range misclassified")
    require(math.isclose(float(forestry["interval_low"]), -0.154557057073, rel_tol=0, abs_tol=1e-15) and
            math.isclose(float(forestry["interval_high"]), -0.037064745818, rel_tol=0, abs_tol=1e-15),
            "forestry OAT diagnostic range changed")
    require(set(forestry["incompatibility_codes"].split("|")) == {
        "SOURCE_COEFFICIENT_CONFLICT", "LEGACY_CALIBRATION", "FUND_GIVE_SCENARIO_MISMATCH",
        "FOREST_DISTURBANCE_OVERLAP",
    }, "forestry incompatibility inventory changed")
    wetland = next(row for row in rows if row["component_id"] == "wetland_methane_feedback")
    require(wetland["central_value"] == "" and wetland["statistic"] == "none",
            "wetland methane SCC invented")
    require(set(wetland["incompatibility_codes"].split("|")) == {
        "NATURAL_CH4_BASELINE_PARTITION", "BIOGENIC_OXIDATION_ROUTING", "METHANE_TIMING",
        "GMST_PROXY_REVERSIBILITY", "NEGATIVE_SLOPE_TAIL", "MAGICC_VERSION_ALIGNMENT",
        "RECURSIVE_BASELINE_PULSE",
    }, "wetland methane incompatibility inventory changed")
    require("168.83862060475192" in wetland["blocker"] and "30 +/- 13" in wetland["blocker"],
            "wetland baseline or slope benchmark missing")


def validate(root: Path, config_path: Path, receipt_path: Path) -> dict[str, Any]:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    require(config["schema"] == "give_damage_expansion_master_ledger_config/v1", "bad config schema")
    require(config["aggregation_policy"]["headline_master_total_authorized"] is False,
            "headline total gate opened")
    require(config["aggregation_policy"]["currently_compatible_component_sets"] == [],
            "unverified compatible set present")
    require(all(row["master_total_eligible"] is False for row in config["rows"]),
            "config contains total-eligible row")

    for evidence_id, spec in config["evidence"].items():
        path = (root / spec["path"]).resolve()
        require(path.is_file() and not path.is_symlink(), f"missing evidence: {evidence_id}")
        require(root.parent.resolve() in path.parents, f"evidence escapes workspace: {evidence_id}")
        require(sha256(path) == spec["sha256"], f"source hash mismatch: {evidence_id}")
        require(receipt["bound_evidence"][evidence_id]["sha256"] == spec["sha256"],
                f"receipt evidence mismatch: {evidence_id}")
        if "source_commit" in spec:
            require(receipt["bound_evidence"][evidence_id].get("source_commit") == spec["source_commit"],
                    f"receipt source-commit mismatch: {evidence_id}")

    require(receipt["schema"] == "give_damage_expansion_master_ledger_receipt/v1", "bad receipt schema")
    require(receipt["config"]["sha256"] == sha256(config_path), "config hash mismatch")
    require(receipt["headline_master_total"] is None, "headline total invented")
    require(receipt["headline_master_total_authorized"] is False, "headline total authorized")
    require(receipt["numeric_row_count"] == 16 and receipt["row_count"] == 27, "receipt counts changed")

    ledger = root / receipt["output"]["path"]
    require(sha256(ledger) == receipt["output"]["sha256"], "ledger hash mismatch")
    with ledger.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    validate_rows(rows)

    scenario_path = root / receipt["scenario_benchmark_output"]["path"]
    require(sha256(scenario_path) == receipt["scenario_benchmark_output"]["sha256"],
            "scenario benchmark hash mismatch")
    require(receipt["scenario_benchmark_output"]["is_scc"] is False, "scenario benchmark promoted to SCC")
    require(receipt["scenario_benchmark_output"]["additive_to_give"] is False,
            "scenario benchmark promoted to additive")
    with scenario_path.open(newline="", encoding="utf-8") as handle:
        scenario_rows = list(csv.DictReader(handle))
    expected_scenarios = {
        ("all_fishing", "RCP4.5"): -38000.0,
        ("all_fishing", "RCP8.5"): -45000.0,
        ("coldwater_fishing", "RCP4.5"): -93000.0,
        ("coldwater_fishing", "RCP8.5"): -100000.0,
    }
    require(len(scenario_rows) == 4, "scenario benchmark row count changed")
    for row in scenario_rows:
        key = (row["fishing_scope"], row["scenario"])
        require(key in expected_scenarios and float(row["value"]) == expected_scenarios[key],
                "freshwater scenario value changed")
        require(row["units"] == "million 2015 USD", "freshwater scenario units changed")
        require(row["is_scc"] == "false" and row["additive_to_give"] == "false",
                "freshwater scenario promoted")

    overlap_path = root / config["outputs"]["overlap_matrix"]
    with overlap_path.open(newline="", encoding="utf-8") as handle:
        overlap = list(csv.DictReader(handle))
    require(len(overlap) == 45, "overlap matrix row count changed")
    require(all(row["status"] and row["decision_rule"] for row in overlap), "incomplete overlap row")
    require(any(row["status"] == "umbrella_macro_overlap" for row in overlap), "macro-overlap gate missing")
    require(any(row["status"] == "mutually_exclusive_target_contracts" for row in overlap),
            "agriculture target incompatibility missing")
    permafrost_overlap = [row for row in overlap if row["component_a"] == "permafrost_carbon_feedback"]
    require(len(permafrost_overlap) == 3, "permafrost overlap inventory changed")
    require({row["status"] for row in permafrost_overlap} == {
        "unresolved_feedback_boundary", "unresolved_baseline_emissions_boundary",
        "conditionally_distinct_recursive_feedbacks",
    }, "permafrost overlap rule changed")
    amazon_overlap = [row for row in overlap if row["component_a"] == "amazon_dieback_carbon_feedback"]
    require(len(amazon_overlap) == 3, "Amazon overlap inventory changed")
    require({row["status"] for row in amazon_overlap} == {
        "unresolved_feedback_boundary", "unresolved_baseline_land_use_boundary",
        "unresolved_interacting_hazard_boundary",
    }, "Amazon overlap rule changed")
    forestry_overlap = [row for row in overlap if row["component_a"] == "global_forestry_market_welfare"]
    require(len(forestry_overlap) == 3, "forestry overlap inventory changed")
    require({row["status"] for row in forestry_overlap} == {
        "unresolved_disturbance_overlap", "shared_physical_state_boundary", "conditionally_disjoint_valuation",
    }, "forestry overlap rule changed")
    wetland_overlap = [row for row in overlap if row["component_a"] == "wetland_methane_feedback"]
    require(len(wetland_overlap) == 3, "wetland methane overlap inventory changed")
    require({row["status"] for row in wetland_overlap} == {
        "unresolved_baseline_partition", "shared_biogenic_methane_interface",
        "unresolved_oxidation_and_timing_boundary",
    }, "wetland methane overlap rule changed")

    priority_path = root / config["outputs"]["priorities"]
    with priority_path.open(newline="", encoding="utf-8") as handle:
        priorities = list(csv.DictReader(handle))
    require([int(row["priority"]) for row in priorities] == list(range(1, 20)), "priority order changed")
    require(priorities[0]["workstream"] == "Joint target model and endpoint registry",
            "joint target no longer first priority")

    manuscript = root / config["outputs"]["manuscript_structure"]
    require(manuscript.is_file() and manuscript.stat().st_size > 3000, "manuscript structure missing")
    text = manuscript.read_text(encoding="utf-8")
    for heading in ("AI-assisted scientific workflow", "Evidence tiers and aggregation rules",
                    "Overlap and welfare accounting", "What AI changed", "Limitations and research agenda"):
        require(heading in text, f"manuscript section missing: {heading}")

    return {
        "schema": "give_damage_expansion_master_ledger_validation/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "passed_hash_bound_tiered_ledger_and_no_sum_gate",
        "checks_passed": 269,
        "rows_validated": 27,
        "scenario_benchmark_rows_validated": 4,
        "overlap_rows_validated": 45,
        "priority_rows_validated": 19,
        "headline_master_total_authorized": False,
        "inputs": {
            "config_sha256": sha256(config_path), "receipt_sha256": sha256(receipt_path),
            "ledger_sha256": sha256(ledger), "scenario_benchmarks_sha256": sha256(scenario_path),
            "overlap_sha256": sha256(overlap_path),
            "priorities_sha256": sha256(priority_path), "manuscript_sha256": sha256(manuscript),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--config", type=Path, default=Path("config/master_ledger_v1.json"))
    parser.add_argument("--receipt", type=Path, default=Path("data/provenance/master_damage_sector_ledger_receipt_v1.json"))
    args = parser.parse_args()
    root = args.root.resolve()
    config_path = args.config if args.config.is_absolute() else root / args.config
    receipt_path = args.receipt if args.receipt.is_absolute() else root / args.receipt
    result = validate(root, config_path, receipt_path)
    config = json.loads(config_path.read_text(encoding="utf-8"))
    output = root / config["outputs"]["validation"]
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "checks": result["checks_passed"]}))


if __name__ == "__main__":
    main()
