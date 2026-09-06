#!/usr/bin/env python3
"""Tiny synthetic success and failure fixtures for the future output gate."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from validate_climate_daily_pair_output import canonical_records_sha256, validate_bundle


root = Path(__file__).resolve().parents[1]
config = root / "config/climate_daily_pair_output_schema_v1.toml"
parameter_sha = "b" * 64
innovation_sha = "d" * 64


def daily(value_before: float, value_after: float) -> list[dict[str, object]]:
    return [
        {
            "date_or_model_day": f"2001-02-{day:02d}",
            "precipitation_mm": value_before if day < 15 else value_after,
        }
        for day in range(1, 29)
    ]


def record(scale: float, role: str, target: float, values: list[dict[str, object]]) -> dict[str, object]:
    return {
        "climate_draw_id": "synthetic-draw-001",
        "esm_id": "synthetic-esm",
        "member_id": "synthetic-member",
        "grid_id": "synthetic-grid",
        "calendar": "proleptic_gregorian",
        "year": 2001,
        "month": 2,
        "pulse_scale_tonnes_c": scale,
        "path_role": role,
        "first_divergence_date_or_model_day": "2001-02-15",
        "monthly_precipitation_mm": target,
        "monthly_temperature_degc": 20.0,
        "parameter_bundle_sha256": parameter_sha,
        "monthly_innovation_digest": innovation_sha,
        "support_flag": "within",
        "daily": values,
    }


def valid_bundle() -> dict[str, object]:
    baseline = daily(2.0, 2.0)
    cases = [(0.0, 56.0, 2.0), (4.0, 57.75, 2.125), (2.0, 56.875, 2.0625), (1.0, 56.4375, 2.03125)]
    records: list[dict[str, object]] = []
    for scale, target, after in cases:
        records.append(record(scale, "baseline", 56.0, deepcopy(baseline)))
        pulse_values = deepcopy(baseline) if scale == 0 else daily(2.0, after)
        records.append(record(scale, "pulse", target, pulse_values))
    bundle: dict[str, object] = {
        "schema": "climate_daily_pair_output_bundle_v1",
        "receipt": {
            "contract_sha256": "2e5c4e57f33931f32bcde3c0bc0673c012820ccd4723ace28a8197a8333d8b39",
            "generator_code_identity": "synthetic-fixture-no-generator-implementation",
            "paper_doi": "10.1002/joc.8320",
            "parameter_bundle_sha256": parameter_sha,
            "monthly_input_sha256": "c" * 64,
            "rng_algorithm": "synthetic-keyed-fixture",
            "rng_version": "test-only-v1",
            "seed_namespace": "synthetic-schema-gate",
            "daily_output_sha256": canonical_records_sha256(records),
            "maximum_monthly_mass_error_mm": 0.0,
            "peak_resident_memory_bytes": 1,
        },
        "records": records,
    }
    return bundle


def rehash(bundle: dict[str, object]) -> None:
    bundle["receipt"]["daily_output_sha256"] = canonical_records_sha256(bundle["records"])


def expect_failure(mutator, message: str, *, refresh_hash: bool = True) -> None:
    bundle = valid_bundle()
    mutator(bundle)
    if refresh_hash:
        rehash(bundle)
    try:
        validate_bundle(bundle, config, root)
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


result = validate_bundle(valid_bundle(), config, root)
assert result["record_count"] == 8
assert result["pair_count"] == 4
assert result["cross_pulse_month_count"] == 1
assert result["maximum_monthly_mass_error_mm"] == 0
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

print("climate daily-pair output synthetic schema tests passed")
