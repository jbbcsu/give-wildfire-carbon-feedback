#!/usr/bin/env python3
"""Validate the metadata-only conservative common-innovation daily-pair interface."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import tomllib


SCHEMA = "climate_daily_pair_interface_contract_v1"
ROLE = "outcome_blind_metadata_method_interface_for_conservative_common_innovation_daily_precipitation_pairs"
GENERATOR = "kemsley_markov_gamma"
INNOVATION_FAMILIES = ["wet_state_uniform", "wet_amount_uniform", "spatial_dependence_latent"]
INNOVATION_KEYS = [
    "seed_namespace",
    "generator_code_identity",
    "parameter_bundle_sha256",
    "climate_draw_id",
    "esm_id",
    "member_id",
    "grid_id",
    "calendar",
    "year",
    "month",
    "date_or_model_day",
    "innovation_family",
    "innovation_slot",
]
EXCLUDED_INNOVATION_KEYS = [
    "path_role",
    "pulse_scale_tonnes_c",
    "monthly_precipitation_mm",
    "monthly_temperature_degc",
    "path_specific_parameter_value",
]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate(config_path: Path, root: Path) -> dict[str, object]:
    config = tomllib.loads(config_path.read_text(encoding="utf-8"))
    require(config.get("schema") == SCHEMA, "contract schema changed")
    require(config.get("role") == ROLE, "contract role changed")
    require(config.get("primary_climate_route") == "direct_isimip3b_daily_feature_response", "primary route changed")
    require(
        config.get("fallback_climate_route") == "mesmer_m_tp_plus_kemsley_markov_gamma_daily_generator",
        "fallback route changed",
    )
    require(config.get("daily_generator_id") == GENERATOR, "daily generator changed")
    require(config.get("daily_generator_paper_doi") == "10.1002/joc.8320", "daily generator paper changed")
    require(config.get("daily_generator_pinned_public_executable_source_available") is False, "missing-code blocker changed")
    for gate in (
        "generator_implementation_authorized",
        "component_substitution_authorized",
        "software_acquisition_authorized",
        "climate_payload_acquisition_authorized",
        "emulator_fit_authorized",
        "fair_feature_response_authorized",
        "response_estimation_authorized",
        "damage_or_scc_authorized",
    ):
        require(config.get(gate) is False, f"closed gate changed: {gate}")

    receipts = []
    expected_roles = ["fallback_readiness_gate", "matched_give_fair_temperature_gate"]
    for receipt in config.get("source_receipts", []):
        path = root / receipt["path"]
        observed = sha256(path)
        require(observed == receipt.get("sha256"), f"source receipt hash changed: {receipt['path']}")
        receipts.append({**receipt, "sha256": observed})
    require([receipt.get("role") for receipt in receipts] == expected_roles, "source receipt roles changed")

    identity = config.get("identity", {})
    require(identity.get("path_roles") == ["baseline", "pulse"], "path roles changed")
    require(identity.get("required_zero_pulse_controls") == 1, "zero-pulse control changed")
    require(identity.get("minimum_distinct_decreasing_positive_pulse_scales", 0) >= 3, "shrinking-pulse count weakened")
    for gate in ("same_realization_gmst_required", "duplicate_keys_forbidden", "missing_months_forbidden", "missing_days_forbidden"):
        require(identity.get(gate) is True, f"identity gate changed: {gate}")
    for key_name in ("pair_key", "monthly_record_key", "daily_record_key"):
        keys = identity.get(key_name, [])
        require(len(keys) == len(set(keys)) and "pulse_scale_tonnes_c" in keys, f"invalid {key_name}")
    require("path_role" not in identity["pair_key"], "pair key must identify both path roles")
    require("path_role" in identity["monthly_record_key"], "monthly record key lacks path role")
    require("path_role" in identity["daily_record_key"], "daily record key lacks path role")

    monthly = config.get("monthly_input", {})
    require(monthly.get("precipitation_unit") == "mm_month-1", "precipitation unit changed")
    require(monthly.get("temperature_unit") == "degC", "temperature unit changed")
    for gate in (
        "finite_values_required",
        "nonnegative_precipitation_required",
        "calendar_specific_days_in_month_required",
        "monthly_backbone_identity_and_version_required",
        "monthly_parameter_bundle_sha256_required",
        "separate_baseline_and_pulse_values_required",
    ):
        require(monthly.get(gate) is True, f"monthly-input gate changed: {gate}")

    innovations = config.get("innovations", {})
    require(innovations.get("rng_requirement") == "counter_based_or_equivalent_keyed_random_access", "RNG requirement changed")
    require(innovations.get("innovation_families") == INNOVATION_FAMILIES, "innovation families changed")
    require(innovations.get("innovation_value_domain") == "open_unit_interval", "innovation domain changed")
    require(innovations.get("key_fields") == INNOVATION_KEYS, "innovation key changed")
    require(innovations.get("excluded_key_fields") == EXCLUDED_INNOVATION_KEYS, "path-specific key exclusion changed")
    require(not set(INNOVATION_KEYS).intersection(EXCLUDED_INNOVATION_KEYS), "innovation key includes path-specific field")
    for gate in (
        "seed_namespace_identity_required",
        "rng_algorithm_and_version_required",
        "same_key_same_value_required",
        "path_independent_call_count_required",
        "monthly_innovation_digest_required",
        "baseline_pulse_digest_identity_required",
        "cross_pulse_scale_digest_identity_required",
    ):
        require(innovations.get(gate) is True, f"innovation gate changed: {gate}")

    conservation = config.get("conservation", {})
    require(conservation.get("positive_month_rescaling") == "multiply_each_positive_provisional_amount_by_monthly_target_divided_by_provisional_sum", "positive-month conservation rule changed")
    require(conservation.get("roundoff_residual_assignment") == "last_positive_wet_day_in_calendar_order", "roundoff rule changed")
    require(conservation.get("absolute_tolerance_mm") == 1e-9, "absolute conservation tolerance changed")
    require(conservation.get("relative_tolerance") == 1e-12, "relative conservation tolerance changed")
    for gate in (
        "apply_separately_to_each_path",
        "provisional_daily_values_finite_and_nonnegative_required",
        "zero_month_requires_all_daily_zero",
        "positive_month_requires_positive_provisional_month_sum",
        "wet_dry_occurrence_unchanged_by_rescaling",
        "post_residual_nonnegative_required",
    ):
        require(conservation.get(gate) is True, f"conservation gate changed: {gate}")

    pairing = config.get("pair_validation", {})
    for gate in (
        "common_innovations_do_not_imply_equal_path_parameters",
        "common_innovations_do_not_imply_equal_daily_occurrence",
        "each_path_must_pass_monthly_conservation",
        "zero_pulse_daily_identity_required",
        "pre_divergence_daily_identity_required",
        "separate_baseline_and_pulse_support_flags_required",
        "direct_daily_reference_benchmark_required_before_promotion",
        "wet_day_frequency_required_before_promotion",
        "consecutive_dry_days_required_before_promotion",
        "rx1day_required_before_promotion",
        "rx5day_required_before_promotion",
        "crop_stage_feature_reconciliation_required_before_promotion",
        "whole_esm_holdout_required_before_promotion",
        "whole_scenario_holdout_required_before_promotion",
        "shrinking_pulse_normalized_feature_convergence_required_before_promotion",
    ):
        require(pairing.get(gate) is True, f"pair-validation gate changed: {gate}")

    future_receipt = config.get("future_receipt", {})
    required_receipt_fields = future_receipt.get("required_fields", [])
    for field in (
        "contract_sha256",
        "generator_code_identity",
        "parameter_bundle_sha256",
        "monthly_innovation_digest",
        "daily_output_sha256",
        "maximum_monthly_mass_error_mm",
        "peak_resident_memory_bytes",
    ):
        require(field in required_receipt_fields, f"future receipt field missing: {field}")
    require(len(required_receipt_fields) == len(set(required_receipt_fields)), "duplicate future receipt field")
    require(future_receipt.get("blank_or_missing_receipt_field_fails") is True, "receipt completeness gate changed")
    require(future_receipt.get("receipt_is_not_validation") is True, "receipt interpretation changed")

    resources = config.get("resources", {})
    require(resources.get("maximum_peak_resident_memory_bytes") == 2 * 1024**3, "memory ceiling changed")
    require(resources.get("minimum_free_disk_bytes_before_any_future_acquisition") == 150 * 1024**3, "disk floor changed")
    for gate in ("metadata_only", "large_downloads_forbidden", "raw_rehydration_forbidden", "global_daily_inputs_forbidden", "derived_parquet_inputs_forbidden"):
        require(resources.get(gate) is True, f"resource gate changed: {gate}")

    decision = config.get("decision", {})
    require(decision.get("current_status") == "interface_preregistered_no_generator_implementation", "status changed")
    for gate in (
        "missing_pinned_generator_code_is_hard_no_fit_blocker",
        "interface_validation_does_not_authorize_implementation",
        "interface_validation_does_not_establish_scientific_validity",
        "no_outcome_columns",
        "no_empirical_coefficients",
    ):
        require(decision.get(gate) is True, f"decision gate changed: {gate}")

    return {
        "schema": "climate_daily_pair_interface_preregistration_v1",
        "status": "interface_preregistered_no_generator_implementation",
        "config_sha256": sha256(config_path),
        "implementation_sha256": sha256(Path(__file__)),
        "source_receipts": receipts,
        "daily_generator_id": GENERATOR,
        "daily_generator_pinned_public_executable_source_available": False,
        "innovation_families": INNOVATION_FAMILIES,
        "innovation_key_fields": INNOVATION_KEYS,
        "innovation_excluded_key_fields": EXCLUDED_INNOVATION_KEYS,
        "exact_monthly_conservation_required": True,
        "common_innovations_required": True,
        "generator_implementation_authorized": False,
        "software_acquisition_authorized": False,
        "climate_payload_acquisition_authorized": False,
        "emulator_fit_authorized": False,
        "fair_feature_response_authorized": False,
        "response_estimation_authorized": False,
        "damage_or_scc_authorized": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = validate(args.config.resolve(), args.root.resolve())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("climate daily-pair interface preregistration passed")


if __name__ == "__main__":
    main()
