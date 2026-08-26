#!/usr/bin/env python3
"""Synthetic failure tests for the SPEI design contract; performs no fitting."""
from __future__ import annotations

import copy
from pathlib import Path

from validate_spei_competitor_contract import PROJECT_ROOT, load_contract, validate_contract


CONTRACT_PATH = PROJECT_ROOT / "config/spei_competitor_v1.toml"


def rejected(contract: dict, expected: str) -> None:
    try:
        validate_contract(contract)
    except ValueError as error:
        if expected.lower() not in str(error).lower():
            raise AssertionError(f"expected rejection containing {expected!r}, got {error!r}") from error
    else:
        raise AssertionError(f"invalid SPEI contract accepted; expected {expected!r}")


def main() -> None:
    base = load_contract(CONTRACT_PATH)
    validate_contract(base)

    late = copy.deepcopy(base)
    late["calibration"]["end_year"] = 2014
    rejected(late, "boundary")

    noaa_primary = copy.deepcopy(base)
    noaa_primary["source_decision"]["primary_route"] = "published_noaa_nclimgrid_monthly_spei"
    rejected(noaa_primary, "primary route")

    noaa_terminal = copy.deepcopy(base)
    noaa_terminal["source_decision"]["published_noaa_role"] = "primary_terminal_score"
    rejected(noaa_terminal, "terminal scoring")

    thornthwaite = copy.deepcopy(base)
    thornthwaite["method"]["pet_method"] = "thornthwaite_monthly"
    rejected(thornthwaite, "pet_method")

    source_tmean = copy.deepcopy(base)
    source_tmean["method"]["tmean_definition"] = "source_daily_mean"
    rejected(source_tmean, "tmean definition")

    wrong_distribution = copy.deepcopy(base)
    wrong_distribution["method"]["distribution"] = "pearson_type_iii"
    rejected(wrong_distribution, "distribution")

    wrong_tail = copy.deepcopy(base)
    wrong_tail["method"]["cdf_probability_clip_epsilon"] = 1e-6
    rejected(wrong_tail, "tail clip")

    stacked_scales = copy.deepcopy(base)
    stacked_scales["method"]["scales_stacked"] = True
    rejected(stacked_scales, "scales_stacked")

    selected_scale = copy.deepcopy(base)
    selected_scale["method"]["scales_selected_by_outcome"] = True
    rejected(selected_scale, "scales_selected_by_outcome")

    missing_scale = copy.deepcopy(base)
    missing_scale["method"]["accumulation_scales_months"] = [3, 6]
    rejected(missing_scale, "scales")

    family_stack = copy.deepcopy(base)
    family_stack["mutual_exclusivity"]["maximum_moisture_families_per_model"] = 2
    rejected(family_stack, "one moisture family")

    raw_precip = copy.deepcopy(base)
    raw_precip["mutual_exclusivity"]["direct_precipitation_in_spei_model"] = True
    rejected(raw_precip, "direct_precipitation_in_spei_model")

    unequal_support = copy.deepcopy(base)
    unequal_support["common_support"]["test_key_hashes_equal_exactly"] = False
    rejected(unequal_support, "test_key_hashes_equal_exactly")

    fit_authorized = copy.deepcopy(base)
    fit_authorized["predictive_diagnostic_fit_authorized"] = True
    rejected(fit_authorized, "predictive_diagnostic_fit_authorized")

    outcome_calibration = copy.deepcopy(base)
    outcome_calibration["calibration"]["outcomes_in_calibration_allowed"] = True
    rejected(outcome_calibration, "outcomes_in_calibration_allowed")

    forecast_claim = copy.deepcopy(base)
    forecast_claim["features"]["temporal_availability_role"] = "operational_forecast"
    rejected(forecast_claim, "temporal-availability")

    warmup_lost = copy.deepcopy(base)
    warmup_lost["calibration"]["warmup_source_start_year"] = 1982
    rejected(warmup_lost, "boundary")

    wrong_global_source = copy.deepcopy(base)
    wrong_global_source["global"]["weather_source_id"] = "speibase_2_11"
    rejected(wrong_global_source, "weather source")

    truncated_preplant = copy.deepcopy(base)
    truncated_preplant["global"]["preplant90_global_year_start"] = 1982
    rejected(truncated_preplant, "preplant90 boundary")

    no_coverage_receipt = copy.deepcopy(base)
    no_coverage_receipt["global"]["preconstruction_coverage_receipt_hash_required"] = False
    rejected(no_coverage_receipt, "coverage_receipt_hash")

    scpdsi_promotion = copy.deepcopy(base)
    scpdsi_promotion["global"]["terminal_ranking_eligible_families"].append("scpdsi")
    rejected(scpdsi_promotion, "scPDSI entered terminal ranking")

    full_grid = copy.deepcopy(base)
    full_grid["bounded_construction"]["full_grid_invocation_allowed"] = True
    rejected(full_grid, "full_grid_invocation_allowed")

    weak_source_check = copy.deepcopy(base)
    weak_source_check["bounded_construction"]["source_sha512_recomputation_required"] = False
    rejected(weak_source_check, "source_sha512_recomputation_required")

    outcome_read = copy.deepcopy(base)
    outcome_read["bounded_construction"]["outcome_input_allowed"] = True
    rejected(outcome_read, "outcome_input_allowed")

    unbound_environment = copy.deepcopy(base)
    unbound_environment["bounded_construction"][
        "numerical_environment_in_checkpoint_identity_required"
    ] = False
    rejected(unbound_environment, "numerical_environment_in_checkpoint_identity_required")

    assert Path(base["source_decision"]["source_decision_provenance"]).suffix == ".toml"
    print("SPEI design contract synthetic tests passed; no index or outcome fit executed")


if __name__ == "__main__":
    main()
