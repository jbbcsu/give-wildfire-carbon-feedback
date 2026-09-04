#!/usr/bin/env python3
from __future__ import annotations

import tempfile
from pathlib import Path

from validate_isimip3b_rimex_dependence_pool_decision_contract import validate


root = Path(__file__).resolve().parents[1]
config = root / "config/isimip3b_rimex_dependence_pool_decision_v1.toml"
result = validate(config, root)
assert result["status"] == "validated_before_pool_decision_audit"
assert result["minimum_distinct_training_templates_per_permitted_pool"] == 51
assert result["dependence_fit_authorized"] is False

with tempfile.TemporaryDirectory() as temporary:
    tampered = Path(temporary) / "contract.toml"
    tampered.write_text(
        config.read_text(encoding="utf-8").replace(
            "minimum_distinct_training_templates_per_permitted_pool = 51",
            "minimum_distinct_training_templates_per_permitted_pool = 24",
        ),
        encoding="utf-8",
    )
    try:
        validate(tampered, root)
    except ValueError as error:
        assert "minimum template gate changed" in str(error)
    else:
        raise AssertionError("weakened template minimum passed")

print("dependence pool decision preregistration tests passed")
