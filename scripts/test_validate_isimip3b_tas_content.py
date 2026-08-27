#!/usr/bin/env python3
"""Synthetic full-file gates for ISIMIP3b daily mean temperature."""
from __future__ import annotations

import hashlib
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

from validate_isimip3b_pr_content import EXPECTED_LAT, EXPECTED_LON
from validate_isimip3b_tas_content import validate


def write(
    path: Path,
    values: np.ndarray,
    *,
    units: str = "K",
    hour: int = 12,
) -> tuple[int, str]:
    dataset = xr.Dataset(
        {
            "tas": (
                ("time", "lat", "lon"),
                values,
                {"standard_name": "air_temperature", "units": units},
            )
        },
        coords={
            "time": pd.date_range(
                f"2020-01-01 {hour:02d}:00", f"2020-01-02 {hour:02d}:00", freq="D"
            ),
            "lat": ("lat", EXPECTED_LAT, {"units": "degrees_north"}),
            "lon": ("lon", EXPECTED_LON, {"units": "degrees_east"}),
        },
    )
    dataset["time"].encoding.update({"calendar": "proleptic_gregorian"})
    dataset["tas"].encoding.update(
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
    values = np.full((2, 360, 720), 288.0, dtype=np.float32)
    size, digest = write(valid, values)
    result = validate(
        valid,
        expected_bytes=size,
        expected_sha512=digest,
        start_date="2020-01-01",
        end_date="2020-01-02",
    )
    assert result["result"] == "passed"
    assert result["finite_values"] == values.size
    assert result["missing_values"] == 0

    midnight = root / "midnight.nc"
    size, digest = write(midnight, values, hour=0)
    result = validate(
        midnight,
        expected_bytes=size,
        expected_sha512=digest,
        start_date="2020-01-01",
        end_date="2020-01-02",
        expected_hour=0,
    )
    assert result["start_time"].endswith("T00:00:00")

    expect_failure(valid, size, "0" * 128, "SHA-512")

    out_of_bounds = root / "out_of_bounds.nc"
    values[0, 0, 0] = 100.0
    size, digest = write(out_of_bounds, values)
    expect_failure(out_of_bounds, size, digest, "physical Kelvin bounds")

    wrong_units = root / "wrong_units.nc"
    size, digest = write(wrong_units, np.full_like(values, 288.0), units="degC")
    expect_failure(wrong_units, size, digest, "units must be K")

print("ISIMIP3b full temperature content synthetic tests passed")
