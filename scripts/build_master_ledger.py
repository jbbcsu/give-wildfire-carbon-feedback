#!/usr/bin/env python3
"""Build a hash-bound, nonaggregating ledger of GIVE damage-sector outputs."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "give_damage_expansion_master_ledger_config/v1"
FIELDS = [
    "component_id", "sector", "category", "scope", "value_role",
    "central_value", "interval_low", "interval_high", "statistic",
    "units", "pulse_year", "discounting", "source_status",
    "master_total_eligible", "blocker", "evidence_ids",
]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_config(path: Path) -> dict[str, Any]:
    config = json.loads(path.read_text(encoding="utf-8"))
    require(config.get("schema") == SCHEMA, "unexpected config schema")
    allowed = set(config["allowed_categories"])
    require(allowed == {"integrated_pair_tested", "external_sensitivity",
                        "bounded_regional_benchmark", "blocked_nonadditive"},
            "category vocabulary changed")
    policy = config["aggregation_policy"]
    require(policy["headline_master_total_authorized"] is False, "headline total gate opened")
    require(policy["currently_compatible_component_sets"] == [], "unverified compatible set added")
    require(len(config["rows"]) == 20, "expected 20 audited ledger rows")
    require(len({row["component_id"] for row in config["rows"]}) == 20, "duplicate component ID")
    for row in config["rows"]:
        require(row["category"] in allowed, f"bad category: {row['component_id']}")
        require(row["master_total_eligible"] is False, f"master-total gate opened: {row['component_id']}")
        require(row["blocker"].strip(), f"missing claim boundary: {row['component_id']}")
    return config


def load_evidence(root: Path, config: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    payloads: dict[str, Any] = {}
    bound: dict[str, Any] = {}
    for evidence_id, spec in config["evidence"].items():
        path = (root / spec["path"]).resolve()
        require(path.is_file() and not path.is_symlink(), f"missing evidence: {evidence_id}")
        require(root.parent.resolve() in path.parents, f"evidence escapes GIVE workspace: {evidence_id}")
        require(sha256(path) == spec["sha256"], f"evidence hash mismatch: {evidence_id}")
        bound[evidence_id] = {"path": spec["path"], "sha256": spec["sha256"], "bytes": path.stat().st_size}
        if path.suffix == ".json":
            payloads[evidence_id] = json.loads(path.read_text(encoding="utf-8"))
        elif path.suffix == ".csv":
            with path.open(newline="", encoding="utf-8") as handle:
                payloads[evidence_id] = list(csv.DictReader(handle))
        else:
            raise ValueError(f"unsupported evidence type: {evidence_id}")
    return payloads, bound


def empty_result(status: str) -> dict[str, Any]:
    return {"central_value": "", "interval_low": "", "interval_high": "",
            "statistic": "none", "units": "", "pulse_year": "",
            "discounting": "", "source_status": status}


def extract(component_id: str, p: dict[str, Any]) -> dict[str, Any]:
    if component_id == "precip_maize_quantity":
        source = p["precip_coefficient_grid"]
        result = next(item for item in source["results"] if item["discount_rate_label"] == "2.0%")
        require(p["precip_release_validation"]["claim_gates"]["paired_quantity_channel_scc"] is True,
                "precip paired gate closed")
        return {"central_value": result["central_mean_usd2020_per_tco2"],
                "interval_low": result["normal_approximation_95_interval_usd2020_per_tco2"][0],
                "interval_high": result["normal_approximation_95_interval_usd2020_per_tco2"][1],
                "statistic": "equal_26_model_mean_with_coefficient_only_normal_95_interval",
                "units": "2020 USD per metric ton CO2", "pulse_year": "",
                "discounting": "GIVE 2.0% Ramsey", "source_status": source["status"]}
    if component_id == "precip_full_replacement":
        source = p["precip_release_validation"]
        require(source["claim_gates"]["full_precipitation_agriculture_scc"] is False,
                "full precipitation gate unexpectedly open")
        return empty_result("full_precipitation_agriculture_scc_gate_closed")
    if component_id == "labor_heat_productivity":
        source = p["labor_integration"]
        result = source["equal_weight_structural_result"]
        require(source["validation"]["precipitation_agriculture_stacking_allowed"] is False,
                "labor/precip stacking gate changed")
        return {"central_value": result["additive_labor_mean_2020usd_per_tco2"],
                "interval_low": "", "interval_high": "", "statistic": "equal_weight_structural_case_mean",
                "units": "2020 USD per metric ton CO2", "pulse_year": source["invariants"]["pulse_year"],
                "discounting": source["invariants"]["discount_rate_label"], "source_status": source["status"]}
    if component_id == "fisheries_market":
        source = p["fisheries_market_target"]
        result = source["result"]["market_external_sensitivity_2020_usd_per_tco2"]
        require(source["result"]["target_interface"]["additive_eligible"] is False,
                "fisheries additivity gate opened")
        return {"central_value": result["published_mc_median"], "interval_low": result["published_mc_p05"],
                "interval_high": result["published_mc_p95"], "statistic": "published_MC_median_p05_p95",
                "units": "2020 USD per metric ton CO2", "pulse_year": source["result"]["harmonization"]["source_pulse_year"],
                "discounting": "source settings; GIVE target not matched", "source_status": source["status"]}
    if component_id == "fisheries_combined_market_nutrition":
        source = p["fisheries_combined_benchmark"]
        result = source["result"]["published_monte_carlo_usd_per_tco2"]["combined"]
        require(source["scientific_gates"]["additive_to_give_authorized"] is False,
                "combined fisheries additivity gate opened")
        return {"central_value": result["mean"], "interval_low": result["p05"],
                "interval_high": result["p95"], "statistic": "published_MC_mean_p05_p95",
                "units": "source USD per metric ton CO2", "pulse_year": "",
                "discounting": "source Blue-SCC settings", "source_status": source["status"]}
    if component_id == "wildfire_smoke_pm25":
        source = p["smoke_contract"]
        result = source["normalized_result"]
        require(source["headline_addition_authorized"] is False, "smoke additivity gate opened")
        return {"central_value": result["detailed_mean_usd_per_tco2"],
                "interval_low": result["interval_usd_per_tco2"][0], "interval_high": result["interval_usd_per_tco2"][1],
                "statistic": "source_mean_conditional_95_interval", "units": "2020 USD per metric ton CO2",
                "pulse_year": result["pulse_year"], "discounting": "source-reported 2%",
                "source_status": source["status"]}
    if component_id == "nonwildfire_air_pollution_net":
        source = p["air_target_receipt"]
        row = next(item for item in p["air_target_table"] if item["component_id"] == "meteorological_ozone_pm25_net")
        require(source["portfolio_gates"]["any_component_additive_to_baseline_give"] is False,
                "air-pollution additivity gate opened")
        return {"central_value": row["target_price_mean_usd_per_tco2"],
                "interval_low": row["target_price_interval_low_usd_per_tco2"],
                "interval_high": row["target_price_interval_high_usd_per_tco2"],
                "statistic": "published_joint_net_mean_90_interval_price_harmonized",
                "units": source["target"]["units"], "pulse_year": row["source_pulse_year"],
                "discounting": "source 2% Ramsey; target pulse not harmonized", "source_status": source["status"]}
    if component_id == "aggregate_water_resources":
        source = p["water_validation"]
        require(source["additive_to_baseline_give"] is False, "water additivity gate opened")
        return {"central_value": source["central_aggregate_water_scc_2020usd_per_tco2"],
                "interval_low": "", "interval_high": "", "statistic": "deterministic_central",
                "units": "2020 USD per metric ton CO2", "pulse_year": 2025,
                "discounting": "constant 2%", "source_status": source["status"]}
    if component_id == "conus_heat_roads_rail":
        receipt = p["transport_receipt"]
        row = next(item for item in p["transport_summary"] if item["variant"] == "Reactive" and item["component"] == "Roads_plus_Rail")
        require(receipt["claim_gates"]["cross_sector_additivity_authorized"] is False,
                "transport cross-sector gate opened")
        return {"central_value": row["mean_partial_scc_2020usd_per_tco2"],
                "interval_low": row["min_partial_scc_2020usd_per_tco2"], "interval_high": row["max_partial_scc_2020usd_per_tco2"],
                "statistic": "six_surface_mean_and_range", "units": "2020 USD per metric ton CO2",
                "pulse_year": 2025, "discounting": "GIVE 2.0% Ramsey", "source_status": receipt["status"]}
    if component_id == "conus_grid_td_direct_cost":
        receipt = p["grid_td_receipt"]
        row = next(item for item in p["grid_td_summary"] if item["horizon"] == "2300" and item["adaptation_variant"] == "Reactive")
        require(receipt["claim_scope"]["additivity_to_give_authorized"] is False,
                "grid T&D additivity gate opened")
        require(receipt["claim_scope"]["outage_reliability_welfare"] == "NOT_INCLUDED",
                "grid benchmark misrepresented as outage welfare")
        require(row["additive_to_give"] == "false", "grid summary additivity gate opened")
        return {"central_value": row["mean_2020usd_per_tco2"],
                "interval_low": row["min_2020usd_per_tco2"], "interval_high": row["max_2020usd_per_tco2"],
                "statistic": "six_GCM_mean_and_range_direct_cost_not_outage_welfare",
                "units": "2020 USD direct cost per metric ton CO2", "pulse_year": 2025,
                "discounting": "GIVE 2.0% Ramsey", "source_status": receipt["status"]}
    if component_id == "conus_inland_riverine_flood":
        receipt = p["flood_receipt"]
        row = next(item for item in p["flood_summary"] if item["horizon"] == "2300")
        require(receipt["claim_gates"]["global_scc_authorized"] is False, "flood global gate opened")
        return {"central_value": row["partial_scc_2020usd_per_tco2"], "interval_low": "", "interval_high": "",
                "statistic": "deterministic_GCM_ensemble_with_endpoint_extrapolation", "units": "2020 USD per metric ton CO2",
                "pulse_year": 2025, "discounting": "GIVE 2.0% Ramsey", "source_status": receipt["status"]}
    if component_id == "conus_freshwater_quality":
        receipt = p["water_quality_receipt"]
        row = p["water_quality_summary"][0]
        require(receipt["claim_gates"]["additive_give_scc_allowed"] is False,
                "water-quality additivity gate opened")
        return {"central_value": row["mean_partial_scc_2020usd_per_tco2"],
                "interval_low": row["min_partial_scc_2020usd_per_tco2"], "interval_high": row["max_partial_scc_2020usd_per_tco2"],
                "statistic": "five_GCM_mean_and_range", "units": "2020 USD per metric ton CO2",
                "pulse_year": 2025, "discounting": "GIVE 2.0% Ramsey", "source_status": receipt["status"]}
    if component_id == "global_ecosystem_services":
        receipt = p["water_quality_receipt"]
        require(receipt["claim_gates"]["global_extrapolation_allowed"] is False,
                "ecosystem global gate opened")
        return empty_result("global_extrapolation_gate_closed")
    if component_id == "conus_temperature_crime":
        receipt = p["crime_receipt"]
        row = next(item for item in p["crime_summary"] if item["horizon"] == "2300" and item["component"] == "Total")
        require(receipt["claim_scope"]["additivity_to_give_authorized"] is False, "crime additivity gate opened")
        return {"central_value": row["mean_2020usd_per_tco2"], "interval_low": row["min_2020usd_per_tco2"],
                "interval_high": row["max_2020usd_per_tco2"], "statistic": "six_GCM_mean_and_range",
                "units": "2020 USD per metric ton CO2", "pulse_year": 2025,
                "discounting": "GIVE 2.0% Ramsey", "source_status": receipt["status"]}
    if component_id == "organized_armed_conflict":
        source = p["crime_receipt"]
        require(source["organized_armed_conflict_status"] == "BLOCKED_NO_SCC", "conflict status changed")
        return empty_result(source["organized_armed_conflict_status"])
    if component_id == "conus_winter_recreation_revenue":
        receipt = p["winter_recreation_receipt"]
        row = next(item for item in p["winter_recreation_summary"] if item["horizon"] == "2300" and item["component"] == "Total")
        require(receipt["claim_scope"]["additivity_to_give_authorized"] is False,
                "winter recreation additivity gate opened")
        require(row["additive_to_give"] == "false", "winter recreation table additivity gate opened")
        return {"central_value": row["mean_2020usd_per_tco2"],
                "interval_low": row["min_2020usd_per_tco2"], "interval_high": row["max_2020usd_per_tco2"],
                "statistic": "six_GCM_mean_and_range_lost_revenue_not_welfare",
                "units": "2020 USD lost revenue per metric ton CO2", "pulse_year": 2025,
                "discounting": "GIVE 2.0% Ramsey", "source_status": receipt["status"]}
    if component_id == "heat_morbidity_direct_medical_costs":
        source = p["heat_morbidity_readiness"]
        require(source["give_addition_authorized"] is False, "heat morbidity additivity gate opened")
        require(source["numeric_scc_produced"] is False, "heat morbidity SCC unexpectedly produced")
        return empty_result(source["status"])
    if component_id == "tropical_cyclone_macro":
        source = p["cyclone_readiness"]
        audit = source["source_data_audit"]
        require(source["numeric_give_addition_authorized"] is False, "cyclone additivity gate opened")
        require(audit["paired_global_tc_quantile_found"] is False, "unexpected paired cyclone quantile")
        return {"central_value": audit["difference_of_published_medians"], "interval_low": "", "interval_high": "",
                "statistic": "difference_of_published_medians_not_paired_component_quantile",
                "units": "constant 2005 USD per metric ton CO2", "pulse_year": 2025,
                "discounting": "Ricke prtp 2%, eta 1.5", "source_status": source["conclusion"]}
    if component_id == "dengue_nonfatal_morbidity":
        source = p["disease_readiness"]
        require(source["additive_scc_allowed"] is False, "disease SCC gate opened")
        return empty_result(source["interpretation"])
    if component_id == "noncoastal_climate_migration":
        source = p["migration_readiness"]
        require(source["numeric_scc_produced"] is False, "migration numeric SCC appeared")
        return empty_result(source["status"])
    raise ValueError(f"no extractor for {component_id}")


def build_rows(config: dict[str, Any], payloads: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for spec in config["rows"]:
        for evidence_id in spec["evidence_ids"]:
            require(evidence_id in payloads, f"row references unknown evidence: {evidence_id}")
        result = extract(spec["component_id"], payloads)
        row = {key: spec[key] for key in ("component_id", "sector", "category", "scope", "value_role")}
        row.update(result)
        row.update({"master_total_eligible": False, "blocker": spec["blocker"],
                    "evidence_ids": "|".join(spec["evidence_ids"])})
        rows.append(row)
    require(not any(row["master_total_eligible"] for row in rows), "master total contains an eligible row")
    return rows


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".partial")
    with temp.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: str(value).lower() if isinstance(value, bool) else value for key, value in row.items()})
    temp.replace(path)


def build(root: Path, config_path: Path) -> dict[str, Any]:
    config = load_config(config_path)
    payloads, bound = load_evidence(root, config)
    rows = build_rows(config, payloads)
    ledger = root / config["outputs"]["ledger"]
    write_csv(ledger, rows)
    counts = Counter(row["category"] for row in rows)
    return {
        "schema": "give_damage_expansion_master_ledger_receipt/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "master_ledger_built_no_cross_sector_total_authorized",
        "row_count": len(rows),
        "numeric_row_count": sum(row["central_value"] != "" for row in rows),
        "category_counts": dict(sorted(counts.items())),
        "headline_master_total": None,
        "headline_master_total_authorized": False,
        "bound_evidence": bound,
        "output": {"path": config["outputs"]["ledger"], "sha256": sha256(ledger), "bytes": ledger.stat().st_size},
        "config": {"path": str(config_path.relative_to(root)), "sha256": sha256(config_path)},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--config", type=Path, default=Path("config/master_ledger_v1.json"))
    args = parser.parse_args()
    root = args.root.resolve()
    config_path = args.config if args.config.is_absolute() else root / args.config
    receipt = build(root, config_path)
    config = load_config(config_path)
    output = root / config["outputs"]["receipt"]
    output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": receipt["status"], "rows": receipt["row_count"], "headline_total": None}))


if __name__ == "__main__":
    main()
