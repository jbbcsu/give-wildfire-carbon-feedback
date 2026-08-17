#!/usr/bin/env python3
"""Validate and combine latitude-partitioned crop-stage climate features.

This intentionally has a separate contract from ``combine_feature_partitions``:
one crop-year/grid key has one row for each temporal proxy stage.  The script
refuses incomplete or duplicated stage panels before writing an analysis input.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


REQUIRED_COLUMNS = {
    "harvest_year", "plant_year", "lat", "lon", "lon_360", "crop", "irrigation",
    "cross_year", "stage_id", "stage_start_offset_day", "stage_end_offset_day",
    "stage_days", "stage_fractions", "tmean_c", "precip_mm", "wet_days_n",
    "cdd_max_days", "rx1day_mm", "rx5day_mm",
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--expected-partitions", type=int, required=True)
    parser.add_argument("--expected-stages", type=int, default=3)
    args = parser.parse_args()
    paths = sorted(Path(args.directory).glob("*.parquet"))
    if len(paths) != args.expected_partitions:
        raise ValueError(f"Expected {args.expected_partitions} partitions, found {len(paths)}")
    frames = [pd.read_parquet(path) for path in paths]
    for path, frame in zip(paths, frames):
        # The builder writes a valid zero-row parquet without columns when a
        # latitude band has no calendar cells.  Retain it in the expected
        # partition count, but do not treat its absent inferred schema as a
        # conflict with populated bands.
        if frame.empty and len(frame.columns) == 0:
            continue
        if set(frame.columns) != REQUIRED_COLUMNS:
            missing = sorted(REQUIRED_COLUMNS - set(frame.columns))
            extra = sorted(set(frame.columns) - REQUIRED_COLUMNS)
            raise ValueError(f"Schema mismatch in {path}: missing={missing}, extra={extra}")
    populated = [frame for frame in frames if not frame.empty]
    combined = pd.concat(populated, ignore_index=True) if populated else pd.DataFrame(columns=sorted(REQUIRED_COLUMNS))
    base_keys = ["harvest_year", "lat", "lon_360", "crop", "irrigation"]
    keys = base_keys + ["stage_id"]
    if combined.empty:
        raise ValueError("No stage rows to combine")
    if combined.duplicated(keys).any():
        raise ValueError("Duplicate crop-year/grid/stage rows across partitions")
    expected = set(range(1, args.expected_stages + 1))
    stage_sets = combined.groupby(base_keys, observed=True).stage_id.agg(lambda x: set(x))
    if not stage_sets.map(lambda observed: observed == expected).all():
        bad = stage_sets.loc[~stage_sets.map(lambda observed: observed == expected)].head()
        raise ValueError(f"Incomplete or unexpected stage IDs; examples: {bad.to_dict()}")
    nonnegative = ["stage_days", "precip_mm", "wet_days_n", "cdd_max_days", "rx1day_mm", "rx5day_mm"]
    if (combined[nonnegative] < 0).any().any():
        raise ValueError("Negative count or precipitation metric")
    if (combined.rx5day_mm + 1e-9 < combined.rx1day_mm).any():
        raise ValueError("A stage has rx5day below rx1day")
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    combined.to_parquet(args.out, index=False)
    print(f"wrote {len(combined)} combined stage rows from {len(paths)} partitions")


if __name__ == "__main__":
    main()
