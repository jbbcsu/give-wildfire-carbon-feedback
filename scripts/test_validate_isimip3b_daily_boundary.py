#!/usr/bin/env python3
"""Synthetic tests for the historical/projection daily-boundary gate."""
from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

from validate_isimip3b_daily_boundary import validate


def write_block(path: Path, start: str, end: str, *, units: str = "K") -> None:
    time = pd.date_range(start, end, freq="D") + pd.Timedelta(hours=12)
    values = np.ones((len(time), 2, 2), dtype=np.float32)
    xr.Dataset({"tas": (("time", "lat", "lon"), values, {"units": units})},
               coords={"time": time, "lat": [0.25, -0.25], "lon": [0.25, 0.75]}).to_netcdf(path, engine="h5netcdf")


def main() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        folder = Path(temporary)
        historical, projection = folder / "historical.nc", folder / "projection.nc"
        write_block(historical, "2014-12-30", "2014-12-31")
        write_block(projection, "2015-01-01", "2015-01-02")
        assert validate(historical, projection, variable="tas")["result"] == "passed"
        write_block(projection, "2015-01-02", "2015-01-03")
        try:
            validate(historical, projection, variable="tas")
        except ValueError as error:
            assert "projection start" in str(error)
        else:
            raise AssertionError("gap at boundary was accepted")
        write_block(projection, "2015-01-01", "2015-01-02", units="degC")
        try:
            validate(historical, projection, variable="tas")
        except ValueError as error:
            assert "metadata differ" in str(error)
        else:
            raise AssertionError("unit mismatch was accepted")
    print("historical/projection boundary tests passed")


if __name__ == "__main__":
    main()
