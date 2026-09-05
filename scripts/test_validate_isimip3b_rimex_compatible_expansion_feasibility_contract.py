#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import tempfile

from validate_isimip3b_rimex_compatible_expansion_feasibility_contract import validate


root = Path(__file__).resolve().parents[1]
config = root / "config/isimip3b_rimex_compatible_expansion_feasibility_v1.toml"
result = validate(config, root)
assert result["status"] == "validated_before_metadata_only_feasibility_audit"
assert result["minimum_distinct_training_templates_per_holdout"] == 51
assert result["dependence_fit_authorized"] is False
assert result["acquisition_authorized"] is False

with tempfile.TemporaryDirectory() as temporary:
    tampered = Path(temporary) / "contract.toml"
    tampered.write_text(
        config.read_text(encoding="utf-8").replace(
            "maximum_members_per_esm_family = 2",
            "maximum_members_per_esm_family = 3",
        ),
        encoding="utf-8",
    )
    try:
        validate(tampered, root)
    except ValueError as error:
        assert "ESM-family cap changed" in str(error)
    else:
        raise AssertionError("weakened ESM-family cap passed")

print("compatible expansion feasibility preregistration tests passed")
