#!/usr/bin/env python3
"""Check that stage partitions reproduce additive season-level features.

The check is deliberately independent of the feature builder.  It is a guard
against off-by-one date, cross-year, and stage-boundary errors before empirical
estimation; it does not validate causal identification.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


KEYS = ["harvest_year", "lat", "lon_360", "crop", "irrigation"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stages", required=True)
    parser.add_argument("--season", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    stages = pd.read_parquet(args.stages)
    season = pd.read_parquet(args.season)
    grouped = stages.groupby(KEYS, observed=True).agg(
        stage_days=("stage_days", "sum"),
        precip_mm=("precip_mm", "sum"),
        wet_days_n=("wet_days_n", "sum"),
        rx1day_mm=("rx1day_mm", "max"),
    ).reset_index()
    merged = season.merge(grouped, on=KEYS, suffixes=("_season", "_stages"), validate="one_to_one")
    if len(merged) != len(season):
        raise ValueError("Stage aggregation does not cover every season row")
    differences = {
        "stage_days": (merged.stage_days - merged.season_days).abs(),
        "precip_mm": (merged.precip_mm_stages - merged.precip_mm_season).abs(),
        "wet_days_n": (merged.wet_days_n_stages - merged.wet_days_n_season).abs(),
        "rx1day_mm": (merged.rx1day_mm_stages - merged.rx1day_mm_season).abs(),
    }
    tolerances = {"stage_days": 0.0, "precip_mm": 1e-3, "wet_days_n": 0.0, "rx1day_mm": 1e-6}
    summary = {
        "n_crop_year_grid_rows": int(len(merged)),
        "max_absolute_differences": {key: float(value.max()) for key, value in differences.items()},
        "tolerances": tolerances,
        "status": "passed",
    }
    failures = {key: float(value.max()) for key, value in differences.items() if value.max() > tolerances[key]}
    if failures:
        raise ValueError(f"Stage-to-season reconciliation failed: {failures}")
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
