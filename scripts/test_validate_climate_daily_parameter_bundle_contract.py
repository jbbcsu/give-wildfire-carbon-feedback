#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import tempfile

from validate_climate_daily_parameter_bundle_contract import validate


root = Path(__file__).resolve().parents[1]
config = root / "config/climate_daily_parameter_bundle_v1.toml"


def expect_failure(old: str, new: str, message: str) -> None:
    with tempfile.TemporaryDirectory() as temporary:
        path = Path(temporary) / "contract.toml"
        source = config.read_text(encoding="utf-8")
        assert old in source
        path.write_text(source.replace(old, new, 1), encoding="utf-8")
        try:
            validate(path, root)
        except ValueError as error:
            assert message in str(error), str(error)
        else:
            raise AssertionError(f"tampered contract passed: {message}")


result = validate(config, root)
assert result["status"] == "parameter_bundle_schema_preregistered_no_generator_or_real_parameters"
assert result["probability_fields"] == [
    "wet_probability_given_previous_dry", "wet_probability_given_previous_wet",
]
assert result["strictly_positive_fields"] == ["wet_amount_gamma_shape", "wet_amount_gamma_scale_mm"]
assert result["generator_implementation_authorized"] is False
assert result["damage_or_scc_authorized"] is False

expect_failure("record_order_invariant = true", "record_order_invariant = false", "hashing gate")
expect_failure(
    "record_keys_must_exactly_match_output_monthly_record_keys = true",
    "record_keys_must_exactly_match_output_monthly_record_keys = false",
    "output-linkage gate",
)
expect_failure(
    "gamma_parameters_must_be_strictly_positive = true",
    "gamma_parameters_must_be_strictly_positive = false",
    "parameter-record gate",
)
expect_failure(
    "generator_implementation_authorized = false",
    "generator_implementation_authorized = true",
    "closed gate",
)

print("climate daily parameter-bundle contract tests passed")
