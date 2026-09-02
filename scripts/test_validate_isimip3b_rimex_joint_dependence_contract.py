#!/usr/bin/env python3
from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

from validate_isimip3b_rimex_joint_dependence_contract import (
    COORDINATES, decode_physical, ecc_q, encode_physical, validate,
)


root = Path(__file__).resolve().parents[1]
config = root / "config/isimip3b_rimex_joint_dependence_v1.toml"
result = validate(config, root)
assert result["status"] == "preregistered_synthetic_mechanics_pass_pilot_template_support_insufficient"
assert result["synthetic_smoke"]["physical_failures"] == 0
assert result["synthetic_smoke"]["zero_pulse_identity"] is True

frame = pd.DataFrame({
    "tmean_c": [20.0, 25.0], "precip_mm": [100.0, 200.0], "season_days": [100.0, 100.0],
    "wet_days_n": [0.0, 100.0], "cdd_max_days": [100.0, 0.0],
    "rx1day_mm": [10.0, 20.0], "rx5day_mm": [20.0, 50.0],
    "stage1_precip_share": [0.0, 0.2], "stage2_precip_share": [0.4, 0.3],
    "stage3_precip_share": [0.6, 0.5],
})
linked = encode_physical(frame, 1e-6)
decoded = decode_physical(linked, frame.season_days.to_numpy(), 1e-6)
for column in ["tmean_c", "precip_mm", "wet_days_n", "cdd_max_days", "rx1day_mm", "rx5day_mm", "stage1_precip_share", "stage2_precip_share", "stage3_precip_share"]:
    assert np.allclose(decoded[column], frame[column], rtol=0, atol=1e-10), column

marginal = np.arange(24, dtype=float).reshape(3, len(COORDINATES))
template = marginal[::-1].copy()
first = ecc_q(marginal, template, "seed")
second = ecc_q(marginal, template, "seed")
assert np.array_equal(first, second)
for column in range(marginal.shape[1]):
    assert np.array_equal(np.sort(first[:, column]), np.sort(marginal[:, column]))

with tempfile.TemporaryDirectory() as temporary:
    tampered = Path(temporary) / "contract.toml"
    tampered.write_text(config.read_text().replace("real_joint_fit_authorized = false", "real_joint_fit_authorized = true"), encoding="utf-8")
    try:
        validate(tampered, root)
    except ValueError as error:
        assert "closed gate" in str(error)
    else:
        raise AssertionError("tampered contract opened the real joint-fit gate")

print("RIME-X joint-dependence contract tests passed")
