#!/usr/bin/env python3
"""Synthetic tests for the outcome-blind selector geography audit."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile

import pandas as pd


MODULE_PATH = Path(__file__).with_name("audit_national_irrigation_selector_geography.py")
SPEC = importlib.util.spec_from_file_location("selector_geography", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def frame() -> pd.DataFrame:
    rows = []
    for crop in ("corn_grain", "soybeans"):
        for year in range(1981, 2020):
            for geoid, share_ok, outcome_ok, selected10, selected20 in (
                ("01001", True, True, True, True),
                ("02001", True, True, False, True),
                ("03001", False, True, False, False),
            ):
                rows.append({
                    "county_geoid": geoid,
                    "outcome_crop": crop,
                    "harvest_year": year,
                    "irrigation_share_vintage": 2017,
                    "irrigation_share_eligible": share_ok,
                    "outcome_value_eligible": outcome_ok,
                    "rainfed_dominant_10pct": selected10,
                    "rainfed_dominant_20pct": selected20,
                    "rainfed_dominant_30pct": selected20,
                })
    return pd.DataFrame(rows)


with tempfile.TemporaryDirectory() as folder:
    path = Path(folder) / "panel.parquet"
    good = frame()
    good.to_parquet(path, index=False)
    result = MODULE.audit(path)
    assert result["yield_magnitudes_read"] is False
    corn = next(item for item in result["results"] if item["crop"] == "corn_grain")
    assert corn["reported_states"] == 3
    first = corn["thresholds"][0]
    assert first["states"] == 1
    assert first["selected_reported_county_years"] == 39
    assert first["state_county_year_hhi"] == 1.0
    second = corn["thresholds"][1]
    assert second["states"] == 2
    assert second["top1_state_county_year_share"] == 0.5

    bad = pd.concat([good, good.iloc[[0]]], ignore_index=True)
    bad.to_parquet(path, index=False)
    try:
        MODULE.audit(path)
    except ValueError as error:
        assert "duplicate" in str(error)
    else:
        raise AssertionError("duplicate key was accepted")

    bad = good.copy()
    bad.loc[0, "county_geoid"] = "1001"
    bad.to_parquet(path, index=False)
    try:
        MODULE.audit(path)
    except ValueError as error:
        assert "GEOID" in str(error)
    else:
        raise AssertionError("invalid GEOID was accepted")

print("national irrigation-selector geography tests passed")
