#!/usr/bin/env python3
"""Build annual same-realization GMST from pinned ISIMIP3b daily tas files."""
from __future__ import annotations

import argparse
from contextlib import ExitStack
from pathlib import Path

import numpy as np
import pandas as pd

from climate_inputs import open_checked_daily_file_arrays


def build(
    paths: list[str],
    *,
    esm_id: str,
    member_id: str,
    scenario: str,
    source_id: str,
    year_start: int,
    year_end: int,
    block_days: int = 32,
) -> pd.DataFrame:
    identifiers = [esm_id, member_id, scenario, source_id]
    if any(not value.strip() for value in identifiers):
        raise ValueError("ESM, member, scenario, and GMST source ID must be explicit")
    if year_start > year_end:
        raise ValueError("GMST year range is reversed")
    if block_days < 1:
        raise ValueError("GMST block_days must be positive")
    with ExitStack() as stack:
        arrays, timestamp_parts = open_checked_daily_file_arrays(stack, paths, "tas")
        if any(array.dims != ("time", "lat", "lon") for array in arrays):
            raise ValueError("tas must use time/lat/lon dimensions")
        if any(array.attrs.get("units") not in {"K", "kelvin"} for array in arrays):
            raise ValueError("tas must retain Kelvin units")
        latitude = arrays[0]["lat"].values.astype(float)
        longitude = arrays[0]["lon"].values.astype(float)
        if not np.isfinite(latitude).all() or not np.isfinite(longitude).all():
            raise ValueError("GMST grid coordinates must be finite")
        if len(np.unique(latitude)) != len(latitude) or len(np.unique(longitude)) != len(longitude):
            raise ValueError("GMST grid coordinates must be unique")
        weights = np.cos(np.deg2rad(arrays[0]["lat"]))
        if not np.isfinite(weights).all() or (weights <= 0).any():
            raise ValueError("latitude cell weights are invalid")
        # Never reduce the full multi-decadal global array in one xarray
        # expression.  Weighted reductions can materialize the source,
        # broadcast weights, masks, and float64 temporaries simultaneously.
        # On the 30-year 0.5-degree input this exceeded physical RAM.  Limit
        # every payload reduction to an explicit time block instead.
        daily_parts: list[np.ndarray] = []
        date_parts: list[np.ndarray] = []
        first = np.datetime64(f"{year_start:04d}-01-01", "ns")
        last_exclusive = np.datetime64(f"{year_end + 1:04d}-01-01", "ns")
        for array, timestamps in zip(arrays, timestamp_parts):
            selected = np.flatnonzero(
                (timestamps >= first) & (timestamps < last_exclusive)
            )
            for start in range(0, len(selected), block_days):
                positions = selected[start : start + block_days]
                block = array.isel(time=positions)
                reduced = block.weighted(weights).mean(("lat", "lon"), skipna=False)
                daily_parts.append(np.asarray(reduced.values, dtype=float))
                date_parts.append(timestamps[positions])
        if not daily_parts:
            raise ValueError(f"Climate input has no days for GMST years {year_start}-{year_end}")
        values = np.concatenate(daily_parts)
        if not np.isfinite(values).all() or not ((values > 150.0) & (values < 350.0)).all():
            raise ValueError("daily global temperature means are missing or outside physical bounds")
        dates = pd.DatetimeIndex(np.concatenate(date_parts))
    output = (
        pd.DataFrame({"date": dates, "gmst_daily_k": values})
        .assign(year=lambda frame: frame.date.dt.year)
        .groupby("year", as_index=False, sort=True)["gmst_daily_k"]
        .mean()
        .rename(columns={"gmst_daily_k": "gmst_value_k"})
    )
    expected_years = list(range(year_start, year_end + 1))
    if output["year"].tolist() != expected_years:
        raise ValueError("annual GMST output lacks the exact requested year sequence")
    output.insert(0, "gmst_source_id", source_id)
    output.insert(0, "scenario", scenario)
    output.insert(0, "member_id", member_id)
    output.insert(0, "esm_id", esm_id)
    output["daily_count"] = [
        int(((dates.year == year)).sum()) for year in expected_years
    ]
    expected_counts = [len(pd.date_range(f"{year}-01-01", f"{year}-12-31", freq="D")) for year in expected_years]
    if output["daily_count"].tolist() != expected_counts:
        raise ValueError("annual GMST daily counts do not match the decoded calendar")
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tas", nargs="+", required=True)
    parser.add_argument("--esm-id", required=True)
    parser.add_argument("--member-id", required=True)
    parser.add_argument("--scenario", required=True)
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--year-start", type=int, required=True)
    parser.add_argument("--year-end", type=int, required=True)
    parser.add_argument("--block-days", type=int, default=32)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    output = build(
        args.tas,
        esm_id=args.esm_id,
        member_id=args.member_id,
        scenario=args.scenario,
        source_id=args.source_id,
        year_start=args.year_start,
        year_end=args.year_end,
        block_days=args.block_days,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    output.to_parquet(args.out, index=False)
    print(f"wrote {len(output)} annual same-realization GMST rows to {args.out}")


if __name__ == "__main__":
    main()
