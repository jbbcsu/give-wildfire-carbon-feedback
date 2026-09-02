#!/usr/bin/env python3
"""Contract regression and fail-closed physical-link tests."""
from __future__ import annotations

import tempfile
from pathlib import Path

from validate_isimip3b_physical_link_feature_response_contract import validate


root = Path(__file__).resolve().parents[1]
config = root / "config/isimip3b_physical_link_feature_response_v1.toml"
result = validate(config, root)
assert result["status"] == "validated_preregistered_candidate_not_fitted_or_promoted"
assert result["links"]["composition"] == ["stage1_precip_share", "stage2_precip_share", "stage3_precip_share"]
assert result["damage_or_scc_authorized"] is False

with tempfile.TemporaryDirectory() as directory:
    bad = Path(directory) / "bad.toml"
    text = config.read_text(encoding="utf-8").replace(
        'composition_link = "centered_log_ratio"', 'composition_link = "independent_identity"', 1
    )
    bad.write_text(text, encoding="utf-8")
    try:
        validate(bad, root)
    except ValueError as error:
        assert "composition link" in str(error), error
    else:
        raise AssertionError("independent stage-share links should fail closed")

print("ISIMIP3b physical-link feature-response contract tests passed")
