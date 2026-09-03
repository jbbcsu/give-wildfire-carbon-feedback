#!/usr/bin/env python3
"""Synthetic tests for the counts-only national selector-support audit."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile

import numpy as np
import pandas as pd


MODULE_PATH = Path(__file__).with_name("audit_national_irrigation_selector_support.py")
SPEC = importlib.util.spec_from_file_location("selector_support", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def frame() -> pd.DataFrame:
    rows = []
    for crop in ("corn_grain", "soybeans"):
        for year in range(1981, 2020):
            for geoid, share, share_ok, outcome_ok in (
                ("01001", 0.05, True, True),
                ("01003", 0.15, True, year % 2 == 0),
                ("01005", np.nan, False, True),
            ):
                rows.append({
                    "county_geoid": geoid, "outcome_crop": crop, "harvest_year": year,
                    "irrigation_share_vintage": 2017, "irrigation_share": share,
                    "irrigation_share_eligible": share_ok, "outcome_value_eligible": outcome_ok,
                    "rainfed_dominant_10pct": share_ok and share <= 0.10,
                    "rainfed_dominant_20pct": share_ok and share <= 0.20,
                    "rainfed_dominant_30pct": share_ok and share <= 0.30,
                })
    return pd.DataFrame(rows)


with tempfile.TemporaryDirectory() as folder:
    path = Path(folder) / "panel.parquet"
    good = frame()
    good.to_parquet(path, index=False)
    result = MODULE.audit(path)
    assert result["yield_magnitudes_read"] is False
    assert len(result["results"]) == 2
    corn = next(item for item in result["results"] if item["crop"] == "corn_grain")
    assert corn["panel_county_years"] == 117
    assert corn["thresholds"][0]["selected_county_years"] == 39
    assert corn["thresholds"][1]["selected_county_years"] == 78

    bad = good.copy()
    bad.loc[0, "rainfed_dominant_10pct"] = False
    bad.to_parquet(path, index=False)
    try:
        MODULE.audit(path)
    except ValueError as error:
        assert "fixed-share rule" in str(error)
    else:
        raise AssertionError("inconsistent selector flag was accepted")

    bad = good.copy()
    bad = pd.concat([bad, bad.iloc[[0]]], ignore_index=True)
    bad.to_parquet(path, index=False)
    try:
        MODULE.audit(path)
    except ValueError as error:
        assert "duplicate" in str(error)
    else:
        raise AssertionError("duplicate county-crop-year was accepted")

print("national irrigation-selector support tests passed")
