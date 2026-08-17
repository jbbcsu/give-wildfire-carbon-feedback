#!/usr/bin/env python3
"""Validate and combine same-schema crop-year feature partitions."""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from build_crop_year_features import FEATURE_COLUMNS


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--expected-partitions", type=int, required=True)
    args = parser.parse_args()
    paths = sorted(Path(args.directory).glob("*.parquet"))
    if len(paths) != args.expected_partitions:
        raise ValueError(f"Expected {args.expected_partitions} partitions, found {len(paths)}")
    frames = [pd.read_parquet(path) for path in paths]
    for path, frame in zip(paths, frames):
        if frame.empty and len(frame.columns) == 0:
            continue
        if set(frame.columns) != set(FEATURE_COLUMNS):
            raise ValueError(f"Schema mismatch in {path}")
    populated = [frame for frame in frames if not frame.empty]
    combined = pd.concat(populated, ignore_index=True) if populated else pd.DataFrame(columns=FEATURE_COLUMNS)
    keys = ["harvest_year", "lat", "lon_360", "crop", "irrigation"]
    if combined.duplicated(keys).any():
        raise ValueError("Duplicate rows across latitude partitions")
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    combined.to_parquet(args.out, index=False)
    print(f"wrote {len(combined)} combined rows from {len(paths)} partitions")


if __name__ == "__main__":
    main()
