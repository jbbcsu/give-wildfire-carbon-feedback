#!/usr/bin/env python3
"""Synthetic failure test for paired-practice coefficient identity audit."""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from validate_us_paired_practice_gap_association_independent import validate  # noqa: E402


with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    gates = {
        "causal_claim_authorized": False,
        "damage_claim_authorized": False,
        "scc_claim_authorized": False,
    }
    paired = {
        "schema": "us_paired_practice_gap_association_result_v1",
        **gates,
        "estimates": [{
            "crop": "corn_grain", "form": "quantity", "rows": 100,
            "coefficients": [{"term": "rain", "estimate": 1.5}],
        }],
    }
    separate = {
        "schema": "us_direct_practice_precipitation_association_result_v1",
        **gates,
        "estimates": [
            {"crop": "corn_grain", "form": "quantity", "irrigation_practice": "irrigated", "rows": 100, "coefficients": [{"term": "rain", "estimate": 2.0}]},
            {"crop": "corn_grain", "form": "quantity", "irrigation_practice": "non_irrigated", "rows": 100, "coefficients": [{"term": "rain", "estimate": 0.5}]},
        ],
    }
    paired_path, separate_path = root / "paired.json", root / "separate.json"
    paired_path.write_text(json.dumps(paired), encoding="utf-8")
    separate_path.write_text(json.dumps(separate), encoding="utf-8")
    result = validate(paired_path, separate_path)
    assert result["comparisons"] == 1
    assert result["maximum_absolute_difference"] == 0
    paired["estimates"][0]["coefficients"][0]["estimate"] = 1.6
    paired_path.write_text(json.dumps(paired), encoding="utf-8")
    try:
        validate(paired_path, separate_path)
    except ValueError as error:
        assert "identity differs" in str(error)
    else:
        raise AssertionError("incorrect paired coefficient was accepted")

print("paired-practice coefficient identity synthetic tests passed")
