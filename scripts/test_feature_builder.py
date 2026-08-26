#!/usr/bin/env python3
"""Synthetic end-to-end test for crop-year feature construction."""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

from build_crop_year_features import (
    normalize_precip,
    normalize_temperature,
    validate_wet_day_threshold,
)
from reconcile_stage_season_features import validate_row_invariants


PROJECT = Path(__file__).resolve().parents[1]

values = np.array([1.0])
assert normalize_precip(values, "kg m-2 s-1")[0] == 86400.0
assert normalize_precip(values, "mm/day")[0] == 1.0
assert np.isclose(normalize_temperature(np.array([273.15]), "K")[0], 0.0)
assert normalize_temperature(values, "degC")[0] == 1.0
for normalizer, units in ((normalize_precip, ""), (normalize_precip, "inch/day"), (normalize_temperature, ""), (normalize_temperature, "F")):
    try:
        normalizer(values, units)
    except ValueError as error:
        assert "Unsupported" in str(error)
    else:
        raise AssertionError(f"Unknown units {units!r} were accepted")
for threshold in (0.0, -1.0, np.nan):
    try:
        validate_wet_day_threshold(threshold)
    except ValueError as error:
        assert "strictly positive" in str(error)
    else:
        raise AssertionError(f"Invalid wet-day threshold {threshold} was accepted")

with tempfile.TemporaryDirectory() as temporary:
    root = Path(temporary)
    # ISIMIP daily fields can be stamped at noon.  A date-based crop calendar
    # must still include the planting and maturity dates in full.
    dates = pd.date_range("2020-01-01 12:00", "2020-01-05 12:00", freq="D")
    coords = {"time": dates, "lat": [0.25], "lon": [0.25]}
    rain = np.array([1, 2, 3, 4, 5], dtype=float).reshape(5, 1, 1)
    temperature = np.full((5, 1, 1), 280.0)
    for name, values, variable, units, subset in (
        ("first", rain, "pr", "mm/day", slice(0, 3)),
        ("second", rain, "pr", "mm/day", slice(3, 5)),
        ("first", temperature, "tas", "K", slice(0, 3)),
        ("second", temperature, "tas", "K", slice(3, 5)),
    ):
        xr.Dataset(
            {variable: (("time", "lat", "lon"), values[subset], {"units": units})},
            coords={"time": dates[subset], "lat": [0.25], "lon": [0.25]},
        ).to_netcdf(root / f"{variable}_{name}.nc", engine="h5netcdf")
    xr.Dataset({
        "planting_day": (("lat", "lon"), [[1.0]]),
        "maturity_day": (("lat", "lon"), [[5.0]]),
        "growing_season_length": (("lat", "lon"), [[5.0]]),
    }, coords={"lat": [0.25], "lon": [0.25]}).to_netcdf(root / "calendar.nc", engine="h5netcdf")
    output = root / "features.parquet"
    subprocess.run([
        sys.executable, str(PROJECT / "scripts" / "build_crop_year_features.py"),
        "--precip", str(root / "pr_first.nc"), str(root / "pr_second.nc"),
        "--temperature", str(root / "tas_first.nc"), str(root / "tas_second.nc"),
        "--calendar", str(root / "calendar.nc"), "--crop", "mai", "--irrigation", "noirr",
        "--year-start", "2020", "--year-end", "2020", "--lat-start", "0", "--lat-stop", "1",
        "--out", str(output),
    ], check=True)
    season = pd.read_parquet(output)
    row = season.iloc[0]
    assert row.precip_mm == 15.0
    assert row.wet_days_n == 5
    assert row.cdd_max_days == 0
    assert row.rx1day_mm == 5.0
    assert row.rx5day_mm == 15.0
    assert abs(row.tmean_c - 6.85) < 1e-9
    stage_output = root / "stages.parquet"
    subprocess.run([
        sys.executable, str(PROJECT / "scripts" / "build_crop_stage_features.py"),
        "--precip", str(root / "pr_first.nc"), str(root / "pr_second.nc"),
        "--temperature", str(root / "tas_first.nc"), str(root / "tas_second.nc"),
        "--calendar", str(root / "calendar.nc"), "--crop", "mai", "--irrigation", "noirr",
        "--year-start", "2020", "--year-end", "2020", "--lat-start", "0", "--lat-stop", "1",
        "--out", str(stage_output), "--stage-fractions", "0,0.4,1",
    ], check=True)
    stages = pd.read_parquet(stage_output)
    assert stages.stage_id.tolist() == [1, 2]
    assert stages.stage_days.sum() == 5
    assert stages.precip_mm.sum() == 15.0
    validate_row_invariants(season, "season_days", "season")
    validate_row_invariants(stages, "stage_days", "stage")
    bad = season.copy()
    bad.loc[bad.index[0], "rx5day_mm"] = bad.loc[bad.index[0], "precip_mm"] + 1
    try:
        validate_row_invariants(bad, "season_days", "season")
    except ValueError as error:
        assert "Rx1day/Rx5day" in str(error)
    else:
        raise AssertionError("Rx5day above total precipitation should fail")
print("feature-builder synthetic test passed")
