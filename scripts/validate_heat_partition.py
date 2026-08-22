#!/usr/bin/env python3
"""Validate one latitude partition of seasonal crop heat features."""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from build_crop_heat_features import threshold_name


BASE_COLUMNS = {
    "harvest_year", "plant_year", "lat", "lon", "lon_360", "crop", "irrigation",
    "cross_year", "plant_doy", "maturity_doy", "season_days", "tmax_mean_c",
}
KEYS = ["harvest_year", "lat", "lon_360", "crop", "irrigation"]


def metric_columns(thresholds: list[float]) -> set[str]:
    return {
        item
        for threshold in sorted(set(thresholds))
        for item in (
            f"{threshold_name(threshold)}_days",
            f"{threshold_name(threshold)}_degree_days",
        )
    }


def validate_frame(frame: pd.DataFrame, thresholds: list[float]) -> None:
    expected_columns = BASE_COLUMNS | metric_columns(thresholds)
    if set(frame.columns) != expected_columns:
        raise ValueError(
            f"Heat schema mismatch: missing={sorted(expected_columns - set(frame.columns))}, "
            f"extra={sorted(set(frame.columns) - expected_columns)}"
        )
    if frame.empty:
        return
    if frame.duplicated(KEYS).any():
        raise ValueError("Duplicate seasonal crop-year/grid heat rows")
    metrics = sorted(metric_columns(thresholds))
    if not np.isfinite(frame[["tmax_mean_c"] + metrics].to_numpy(dtype=float)).all():
        raise ValueError("Heat partition contains nonfinite metrics")
    if (frame.season_days <= 0).any() or not np.equal(frame.season_days, np.floor(frame.season_days)).all():
        raise ValueError("Season lengths must be positive integers")
    if (frame[metrics].to_numpy(dtype=float) < 0).any():
        raise ValueError("Heat day or degree-day metric is negative")
    day_counts = [name for name in metrics if name.endswith("c_days")]
    if day_counts and not np.equal(frame[day_counts], np.floor(frame[day_counts])).all().all():
        raise ValueError("Heat threshold day counts must be integers")
    if day_counts and (frame[day_counts].to_numpy(dtype=float) > frame.season_days.to_numpy()[:, None]).any():
        raise ValueError("Heat threshold day count exceeds season length")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("partition")
    parser.add_argument("--threshold-c", action="append", type=float, required=True)
    args = parser.parse_args()
    validate_frame(pd.read_parquet(Path(args.partition)), args.threshold_c)
    print(f"valid heat partition: {args.partition}")


if __name__ == "__main__":
    main()
