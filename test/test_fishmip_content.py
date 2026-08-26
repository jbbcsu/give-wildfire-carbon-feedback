#!/usr/bin/env python3
"""Synthetic complete-file checks for FishMIP total catch."""
from __future__ import annotations

import hashlib
import sys
import tempfile
from pathlib import Path

import numpy as np
import xarray as xr

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from validate_fishmip_content import (
    EXPECTED_LAT,
    EXPECTED_LON,
    expected_time,
    validate,
    validate_cross_model_support,
    validate_pair,
)


def base_metadata(model: str = "boats", year: int = 2020, scenario: str = "historical") -> dict[str, str]:
    return {
        "dataset_id": "dataset",
        "file_id": "file",
        "model": model,
        "climate_forcing": "gfdl-esm4",
        "climate_scenario": scenario,
        "version": "test",
        "start_year": str(year),
        "end_year": str(year),
    }


def write(
    path: Path,
    values: np.ndarray,
    model: str = "boats",
    *,
    year: int = 2020,
    scenario: str = "historical",
    units: str = "g m-2",
) -> tuple[int, str]:
    time, time_units, time_calendar = expected_time(base_metadata(model, year, scenario))
    dataset = xr.Dataset(
        {"tc": (("time", "lat", "lon"), values, {"units": units})},
        coords={
            "time": ("time", time, {"units": time_units, "calendar": time_calendar}),
            "lat": EXPECTED_LAT,
            "lon": EXPECTED_LON,
        },
    )
    dataset["tc"].encoding.update(
        {"chunksizes": (1, 180, 360), "_FillValue": np.float32(1e20), "missing_value": np.float32(1e20)}
    )
    dataset.to_netcdf(path, engine="h5netcdf")
    raw = path.read_bytes()
    return len(raw), hashlib.sha512(raw).hexdigest()


def row(
    path: Path,
    size: int,
    digest: str,
    model: str = "boats",
    year: int = 2020,
    scenario: str = "historical",
) -> dict[str, str]:
    return {**base_metadata(model, year, scenario), "bytes": str(size), "sha512": digest}


def failure(path: Path, metadata: dict[str, str], message: str) -> None:
    try:
        validate(path, metadata)
    except ValueError as error:
        assert message in str(error), error
    else:
        raise AssertionError(f"expected failure containing {message!r}")


with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    valid = root / "valid.nc"
    values = np.zeros((12, 180, 360), dtype=np.float32)
    values[:, :20, :] = np.nan
    values[0, 20, 0] = 2.0
    size, digest = write(valid, values)
    metadata = row(valid, size, digest)
    audit = validate(valid, metadata)
    assert audit["result"] == "passed"
    assert audit["negative_values"] == 0
    assert audit["always_missing_grid_cells"] == 20 * 360

    ecoocean = root / "ecoocean.nc"
    ecoocean_values = values.copy()
    ecoocean_values[:, 10, 0] = 1.0
    size, digest = write(ecoocean, ecoocean_values, "ecoocean")
    ecoocean_audit = validate(ecoocean, row(ecoocean, size, digest, "ecoocean"))
    assert ecoocean_audit["calendar"] == "365_day"
    assert ecoocean_audit["time_units"] == "days since 1601-1-1 00:00:00"

    future = root / "ecoocean_future.nc"
    future_size, future_digest = write(
        future, ecoocean_values, "ecoocean", year=2021, scenario="ssp126"
    )
    pair_audit = validate_pair(
        ecoocean,
        row(ecoocean, size, digest, "ecoocean"),
        future,
        row(future, future_size, future_digest, "ecoocean", 2021, "ssp126"),
    )
    assert pair_audit["calendar"] == "365_day"
    assert pair_audit["future_first_time"] - pair_audit["historical_last_time"] == 31
    support_audit = validate_cross_model_support(
        valid,
        metadata,
        ecoocean,
        row(ecoocean, size, digest, "ecoocean"),
    )
    assert support_audit["common_finite_grid_cells"] == 160 * 360
    assert support_audit["second_only_grid_cells"] == 1

    failure(valid, {**metadata, "sha512": "0" * 128}, "SHA-512")

    negative = root / "negative.nc"
    values[1, 20, 0] = -1.0
    size, digest = write(negative, values)
    failure(negative, row(negative, size, digest), "negative catch")

    wrong_units = root / "wrong_units.nc"
    size, digest = write(wrong_units, np.zeros_like(values), units="kg m-2")
    failure(wrong_units, row(wrong_units, size, digest), "units")

print("FishMIP full content synthetic tests passed")
