#!/usr/bin/env python3
"""Synthetic support-selection invariants for the bounded NASS smoke."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pandas as pd


SCRIPT = Path(__file__).with_name("prepare_nass_practice_pair_support.py")
sys.path.insert(0, str(SCRIPT.parent))
spec = importlib.util.spec_from_file_location("practice_support", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def frame(crop: str, practice: str, value: float) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "crop": [crop],
            "year": [1981],
            "county_geoid": ["31039"],
            "practice": [practice],
            "yield_eligible": [True],
            "analysis_value": [value],
            "value_raw": [str(value)],
            "state_alpha": ["NE"],
            "county_name": ["CUMING"],
        }
    )


frames = [
    frame("corn", "IRRIGATED", 120),
    frame("corn", "NON-IRRIGATED", 74.2),
    frame("soybeans", "IRRIGATED", 41),
    frame("soybeans", "NON-IRRIGATED", 35),
]
output = module.select_support(frames, "31039", 1981)
assert len(output) == 4
assert set(output.outcome_crop) == {"corn_grain", "soybeans"}
assert set(output.irrigation_practice) == {"irrigated", "non_irrigated"}
assert output.yield_bu_acre.sum() == 270.2
assert output.weather_exposure_role.eq("shared_county_polygon_proxy_across_practices").all()
assert not output.response_estimation_authorized.any()
assert not output.scc_authorized.any()

for invalid_frames, expected in [
    (frames[:-1], "both irrigation practices"),
    (frames + [frames[0]], "duplicate crop/practice"),
    ([frames[0], frames[1]], "both corn and soybean"),
]:
    try:
        module.select_support(invalid_frames, "31039", 1981)
    except ValueError as error:
        assert expected in str(error), str(error)
    else:
        raise AssertionError(f"Invalid support should fail: {expected}")

try:
    module.select_support(frames, "3103", 1981)
except ValueError as error:
    assert "five-digit GEOID" in str(error)
else:
    raise AssertionError("Malformed county GEOID should fail")

print("NASS paired-practice support selection tests passed")
