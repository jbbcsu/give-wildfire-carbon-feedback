#!/usr/bin/env python3
"""Synthetic same-realization GMST builder checks."""
from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

from build_same_realization_gmst import build


def write(path: Path, dates: pd.DatetimeIndex, values: np.ndarray, *, units: str = "K") -> None:
    xr.Dataset(
        {"tas": (("time", "lat", "lon"), values, {"units": units})},
        coords={"time": dates, "lat": [-60.0, 0.0, 60.0], "lon": [-120.0, 0.0, 120.0]},
    ).to_netcdf(path, engine="h5netcdf")


def failure(paths: list[str], message: str, **changes: object) -> None:
    kwargs = {
        "esm_id": "mri-esm2-0",
        "member_id": "r1i1p1f1",
        "scenario": "historical",
        "source_id": "pinned-tas-files-sha512-set",
        "year_start": 2019,
        "year_end": 2020,
    }
    kwargs.update(changes)
    try:
        build(paths, **kwargs)
    except ValueError as error:
        assert message in str(error), error
    else:
        raise AssertionError(f"expected failure containing {message!r}")


with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    dates = pd.date_range("2019-01-01", "2020-12-31", freq="D")
    values = np.full((len(dates), 3, 3), 288.0, dtype=np.float32)
    values[:, 1, :] = 290.0
    first = root / "tas_2019.nc"
    second = root / "tas_2020.nc"
    write(first, dates[dates.year == 2019], values[dates.year == 2019])
    write(second, dates[dates.year == 2020], values[dates.year == 2020])
    output = build(
        [str(first), str(second)],
        esm_id="mri-esm2-0",
        member_id="r1i1p1f1",
        scenario="historical",
        source_id="pinned-tas-files-sha512-set",
        year_start=2019,
        year_end=2020,
    )
    assert output["year"].tolist() == [2019, 2020]
    assert output["daily_count"].tolist() == [365, 366]
    assert output["gmst_source_id"].nunique() == 1

    # The bounded reducer must be invariant to block size, including blocks
    # that cross the input-file boundary.
    one_day = build(
        [str(first), str(second)],
        esm_id="mri-esm2-0",
        member_id="r1i1p1f1",
        scenario="historical",
        source_id="pinned-tas-files-sha512-set",
        year_start=2019,
        year_end=2020,
        block_days=1,
    )
    boundary_crossing = build(
        [str(first), str(second)],
        esm_id="mri-esm2-0",
        member_id="r1i1p1f1",
        scenario="historical",
        source_id="pinned-tas-files-sha512-set",
        year_start=2019,
        year_end=2020,
        block_days=400,
    )
    pd.testing.assert_frame_equal(output, one_day)
    pd.testing.assert_frame_equal(output, boundary_crossing)
    failure([str(first), str(second)], "block_days", block_days=0)

    gap = root / "tas_gap.nc"
    write(gap, dates.delete(10), values[np.arange(len(dates)) != 10])
    failure([str(gap)], "daily")

    wrong_units = root / "tas_celsius.nc"
    # This spelling passes the general daily-temperature unit contract so the
    # GMST-specific Kelvin-only gate is exercised.
    write(wrong_units, dates, values, units="degree_Celsius")
    failure([str(wrong_units)], "Kelvin")

print("same-realization GMST synthetic tests passed")
