#!/usr/bin/env python3
"""Open one or more contiguous daily climate files as one audited time series."""
from __future__ import annotations

from contextlib import ExitStack
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr


PRECIP_UNIT_KEYS = {"kgm-2s-1", "kgm**-2s**-1", "kg/m2/s", "kgm^-2s^-1", "mm", "mm/day", "mmday-1", "mmd-1", "mmd**-1", "mmd^-1"}
TEMPERATURE_UNIT_KEYS = {"k", "kelvin", "c", "degc", "degree_celsius", "degreescelsius", "°c"}


def canonical_units(units: str) -> str:
    return (units or "").strip().lower().replace(" ", "")


def validate_daily_units(variable: str, units: str) -> str:
    canonical = canonical_units(units)
    if variable == "pr" and canonical not in PRECIP_UNIT_KEYS:
        raise ValueError(f"Unsupported precipitation units {units!r}")
    if variable in {"tas", "tasmax", "tasmin"} and canonical not in TEMPERATURE_UNIT_KEYS:
        raise ValueError(f"Unsupported temperature units {units!r}")
    if variable not in {"pr", "tas", "tasmax", "tasmin"}:
        raise ValueError(f"No daily-unit contract is registered for climate variable {variable!r}")
    return canonical


def climate_array(dataset: xr.Dataset, preferred: str) -> xr.DataArray:
    if preferred in dataset:
        return dataset[preferred]
    if len(dataset.data_vars) != 1:
        raise ValueError(f"Cannot infer {preferred}; variables are {list(dataset.data_vars)}")
    return next(iter(dataset.data_vars.values()))


def _open_checked_daily_arrays(
    stack: ExitStack, paths: list[str], preferred: str
) -> tuple[list[xr.DataArray], list[np.ndarray]]:
    """Open files and validate their full coordinates without concatenating data."""
    if not paths:
        raise ValueError(f"At least one {preferred} file is required")
    arrays: list[xr.DataArray] = []
    timestamp_parts: list[np.ndarray] = []
    for raw_path in paths:
        path = Path(raw_path)
        if not path.is_file():
            raise FileNotFoundError(path)
        dataset = stack.enter_context(xr.open_dataset(path, engine="h5netcdf"))
        array = climate_array(dataset, preferred)
        if "time" not in array.dims or "lat" not in array.dims or "lon" not in array.dims:
            raise ValueError(f"{path} must have time, lat, and lon dimensions")
        validate_daily_units(preferred, str(array.attrs.get("units", "")))
        if arrays and not (
            np.array_equal(array.lat.values, arrays[0].lat.values)
            and np.array_equal(array.lon.values, arrays[0].lon.values)
        ):
            raise ValueError(f"{preferred} coordinates differ across input files: {path}")
        if arrays and array.dims != arrays[0].dims:
            raise ValueError(f"{preferred} dimension order differs across input files: {path}")
        if arrays and array.attrs.get("units", "") != arrays[0].attrs.get("units", ""):
            raise ValueError(f"{preferred} units differ across input files: {path}")
        try:
            timestamps = array.time.values.astype("datetime64[ns]")
        except (TypeError, ValueError) as error:
            raise ValueError(
                f"{preferred} time axis must be Gregorian-compatible daily dates"
            ) from error
        arrays.append(array)
        timestamp_parts.append(timestamps)

    timestamps = np.concatenate(timestamp_parts)
    if len(timestamps) < 1:
        raise ValueError(f"{preferred} time series is empty")
    if len(timestamps) > 1:
        differences = np.diff(timestamps)
        if not np.all(differences == np.timedelta64(1, "D")):
            raise ValueError(
                f"{preferred} files must form one strictly increasing daily series; "
                f"observed steps={sorted(set(str(value) for value in differences))}"
            )
    return arrays, timestamp_parts


