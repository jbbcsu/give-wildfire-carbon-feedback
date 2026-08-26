#!/usr/bin/env python3
"""Fail-closed gate for a historical-to-projection daily-file boundary.

This validates data plumbing only.  A passing result does not estimate a
climate response, construct a FAIR pulse, or establish an SCC contribution.
"""
from __future__ import annotations

import argparse
import json
from contextlib import ExitStack
from pathlib import Path

import pandas as pd
import xarray as xr

from climate_inputs import open_daily_series


def _time_bounds(path: Path, variable: str) -> tuple[pd.Timestamp, pd.Timestamp, str, tuple[str, ...]]:
    with xr.open_dataset(path, engine="h5netcdf") as dataset:
        if variable not in dataset:
            raise ValueError(f"{path} does not contain requested variable {variable}")
        array = dataset[variable]
        times = pd.DatetimeIndex(array.time.values)
        if len(times) == 0:
            raise ValueError(f"{path} has an empty time axis")
        return times[0], times[-1], array.attrs.get("units", ""), array.dims


def validate(
    historical: Path,
    projection: Path,
    *,
    variable: str,
    expected_historical_end: str = "2014-12-31T12:00:00",
    expected_projection_start: str = "2015-01-01T12:00:00",
) -> dict[str, object]:
    historical_start, historical_end, historical_units, historical_dims = _time_bounds(historical, variable)
    projection_start, projection_end, projection_units, projection_dims = _time_bounds(projection, variable)
    expected_end = pd.Timestamp(expected_historical_end)
    expected_start = pd.Timestamp(expected_projection_start)
    if historical_end != expected_end:
        raise ValueError(f"historical endpoint must be {expected_end.isoformat()}, got {historical_end.isoformat()}")
    if projection_start != expected_start:
        raise ValueError(f"projection start must be {expected_start.isoformat()}, got {projection_start.isoformat()}")
    if projection_start - historical_end != pd.Timedelta(days=1):
        raise ValueError("historical/projection boundary is not exactly one daily step")
    if historical_units != projection_units or historical_dims != projection_dims:
        raise ValueError("historical and projection variable metadata differ at the boundary")
    with ExitStack() as stack:
        combined = open_daily_series(stack, [str(historical), str(projection)], variable)
        dates = pd.DatetimeIndex(combined.time.values)
        if dates[-1] != projection_end or dates[0] != historical_start:
            raise ValueError("combined daily series does not retain the source time bounds")
    return {
        "role": "complete_file_historical_to_projection_boundary_engineering_gate_not_feature_response_or_scc",
        "result": "passed",
        "variable": variable,
        "historical": {"file_name": historical.name, "start_time": historical_start.isoformat(), "end_time": historical_end.isoformat()},
        "projection": {"file_name": projection.name, "start_time": projection_start.isoformat(), "end_time": projection_end.isoformat()},
        "units": historical_units,
        "dimensions": list(historical_dims),
        "boundary_step_hours": 24,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--historical", type=Path, required=True)
    parser.add_argument("--projection", type=Path, required=True)
    parser.add_argument("--variable", required=True)
    parser.add_argument("--expected-historical-end", default="2014-12-31T12:00:00")
    parser.add_argument("--expected-projection-start", default="2015-01-01T12:00:00")
    parser.add_argument("--audit-out", type=Path, required=True)
    args = parser.parse_args()
    audit = validate(args.historical, args.projection, variable=args.variable,
                     expected_historical_end=args.expected_historical_end,
                     expected_projection_start=args.expected_projection_start)
    args.audit_out.parent.mkdir(parents=True, exist_ok=True)
    args.audit_out.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"ISIMIP3b {args.variable} historical/projection boundary gate passed")


if __name__ == "__main__":
    main()
