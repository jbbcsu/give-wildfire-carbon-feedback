#!/usr/bin/env python3
"""Synthetic pairing gates for the U.S. practice-gap association."""
from __future__ import annotations

import copy
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from estimate_us_paired_practice_gap_association import build_paired_frame  # noqa: E402


config = {
    "input": {
        "crops": ["corn_grain"],
        "practices": ["non_irrigated", "irrigated"],
        "year_min": 2000,
        "year_max": 2001,
    }
}
rows = []
for year in (2000, 2001):
    for practice, value in (("non_irrigated", 100.0), ("irrigated", 120.0)):
        rows.append({
            "county_geoid": "01001",
            "state": "AL",
            "outcome_crop": "corn_grain",
            "harvest_year": year,
            "irrigation_practice": practice,
            "yield_bu_acre": value + year - 2000,
            "precip_mm": 500.0 + year - 2000,
            "stage1_precip_share": 0.2,
            "stage2_precip_share": 0.3,
            "stage1_tmean_c": 15.0,
            "stage2_tmean_c": 20.0,
            "stage3_tmean_c": 22.0,
            "weather_exposure_shared_across_practices": True,
        })
frame = pd.DataFrame(rows)
paired = build_paired_frame(frame, config)
assert len(paired) == 2
assert set(paired["harvest_year"]) == {2000, 2001}
assert (paired["log_yield_gap"] > 0).all()

missing = frame.drop(index=0)
try:
    build_paired_frame(missing, config)
except ValueError as error:
    assert "exact practice pair" in str(error)
else:
    raise AssertionError("missing practice pair was accepted")

different_weather = copy.deepcopy(frame)
different_weather.loc[0, "precip_mm"] = 499.0
try:
    build_paired_frame(different_weather, config)
except ValueError as error:
    assert "weather exposure differs" in str(error)
else:
    raise AssertionError("practice-specific weather mismatch was accepted")

print("U.S. paired-practice yield-gap association synthetic tests passed")
