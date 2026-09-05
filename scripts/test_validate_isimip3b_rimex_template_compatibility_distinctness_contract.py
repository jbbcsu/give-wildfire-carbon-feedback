#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import tempfile

from validate_isimip3b_rimex_template_compatibility_distinctness_contract import validate


root = Path(__file__).resolve().parents[1]
config = root / "config/isimip3b_rimex_template_compatibility_distinctness_v2.toml"
result = validate(config, root)
assert result["status"] == "validated_before_corrected_compatibility_distinctness_audit"
assert result["top_level_receipts_read"] == 6
assert result["nested_compatible_receipts_read"] == 11
assert result["minimum_distinct_training_templates"] == 51
assert result["dependence_fit_authorized"] is False

with tempfile.TemporaryDirectory() as temporary:
    tampered = Path(temporary) / "contract.toml"
    tampered.write_text(
        config.read_text(encoding="utf-8").replace(
            "incompatible_candidate_receipts_contribute_zero_templates = true",
            "incompatible_candidate_receipts_contribute_zero_templates = false",
        ),
        encoding="utf-8",
    )
    try:
        validate(tampered, root)
    except ValueError as error:
        assert "decision gate changed" in str(error)
    else:
        raise AssertionError("incompatible candidate products were allowed")

print("corrected template compatibility/distinctness preregistration tests passed")
