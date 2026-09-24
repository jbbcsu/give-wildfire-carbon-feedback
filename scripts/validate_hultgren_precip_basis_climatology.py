#!/usr/bin/env python3
"""Validate precipitation-basis climatologies with fixed daily sentinels."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

from build_hultgren_grid_weather_basis import crop_month_keys
from build_hultgren_precip_basis_climatology import FEATURES, phase_basis

KEYS = ["regime", "native_lat_index", "native_lon_index"]


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
    if receipt["schema"] != "hultgren_precip_basis_climatology/v1":
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
    for source in receipt["support_sources"].values():
        if digest(Path(source["path"])) != source["sha256"]:
            raise AssertionError(f"support source identity differs: {source['path']}")

    frame = pd.read_parquet(data_path).sort_values(KEYS).reset_index(drop=True)
    if len(frame) != receipt["support"]["output_rows"] or frame.duplicated(KEYS).any():
        raise AssertionError("output support differs")
    if set(frame.regime) != {"rainfed", "irrigated"}:
        raise AssertionError("regime support differs")
    if not np.isfinite(frame[FEATURES].to_numpy()).all() or np.any(frame[FEATURES].to_numpy() < 0):
        raise AssertionError("output precipitation basis invalid")
    if not frame.complete_harvest_years.eq(29).all():
        raise AssertionError("harvest-year counts differ")

    positions = sorted({0, len(frame) // 4, len(frame) // 2, 3 * len(frame) // 4, len(frame) - 1})
    sentinel = frame.iloc[positions].copy().reset_index(drop=True)
    lat_indices = sentinel.native_lat_index.to_numpy(dtype=np.int64)
    lon_indices = sentinel.native_lon_index.to_numpy(dtype=np.int64)
    months = pd.date_range("1981-01-01", "2010-12-01", freq="MS")
    monthly = np.zeros((len(months), len(sentinel)), dtype=np.float64)
    counts = np.zeros((len(months), len(sentinel)), dtype=np.int16)
    daily_steps = 0
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
            for index, day in enumerate(dates):
                month_index = (int(day.year) - 1981) * 12 + int(day.month) - 1
                monthly[month_index] += np.maximum(values[index], 0.0)
                counts[month_index] += 1
            daily_steps += len(dates)
    expected_counts = months.days_in_month.to_numpy(dtype=np.int16)[:, None]
    if not np.array_equal(counts, np.broadcast_to(expected_counts, counts.shape)):
        raise AssertionError("sentinel cell-month incomplete")

    month_lookup = {(int(value.year), int(value.month)): index for index, value in enumerate(months)}
    expected = np.zeros((len(sentinel), len(FEATURES)), dtype=np.float64)
    for position, row in enumerate(sentinel.itertuples(index=False)):
        yearly = []
        for harvest_year in range(1982, 2011):
            keys = crop_month_keys(harvest_year, int(row.plant_month), int(row.harvest_month))
            yearly.append(phase_basis(monthly[[month_lookup[key] for key in keys], position]))
        expected[position] = np.stack(yearly).mean(axis=0)
    actual = sentinel[FEATURES].to_numpy(dtype=np.float64)
    absolute = np.abs(actual - expected)
    if not np.allclose(actual, expected, rtol=2e-12, atol=1e-8):
        raise AssertionError(f"sentinel precipitation basis differs: {absolute.max()}")
    errors = {field: float(absolute[:, index].max()) for index, field in enumerate(FEATURES)}

    result = {
        "schema": "hultgren_precip_basis_climatology_validation/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "pass",
        "source": {"path": str(args.receipt), "sha256": digest(args.receipt)},
        "validation": {
            "all_source_support_and_output_hashes_checked": True,
            "all_output_keys_and_finite_values_checked": True,
            "daily_steps_reaggregated_per_sentinel": daily_steps,
            "sentinel_positions": positions,
            "sentinel_cells": sentinel[KEYS].to_dict("records"),
            "sentinel_harvest_year_bases_reaggregated": int(len(sentinel) * 29),
            "maximum_absolute_errors": errors,
            "claim_gates_checked": True,
        },
        "scope": "Full artifact identity/support checks plus independent daily reaggregation at five fixed key-order regime-cell sentinels; not a second full-cell calculation.",
        "interpretation": "Historical precipitation-basis input validation only; no response, damage, or SCC gate is opened.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