def daily_series_coordinates(
    stack: ExitStack, paths: list[str], preferred: str
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return audited full-series time/latitude/longitude coordinates only.

    This path intentionally avoids concatenating the climate payload. It is
    suitable for readiness audits of many multi-gigabyte decadal files.
    """
    arrays, timestamp_parts = _open_checked_daily_arrays(stack, paths, preferred)
    return (
        np.concatenate(timestamp_parts),
        arrays[0].lat.values.copy(),
        arrays[0].lon.values.copy(),
    )


def open_checked_daily_file_arrays(
    stack: ExitStack, paths: list[str], preferred: str
) -> tuple[list[xr.DataArray], list[np.ndarray]]:
    """Return separately opened arrays after full cross-file coordinate checks.

    This interface is for global reductions that must stream each source file
    independently.  It deliberately avoids :func:`xr.concat`, whose indexed
    reductions can materialize unexpectedly large multi-file payloads.
    """
    return _open_checked_daily_arrays(stack, paths, preferred)


def open_daily_series(stack: ExitStack, paths: list[str], preferred: str) -> xr.DataArray:
    """Return a coordinate-checked concatenation of daily input files.

    Files must be supplied in chronological order. Duplicate, decreasing, or
    non-daily timestamps fail closed so a growing season cannot silently lose
    or double-count days at a decadal file boundary. For multi-gigabyte inputs,
    callers that need a bounded crop/latitude window should use
    :func:`open_daily_crop_window` so full-grid payloads are not materialized.
    """
    arrays, _ = _open_checked_daily_arrays(stack, paths, preferred)
    combined = arrays[0] if len(arrays) == 1 else xr.concat(arrays, dim="time")
    return combined


def open_daily_crop_window(
    stack: ExitStack,
    paths: list[str],
    preferred: str,
    year_start: int,
    year_end: int,
    lat_start: int,
    lat_stop: int,
) -> xr.DataArray:
    """Return only the crop-year time window and requested latitude cells.

    Full-file chronology, grid, dimensions, and units are checked first. Each
    source file is then sliced *before* concatenation. This preserves the same
    scientific contract as :func:`open_daily_series` while bounding memory and
    I/O for multi-decadal global inputs.
    """
    if year_end < year_start:
        raise ValueError("year_end must not precede year_start")
    arrays, timestamp_parts = _open_checked_daily_arrays(stack, paths, preferred)
    latitude_count = int(arrays[0].sizes["lat"])
    if lat_start < 0 or lat_stop <= lat_start or lat_stop > latitude_count:
        raise ValueError("Latitude window is outside the daily climate grid")
    first = np.datetime64(f"{year_start - 1:04d}-01-01", "ns")
    last_exclusive = np.datetime64(f"{year_end + 1:04d}-01-01", "ns")
    selected: list[xr.DataArray] = []
    for array, timestamps in zip(arrays, timestamp_parts):
        positions = np.flatnonzero(
            (timestamps >= first) & (timestamps < last_exclusive)
        )
        if len(positions):
            selected.append(
                array.isel(time=positions, lat=slice(lat_start, lat_stop))
            )
    if not selected:
        raise ValueError(
            f"Climate input has no days for harvest years {year_start}-{year_end}"
        )
    combined = selected[0] if len(selected) == 1 else xr.concat(selected, dim="time")
    # The full chronology is already checked. Verify the selected boundary as
    # a defensive invariant against accidental selector changes.
    selected_times = combined.time.values.astype("datetime64[ns]")
    if len(selected_times) > 1:
        differences = np.diff(selected_times)
        if not np.all(differences == np.timedelta64(1, "D")):
            raise AssertionError("Selected daily crop window is not contiguous")
    return combined


def crop_year_window(array: xr.DataArray, year_start: int, year_end: int) -> xr.DataArray:
    """Keep only days that can enter the requested harvest-year seasons."""
    if year_end < year_start:
        raise ValueError("year_end must not precede year_start")
    dates = pd.DatetimeIndex(array.time.values)
    first = pd.Timestamp(year_start - 1, 1, 1)
    # ISIMIP daily fields are commonly timestamped at noon.  Use an exclusive
    # next-year boundary so December 31 is retained regardless of intraday
    # timestamp while January 1 of the following year is still excluded.
    last_exclusive = pd.Timestamp(year_end + 1, 1, 1)
    selected = np.flatnonzero((dates >= first) & (dates < last_exclusive))
    if len(selected) == 0:
        raise ValueError(f"Climate input has no days for harvest years {year_start}-{year_end}")
    return array.isel(time=selected)
