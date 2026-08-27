#!/usr/bin/env python3
"""Full-file content gate for a pinned ISIMIP3b daily air-temperature block."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

from validate_isimip3b_pr_content import EXPECTED_LAT, EXPECTED_LON, sha512


def validate(
    path: Path,
    *,
    expected_bytes: int,
    expected_sha512: str,
    start_date: str,
    end_date: str,
    variable_name: str = "tas",
    expected_hour: int = 12,
    block_days: int = 32,
) -> dict[str, object]:
    if block_days < 1:
        raise ValueError("block_days must be positive")
    if expected_hour not in range(24):
        raise ValueError("expected_hour must be an integer from 0 through 23")
    if variable_name not in {"tas", "tasmin", "tasmax"}:
        raise ValueError("variable_name must be tas, tasmin, or tasmax")
    actual_bytes = path.stat().st_size
    if actual_bytes != expected_bytes:
        raise ValueError(f"file byte size mismatch: expected {expected_bytes}, got {actual_bytes}")
    actual_sha512 = sha512(path)
    if actual_sha512 != expected_sha512:
        raise ValueError("file SHA-512 differs from the pinned catalogue checksum")
    expected_time = pd.date_range(start_date, end_date, freq="D") + pd.Timedelta(hours=expected_hour)
    counts = {"finite": 0, "missing": 0}
    minimum = np.inf
    maximum = -np.inf
    with xr.open_dataset(path, engine="h5netcdf") as dataset:
        if set(dataset.data_vars) != {variable_name}:
            raise ValueError(
                f"expected only data variable {variable_name}, got {sorted(dataset.data_vars)}"
            )
        variable = dataset[variable_name]
        if variable.dims != ("time", "lat", "lon"):
            raise ValueError(f"unexpected {variable_name} dimension order: {variable.dims}")
        if dataset.sizes != {"time": len(expected_time), "lat": 360, "lon": 720}:
            raise ValueError(f"unexpected decoded dimensions: {dict(dataset.sizes)}")
        if variable.attrs.get("standard_name") != "air_temperature":
            raise ValueError(f"{variable_name} standard_name must be air_temperature")
        if variable.attrs.get("units") != "K":
            raise ValueError(f"{variable_name} units must be K")
        if dataset["lat"].attrs.get("units") != "degrees_north":
            raise ValueError("latitude units changed")
        if dataset["lon"].attrs.get("units") != "degrees_east":
            raise ValueError("longitude units changed")
        if not np.array_equal(dataset["lat"].values, EXPECTED_LAT):
            raise ValueError("latitude grid is not the registered descending 0.5-degree grid")
        if not np.array_equal(dataset["lon"].values, EXPECTED_LON):
            raise ValueError("longitude grid is not the registered -179.75..179.75 grid")
        if not pd.DatetimeIndex(dataset["time"].values).equals(expected_time):
            raise ValueError(
                f"decoded time is not the exact complete daily {expected_hour:02d}:00 sequence"
            )
        if dataset["time"].encoding.get("calendar") != "proleptic_gregorian":
            raise ValueError("time calendar must be proleptic_gregorian")
        fill = variable.encoding.get("_FillValue")
        missing = variable.encoding.get("missing_value")
        if fill is None or missing is None or float(fill) != float(missing):
            raise ValueError(
                f"{variable_name} fill and missing-value encodings must be explicit and equal"
            )
        chunks = variable.encoding.get("chunksizes")
        if chunks != (1, 360, 720):
            raise ValueError(f"unexpected {variable_name} chunking: {chunks}")
        for start in range(0, dataset.sizes["time"], block_days):
            values = variable.isel(time=slice(start, start + block_days)).values
            finite = np.isfinite(values)
            counts["finite"] += int(finite.sum())
            counts["missing"] += int((~finite).sum())
            if finite.any():
                valid = values[finite]
                minimum = min(minimum, float(valid.min()))
                maximum = max(maximum, float(valid.max()))
    if counts["finite"] == 0 or counts["missing"] != 0:
        raise ValueError(f"temperature values fail complete-finite smoke gate: {counts}")
    if minimum <= 150.0 or maximum >= 350.0:
        raise ValueError(f"temperature values fall outside physical Kelvin bounds: {minimum}..{maximum}")
    return {
        "role": "complete_file_engineering_smoke_not_feature_response_or_scc",
        "file_name": path.name,
        "bytes": actual_bytes,
        "sha512": actual_sha512,
        "variable": variable_name,
        "dimensions": {"time": len(expected_time), "lat": 360, "lon": 720},
        "start_time": expected_time[0].isoformat(),
        "end_time": expected_time[-1].isoformat(),
        "calendar": "proleptic_gregorian",
        "units": "K",
        "grid_resolution_degrees": 0.5,
        "latitude_orientation": "descending",
        "longitude_convention": "-179.75_to_179.75",
        "fill_value": float(fill),
        "chunksizes": list(chunks),
        "finite_values": counts["finite"],
        "missing_values": counts["missing"],
        "minimum_temperature_k": minimum,
        "maximum_temperature_k": maximum,
        "result": "passed",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("file", type=Path)
    parser.add_argument("--expected-bytes", type=int, required=True)
    parser.add_argument("--expected-sha512", required=True)
    parser.add_argument("--start-date", required=True)
    parser.add_argument("--end-date", required=True)
    parser.add_argument("--variable", choices=("tas", "tasmin", "tasmax"), default="tas")
    parser.add_argument("--expected-hour", type=int, choices=range(24), default=12)
    parser.add_argument("--block-days", type=int, default=32)
    parser.add_argument("--audit-out", type=Path, required=True)
    args = parser.parse_args()
    result = validate(
        args.file,
        expected_bytes=args.expected_bytes,
        expected_sha512=args.expected_sha512,
        start_date=args.start_date,
        end_date=args.end_date,
        variable_name=args.variable,
        expected_hour=args.expected_hour,
        block_days=args.block_days,
    )
    args.audit_out.parent.mkdir(parents=True, exist_ok=True)
    args.audit_out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        f"ISIMIP3b full temperature content gate passed: {result['finite_values']} finite values, "
        f"range={result['minimum_temperature_k']}..{result['maximum_temperature_k']} K"
    )


if __name__ == "__main__":
    main()
