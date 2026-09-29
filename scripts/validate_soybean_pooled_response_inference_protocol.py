#!/usr/bin/env python3
"""Mechanically validate the pooled-only soybean response/inference protocol."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import resource
import sys
import tomllib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def require(value: bool, message: str) -> None:
    if not value:
        raise ValueError(message)


def resolve(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 << 20), b""):
            value.update(block)
    return value.hexdigest()


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def peak_rss_bytes() -> int:
    value = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    return value if sys.platform == "darwin" else value * 1024


def contract_errors(config: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if config["estimand"]["outcome_level"] != "natural_log_of_yield_t_ha": errors.append("outcome scale")
    if config["estimand"]["causal_interpretation"] is not False: errors.append("causal estimand")
    if config["estimand"]["pair_weighting"] != "equal_weight_per_cell_pair": errors.append("pair weighting")
    if config["controls"]["primary_group_year_control"] != "singleton_country_proxy_by_pair_end_year": errors.append("primary controls")
    if config["family_hierarchy"]["primary"] != "quantity": errors.append("primary family")
    if config["family_hierarchy"]["challengers"] != ["distribution", "scpdsi_season"]: errors.append("challenger family")
    if config["family_hierarchy"]["direct_and_scpdsi_stacking_allowed"] is not False: errors.append("direct/scpdsi stacking")
    if config["family_hierarchy"]["distribution_and_scpdsi_stacking_allowed"] is not False: errors.append("distribution/scpdsi stacking")
    if config["family_hierarchy"]["automatic_family_selection_allowed"] is not False: errors.append("automatic selection")
    if config["inference"]["primary_spatial_cluster"] != "10_degree_block": errors.append("spatial cluster")
    if config["inference"]["cluster_covariance"] != "CR2 small-sample cluster-robust covariance": errors.append("CR2")
    if int(config["inference"]["wild_cluster_bootstrap_draws"]) != 9999: errors.append("bootstrap draws")
    if config["later_period_validation"]["reuse_as_fresh_confirmation_allowed"] is not False: errors.append("fresh confirmation")
    if config["later_period_validation"]["hyperparameter_or_family_tuning_on_terminal_period_allowed"] is not False: errors.append("terminal tuning")
    if config["adaptation_interface"]["primary_projection_multiplier"] != 1.0: errors.append("primary adaptation")
    if config["adaptation_interface"]["optional_multiplier_may_vary_by_country_block_cell_or_irrigation"] is not False: errors.append("geographic adaptation")
    if not all(config["prohibitions"].values()): errors.append("prohibition disabled")
    if config["claim_gates"]["protocol_draft_authorized"] is not True: errors.append("draft gate")
    if any(value for key, value in config["claim_gates"].items() if key != "protocol_draft_authorized"): errors.append("downstream claim gate")
    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--synthetic-tests", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), "fresh protocol-validation output required")
    config = tomllib.loads(args.config.read_text(encoding="utf-8"))
    require(config["contract_id"] == "soybean_pooled_response_inference_protocol_v1", "contract id differs")
    require(not contract_errors(config), f"contract errors: {contract_errors(config)}")
    for record in config["sources"].values():
        path = resolve(record["path"])
        require(path.is_file() and digest(path) == record["sha256"], f"source hash differs: {path}")

    readiness = load(resolve(config["sources"]["readiness_audit"]["path"]))
    preflight = load(resolve(config["sources"]["design_preflight"]["path"]))
    preflight_validation = load(resolve(config["sources"]["design_preflight_validation"]["path"]))
    require(preflight_validation["status"] == "validated_outcome_blind_design_preflight_fail_closed", "preflight validation status differs")
    require(preflight["resolution"]["finest_support_qualified_geographic_resolution"] == "pooled_global", "pooled-only resolution not established")
    require(preflight["country_quantity_qualification"]["resolution_gate"]["passes"] is False, "country-resolution gate unexpectedly passed")

    quantity = preflight["families"]["quantity"]["control_alternatives"]["country_year"]
    scpdsi = preflight["families"]["scpdsi_season"]["control_alternatives"]["country_year"]
    expected_direct = config["expected_training_support"]["direct_primary"]
    expected_scpdsi = config["expected_training_support"]["scpdsi_common"]
    require(quantity["finite_pairs"] == expected_direct["pairs"] == 157868, "direct primary pair support differs")
    require(scpdsi["finite_pairs"] == expected_scpdsi["pairs"] == 157003, "scPDSI common support differs")
    require(quantity["support"]["pair_end_years"] == expected_direct["pair_end_years"] == 28, "direct years differ")
    require(quantity["support"]["cells"] >= expected_direct["cells_minimum"], "direct cells below contract")
    require(quantity["support"]["countries_singleton"] == expected_direct["singleton_country_proxies"], "country proxy count differs")
    require(quantity["support"]["blocks10"] >= expected_direct["blocks10_minimum"], "direct blocks below contract")

    gates = config["prefit_gates"]
    direct_support = preflight["pair_construction"]["direct_heat_pairs"]
    prefit_checks = {
        "minimum_primary_pairs": quantity["finite_pairs"] >= int(gates["minimum_primary_pairs"]),
        "minimum_pair_end_years": quantity["support"]["pair_end_years"] >= int(gates["minimum_pair_end_years"]),
        "minimum_cells": quantity["support"]["cells"] >= int(gates["minimum_cells"]),
        "minimum_raw_blocks10": quantity["support"]["blocks10"] >= int(gates["minimum_raw_blocks10"]),
        "minimum_effective_blocks10": direct_support["effective_block10_clusters_inverse_herfindahl"] >= float(gates["minimum_effective_blocks10"]),
        "minimum_effective_country_proxies": direct_support["effective_country_clusters_inverse_herfindahl"] >= float(gates["minimum_effective_country_proxies"]),
        "maximum_largest_block_pair_share": direct_support["largest_block10_pair_share"] <= float(gates["maximum_largest_block_pair_share"]),
        "full_column_rank": quantity["full_column_rank"],
        "maximum_scaled_condition_number": quantity["scaled_condition_number"] <= float(gates["maximum_scaled_condition_number"]),
        "maximum_row_leverage": quantity["leverage"]["maximum"] <= float(gates["maximum_row_leverage"]),
        "maximum_p99_row_leverage": quantity["leverage"]["p99"] <= float(gates["maximum_p99_row_leverage"]),
        "maximum_top_one_percent_leverage_share": quantity["leverage"]["top_one_percent_share"] <= float(gates["maximum_top_one_percent_leverage_share"]),
        "block_overlap": all(
            record["two_sided_p05_p95"] and record["fraction_inside_global_p05_p95"] >= float(gates["minimum_each_block_fraction_inside_global_quantity_p05_p95"])
            for record in preflight["primary_quantity_variation"]["block10"].values()
        ),
    }
    require(all(prefit_checks.values()), f"frozen primary prefit support fails: {[key for key, value in prefit_checks.items() if not value]}")

    response = readiness["response_evidence"]
    quantity_terminal = response["spatial_terminal_prediction"]["quantity_minus_heat_rmse"]
    distribution_terminal = response["independent_later_rainfed_distribution_confirmation"]
    scpdsi_terminal = response["spatial_terminal_prediction"]["scpdsi_mean_minus_quantity_rmse"]
    inherited_terminal = {
        "quantity_point_favors_candidate": quantity_terminal["point_rmse_difference"] < 0,
        "quantity_bootstrap_upper_below_zero": quantity_terminal["cluster_bootstrap"]["p975"] < 0,
        "distribution_existing_confirmation_passed": distribution_terminal["passes"],
        "scpdsi_point_favors_candidate": scpdsi_terminal["point_rmse_difference"] < 0,
        "scpdsi_bootstrap_upper_below_zero": scpdsi_terminal["cluster_bootstrap"]["p975"] < 0,
    }
    require(inherited_terminal == {
        "quantity_point_favors_candidate": True,
        "quantity_bootstrap_upper_below_zero": False,
        "distribution_existing_confirmation_passed": False,
        "scpdsi_point_favors_candidate": False,
        "scpdsi_bootstrap_upper_below_zero": False,
    }, "inherited terminal evidence differs")

    synthetic = load(args.synthetic_tests)
    require(synthetic["config"]["sha256"] == digest(args.config), "synthetic/config binding differs")
    require(synthetic["status"] == "passed_synthetic_only_no_real_outcome_fit", "synthetic status differs")
    require(synthetic["real_outcome_data_read"] is False and synthetic["results"]["all_pass"] is True, "synthetic boundary or tests failed")
    required_tests = {
        "coefficient_recovery", "stable_influence_acceptance", "rank_failure", "overlap_failure",
        "influence_failure", "family_nonstacking_failure", "geographic_slope_prohibition", "later_validation_fail_closed",
    }
    require(set(synthetic["results"]["tests"]) == required_tests, "synthetic test inventory differs")
    require(all(record["passes"] for record in synthetic["results"]["tests"].values()), "synthetic test failure")
    recovery = synthetic["results"]["tests"]["coefficient_recovery"]
    require(recovery["synthetic_only"] and recovery["absolute_error"] <= float(config["synthetic_tests"]["maximum_absolute_recovery_error"]), "synthetic recovery differs")

    protocol_text = args.protocol.read_text(encoding="utf-8")
    required_phrases = [
        "does not perform one", "pooled global response", "Country-, block-, cell-, and irrigation-specific slopes are prohibited",
        "mutually exclusive", "CR2", "wild-cluster bootstrap", "locked for a terminal transport stress test",
        "no_additional_adaptation", "winner/loser claims", "remains pooled and associational",
    ]
    require(all(phrase in protocol_text for phrase in required_phrases), "protocol narrative boundary text differs")

    stacking_mutation = copy.deepcopy(config)
    stacking_mutation["family_hierarchy"]["direct_and_scpdsi_stacking_allowed"] = True
    geography_mutation = copy.deepcopy(config)
    geography_mutation["prohibitions"]["country_specific_response_slopes"] = False
    downstream_mutation = copy.deepcopy(config)
    downstream_mutation["claim_gates"]["real_outcome_slope_fit_authorized"] = True
    deliberate_mutation_checks = {
        "stacking_would_fail": bool(contract_errors(stacking_mutation)),
        "geographic_slope_would_fail": bool(contract_errors(geography_mutation)),
        "terminal_upper_bound_at_or_above_zero_would_fail": synthetic["results"]["tests"]["later_validation_fail_closed"]["failing_case_rejected"],
        "any_downstream_claim_gate_would_fail": bool(contract_errors(downstream_mutation)),
    }
    require(all(deliberate_mutation_checks.values()), "one or more deliberate fail-closed mutations was accepted")
    rss = peak_rss_bytes()
    cap = int(config["memory_cap_bytes"])
    require(rss < cap, f"memory cap exceeded: {rss}")
    result = {
        "schema": "soybean_pooled_response_inference_protocol_validation/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "mechanically_validated_protocol_only_fail_closed_no_real_fit",
        "config": {"path": str(args.config), "sha256": digest(args.config)},
        "protocol": {"path": str(args.protocol), "sha256": digest(args.protocol)},
        "synthetic_tests": {"path": str(args.synthetic_tests), "sha256": digest(args.synthetic_tests)},
        "source_bindings": {key: {"path": record["path"], "sha256": record["sha256"]} for key, record in config["sources"].items()},
        "checks": {
            "contract_errors": [], "prefit_support": prefit_checks,
            "pooled_only_resolution": True, "country_or_block_slopes_prohibited": True,
            "family_nonstacking": True, "inherited_terminal_evidence": inherited_terminal,
            "synthetic_all_pass": True, "deliberate_mutation_checks": deliberate_mutation_checks,
            "real_outcome_magnitudes_read": False, "real_outcome_slope_fit": False,
        },
        "promotion_state": {
            "protocol_mechanically_validated": True,
            "real_outcome_slope_fit_authorized": False,
            "associational_fit_diagnostic": False,
            "predictive_response_candidate": False,
            "causal_response": False,
            "country_or_block_response_heterogeneity": False,
            "winner_loser_claims": False,
            "damage_calculation": False, "scc": False, "give_integration": False,
        },
        "resources": {"peak_rss_bytes": rss, "memory_cap_bytes": cap, "memory_gate_passed": True},
        "implementation": {"path": str(Path(__file__).resolve().relative_to(ROOT)), "sha256": digest(Path(__file__).resolve())},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "checks": result["checks"], "promotion_state": result["promotion_state"], "resources": result["resources"]}, indent=2))


if __name__ == "__main__":
    main()
