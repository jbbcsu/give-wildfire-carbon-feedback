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


PROJECT = Path(__file__).resolve().parents[1]

with tempfile.TemporaryDirectory() as temporary:
    root = Path(temporary)
    dates = pd.date_range("2020-01-01", "2020-01-05", freq="D")
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
    row = pd.read_parquet(output).iloc[0]
    assert row.precip_mm == 15.0
    assert row.wet_days_n == 5
    assert row.cdd_max_days == 0
    assert row.rx1day_mm == 5.0
    assert row.rx5day_mm == 15.0
    assert abs(row.tmean_c - 6.85) < 1e-9
print("feature-builder synthetic test passed")
