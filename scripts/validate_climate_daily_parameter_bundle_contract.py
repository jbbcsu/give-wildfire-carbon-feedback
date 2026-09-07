#!/usr/bin/env python3
"""Validate the synthetic-only future daily-generator parameter contract."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import tomllib


SCHEMA = "climate_daily_parameter_bundle_contract_v1"
ROLE = "synthetic_only_canonical_named_parameter_boundary_for_future_kemsley_daily_pairs"
TOP_LEVEL_FIELDS = [
    "schema", "generator_id", "paper_doi", "generator_code_identity",
    "parameterization_id", "records",
]
PARAMETER_FIELDS = [
    "climate_draw_id", "esm_id", "member_id", "grid_id", "calendar", "year", "month",
    "pulse_scale_tonnes_c", "path_role", "wet_probability_given_previous_dry",
    "wet_probability_given_previous_wet", "wet_amount_gamma_shape",
    "wet_amount_gamma_scale_mm", "spatial_dependence_parameter_sha256",
    "temperature_precipitation_coupling_parameter_sha256", "support_flag",
]
PARAMETER_KEY = [
    "climate_draw_id", "esm_id", "member_id", "grid_id", "calendar", "year", "month",
    "pulse_scale_tonnes_c", "path_role",
]
PROBABILITY_FIELDS = ["wet_probability_given_previous_dry", "wet_probability_given_previous_wet"]
POSITIVE_FIELDS = ["wet_amount_gamma_shape", "wet_amount_gamma_scale_mm"]
SHA256_FIELDS = ["spatial_dependence_parameter_sha256", "temperature_precipitation_coupling_parameter_sha256"]


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
    require(config.get("parent_interface_path") == "config/climate_daily_pair_interface_v1.toml", "parent path changed")
    require(config.get("parent_interface_sha256") == sha256(root / str(config["parent_interface_path"])), "parent hash changed")
    require(config.get("output_schema_path") == "config/climate_daily_pair_output_schema_v1.toml", "output schema path changed")
    require(config.get("output_schema_sha256") == sha256(root / str(config["output_schema_path"])), "output schema hash changed")
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
    require(bundle.get("future_schema") == "climate_daily_parameter_bundle_v1", "future schema changed")
    require(bundle.get("exact_top_level_fields") == TOP_LEVEL_FIELDS, "top-level fields changed")
    for gate in ("records_must_be_nonempty", "unknown_top_level_fields_forbidden"):
        require(bundle.get(gate) is True, f"bundle gate changed: {gate}")

    record = config.get("parameter_record", {})
    require(record.get("exact_fields") == PARAMETER_FIELDS, "parameter fields changed")
    require(record.get("key_fields") == PARAMETER_KEY, "parameter key changed")
    require(record.get("path_roles") == ["baseline", "pulse"], "path roles changed")
    require(record.get("support_flags") == ["within", "below", "above"], "support flags changed")
    require(record.get("probability_fields") == PROBABILITY_FIELDS, "probability fields changed")
    require(record.get("strictly_positive_fields") == POSITIVE_FIELDS, "positive fields changed")
    require(record.get("sha256_fields") == SHA256_FIELDS, "SHA-256 fields changed")
    for gate in (
        "finite_numeric_fields_required", "probabilities_must_be_closed_unit_interval",
        "gamma_parameters_must_be_strictly_positive", "duplicate_record_keys_forbidden",
    ):
        require(record.get(gate) is True, f"parameter-record gate changed: {gate}")

    hashing = config.get("hashing", {})
    require(hashing.get("algorithm") == "sha256", "hash algorithm changed")
    require(
        hashing.get("canonicalization")
        == "sort_records_by_parameter_key_then_utf8_json_sort_keys_true_separators_comma_colon_allow_nan_false",
        "canonicalization changed",
    )
    require(hashing.get("hex_digest_length") == 64, "digest length changed")
    for gate in ("record_order_invariant", "all_top_level_and_record_fields_included"):
        require(hashing.get(gate) is True, f"hashing gate changed: {gate}")

    linkage = config.get("output_linkage", {})
    for gate in (
        "parameter_bundle_sha256_must_match_canonical_bundle",
        "generator_code_identity_must_match_output_receipt",
        "record_keys_must_exactly_match_output_monthly_record_keys",
        "support_flags_must_match_output_records",
        "parameter_hash_must_match_every_output_monthly_record",
        "missing_or_extra_parameter_records_forbidden",
    ):
        require(linkage.get(gate) is True, f"output-linkage gate changed: {gate}")

    resources = config.get("resources", {})
    require(resources.get("maximum_peak_resident_memory_bytes") == 2 * 1024**3, "memory ceiling changed")
    require(resources.get("minimum_free_disk_bytes_before_any_future_acquisition") == 150 * 1024**3, "disk floor changed")
    for gate in (
        "metadata_and_schema_only", "synthetic_fixture_only", "large_downloads_forbidden",
        "raw_rehydration_forbidden", "global_daily_inputs_forbidden", "derived_parquet_inputs_forbidden",
    ):
        require(resources.get(gate) is True, f"resource gate changed: {gate}")

    decision = config.get("decision", {})
    require(
        decision.get("current_status")
        == "parameter_bundle_schema_preregistered_no_generator_or_real_parameters",
        "status changed",
    )
    for gate in (
        "schema_validation_does_not_authorize_generator_implementation",
        "schema_validation_does_not_establish_scientific_validity",
        "missing_pinned_generator_code_is_hard_no_fit_blocker", "no_outcome_columns",
        "no_empirical_coefficients", "no_fitted_or_real_generator_parameters",
    ):
        require(decision.get(gate) is True, f"decision gate changed: {gate}")

    return {
        "schema": "climate_daily_parameter_bundle_preregistration_v1",
        "status": "parameter_bundle_schema_preregistered_no_generator_or_real_parameters",
        "config_sha256": sha256(config_path),
        "implementation_sha256": sha256(Path(__file__)),
        "parent_interface_sha256": config["parent_interface_sha256"],
        "output_schema_sha256": config["output_schema_sha256"],
        "future_schema": bundle["future_schema"],
        "top_level_fields": TOP_LEVEL_FIELDS,
        "parameter_record_fields": PARAMETER_FIELDS,
        "parameter_key_fields": PARAMETER_KEY,
        "probability_fields": PROBABILITY_FIELDS,
        "strictly_positive_fields": POSITIVE_FIELDS,
        "sha256_fields": SHA256_FIELDS,
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
    print("climate daily parameter-bundle preregistration passed")


if __name__ == "__main__":
    main()
