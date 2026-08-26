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


def validate_row_invariants(frame: pd.DataFrame, day_column: str, label: str) -> None:
    required = {day_column, "precip_mm", "wet_days_n", "cdd_max_days", "rx1day_mm", "rx5day_mm"}
    if missing := required - set(frame.columns):
        raise ValueError(f"{label} rows lack invariant fields {sorted(missing)}")
    always_finite = required - {"rx5day_mm"}
    values = frame[list(always_finite)].to_numpy(dtype=float)
    if not np.isfinite(values).all():
        raise ValueError(f"{label} rainfall invariants contain nonfinite values")
    days = frame[day_column].to_numpy(dtype=float)
    precipitation = frame.precip_mm.to_numpy(dtype=float)
    wet_days = frame.wet_days_n.to_numpy(dtype=float)
    dry_spell = frame.cdd_max_days.to_numpy(dtype=float)
    rx1 = frame.rx1day_mm.to_numpy(dtype=float)
    rx5 = frame.rx5day_mm.to_numpy(dtype=float)
    if (days <= 0).any() or (precipitation < 0).any():
        raise ValueError(f"{label} rows contain nonpositive days or negative precipitation")
    if ((wet_days < 0) | (wet_days > days) | (dry_spell < 0) | (dry_spell > days)).any():
        raise ValueError(f"{label} wet-day or dry-spell counts exceed the crop window")
    rx5_finite = np.isfinite(rx5)
    if ((~rx5_finite) & (days >= 5)).any():
        raise ValueError(f"{label} Rx5day is missing for a window of at least five days")
    if (
        (rx1 < 0)
        | (rx5_finite & (rx5 + 1e-12 < rx1))
        | (rx5_finite & (rx5 > precipitation + 1e-9))
    ).any():
        raise ValueError(f"{label} Rx1day/Rx5day ordering or total-precipitation bound failed")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stages", required=True)
    parser.add_argument("--season", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    stages = pd.read_parquet(args.stages)
    season = pd.read_parquet(args.season)
    validate_row_invariants(stages, "stage_days", "stage")
    validate_row_invariants(season, "season_days", "season")
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
        "row_invariants": {
            "stage_rows_checked": int(len(stages)),
            "season_rows_checked": int(len(season)),
            "checks": [
                "finite_nonnegative_precipitation",
                "bounded_wet_days",
                "bounded_maximum_dry_spell",
                "0 <= Rx1day <= Rx5day <= total precipitation where window length is at least five days",
            ],
        },
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
