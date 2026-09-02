#!/usr/bin/env python3
"""Synthetic and fail-closed tests for the RIME-X benchmark contract."""
from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np

from validate_isimip3b_rimex_feature_response_benchmark import interpolate_quantile_map, validate


root = Path(__file__).resolve().parents[1]
config = root / "config/isimip3b_rimex_feature_response_benchmark_v1.toml"
result = validate(config, root)
assert result["status"] == "validated_preregistered_benchmark_real_fit_blocked_by_contiguous_support_and_joint_dependence"
smoke = result["engineering_smoke"]
assert smoke["zero_pulse_identity"] is True
assert smoke["pre_divergence_identity"] is True
assert smoke["out_of_support_extrapolation_rejected"] is True
assert smoke["maximum_normalized_pulse_disagreement"] <= 1e-10

levels = np.array([0.0, 0.1])
quantiles = np.array([0.0, 1.0])
values = np.array([[1.0, 3.0], [2.0, 4.0]])
value, supported = interpolate_quantile_map(levels, quantiles, values, 0.05, 0.25)
assert supported and abs(value - 2.0) <= 1e-12
outside, supported = interpolate_quantile_map(levels, quantiles, values, 0.2, 0.25)
assert not supported and np.isnan(outside)

for bad_levels, message in [
    (np.array([0.0, 0.0]), "strictly increasing"),
    (np.array([0.1, 0.0]), "strictly increasing"),
]:
    try:
        interpolate_quantile_map(bad_levels, quantiles, values, 0.05, 0.25)
    except ValueError as error:
        assert message in str(error)
    else:
        raise AssertionError("invalid warming levels were accepted")

with tempfile.TemporaryDirectory() as temporary:
    tampered = Path(temporary) / "contract.toml"
    tampered.write_text(
        config.read_text(encoding="utf-8").replace("real_feature_fit_authorized = false", "real_feature_fit_authorized = true"),
        encoding="utf-8",
    )
    try:
        validate(tampered, root)
    except ValueError as error:
        assert "closed gate" in str(error)
    else:
        raise AssertionError("contract opened the real-fit gate")

print("ISIMIP3b RIME-X feature benchmark tests passed")
