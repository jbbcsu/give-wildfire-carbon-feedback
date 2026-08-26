#!/usr/bin/env python3
"""Synthetic failure-mode tests for multi-file daily climate inputs."""
from __future__ import annotations

from contextlib import ExitStack
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

from climate_inputs import crop_year_window, open_daily_series


def write(path: Path, dates: pd.DatetimeIndex, *, lat: float = 0.25, units: str = "mm/day") -> None:
    values = np.ones((len(dates), 1, 1), dtype=float)
    xr.Dataset(
        {"pr": (("time", "lat", "lon"), values, {"units": units})},
        coords={"time": dates, "lat": [lat], "lon": [0.25]},
    ).to_netcdf(path, engine="h5netcdf")


def expect_failure(paths: list[str], message: str) -> None:
    try:
        with ExitStack() as stack:
            open_daily_series(stack, paths, "pr")
    except ValueError as error:
        assert message in str(error), error
    else:
        raise AssertionError(f"Expected failure containing {message!r}")


with tempfile.TemporaryDirectory() as temporary:
    root = Path(temporary)
    first = root / "first.nc"
    second = root / "second.nc"
    write(first, pd.date_range("2019-12-30", "2019-12-31", freq="D"))
    write(second, pd.date_range("2020-01-01", "2020-01-03", freq="D"))
    with ExitStack() as stack:
        combined = open_daily_series(stack, [str(first), str(second)], "pr")
        assert len(combined.time) == 5
        assert len(crop_year_window(combined, 2020, 2020).time) == 5

    noon_year_end = root / "noon_year_end.nc"
    write(noon_year_end, pd.date_range("2020-12-30 12:00", "2020-12-31 12:00", freq="D"))
    with ExitStack() as stack:
        noon = open_daily_series(stack, [str(noon_year_end)], "pr")
        selected = crop_year_window(noon, 2020, 2020)
        assert len(selected.time) == 2
        assert pd.Timestamp(selected.time.values[-1]) == pd.Timestamp("2020-12-31 12:00")

    gap = root / "gap.nc"
    write(gap, pd.date_range("2020-01-02", "2020-01-03", freq="D"))
    expect_failure([str(first), str(gap)], "strictly increasing daily series")
    expect_failure([str(second), str(first)], "strictly increasing daily series")

    shifted = root / "shifted.nc"
    write(shifted, pd.date_range("2020-01-04", "2020-01-05", freq="D"), lat=0.75)
    expect_failure([str(second), str(shifted)], "coordinates differ")

    changed_units = root / "changed_units.nc"
    write(changed_units, pd.date_range("2020-01-04", "2020-01-05", freq="D"), units="kg m-2 s-1")
    expect_failure([str(second), str(changed_units)], "units differ")

print("multi-file climate input synthetic tests passed")
