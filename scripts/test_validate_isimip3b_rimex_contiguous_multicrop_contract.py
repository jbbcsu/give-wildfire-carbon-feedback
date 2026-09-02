#!/usr/bin/env python3
from __future__ import annotations

import tempfile
from pathlib import Path

from validate_isimip3b_rimex_contiguous_multicrop_contract import validate


root = Path(__file__).resolve().parents[1]
config = root / "config/isimip3b_rimex_contiguous_multicrop_regime_v1.toml"
result = validate(config, root)
assert result["status"] == "preregistered_before_feature_construction"
assert len(result["cells"]) == 12
assert sum(cell["expected_season_rows"] for cell in result["cells"]) == 214_928
assert sum(cell["expected_centered_season_rows"] for cell in result["cells"]) == 61_408
assert result["irrigation_treatment_effect_authorized"] is False

expanded_config = root / "config/isimip3b_rimex_contiguous_multicrop_regime_gfdl_ssp370_v1.toml"
expanded = validate(expanded_config, root)
assert expanded["realization"] == {
    "esm": "GFDL-ESM4", "member": "r1i1p1f1", "scenario": "ssp370"
}
assert len(expanded["cells"]) == 12

with tempfile.TemporaryDirectory() as temporary:
    tampered = Path(temporary) / "contract.toml"
    tampered.write_text(config.read_text().replace(
        "damage_or_scc_authorized = false", "damage_or_scc_authorized = true"
    ), encoding="utf-8")
    try:
        validate(tampered, root)
    except ValueError as error:
        assert "closed gate" in str(error)
    else:
        raise AssertionError("tampered contract opened the damage/SCC gate")

with tempfile.TemporaryDirectory() as temporary:
    tampered = Path(temporary) / "contract.toml"
    tampered.write_text(config.read_text().replace(
        'scenario = "ssp126"', 'scenario = "ssp370"'
    ), encoding="utf-8")
    try:
        validate(tampered, root)
    except ValueError as error:
        assert "source receipt realization differs" in str(error)
    else:
        raise AssertionError("contract accepted a source receipt from another scenario")

with tempfile.TemporaryDirectory() as temporary:
    tampered = Path(temporary) / "contract.toml"
    tampered.write_text(config.read_text().replace(
        'esm = "GFDL-ESM4"', 'esm = "Unfrozen-ESM"'
    ), encoding="utf-8")
    try:
        validate(tampered, root)
    except ValueError as error:
        assert "frozen ESM/member matrix" in str(error)
    else:
        raise AssertionError("contract accepted an ESM outside the frozen matrix")

print("contiguous multi-ESM multi-crop contract tests passed")
