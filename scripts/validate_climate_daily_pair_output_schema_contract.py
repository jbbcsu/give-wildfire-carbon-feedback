#!/usr/bin/env python3
"""Validate the preregistered schema-only daily-pair output contract."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import tomllib


SCHEMA = "climate_daily_pair_output_schema_contract_v1"
ROLE = "schema_only_future_output_gate_for_conservative_common_innovation_daily_precipitation_pairs"
PARENT_SHA256 = "2e5c4e57f33931f32bcde3c0bc0673c012820ccd4723ace28a8197a8333d8b39"
RECEIPT_FIELDS = [
    "contract_sha256", "generator_code_identity", "paper_doi", "parameter_bundle_sha256",
    "monthly_input_sha256", "rng_algorithm", "rng_version", "seed_namespace",
    "daily_output_sha256", "maximum_monthly_mass_error_mm", "peak_resident_memory_bytes",
]
MONTHLY_FIELDS = [
    "climate_draw_id", "esm_id", "member_id", "grid_id", "calendar", "year", "month",
    "pulse_scale_tonnes_c", "path_role", "first_divergence_date_or_model_day",
    "monthly_precipitation_mm", "monthly_temperature_degc", "parameter_bundle_sha256",
    "monthly_innovation_digest", "support_flag", "daily",
]
MONTHLY_KEY = [
    "climate_draw_id", "esm_id", "member_id", "grid_id", "calendar", "year", "month",
    "pulse_scale_tonnes_c", "path_role",
]
PAIR_KEY = MONTHLY_KEY[:-1]
CROSS_PULSE_KEY = MONTHLY_KEY[:7]
MONTHLY_INPUT_FIELDS = [
    "climate_draw_id", "esm_id", "member_id", "grid_id", "calendar", "year", "month",
    "pulse_scale_tonnes_c", "path_role", "first_divergence_date_or_model_day",
    "monthly_precipitation_mm", "monthly_temperature_degc", "parameter_bundle_sha256",
    "support_flag",
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
    require(config.get("parent_interface_path") == "config/climate_daily_pair_interface_v1.toml", "parent interface path changed")
    parent_path = root / str(config["parent_interface_path"])
    require(config.get("parent_interface_sha256") == PARENT_SHA256, "registered parent hash changed")
    require(sha256(parent_path) == PARENT_SHA256, "parent interface hash changed")
    require(config.get("future_bundle_schema") == "climate_daily_pair_output_bundle_v1", "future bundle schema changed")
    require(config.get("daily_generator_id") == "kemsley_markov_gamma", "daily generator changed")
    require(config.get("daily_generator_paper_doi") == "10.1002/joc.8320", "daily generator paper changed")
    require(config.get("daily_generator_pinned_public_executable_source_available") is False, "missing-code blocker changed")
    for gate in (
        "generator_implementation_authorized", "component_substitution_authorized",
        "software_acquisition_authorized", "climate_payload_acquisition_authorized",
        "emulator_fit_authorized", "fair_feature_response_authorized",
        "response_estimation_authorized", "damage_or_scc_authorized",
    ):
        require(config.get(gate) is False, f"closed gate changed: {gate}")

    bundle = config.get("bundle", {})
    require(bundle.get("exact_top_level_fields") == ["schema", "receipt", "records"], "top-level fields changed")
    for gate in ("records_must_be_nonempty", "unknown_top_level_fields_forbidden"):
        require(bundle.get(gate) is True, f"bundle gate changed: {gate}")

    receipt = config.get("receipt", {})
    require(receipt.get("required_fields") == RECEIPT_FIELDS, "receipt fields changed")
    for gate in (
        "exact_fields_required", "blank_or_missing_field_fails", "contract_sha256_must_match_parent_interface",
        "paper_doi_must_match_registered_generator", "monthly_input_sha256_must_match_canonical_projection",
        "daily_output_sha256_covers_canonical_records",
        "maximum_monthly_mass_error_must_reconcile", "peak_resident_memory_must_not_exceed_interface_ceiling",
        "receipt_is_not_scientific_validation",
    ):
        require(receipt.get(gate) is True, f"receipt gate changed: {gate}")

    monthly = config.get("monthly_record", {})
    require(monthly.get("exact_fields") == MONTHLY_FIELDS, "monthly fields changed")
    require(monthly.get("key_fields") == MONTHLY_KEY, "monthly key changed")
    require(monthly.get("pair_key_fields") == PAIR_KEY, "pair key changed")
    require(monthly.get("cross_pulse_month_key_fields") == CROSS_PULSE_KEY, "cross-pulse key changed")
    require(monthly.get("path_roles") == ["baseline", "pulse"], "path roles changed")
    require(monthly.get("support_flags") == ["within", "below", "above"], "support flags changed")
    require(monthly.get("precipitation_unit") == "mm_month-1", "monthly precipitation unit changed")
    require(monthly.get("temperature_unit") == "degC", "temperature unit changed")
    require(monthly.get("minimum_distinct_decreasing_positive_pulse_scales", 0) >= 3, "positive pulse count weakened")
    require(monthly.get("exactly_one_zero_pulse_scale") is True, "zero-pulse count gate changed")
    for gate in (
        "finite_numeric_fields_required", "nonnegative_precipitation_and_pulse_required",
        "parameter_bundle_must_match_receipt", "duplicate_record_keys_forbidden",
        "exactly_one_record_per_path_role_per_pair",
    ):
        require(monthly.get(gate) is True, f"monthly-record gate changed: {gate}")

    daily = config.get("daily_record", {})
    require(daily.get("exact_fields") == ["date_or_model_day", "precipitation_mm"], "daily fields changed")
    require(daily.get("date_key") == "date_or_model_day", "daily key changed")
    require(daily.get("precipitation_unit") == "mm_day-1", "daily unit changed")
    for gate in (
        "finite_nonnegative_values_required", "calendar_specific_complete_month_required",
        "duplicate_or_missing_days_forbidden", "daily_order_must_be_strictly_increasing",
    ):
        require(daily.get(gate) is True, f"daily-record gate changed: {gate}")

    checks = config.get("pair_checks", {})
    require(checks.get("absolute_conservation_tolerance_mm") == 1e-9, "absolute tolerance changed")
    require(checks.get("relative_conservation_tolerance") == 1e-12, "relative tolerance changed")
    for gate in (
        "monthly_innovation_digest_nonblank_required", "baseline_pulse_innovation_digest_identity_required",
        "cross_pulse_scale_innovation_digest_identity_required",
        "baseline_daily_path_identity_across_pulse_scales_required",
        "separate_baseline_and_pulse_monthly_conservation_required", "zero_month_requires_all_daily_zero",
        "positive_month_requires_at_least_one_positive_daily_value", "zero_pulse_daily_identity_required",
        "pre_divergence_daily_identity_required", "separate_baseline_and_pulse_support_flags_required",
    ):
        require(checks.get(gate) is True, f"pair-check gate changed: {gate}")

    hashing = config.get("hashing", {})
    require(hashing.get("algorithm") == "sha256", "hash algorithm changed")
    require(hashing.get("monthly_input_projection_fields") == MONTHLY_INPUT_FIELDS, "monthly-input projection fields changed")
    require(hashing.get("monthly_input_excluded_fields") == ["monthly_innovation_digest", "daily"], "monthly-input excluded fields changed")
    require(hashing.get("monthly_input_sort_key_fields") == MONTHLY_KEY, "monthly-input sort key changed")
    require(
        hashing.get("monthly_input_canonicalization")
        == "project_fields_sort_by_monthly_key_utf8_json_sort_keys_true_separators_comma_colon_allow_nan_false",
        "monthly-input canonicalization changed",
    )
    for gate in ("monthly_input_record_order_invariant", "monthly_input_record_count_must_match_output_records"):
        require(hashing.get(gate) is True, f"monthly-input hash gate changed: {gate}")
    require(hashing.get("records_canonicalization") == "utf8_json_sort_keys_true_separators_comma_colon_allow_nan_false", "canonicalization changed")
    require(hashing.get("hex_digest_length") == 64, "digest length changed")

    resources = config.get("resources", {})
    require(resources.get("maximum_peak_resident_memory_bytes") == 2 * 1024**3, "memory ceiling changed")
    require(resources.get("minimum_free_disk_bytes_before_any_future_acquisition") == 150 * 1024**3, "disk floor changed")
    for gate in (
        "metadata_and_schema_only", "synthetic_fixture_only", "large_downloads_forbidden",
        "raw_rehydration_forbidden", "global_daily_inputs_forbidden", "derived_parquet_inputs_forbidden",
    ):
        require(resources.get(gate) is True, f"resource gate changed: {gate}")

    decision = config.get("decision", {})
    require(decision.get("current_status") == "output_schema_preregistered_no_generator_or_real_output", "status changed")
    for gate in (
        "schema_validation_does_not_authorize_generator_implementation",
        "schema_validation_does_not_establish_scientific_validity",
        "missing_pinned_generator_code_is_hard_no_fit_blocker", "no_outcome_columns",
        "no_empirical_coefficients", "no_real_daily_climate_values",
    ):
        require(decision.get(gate) is True, f"decision gate changed: {gate}")

    return {
        "schema": "climate_daily_pair_output_schema_preregistration_v1",
        "status": "output_schema_preregistered_no_generator_or_real_output",
        "config_sha256": sha256(config_path),
        "implementation_sha256": sha256(Path(__file__)),
        "parent_interface_sha256": PARENT_SHA256,
        "future_bundle_schema": "climate_daily_pair_output_bundle_v1",
        "receipt_fields": RECEIPT_FIELDS,
        "monthly_input_projection_fields": MONTHLY_INPUT_FIELDS,
        "monthly_input_excluded_fields": ["monthly_innovation_digest", "daily"],
        "monthly_record_fields": MONTHLY_FIELDS,
        "daily_record_fields": ["date_or_model_day", "precipitation_mm"],
        "generator_implementation_authorized": False,
        "climate_payload_acquisition_authorized": False,
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
    print("climate daily-pair output schema preregistration passed")


if __name__ == "__main__":
    main()
