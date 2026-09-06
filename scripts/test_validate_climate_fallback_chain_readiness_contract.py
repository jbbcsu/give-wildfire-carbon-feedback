#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import tempfile

from validate_climate_fallback_chain_readiness_contract import validate


root = Path(__file__).resolve().parents[1]
config = root / "config/climate_fallback_chain_readiness_v1.toml"
result = validate(config, root)
assert result["status"] == "validated_before_fallback_source_metadata_snapshot"
assert result["component_ids"] == ["mesmer_m_tp", "kemsley_markov_gamma", "mesmer_x_rx1day", "stitches"]
assert result["emulator_fit_authorized"] is False
assert result["damage_or_scc_authorized"] is False

with tempfile.TemporaryDirectory() as temporary:
    tampered = Path(temporary) / "contract.toml"
    tampered.write_text(
        config.read_text(encoding="utf-8").replace(
            "exact_monthly_precipitation_conservation_required = true",
            "exact_monthly_precipitation_conservation_required = false",
        ),
        encoding="utf-8",
    )
    try:
        validate(tampered, root)
    except ValueError as error:
        assert "exact_monthly_precipitation_conservation_required" in str(error)
    else:
        raise AssertionError("weakened monthly-conservation gate passed")

print("climate fallback readiness preregistration tests passed")
