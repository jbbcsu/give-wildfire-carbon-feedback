#!/usr/bin/env python3
"""Validate a crop-year feature partition before it enters the estimation panel."""
from __future__ import annotations

import argparse
import sys

import pandas as pd

from build_crop_year_features import FEATURE_COLUMNS


parser = argparse.ArgumentParser()
parser.add_argument("partition")
args = parser.parse_args()
frame = pd.read_parquet(args.partition)
missing = set(FEATURE_COLUMNS) - set(frame.columns)
if missing:
    raise SystemExit(f"Missing schema columns: {sorted(missing)}")
if frame.empty:
    print("OK empty valid partition")
    raise SystemExit(0)
keys = ["harvest_year", "lat", "lon_360", "crop", "irrigation"]
if frame.duplicated(keys).any():
    raise SystemExit("Duplicate crop-year grid rows")
if (frame[["precip_mm", "wet_days_n", "cdd_max_days", "rx1day_mm", "rx5day_mm"]] < 0).any().any():
    raise SystemExit("Negative precipitation/count/extreme metric")
if (frame.wet_days_n > frame.season_days).any() or (frame.cdd_max_days > frame.season_days).any():
    raise SystemExit("Day-count metric exceeds season length")
if (frame.rx5day_mm > frame.precip_mm + 1e-6).any():
    raise SystemExit("Five-day maximum exceeds seasonal precipitation")
if (frame.season_days < 1).any():
    raise SystemExit("Nonpositive season length")
print(f"OK {len(frame)} rows; years={frame.harvest_year.min()}–{frame.harvest_year.max()}")
