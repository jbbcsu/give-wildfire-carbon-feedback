#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import tempfile

from validate_isimip3b_rimex_temporal_distinctness_contract import validate


root = Path(__file__).resolve().parents[1]
config = root / "config/isimip3b_rimex_temporal_distinctness_v1.toml"
result = validate(config, root)
assert result["status"] == "validated_before_temporal_distinctness_audit"
assert result["top_level_receipts_read"] == 4
assert result["nested_receipts_read"] == 15
assert result["minimum_distinct_training_templates"] == 51
assert result["dependence_fit_authorized"] is False

with tempfile.TemporaryDirectory() as temporary:
    tampered = Path(temporary) / "contract.toml"
    tampered.write_text(
        config.read_text(encoding="utf-8").replace(
            "minimum_distinct_training_templates_per_permitted_pool = 51",
            "minimum_distinct_training_templates_per_permitted_pool = 45",
        ),
        encoding="utf-8",
    )
    try:
        validate(tampered, root)
    except ValueError as error:
        assert "minimum template gate changed" in str(error)
    else:
        raise AssertionError("weakened distinct-template minimum passed")

print("temporal distinctness preregistration tests passed")
