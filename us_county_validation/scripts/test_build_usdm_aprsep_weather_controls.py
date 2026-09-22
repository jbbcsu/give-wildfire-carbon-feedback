#!/usr/bin/env python3
"""Synthetic arithmetic check for April--September weather controls."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np


SCRIPT = Path(__file__).with_name("build_usdm_aprsep_weather_controls.py")
SPEC = importlib.util.spec_from_file_location("weather_controls", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load weather control builder")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

original_source = MODULE.BUILDER.source_year
original_state = MODULE.BUILDER.state_fips_to_alpha
try:
    def fake_source(year, hashes):
        days = 366 if year == 2012 else 365
        rain = np.ones((1, days), dtype="float32")
        tavg = np.full((1, days), 20.0, dtype="float32")
        tmax = np.full((1, days), 31.0, dtype="float32")
        return ["01001"], {"PRCP": rain, "TAVG": tavg, "TMIN": tavg - 5, "TMAX": tmax}, []
    MODULE.BUILDER.source_year = fake_source
    MODULE.BUILDER.state_fips_to_alpha = lambda: {"01": "AL"}
    frame, _ = MODULE.controls_for_year(2012, {})
    assert len(frame) == 2 and set(frame.weather_days) == {183}
    assert set(frame.precipitation_mm) == {183.0}
    corn = frame.loc[frame.outcome_crop.eq("corn_grain")].iloc[0]
    soy = frame.loc[frame.outcome_crop.eq("soybeans")].iloc[0]
    assert corn.crop_tmax_exceedance_c_days == 366.0
    assert soy.crop_tmax_exceedance_c_days == 183.0
finally:
    MODULE.BUILDER.source_year = original_source
    MODULE.BUILDER.state_fips_to_alpha = original_state

print("April--September weather-control tests passed")
