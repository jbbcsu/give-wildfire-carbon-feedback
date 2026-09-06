#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import tempfile

from validate_climate_daily_pair_output_schema_contract import validate


root = Path(__file__).resolve().parents[1]
config = root / "config/climate_daily_pair_output_schema_v1.toml"


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
assert result["status"] == "output_schema_preregistered_no_generator_or_real_output"
assert result["future_bundle_schema"] == "climate_daily_pair_output_bundle_v1"
assert result["generator_implementation_authorized"] is False
assert result["damage_or_scc_authorized"] is False

expect_failure("generator_implementation_authorized = false", "generator_implementation_authorized = true", "closed gate")
expect_failure("cross_pulse_scale_innovation_digest_identity_required = true", "cross_pulse_scale_innovation_digest_identity_required = false", "cross_pulse_scale")
expect_failure("absolute_conservation_tolerance_mm = 1e-9", "absolute_conservation_tolerance_mm = 1e-6", "absolute tolerance")
expect_failure("pre_divergence_daily_identity_required = true", "pre_divergence_daily_identity_required = false", "pre_divergence")
expect_failure("no_real_daily_climate_values = true", "no_real_daily_climate_values = false", "no_real_daily_climate_values")

print("climate daily-pair output schema contract tests passed")
