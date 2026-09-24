#!/usr/bin/env python3
"""Validate the maize-cell annual precipitation baseline with fixed sentinels."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

FIELDS = ["annual_precip_mean_mm", "annual_precip_sd_mm", "annual_precip_min_mm", "annual_precip_max_mm"]
KEYS = ["native_lat_index", "native_lon_index"]


def digest(path: Path, algorithm: str = "sha256") -> str:
    value = hashlib.new(algorithm)
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("fresh output required")
    receipt = json.loads(args.receipt.read_text(encoding="utf-8"))
    if receipt["schema"] != "hultgren_cell_annual_precip_climatology/v1":
        raise AssertionError("unexpected receipt schema")
    if receipt["claim_gates"]["response"] or receipt["claim_gates"]["damage_or_scc"]:
        raise AssertionError("claim gate promoted")
    data_path = Path(receipt["output"]["path"])
    if digest(data_path) != receipt["output"]["sha256"]:
        raise AssertionError("output hash differs")
    for source in receipt["sources"]:
        path = Path(source["path"])
        if path.stat().st_size != source["bytes"] or digest(path, "sha512") != source["sha512"]:
            raise AssertionError(f"source identity differs: {path}")

    frame = pd.read_parquet(data_path).sort_values(KEYS).reset_index(drop=True)
    if len(frame) != receipt["support"]["unique_cells"] or frame.duplicated(KEYS).any():
        raise AssertionError("output support differs")
    if not np.isfinite(frame[FIELDS].to_numpy()).all() or not frame.annual_precip_mean_mm.gt(0).all():
        raise AssertionError("output precipitation invalid")
    positions = sorted({0, len(frame) // 4, len(frame) // 2, 3 * len(frame) // 4, len(frame) - 1})
    sentinel = frame.iloc[positions].copy().reset_index(drop=True)
    lat_indices = sentinel.native_lat_index.to_numpy(dtype=np.int64)
    lon_indices = sentinel.native_lon_index.to_numpy(dtype=np.int64)
    annual: list[np.ndarray] = []
    years: list[int] = []
    for source in receipt["sources"]:
        with xr.open_dataset(source["path"], engine="h5netcdf", decode_times=True, cache=False) as dataset:
            if dataset.pr.dims != ("time", "lat", "lon") or dataset.pr.attrs.get("units") != "kg m-2 s-1":
                raise AssertionError("source schema changed")
            point = dataset.pr.isel(
                lat=xr.DataArray(lat_indices, dims="point"),
                lon=xr.DataArray(lon_indices, dims="point"),
            )
            values = np.asarray(point.values, dtype=np.float64) * 86_400.0
            dates = pd.DatetimeIndex(dataset.time.values).normalize()
            if values.shape != (len(dates), len(sentinel)) or not np.isfinite(values).all() or np.any(values < -1e-10):
                raise AssertionError("sentinel daily precipitation invalid")
            for year in sorted(set(dates.year)):
                mask = dates.year == year
                expected_days = 366 if pd.Timestamp(year, 12, 31).dayofyear == 366 else 365
                if int(mask.sum()) != expected_days:
                    raise AssertionError(f"sentinel year incomplete: {year}")
                annual.append(np.maximum(values[mask], 0.0).sum(axis=0))
                years.append(int(year))
    if years != list(range(1981, 2011)):
        raise AssertionError("sentinel years differ")
    matrix = np.stack(annual)
    expected = {
        "annual_precip_mean_mm": matrix.mean(axis=0),
        "annual_precip_sd_mm": matrix.std(axis=0, ddof=1),
        "annual_precip_min_mm": matrix.min(axis=0),
        "annual_precip_max_mm": matrix.max(axis=0),
    }
    errors = {}
    for field, values in expected.items():
        actual = sentinel[field].to_numpy(dtype=np.float64)
        error = float(np.max(np.abs(actual - values)))
        if not np.allclose(actual, values, rtol=2e-12, atol=1e-8):
            raise AssertionError(f"sentinel {field} differs: {error}")
        errors[field] = error
    if not math.isclose(float(frame.annual_precip_mean_mm.min()), receipt["support"]["minimum_mean_annual_precip_mm"], rel_tol=0, abs_tol=1e-12):
        raise AssertionError("receipt minimum differs")
    if not math.isclose(float(frame.annual_precip_mean_mm.max()), receipt["support"]["maximum_mean_annual_precip_mm"], rel_tol=0, abs_tol=1e-12):
        raise AssertionError("receipt maximum differs")

    result = {
        "schema": "hultgren_cell_annual_precip_climatology_validation/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "pass",
        "source": {"path": str(args.receipt), "sha256": digest(args.receipt)},
        "validation": {
            "all_source_and_output_hashes_checked": True,
            "all_output_keys_and_finite_values_checked": True,
            "source_years": years,
            "sentinel_positions": positions,
            "sentinel_cells": sentinel[KEYS].to_dict("records"),
            "sentinel_annual_totals_reaggregated": int(matrix.size),
            "maximum_absolute_errors": errors,
            "claim_gates_checked": True,
        },
        "scope": "Full artifact identity/support checks plus independent daily reaggregation at five key-order sentinels; not a second full-cell calculation.",
        "interpretation": "Climate baseline input validation only; no response, damage, or SCC gate is opened.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
