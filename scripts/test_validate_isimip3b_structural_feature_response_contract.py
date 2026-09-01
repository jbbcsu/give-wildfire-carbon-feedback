#!/usr/bin/env python3
"""Contract regression and fail-closed source-hash test."""
from __future__ import annotations

import tempfile
from pathlib import Path

from validate_isimip3b_structural_feature_response_contract import validate


root = Path(__file__).resolve().parents[1]
config = root / "config/isimip3b_structural_feature_response_v1.toml"
result = validate(config, root)
assert result["status"] == "validated_preregistered_candidate_not_fitted_or_promoted"
assert result["candidate"]["scenario_categorical_effect"] is False
assert result["whole_esm_holdout_required"] is True
assert result["damage_or_scc_authorized"] is False

with tempfile.TemporaryDirectory() as directory:
    bad = Path(directory) / "bad.toml"
    text = config.read_text(encoding="utf-8").replace(
        'scenario_categorical_effect = false', 'scenario_categorical_effect = true', 1
    )
    bad.write_text(text, encoding="utf-8")
    try:
        validate(bad, root)
    except ValueError as error:
        assert "categorical shortcut" in str(error), error
    else:
        raise AssertionError("scenario categorical shortcut should fail closed")

print("ISIMIP3b structural feature-response contract tests passed")
