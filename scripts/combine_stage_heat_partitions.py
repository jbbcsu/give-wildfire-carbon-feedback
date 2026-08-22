#!/usr/bin/env python3
"""Combine a complete set of validated stage-heat latitude partitions."""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from validate_stage_heat_partition import validate_frame


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--expected-partitions", type=int, required=True)
    parser.add_argument("--expected-stages", type=int, default=3)
    parser.add_argument("--threshold-c", action="append", type=float, required=True)
    args = parser.parse_args()
    paths = sorted(Path(args.directory).glob("*.parquet"))
    if len(paths) != args.expected_partitions:
        raise ValueError(f"Expected {args.expected_partitions} partitions, found {len(paths)}")
    frames = [pd.read_parquet(path) for path in paths]
    for frame in frames:
        validate_frame(frame, args.threshold_c, args.expected_stages)
    combined = pd.concat(frames, ignore_index=True)
    validate_frame(combined, args.threshold_c, args.expected_stages)
    if combined.empty:
        raise ValueError("No stage-heat rows to combine")
    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    combined.to_parquet(output, index=False)
    print(f"wrote {len(combined)} stage-heat rows from {len(paths)} partitions")


if __name__ == "__main__":
    main()
