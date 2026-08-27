#!/usr/bin/env python3
"""Synthetic tests for complete daily temperature ordering."""
from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

from validate_isimip3b_temperature_ordering import validate


def write(path: Path, name: str, values: np.ndarray, *, longitude_offset: float = 0) -> None:
    dataset = xr.Dataset(
        {
            name: (
                ("time", "lat", "lon"),
                values,
                {"standard_name": "air_temperature", "units": "K"},
            )
        },
        coords={
            "time": pd.date_range("2020-01-01", "2020-01-02", freq="D"),
            "lat": np.arange(89.75, -90.0, -0.5),
            "lon": np.arange(-179.75, 180.0, 0.5) + longitude_offset,
        },
    )
    dataset.to_netcdf(path, engine="h5netcdf")


with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    shape = (2, 360, 720)
    paths = {name: root / f"{name}.nc" for name in ("tasmin", "tas", "tasmax")}
    write(paths["tasmin"], "tasmin", np.full(shape, 280.0, dtype=np.float32))
    write(paths["tas"], "tas", np.full(shape, 285.0, dtype=np.float32))
    write(paths["tasmax"], "tasmax", np.full(shape, 290.0, dtype=np.float32))
    result = validate(paths["tasmin"], paths["tas"], paths["tasmax"])
    assert result["result"] == "passed"
    assert result["finite_triplets"] == np.prod(shape)
    assert result["minimum_tasmax_minus_tasmin_k"] == 10.0

    rounded_mean = np.full(shape, 285.0, dtype=np.float32)
    rounded_maximum = np.full(shape, 290.0, dtype=np.float32)
    rounded_mean[0, 0, 0] = np.float32(285.00003)
    rounded_maximum[0, 0, 0] = np.float32(285.0)
    write(paths["tas"], "tas", rounded_mean)
    write(paths["tasmax"], "tasmax", rounded_maximum)
    result = validate(paths["tasmin"], paths["tas"], paths["tasmax"])
    assert result["raw_tas_above_tasmax"] == 1
    assert result["tas_above_tasmax_beyond_tolerance"] == 0

    broken = np.full(shape, 285.0, dtype=np.float32)
    broken[0, 0, 0] = 291.0
    write(paths["tas"], "tas", broken)
    write(paths["tasmax"], "tasmax", np.full(shape, 290.0, dtype=np.float32))
    try:
        validate(paths["tasmin"], paths["tas"], paths["tasmax"])
    except ValueError as error:
        assert "temperature ordering failed" in str(error), error
    else:
        raise AssertionError("tas above tasmax should fail closed")

    write(paths["tas"], "tas", np.full(shape, 285.0, dtype=np.float32))
    write(
        paths["tasmax"],
        "tasmax",
        np.full(shape, 290.0, dtype=np.float32),
        longitude_offset=0.25,
    )
    try:
        validate(paths["tasmin"], paths["tas"], paths["tasmax"])
    except ValueError as error:
        assert "lon coordinate differs" in str(error), error
    else:
        raise AssertionError("coordinate mismatch should fail closed")

print("ISIMIP3b temperature-ordering synthetic tests passed")
