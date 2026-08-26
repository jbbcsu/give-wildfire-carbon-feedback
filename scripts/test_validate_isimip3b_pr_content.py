#!/usr/bin/env python3
"""Synthetic full-file gates for ISIMIP3b daily precipitation."""
from __future__ import annotations

import hashlib
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

from validate_isimip3b_pr_content import EXPECTED_LAT, EXPECTED_LON, validate


def write(path: Path, values: np.ndarray, *, lon: np.ndarray = EXPECTED_LON) -> tuple[int, str]:
    dataset = xr.Dataset(
        {
            "pr": (
                ("time", "lat", "lon"),
                values,
                {"standard_name": "precipitation_flux", "units": "kg m-2 s-1"},
            )
        },
        coords={
            "time": pd.date_range("2020-01-01 12:00", "2020-01-02 12:00", freq="D"),
            "lat": ("lat", EXPECTED_LAT, {"units": "degrees_north"}),
            "lon": ("lon", lon, {"units": "degrees_east"}),
        },
    )
    dataset["time"].encoding.update({"calendar": "proleptic_gregorian"})
    dataset["pr"].encoding.update(
        {"chunksizes": (1, 360, 720), "_FillValue": np.float32(1e20), "missing_value": np.float32(1e20)}
    )
    dataset.to_netcdf(path, engine="h5netcdf")
    raw = path.read_bytes()
    return len(raw), hashlib.sha512(raw).hexdigest()


def expect_failure(path: Path, size: int, digest: str, message: str) -> None:
    try:
        validate(
            path,
            expected_bytes=size,
            expected_sha512=digest,
            start_date="2020-01-01",
            end_date="2020-01-02",
        )
    except ValueError as error:
        assert message in str(error), error
    else:
        raise AssertionError(f"expected failure containing {message!r}")


with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    valid = root / "valid.nc"
    values = np.zeros((2, 360, 720), dtype=np.float32)
    values[0, 0, 0] = 0.001
    size, digest = write(valid, values)
    audit = validate(
        valid,
        expected_bytes=size,
        expected_sha512=digest,
        start_date="2020-01-01",
        end_date="2020-01-02",
    )
    assert audit["result"] == "passed"
    assert audit["finite_values"] == values.size
    assert audit["negative_values"] == 0

    expect_failure(valid, size, "0" * 128, "SHA-512")

    negative = root / "negative.nc"
    values[1, 0, 0] = -0.1
    size, digest = write(negative, values)
    expect_failure(negative, size, digest, "finite/nonnegative")

    wrong_grid = root / "wrong_grid.nc"
    size, digest = write(wrong_grid, np.zeros_like(values), lon=EXPECTED_LON + 0.25)
    expect_failure(wrong_grid, size, digest, "longitude grid")

print("ISIMIP3b full precipitation content synthetic tests passed")
