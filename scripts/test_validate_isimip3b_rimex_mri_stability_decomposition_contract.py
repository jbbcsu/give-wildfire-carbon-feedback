#!/usr/bin/env python3
from __future__ import annotations

import tempfile
from pathlib import Path

from validate_isimip3b_rimex_mri_stability_decomposition_contract import validate


root = Path(__file__).resolve().parents[1]
config = root / "config/isimip3b_rimex_mri_stability_decomposition_v1.toml"
result = validate(config, root)
assert result["status"] == "validated_before_mri_decomposition_outputs"
assert result["focal_esm"] == "MRI-ESM2-0"
assert result["shared_scenarios"] == ["ssp126", "ssp370"]
assert result["dependence_fit_authorized"] is False

with tempfile.TemporaryDirectory() as temporary:
    tampered = Path(temporary) / "contract.toml"
    tampered.write_text(
        config.read_text(encoding="utf-8").replace(
            "locked_original_maximum_difference_gate = 0.15",
            "locked_original_maximum_difference_gate = 0.20",
        ),
        encoding="utf-8",
    )
    try:
        validate(tampered, root)
    except ValueError as error:
        assert "locked maximum gate changed" in str(error)
    else:
        raise AssertionError("tampered locked maximum gate passed")

print("MRI dependence-failure decomposition preregistration tests passed")
