#!/usr/bin/env python3
from __future__ import annotations

import tempfile
from pathlib import Path

from validate_isimip3b_rimex_dependence_stability_contract import validate


root = Path(__file__).resolve().parents[1]
config = root / "config/isimip3b_rimex_dependence_stability_v1.toml"
result = validate(config, root)
assert result["status"] == "validated_preregistered_before_real_template_diagnostic"
assert result["completed_templates_locked"] == 88
assert result["represented_holdouts_locked"] == 7
assert result["real_joint_fit_authorized"] is False

with tempfile.TemporaryDirectory() as temporary:
    tampered = Path(temporary) / "contract.toml"
    tampered.write_text(
        config.read_text(encoding="utf-8").replace(
            "maximum_absolute_difference_max = 0.15",
            "maximum_absolute_difference_max = 0.25",
        ),
        encoding="utf-8",
    )
    try:
        validate(tampered, root)
    except ValueError as error:
        assert "maximum stability tolerance changed" in str(error)
    else:
        raise AssertionError("tampered stability tolerance passed")

print("RIME-X represented-template dependence preregistration tests passed")
