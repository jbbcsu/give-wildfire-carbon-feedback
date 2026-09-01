#!/usr/bin/env python3
"""Synthetic contract checks for the expanded FAIR training join."""
from __future__ import annotations

import pandas as pd

from assemble_isimip3b_expanded_fair_training import ESMS, FEATURES, normalize_esm, validate_frame


assert normalize_esm(pd.Series(["mri-esm2-0", "GFDL-ESM4"])).tolist() == ["MRI-ESM2-0", "GFDL-ESM4"]
rows = []
for esm in sorted(ESMS):
    member = "r1i1p1f2" if esm == "UKESM1-0-LL" else "r1i1p1f1"
    for feature in sorted(FEATURES):
        rows.append({
            "harvest_year": 2042, "year": 2042, "lat": 1.0, "lon_360": 2.0,
            "crop": "mai", "irrigation": "noirr", "esm_id": esm, "member_id": member,
            "scenario": "ssp126", "gmst_source_id": f"source-{esm}", "gmst_value_k": 290.0,
            "gmst_esm_id": esm, "gmst_member_id": member, "feature_family": feature,
            "feature_value": 1.0,
        })
frame = pd.DataFrame(rows)
validated = validate_frame(frame, expected_rows=len(frame), expected_years={2042}, expected_scenarios={"ssp126"})
assert len(validated) == len(ESMS) * len(FEATURES)
broken = frame.copy()
broken.loc[0, "gmst_esm_id"] = "IPSL-CM6A-LR"
try:
    validate_frame(broken, expected_rows=len(broken), expected_years={2042}, expected_scenarios={"ssp126"})
except ValueError as error:
    assert "identity" in str(error)
else:
    raise AssertionError("expected feature/GMST identity failure")

print("expanded FAIR training join synthetic tests passed")
