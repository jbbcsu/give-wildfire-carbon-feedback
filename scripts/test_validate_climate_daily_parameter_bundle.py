#!/usr/bin/env python3
"""Synthetic canonical-hash and linkage tests for named daily parameters."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from validate_climate_daily_parameter_bundle import (
    canonical_parameter_bundle_sha256,
    validate_parameter_bundle,
)


root = Path(__file__).resolve().parents[1]
config = root / "config/climate_daily_parameter_bundle_v1.toml"


def fixture() -> tuple[dict[str, object], dict[str, object]]:
    records = []
    output_records = []
    for role in ("baseline", "pulse"):
        record = {
            "climate_draw_id": "synthetic-draw",
            "esm_id": "synthetic-esm",
            "member_id": "synthetic-member",
            "grid_id": "synthetic-grid",
            "calendar": "noleap",
            "year": 2040,
            "month": 7,
            "pulse_scale_tonnes_c": 1.0,
            "path_role": role,
            "wet_probability_given_previous_dry": 0.2,
            "wet_probability_given_previous_wet": 0.7,
            "wet_amount_gamma_shape": 1.5,
            "wet_amount_gamma_scale_mm": 3.0,
            "spatial_dependence_parameter_sha256": "a" * 64,
            "temperature_precipitation_coupling_parameter_sha256": "b" * 64,
            "support_flag": "within",
        }
        records.append(record)
        output_records.append({
            key: record[key]
            for key in (
                "climate_draw_id", "esm_id", "member_id", "grid_id", "calendar",
                "year", "month", "pulse_scale_tonnes_c", "path_role", "support_flag",
            )
        })
    parameter_bundle: dict[str, object] = {
        "schema": "climate_daily_parameter_bundle_v1",
        "generator_id": "kemsley_markov_gamma",
        "paper_doi": "10.1002/joc.8320",
        "generator_code_identity": "synthetic-unimplemented-code-id",
        "parameterization_id": "synthetic-parameterization-v1",
        "records": records,
    }
    observed_hash = canonical_parameter_bundle_sha256(parameter_bundle)
    for record in output_records:
        record["parameter_bundle_sha256"] = observed_hash
    output_bundle: dict[str, object] = {
        "receipt": {
            "generator_code_identity": parameter_bundle["generator_code_identity"],
            "parameter_bundle_sha256": observed_hash,
        },
        "records": output_records,
    }
    return parameter_bundle, output_bundle


def expect_failure(mutator, message: str) -> None:
    parameter_bundle, output_bundle = fixture()
    mutator(parameter_bundle, output_bundle)
    try:
        validate_parameter_bundle(parameter_bundle, output_bundle, config, root)
    except ValueError as error:
        assert message in str(error), str(error)
    else:
        raise AssertionError(f"synthetic parameter corruption passed: {message}")


parameter_bundle, output_bundle = fixture()
result = validate_parameter_bundle(parameter_bundle, output_bundle, config, root)
assert result["parameter_record_count"] == 2
assert result["parameter_bundle_sha256"] == output_bundle["receipt"]["parameter_bundle_sha256"]
assert result["generator_implementation_authorized"] is False
assert result["scientific_validity_established"] is False
assert result["damage_or_scc_authorized"] is False

reordered = deepcopy(parameter_bundle)
reordered["records"].reverse()
assert canonical_parameter_bundle_sha256(reordered) == result["parameter_bundle_sha256"]

expect_failure(lambda parameters, output: parameters.update(extra=True), "exact top-level fields")
expect_failure(lambda parameters, output: parameters["records"].append(deepcopy(parameters["records"][0])), "duplicate parameter record key")
expect_failure(lambda parameters, output: parameters["records"][0].update(wet_probability_given_previous_dry=1.1), "probability is invalid")
expect_failure(lambda parameters, output: parameters["records"][0].update(wet_amount_gamma_shape=0.0), "positive value is invalid")
expect_failure(lambda parameters, output: parameters["records"][0].update(spatial_dependence_parameter_sha256="bad"), "SHA-256 is invalid")
expect_failure(lambda parameters, output: parameters["records"].pop(), "record keys do not match exactly")
expect_failure(lambda parameters, output: output["records"][0].update(support_flag="above"), "support flags differ")
expect_failure(lambda parameters, output: output["receipt"].update(generator_code_identity="other"), "generator code identity differs")
expect_failure(lambda parameters, output: parameters["records"][0].update(wet_amount_gamma_scale_mm=4.0), "hash does not match canonical bundle")
expect_failure(lambda parameters, output: output["records"][0].update(parameter_bundle_sha256="c" * 64), "monthly record parameter bundle hash")

print("climate daily parameter-bundle synthetic tests passed")
