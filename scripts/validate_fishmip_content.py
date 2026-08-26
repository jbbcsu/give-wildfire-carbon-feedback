#!/usr/bin/env python3
"""Validate complete pinned FishMIP total-catch files without SCC inference."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from urllib.parse import urlparse

import numpy as np
import xarray as xr


EXPECTED_LAT = np.arange(89.5, -90.0, -1.0)
EXPECTED_LON = np.arange(-179.5, 180.0, 1.0)
TIME_UNITS = "months since 1601-01-01 00:00:00"
TIME_CALENDAR = "360_day"


def checksum(path: Path) -> str:
    digest = hashlib.sha512()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def plan_row(plan: Path, file_name: str) -> dict[str, str]:
    with plan.open(newline="", encoding="utf-8") as stream:
        rows = [row for row in csv.DictReader(stream) if Path(urlparse(row["file_url"]).path).name == file_name]
    if len(rows) != 1:
        raise ValueError(f"expected one acquisition-plan row for {file_name}, got {len(rows)}")
    if rows[0]["acquisition_stage"] != "content_smoke":
        raise ValueError("file is not authorized in the frozen content-smoke stage")
    return rows[0]


def validate(path: Path, row: dict[str, str], *, block_months: int = 24) -> dict[str, object]:
    if block_months < 1:
        raise ValueError("block_months must be positive")
    expected_bytes = int(row["bytes"])
    if path.stat().st_size != expected_bytes:
        raise ValueError("local FishMIP byte size differs from the acquisition plan")
    actual_checksum = checksum(path)
    if actual_checksum != row["sha512"]:
        raise ValueError("local FishMIP SHA-512 differs from the acquisition plan")
    start_year = int(row["start_year"])
    end_year = int(row["end_year"])
    expected_time = np.arange((start_year - 1601) * 12, (end_year - 1601 + 1) * 12, dtype=float)
    totals = {"finite": 0, "missing": 0, "zero": 0, "negative": 0}
    minimum = np.inf
    maximum = -np.inf
    yearly: list[dict[str, object]] = []
    always_finite: np.ndarray | None = None
    always_missing: np.ndarray | None = None
    with xr.open_dataset(path, engine="h5netcdf", decode_times=False) as dataset:
        if set(dataset.data_vars) != {"tc"}:
            raise ValueError(f"expected only tc data variable, got {sorted(dataset.data_vars)}")
        tc = dataset["tc"]
        if tc.dims != ("time", "lat", "lon"):
            raise ValueError(f"unexpected tc dimension order: {tc.dims}")
        if dataset.sizes != {"time": len(expected_time), "lat": 180, "lon": 360}:
            raise ValueError(f"unexpected FishMIP dimensions: {dict(dataset.sizes)}")
        if tc.attrs.get("units") != "g m-2":
            raise ValueError("tc units must be g m-2")
        if dataset["time"].attrs.get("units") != TIME_UNITS:
            raise ValueError("FishMIP time units changed")
        if dataset["time"].attrs.get("calendar") != TIME_CALENDAR:
            raise ValueError("FishMIP calendar must be explicit 360_day")
        if not np.array_equal(dataset["time"].values, expected_time):
            raise ValueError("FishMIP time coordinate is not the exact contiguous monthly sequence")
        if not np.array_equal(dataset["lat"].values, EXPECTED_LAT):
            raise ValueError("FishMIP latitude grid changed")
        if not np.array_equal(dataset["lon"].values, EXPECTED_LON):
            raise ValueError("FishMIP longitude grid changed")
        fill = tc.encoding.get("_FillValue")
        missing = tc.encoding.get("missing_value")
        if fill is None or missing is None or not np.isclose(float(fill), float(missing), rtol=1e-6, atol=0):
            raise ValueError("tc fill and missing-value encodings must be explicit and equal")
        if tc.encoding.get("chunksizes") != (1, 180, 360):
            raise ValueError(f"unexpected tc chunking: {tc.encoding.get('chunksizes')}")
        for year_index, year in enumerate(range(start_year, end_year + 1)):
            values = tc.isel(time=slice(year_index * 12, (year_index + 1) * 12)).values
            finite = np.isfinite(values)
            valid = values[finite]
            stats = {
                "year": year,
                "finite": int(finite.sum()),
                "missing": int((~finite).sum()),
                "zero": int((valid == 0).sum()),
                "negative": int((valid < 0).sum()),
                "minimum": float(valid.min()) if valid.size else None,
                "maximum": float(valid.max()) if valid.size else None,
            }
            yearly.append(stats)
            for name in totals:
                totals[name] += int(stats[name])
            if valid.size:
                minimum = min(minimum, float(valid.min()))
                maximum = max(maximum, float(valid.max()))
            finite_cell = finite.all(axis=0)
            missing_cell = (~finite).all(axis=0)
            always_finite = finite_cell if always_finite is None else (always_finite & finite_cell)
            always_missing = missing_cell if always_missing is None else (always_missing & missing_cell)
    if totals["finite"] == 0 or totals["negative"] != 0:
        raise ValueError(f"FishMIP tc contains no finite values or negative catch: {totals}")
    mixed_cells = 180 * 360 - int(always_finite.sum()) - int(always_missing.sum())
    return {
        "role": "biophysical_scenario_content_smoke_not_pulse_welfare_or_scc",
        "dataset_id": row["dataset_id"],
        "file_id": row["file_id"],
        "file_name": path.name,
        "model": row["model"],
        "climate_forcing": row["climate_forcing"],
        "climate_scenario": row["climate_scenario"],
        "version": row["version"],
        "bytes": expected_bytes,
        "sha512": actual_checksum,
        "dimensions": {"time": len(expected_time), "lat": 180, "lon": 360},
        "calendar": TIME_CALENDAR,
        "time_units": TIME_UNITS,
        "units": "g m-2",
        "finite_values": totals["finite"],
        "missing_values": totals["missing"],
        "zero_values": totals["zero"],
        "negative_values": totals["negative"],
        "minimum": minimum,
        "maximum": maximum,
        "always_finite_grid_cells": int(always_finite.sum()),
        "always_missing_grid_cells": int(always_missing.sum()),
        "mixed_validity_grid_cells": mixed_cells,
        "yearly": yearly,
        "result": "passed",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("file", type=Path)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--audit-out", type=Path, required=True)
    args = parser.parse_args()
    audit = validate(args.file, plan_row(args.plan, args.file.name))
    args.audit_out.parent.mkdir(parents=True, exist_ok=True)
    args.audit_out.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        f"FishMIP content file passed: finite={audit['finite_values']}, missing={audit['missing_values']}, "
        f"zero={audit['zero_values']}, range={audit['minimum']}..{audit['maximum']}"
    )


if __name__ == "__main__":
    main()
