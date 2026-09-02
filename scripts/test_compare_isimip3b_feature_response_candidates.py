#!/usr/bin/env python3
"""Regression and failure tests for the candidate comparison."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from compare_isimip3b_feature_response_candidates import compare


root = Path(__file__).resolve().parents[1]
affine = pd.read_csv(root / "data/provenance/isimip3b_structural_feature_response_holdouts_20260901.csv")
physical = pd.read_csv(root / "data/provenance/isimip3b_physical_link_feature_response_holdouts_20260901.csv")
result = compare(affine, physical)
assert result["summary"]["exact_key_comparisons"] == 88
assert result["summary"]["physical_rescues_affine_failure"] == 0
assert result["production_promoted"] is False

broken = physical.iloc[:-1].copy()
try:
    compare(affine, broken)
except ValueError as error:
    assert "key product" in str(error), error
else:
    raise AssertionError("missing comparison key should fail closed")

print("ISIMIP3b feature-response candidate comparison tests passed")
