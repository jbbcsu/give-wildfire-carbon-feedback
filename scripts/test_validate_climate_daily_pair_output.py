#!/usr/bin/env python3
"""Tiny synthetic success and failure fixtures for the future output gate."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import math
from pathlib import Path

from validate_climate_daily_pair_output import (
    canonical_monthly_inputs_sha256,
    canonical_records_sha256,
    validate_bundle,
)
from validate_climate_daily_parameter_bundle import canonical_parameter_bundle_sha256


root = Path(__file__).resolve().parents[1]
config = root / "config/climate_daily_pair_output_schema_v1.toml"
parameter_sha = "b" * 64
innovation_sha = "d" * 64
spatial_sha = "a" * 64
coupling_sha = "c" * 64


def daily(
    calendar_name: str,
    year: int,
    month: int,
    day_count: int,
    value_before: float,
    value_after: float,
) -> list[dict[str, object]]:
    return [
        {
            "date_or_model_day": f"{year:04d}-{month:02d}-{day:02d}",
            "precipitation_mm": value_before if day < 15 else value_after,
        }
        for day in range(1, day_count + 1)
    ]


def record(
    group_id: str,
    calendar_name: str,
    year: int,
    month: int,
    scale: float,
    role: str,
    values: list[dict[str, object]],
) -> dict[str, object]:
    return {
        "climate_draw_id": "synthetic-draw-001",
        "esm_id": "synthetic-esm",
        "member_id": "synthetic-member",
        "grid_id": f"synthetic-grid-{group_id}",
        "calendar": calendar_name,
        "year": year,
        "month": month,
        "pulse_scale_tonnes_c": scale,
        "path_role": role,
        "first_divergence_date_or_model_day": f"{year:04d}-{month:02d}-15",
        "monthly_precipitation_mm": math.fsum(float(item["precipitation_mm"]) for item in values),
        "monthly_temperature_degc": 20.0,
        "parameter_bundle_sha256": parameter_sha,
        "monthly_innovation_digest": hashlib.sha256(group_id.encode("utf-8")).hexdigest(),
        "support_flag": "within",
        "daily": values,
    }


def valid_fixture() -> tuple[dict[str, object], dict[str, object]]:
    records: list[dict[str, object]] = []
    groups = [
        ("gregorian-leap", "proleptic_gregorian", 2000, 2, 29, 2.0),
        ("noleap", "noleap", 2000, 2, 28, 2.0),
        ("360-day", "360_day", 2001, 2, 30, 2.0),
        ("zero-month", "gregorian", 2001, 4, 30, 0.0),
    ]
    for group_id, calendar_name, year, month, day_count, baseline_amount in groups:
        baseline = daily(calendar_name, year, month, day_count, baseline_amount, baseline_amount)
        for scale in (0.0, 4.0, 2.0, 1.0):
            records.append(record(group_id, calendar_name, year, month, scale, "baseline", deepcopy(baseline)))
            after = baseline_amount if scale == 0 or baseline_amount == 0 else baseline_amount + scale / 32.0
            pulse_values = daily(calendar_name, year, month, day_count, baseline_amount, after)
            records.append(record(group_id, calendar_name, year, month, scale, "pulse", pulse_values))
    parameter_bundle: dict[str, object] = {
        "schema": "climate_daily_parameter_bundle_v1",
        "generator_id": "kemsley_markov_gamma",
        "paper_doi": "10.1002/joc.8320",
        "generator_code_identity": "synthetic-fixture-no-generator-implementation",
        "parameterization_id": "synthetic-named-parameters-v1",
        "records": [
            {
                **{field: item[field] for field in (
                    "climate_draw_id", "esm_id", "member_id", "grid_id", "calendar", "year", "month",
                    "pulse_scale_tonnes_c", "path_role",
                )},
                "wet_probability_given_previous_dry": 0.25,
                "wet_probability_given_previous_wet": 0.60,
                "wet_amount_gamma_shape": 2.0,
                "wet_amount_gamma_scale_mm": 4.0,
                "spatial_dependence_parameter_sha256": spatial_sha,
                "temperature_precipitation_coupling_parameter_sha256": coupling_sha,
                "support_flag": item["support_flag"],
            }
            for item in records
        ],
    }
    observed_parameter_sha = canonical_parameter_bundle_sha256(parameter_bundle)
    for item in records:
        item["parameter_bundle_sha256"] = observed_parameter_sha
    bundle: dict[str, object] = {
        "schema": "climate_daily_pair_output_bundle_v1",
        "receipt": {
            "contract_sha256": "2e5c4e57f33931f32bcde3c0bc0673c012820ccd4723ace28a8197a8333d8b39",
            "generator_code_identity": "synthetic-fixture-no-generator-implementation",
            "paper_doi": "10.1002/joc.8320",
            "parameter_bundle_sha256": observed_parameter_sha,
            "monthly_input_sha256": canonical_monthly_inputs_sha256(records),
            "rng_algorithm": "synthetic-keyed-fixture",
            "rng_version": "test-only-v1",
            "seed_namespace": "synthetic-schema-gate",
            "daily_output_sha256": canonical_records_sha256(records),
            "maximum_monthly_mass_error_mm": 0.0,
            "peak_resident_memory_bytes": 1,
        },
        "records": records,
    }
    return bundle, parameter_bundle


def valid_bundle() -> dict[str, object]:
    return valid_fixture()[0]


def rehash(bundle: dict[str, object]) -> None:
    bundle["receipt"]["daily_output_sha256"] = canonical_records_sha256(bundle["records"])


def expect_failure(mutator, message: str, *, refresh_hash: bool = True) -> None:
    bundle, parameter_bundle = valid_fixture()
    mutator(bundle)
    if refresh_hash:
        rehash(bundle)
    try:
        validate_bundle(bundle, config, root, parameter_bundle)
    except ValueError as error:
        assert message in str(error), str(error)
    else:
        raise AssertionError(f"synthetic failure fixture passed: {message}")


def change_scale_digest(bundle: dict[str, object]) -> None:
    bundle["records"][2]["monthly_innovation_digest"] = "e" * 64
    bundle["records"][3]["monthly_innovation_digest"] = "e" * 64


def conserve_but_break_identity(bundle: dict[str, object], record_index: int, first_day: int, second_day: int) -> None:
    daily_records = bundle["records"][record_index]["daily"]
    daily_records[first_day]["precipitation_mm"] += 0.125
    daily_records[second_day]["precipitation_mm"] -= 0.125


fixture_bundle, fixture_parameters = valid_fixture()
result = validate_bundle(fixture_bundle, config, root, fixture_parameters)
assert result["record_count"] == 32
assert result["pair_count"] == 16
assert result["cross_pulse_month_count"] == 4
assert result["maximum_monthly_mass_error_mm"] == 0
assert result["monthly_input_sha256"] == valid_bundle()["receipt"]["monthly_input_sha256"]
assert result["parameter_record_count"] == 32
assert result["parameter_bundle_sha256"] == fixture_bundle["receipt"]["parameter_bundle_sha256"]
assert result["generator_implementation_authorized"] is False
assert result["scientific_validity_established"] is False
assert result["damage_or_scc_authorized"] is False

expect_failure(lambda bundle: bundle["receipt"].pop("rng_version"), "exact required fields")
expect_failure(lambda bundle: bundle["records"].append(deepcopy(bundle["records"][0])), "duplicate monthly record key")
expect_failure(lambda bundle: bundle["records"][1].update(monthly_innovation_digest="e" * 64), "innovation digests differ")
expect_failure(change_scale_digest, "innovation digest changes across pulse scales")
expect_failure(lambda bundle: bundle["records"][1]["daily"][0].update(precipitation_mm=2.5), "separate monthly conservation")
expect_failure(lambda bundle: conserve_but_break_identity(bundle, 1, 20, 21), "zero-pulse daily identity")
expect_failure(lambda bundle: conserve_but_break_identity(bundle, 3, 0, 1), "pre-divergence daily identity")
expect_failure(lambda bundle: bundle["records"][0]["daily"].pop(), "missing, duplicate, or unordered calendar days")
expect_failure(lambda bundle: bundle["records"][0].update(unregistered_field=True), "exact monthly fields")
expect_failure(lambda bundle: bundle["receipt"].update(maximum_monthly_mass_error_mm=1e-6), "does not reconcile")
expect_failure(lambda bundle: bundle["receipt"].update(peak_resident_memory_bytes=2147483649), "exceeds interface ceiling")
expect_failure(lambda bundle: bundle["receipt"].update(daily_output_sha256="0" * 64), "daily output hash", refresh_hash=False)


def assert_daily_values_are_excluded() -> None:
    bundle, parameter_bundle = valid_fixture()
    original_input_hash = bundle["receipt"]["monthly_input_sha256"]
    conserve_but_break_identity(bundle, 3, 20, 21)
    rehash(bundle)
    result = validate_bundle(bundle, config, root, parameter_bundle)
    assert result["monthly_input_sha256"] == original_input_hash


def assert_innovation_digest_is_excluded() -> None:
    bundle, parameter_bundle = valid_fixture()
    original_input_hash = bundle["receipt"]["monthly_input_sha256"]
    group = bundle["records"][:8]
    for item in group:
        item["monthly_innovation_digest"] = innovation_sha
    rehash(bundle)
    result = validate_bundle(bundle, config, root, parameter_bundle)
    assert result["monthly_input_sha256"] == original_input_hash


def assert_record_order_is_excluded() -> None:
    bundle, parameter_bundle = valid_fixture()
    original_input_hash = bundle["receipt"]["monthly_input_sha256"]
    bundle["records"].reverse()
    rehash(bundle)
    result = validate_bundle(bundle, config, root, parameter_bundle)
    assert result["monthly_input_sha256"] == original_input_hash


assert_daily_values_are_excluded()
assert_innovation_digest_is_excluded()
assert_record_order_is_excluded()
expect_failure(lambda bundle: bundle["records"][0].update(monthly_temperature_degc=20.25), "monthly input hash")
expect_failure(lambda bundle: bundle["records"][0].update(support_flag="above"), "monthly input hash")

print("climate daily-pair output synthetic schema tests passed")
