#!/usr/bin/env python3
"""Combine non-overlapping response-panel periods under one strict schema."""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


KEYS = ["harvest_year", "lat", "lon_360", "crop", "irrigation"]


def combine(
    paths: list[Path], expected_crop: str, expected_irrigation: str,
    year_start: int, year_end: int,
) -> pd.DataFrame:
    if not paths:
        raise ValueError("At least one panel is required")
    if year_end < year_start:
        raise ValueError("year_end must not precede year_start")
    frames: list[pd.DataFrame] = []
    reference_columns: list[str] | None = None
    for path in paths:
        frame = pd.read_parquet(path)
        if frame.empty:
            raise ValueError(f"Panel is empty: {path}")
        if missing := set(KEYS) - set(frame.columns):
            raise ValueError(f"Panel {path} lacks keys {sorted(missing)}")
        if reference_columns is None:
            reference_columns = frame.columns.tolist()
        elif frame.columns.tolist() != reference_columns:
            raise ValueError(f"Panel schema or column order differs: {path}")
        if set(frame.crop.astype(str)) != {expected_crop}:
            raise ValueError(f"Panel crop differs from {expected_crop}: {path}")
        if set(frame.irrigation.astype(str)) != {expected_irrigation}:
            raise ValueError(f"Panel irrigation differs from {expected_irrigation}: {path}")
        if frame.duplicated(KEYS).any():
            raise ValueError(f"Panel has duplicate keys: {path}")
        frames.append(frame)

    combined = pd.concat(frames, ignore_index=True)
    if combined.duplicated(KEYS).any():
        raise ValueError("Periods overlap on crop-grid-year keys")
    observed_years = sorted(int(value) for value in combined.harvest_year.unique())
    expected_years = list(range(year_start, year_end + 1))
    if observed_years != expected_years:
        raise ValueError(f"Harvest-year coverage is not complete: observed={observed_years}, expected={expected_years}")
    return combined.sort_values(KEYS, kind="stable").reset_index(drop=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--panel", action="append", required=True)
    parser.add_argument("--expected-crop", required=True)
    parser.add_argument("--expected-irrigation", required=True)
    parser.add_argument("--year-start", type=int, required=True)
    parser.add_argument("--year-end", type=int, required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    output = combine(
        [Path(value) for value in args.panel], args.expected_crop, args.expected_irrigation,
        args.year_start, args.year_end,
    )
    path = Path(args.out)
    path.parent.mkdir(parents=True, exist_ok=True)
    output.to_parquet(path, index=False)
    print(
        f"wrote {len(output)} rows for {args.expected_crop}/{args.expected_irrigation}; "
        f"harvest years={args.year_start}-{args.year_end}"
    )


if __name__ == "__main__":
    main()
