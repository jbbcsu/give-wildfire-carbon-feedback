#!/usr/bin/env python3
"""Full-file content gate for a pinned ISIMIP3b daily precipitation block.

This is an engineering/source-integrity check.  It does not fit a climate
feature response, create a baseline/pulse pair, or authorize an SCC input.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr


EXPECTED_LAT = np.arange(89.75, -90.0, -0.5)
EXPECTED_LON = np.arange(-179.75, 180.0, 0.5)


def sha512(path: Path) -> str:
    digest = hashlib.sha512()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate(
    path: Path,
    *,
    expected_bytes: int,
    expected_sha512: str,
    start_date: str,
    end_date: str,
    expected_hour: int = 12,
    block_days: int = 32,
) -> dict[str, object]:
    if block_days < 1:
        raise ValueError("block_days must be positive")
    if expected_hour not in range(24):
        raise ValueError("expected_hour must be an integer from 0 through 23")
    actual_bytes = path.stat().st_size
    if actual_bytes != expected_bytes:
        raise ValueError(f"file byte size mismatch: expected {expected_bytes}, got {actual_bytes}")
    actual_sha512 = sha512(path)
    if actual_sha512 != expected_sha512:
        raise ValueError("file SHA-512 differs from the pinned catalogue checksum")
    expected_time = pd.date_range(start_date, end_date, freq="D") + pd.Timedelta(hours=expected_hour)
    counts = {"finite": 0, "missing": 0, "zero": 0, "negative": 0}
    minimum = np.inf
    maximum = -np.inf
    with xr.open_dataset(path, engine="h5netcdf") as dataset:
        if set(dataset.data_vars) != {"pr"}:
            raise ValueError(f"expected only data variable pr, got {sorted(dataset.data_vars)}")
        variable = dataset["pr"]
        if variable.dims != ("time", "lat", "lon"):
            raise ValueError(f"unexpected pr dimension order: {variable.dims}")
        if dataset.sizes != {"time": len(expected_time), "lat": 360, "lon": 720}:
            raise ValueError(f"unexpected decoded dimensions: {dict(dataset.sizes)}")
        if variable.attrs.get("standard_name") != "precipitation_flux":
            raise ValueError("pr standard_name must be precipitation_flux")
        if variable.attrs.get("units") != "kg m-2 s-1":
            raise ValueError("pr units must be kg m-2 s-1")
        if dataset["lat"].attrs.get("units") != "degrees_north":
            raise ValueError("latitude units changed")
        if dataset["lon"].attrs.get("units") != "degrees_east":
            raise ValueError("longitude units changed")
        if not np.array_equal(dataset["lat"].values, EXPECTED_LAT):
            raise ValueError("latitude grid is not the registered descending 0.5-degree grid")
        if not np.array_equal(dataset["lon"].values, EXPECTED_LON):
            raise ValueError("longitude grid is not the registered -179.75..179.75 grid")
        actual_time = pd.DatetimeIndex(dataset["time"].values)
        if not actual_time.equals(expected_time):
            raise ValueError(
                f"decoded time is not the exact complete daily {expected_hour:02d}:00 sequence"
            )
        if dataset["time"].encoding.get("calendar") != "proleptic_gregorian":
            raise ValueError("time calendar must be proleptic_gregorian")
        fill = variable.encoding.get("_FillValue")
        missing = variable.encoding.get("missing_value")
        if fill is None or missing is None or float(fill) != float(missing):
            raise ValueError("pr fill and missing-value encodings must be explicit and equal")
        chunks = variable.encoding.get("chunksizes")
        if chunks != (1, 360, 720):
            raise ValueError(f"unexpected pr chunking: {chunks}")
        for start in range(0, dataset.sizes["time"], block_days):
            values = variable.isel(time=slice(start, start + block_days)).values
            finite = np.isfinite(values)
            counts["finite"] += int(finite.sum())
            counts["missing"] += int((~finite).sum())
            if finite.any():
                valid = values[finite]
                counts["zero"] += int((valid == 0).sum())
                counts["negative"] += int((valid < 0).sum())
                minimum = min(minimum, float(valid.min()))
                maximum = max(maximum, float(valid.max()))
    if counts["finite"] == 0 or counts["missing"] != 0 or counts["negative"] != 0:
        raise ValueError(f"precipitation values fail finite/nonnegative smoke gate: {counts}")
    return {
        "role": "complete_file_engineering_smoke_not_feature_response_or_scc",
        "file_name": path.name,
        "bytes": actual_bytes,
        "sha512": actual_sha512,
        "variable": "pr",
        "dimensions": {"time": len(expected_time), "lat": 360, "lon": 720},
        "start_time": expected_time[0].isoformat(),
        "end_time": expected_time[-1].isoformat(),
        "calendar": "proleptic_gregorian",
        "units": "kg m-2 s-1",
        "grid_resolution_degrees": 0.5,
        "latitude_orientation": "descending",
        "longitude_convention": "-179.75_to_179.75",
        "fill_value": float(fill),
        "chunksizes": list(chunks),
        "finite_values": counts["finite"],
        "missing_values": counts["missing"],
        "zero_values": counts["zero"],
        "negative_values": counts["negative"],
        "minimum_flux": minimum,
        "maximum_flux": maximum,
        "result": "passed",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("file", type=Path)
    parser.add_argument("--expected-bytes", type=int, required=True)
    parser.add_argument("--expected-sha512", required=True)
    parser.add_argument("--start-date", required=True)
    parser.add_argument("--end-date", required=True)
    parser.add_argument("--expected-hour", type=int, choices=range(24), default=12)
    parser.add_argument("--block-days", type=int, default=32)
    parser.add_argument("--audit-out", type=Path, required=True)
    args = parser.parse_args()
    audit = validate(
        args.file,
        expected_bytes=args.expected_bytes,
        expected_sha512=args.expected_sha512,
        start_date=args.start_date,
        end_date=args.end_date,
        expected_hour=args.expected_hour,
        block_days=args.block_days,
    )
    args.audit_out.parent.mkdir(parents=True, exist_ok=True)
    args.audit_out.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        f"ISIMIP3b full precipitation content gate passed: {audit['finite_values']} finite values, "
        f"{audit['zero_values']} zeros, range={audit['minimum_flux']}..{audit['maximum_flux']}"
    )


if __name__ == "__main__":
    main()
