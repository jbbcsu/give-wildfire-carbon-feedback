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
    xr.Dataset({"pr": (("time", "lat", "lon"), np.array([1, 2, 3, 4, 5], dtype=float).reshape(5, 1, 1), {"units": "mm/day"})}, coords=coords).to_netcdf(root / "pr.nc", engine="h5netcdf")
    xr.Dataset({"tas": (("time", "lat", "lon"), np.full((5, 1, 1), 280.0), {"units": "K"})}, coords=coords).to_netcdf(root / "tas.nc", engine="h5netcdf")
    xr.Dataset({
        "planting_day": (("lat", "lon"), [[1.0]]),
        "maturity_day": (("lat", "lon"), [[5.0]]),
        "growing_season_length": (("lat", "lon"), [[5.0]]),
    }, coords={"lat": [0.25], "lon": [0.25]}).to_netcdf(root / "calendar.nc", engine="h5netcdf")
    output = root / "features.parquet"
    subprocess.run([
        sys.executable, str(PROJECT / "scripts" / "build_crop_year_features.py"),
        "--precip", str(root / "pr.nc"), "--temperature", str(root / "tas.nc"),
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
