#!/usr/bin/env python3
"""Validate a crop-year feature partition before it enters the estimation panel."""
from __future__ import annotations

import argparse
import sys

import numpy as np
import pandas as pd

from build_crop_year_features import FEATURE_COLUMNS


parser = argparse.ArgumentParser()
parser.add_argument("partition")
args = parser.parse_args()
frame = pd.read_parquet(args.partition)
# Older runs may contain a zero-row parquet whose writer inferred no schema.
# Treat it as a completed empty band; newer builder output carries the explicit
# FEATURE_COLUMNS schema above.
if frame.empty and len(frame.columns) == 0:
    print("OK legacy empty valid partition")
    raise SystemExit(0)
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
rounding_tolerance = 1e-6 + 1e-7 * frame.precip_mm.abs()
if (frame.rx5day_mm > frame.precip_mm + rounding_tolerance).any():
    raise SystemExit("Five-day maximum exceeds seasonal precipitation")
if (frame.season_days < 1).any():
    raise SystemExit("Nonpositive season length")
print(f"OK {len(frame)} rows; years={frame.harvest_year.min()}–{frame.harvest_year.max()}")
