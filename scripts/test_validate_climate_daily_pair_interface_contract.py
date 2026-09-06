#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import tempfile

from validate_climate_daily_pair_interface_contract import validate


root = Path(__file__).resolve().parents[1]
config = root / "config/climate_daily_pair_interface_v1.toml"


def expect_failure(replacement: tuple[str, str], message: str) -> None:
    with tempfile.TemporaryDirectory() as temporary:
        tampered = Path(temporary) / "contract.toml"
        source = config.read_text(encoding="utf-8")
        require_old, replacement_new = replacement
        assert require_old in source
        tampered.write_text(source.replace(require_old, replacement_new, 1), encoding="utf-8")
        try:
            validate(tampered, root)
        except ValueError as error:
            assert message in str(error), str(error)
        else:
            raise AssertionError(f"tampered contract passed: {message}")


result = validate(config, root)
assert result["status"] == "interface_preregistered_no_generator_implementation"
assert result["daily_generator_pinned_public_executable_source_available"] is False
assert result["exact_monthly_conservation_required"] is True
assert result["common_innovations_required"] is True
assert result["generator_implementation_authorized"] is False
assert result["damage_or_scc_authorized"] is False

expect_failure(
    ("daily_generator_pinned_public_executable_source_available = false", "daily_generator_pinned_public_executable_source_available = true"),
    "missing-code blocker changed",
)
expect_failure(
    ("path_independent_call_count_required = true", "path_independent_call_count_required = false"),
    "path_independent_call_count_required",
)
expect_failure(
    ("excluded_key_fields = [\"path_role\"", "excluded_key_fields = [\"not_path_role\""),
    "path-specific key exclusion changed",
)
expect_failure(
    ("absolute_tolerance_mm = 1e-9", "absolute_tolerance_mm = 1e-6"),
    "absolute conservation tolerance changed",
)
expect_failure(
    ("zero_pulse_daily_identity_required = true", "zero_pulse_daily_identity_required = false"),
    "zero_pulse_daily_identity_required",
)
expect_failure(
    ("component_substitution_authorized = false", "component_substitution_authorized = true"),
    "component_substitution_authorized",
)

print("climate daily-pair interface contract tests passed")
