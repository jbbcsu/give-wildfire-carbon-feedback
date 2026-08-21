#!/usr/bin/env python3
"""Validate one latitude partition of crop-stage climate features."""
from __future__ import annotations

import argparse

import numpy as np
import pandas as pd

from build_crop_stage_features import STAGE_FEATURE_COLUMNS


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("partition")
    args = parser.parse_args()
    frame = pd.read_parquet(args.partition)
    if frame.empty and len(frame.columns) == 0:
        print("OK legacy empty valid partition")
        return
    missing = set(STAGE_FEATURE_COLUMNS) - set(frame.columns)
    if missing:
        raise ValueError(f"Missing schema columns: {sorted(missing)}")
    if frame.empty:
        print("OK empty valid partition")
        return
    keys = ["harvest_year", "lat", "lon_360", "crop", "irrigation", "stage_id"]
    if frame.duplicated(keys).any():
        raise ValueError("Duplicate crop-year/grid/stage rows")
    nonnegative = ["stage_days", "precip_mm", "wet_days_n", "cdd_max_days", "rx1day_mm"]
    if (frame[nonnegative] < 0).any().any():
        raise ValueError("Negative stage count or precipitation metric")
    if (frame.wet_days_n > frame.stage_days).any() or (frame.cdd_max_days > frame.stage_days).any():
        raise ValueError("Stage day-count metric exceeds stage length")
    if (frame.rx1day_mm > frame.precip_mm + 1e-6 + 1e-7 * frame.precip_mm.abs()).any():
        raise ValueError("Daily maximum exceeds stage precipitation")
    must_have_rx5 = frame.stage_days >= 5
    if frame.loc[must_have_rx5, "rx5day_mm"].isna().any() or frame.loc[~must_have_rx5, "rx5day_mm"].notna().any():
        raise ValueError("Five-day metric missingness does not match stage length")
    five_day = frame.loc[must_have_rx5]
    tolerance = 1e-6 + 1e-7 * five_day.precip_mm.abs()
    if (five_day.rx5day_mm > five_day.precip_mm + tolerance).any():
        raise ValueError("Five-day maximum exceeds stage precipitation")
    print(f"OK {len(frame)} stage rows; years={frame.harvest_year.min()}–{frame.harvest_year.max()}")


if __name__ == "__main__":
    main()
