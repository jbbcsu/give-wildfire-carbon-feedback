#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import tempfile

from evaluate_climate_fallback_chain_readiness import evaluate


root = Path(__file__).resolve().parents[1]
config = root / "config/climate_fallback_chain_readiness_v1.toml"
preregistration = root / "data/provenance/climate_fallback_chain_readiness_preregistration_20260905.json"
snapshot = root / "data/provenance/climate_fallback_chain_source_snapshot_20260905.toml"
result = evaluate(config, preregistration, snapshot, root)
assert result["status"] == "fallback_not_executable_no_fit"
assert result["public_executable_code_missing"] == ["kemsley_markov_gamma"]
assert result["end_to_end_capability_count"] == 15
assert result["end_to_end_capability_pass_count"] == 1
assert result["climate_payload_bytes_downloaded"] == 0
assert result["emulator_fit_authorized"] is False
assert result["damage_or_scc_authorized"] is False

with tempfile.TemporaryDirectory() as temporary:
    tampered = Path(temporary) / "snapshot.toml"
    tampered.write_text(
        snapshot.read_text(encoding="utf-8").replace(
            'public_executable_source = false\nrepository_url = ""',
            'public_executable_source = true\nrepository_url = ""',
            1,
        ),
        encoding="utf-8",
    )
    try:
        evaluate(config, preregistration, tampered, root)
    except ValueError as error:
        assert "repository URL missing: kemsley_markov_gamma" in str(error)
    else:
        raise AssertionError("unsupported executable-source promotion passed")

print("climate fallback readiness audit tests passed")
