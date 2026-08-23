#!/usr/bin/env python3
"""Validate one latitude partition of stage-resolved heat features."""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from heat_threshold_validation import metric_columns, validate_threshold_metrics, validate_thresholds


BASE_COLUMNS = {
    "harvest_year", "plant_year", "lat", "lon", "lon_360", "crop", "irrigation",
    "cross_year", "stage_id", "stage_start_offset_day", "stage_end_offset_day",
    "stage_days", "stage_fractions", "tmax_mean_c",
}
KEYS = ["harvest_year", "lat", "lon_360", "crop", "irrigation"]


def validate_frame(frame: pd.DataFrame, thresholds: list[float], expected_stages: int) -> None:
    if expected_stages < 1:
        raise ValueError("expected_stages must be positive")
    thresholds = validate_thresholds(thresholds)
    expected_columns = BASE_COLUMNS | metric_columns(thresholds)
    if set(frame.columns) != expected_columns:
        raise ValueError(
            f"Stage-heat schema mismatch: missing={sorted(expected_columns - set(frame.columns))}, "
            f"extra={sorted(set(frame.columns) - expected_columns)}"
        )
    if frame.empty:
        return
    if frame.duplicated(KEYS + ["stage_id"]).any():
        raise ValueError("Duplicate crop-year/grid/stage rows")
    expected = set(range(1, expected_stages + 1))
    stage_sets = frame.groupby(KEYS, observed=True).stage_id.agg(lambda values: set(values))
    if not stage_sets.map(lambda values: values == expected).all():
        raise ValueError("A crop-year/grid does not have exactly the expected stages")
    if not np.isfinite(frame[["tmax_mean_c"]].to_numpy(dtype=float)).all():
        raise ValueError("Stage heat partition contains nonfinite metrics")
    if (frame.stage_days <= 0).any() or not np.equal(frame.stage_days, np.floor(frame.stage_days)).all():
        raise ValueError("Stage lengths must be positive integers")
    validate_threshold_metrics(frame, thresholds, "stage_days")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("partition")
    parser.add_argument("--threshold-c", action="append", type=float, required=True)
    parser.add_argument("--expected-stages", type=int, default=3)
    args = parser.parse_args()
    validate_frame(pd.read_parquet(Path(args.partition)), args.threshold_c, args.expected_stages)
    print(f"valid stage-heat partition: {args.partition}")


if __name__ == "__main__":
    main()
