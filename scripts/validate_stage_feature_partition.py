#!/usr/bin/env python3
"""Validate one latitude partition of crop-stage climate features."""
from __future__ import annotations

import argparse

import numpy as np
import pandas as pd

from build_crop_stage_features import STAGE_FEATURE_COLUMNS


KEYS = ["harvest_year", "lat", "lon_360", "crop", "irrigation"]


def validate_frame(
    frame: pd.DataFrame, expected_stages: int, expected_stage_fractions: str
) -> None:
    if expected_stages < 1:
        raise ValueError("expected_stages must be positive")
    if frame.empty and len(frame.columns) == 0:
        return
    if set(frame.columns) != set(STAGE_FEATURE_COLUMNS):
        raise ValueError(
            "Stage-feature schema mismatch: "
            f"missing={sorted(set(STAGE_FEATURE_COLUMNS) - set(frame.columns))}, "
            f"extra={sorted(set(frame.columns) - set(STAGE_FEATURE_COLUMNS))}"
        )
    if frame.empty:
        return
    if frame.duplicated(KEYS + ["stage_id"]).any():
        raise ValueError("Duplicate crop-year/grid/stage rows")
    if set(frame.stage_fractions.astype(str)) != {expected_stage_fractions}:
        raise ValueError("Stage fractions differ from the declared contract")
    expected = set(range(1, expected_stages + 1))
    stage_sets = frame.groupby(KEYS, observed=True).stage_id.agg(lambda values: set(values))
    if not stage_sets.map(lambda values: values == expected).all():
        raise ValueError("A crop-year/grid does not have exactly the expected stages")

    numeric = [
        "harvest_year", "plant_year", "lat", "lon", "lon_360", "stage_id",
        "stage_start_offset_day",
        "stage_end_offset_day", "stage_days", "tmean_c", "precip_mm",
        "wet_days_n", "cdd_max_days", "rx1day_mm",
    ]
    if not np.isfinite(frame[numeric].to_numpy(dtype=float)).all():
        raise ValueError("Stage feature partition contains nonfinite required metrics")
    nonnegative = [
        "stage_days", "precip_mm", "wet_days_n", "cdd_max_days", "rx1day_mm"
    ]
    if (frame[nonnegative] < 0).any().any():
        raise ValueError("Negative stage count or precipitation metric")
    integer_columns = [
        "harvest_year", "plant_year", "stage_id",
        "stage_start_offset_day", "stage_end_offset_day", "stage_days",
        "wet_days_n", "cdd_max_days",
    ]
    integers = frame[integer_columns].to_numpy(dtype=float)
    if not np.equal(integers, np.floor(integers)).all():
        raise ValueError("Calendar, stage, and count fields must be integers")
    if not frame["cross_year"].isin([True, False]).all():
        raise ValueError("cross_year must be Boolean")
    expected_plant_year = frame.harvest_year.astype(int) - frame.cross_year.astype(int)
    if not frame.plant_year.astype(int).equals(expected_plant_year):
        raise ValueError("plant_year is inconsistent with harvest_year/cross_year")
    if (frame.wet_days_n > frame.stage_days).any() or (
        frame.cdd_max_days > frame.stage_days
    ).any():
        raise ValueError("Stage day-count metric exceeds stage length")
    tolerance = 1e-6 + 1e-7 * frame.precip_mm.abs()
    if (frame.rx1day_mm > frame.precip_mm + tolerance).any():
        raise ValueError("Daily maximum exceeds stage precipitation")
    must_have_rx5 = frame.stage_days >= 5
    if frame.loc[must_have_rx5, "rx5day_mm"].isna().any() or frame.loc[
        ~must_have_rx5, "rx5day_mm"
    ].notna().any():
        raise ValueError("Five-day metric missingness does not match stage length")
    five_day = frame.loc[must_have_rx5]
    if not np.isfinite(five_day.rx5day_mm.to_numpy(dtype=float)).all() or (
        five_day.rx5day_mm < 0
    ).any():
        raise ValueError("Five-day precipitation metric must be finite and nonnegative")
    tolerance = 1e-6 + 1e-7 * five_day.precip_mm.abs()
    if (five_day.rx5day_mm > five_day.precip_mm + tolerance).any():
        raise ValueError("Five-day maximum exceeds stage precipitation")
    if (five_day.rx5day_mm + tolerance < five_day.rx1day_mm).any():
        raise ValueError("Five-day maximum is below the daily maximum")

    constant_calendar = ["plant_year", "cross_year"]
    if not frame.groupby(KEYS, observed=True)[constant_calendar].nunique(
        dropna=False
    ).eq(1).all().all():
        raise ValueError("Calendar fields vary across stages within one crop-year/grid")
    ordered = frame.sort_values(KEYS + ["stage_id"])
    starts = ordered.stage_start_offset_day.astype(int)
    ends = ordered.stage_end_offset_day.astype(int)
    first = ordered.stage_id.astype(int).eq(1)
    if not starts.loc[first].eq(1).all():
        raise ValueError("The first stage does not start on crop-season day one")
    previous_end = ordered.groupby(
        KEYS, observed=True, sort=False
    ).stage_end_offset_day.shift(1)
    if not starts.loc[~first].eq(previous_end.loc[~first].astype(int) + 1).all():
        raise ValueError("Stage offsets are not contiguous")
    if not (ends - starts + 1).eq(ordered.stage_days.astype(int)).all():
        raise ValueError("Stage offsets and stage lengths differ")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("partition")
    parser.add_argument("--expected-stages", type=int, default=3)
    parser.add_argument("--expected-stage-fractions", default="0,0.3,0.7,1")
    args = parser.parse_args()
    frame = pd.read_parquet(args.partition)
    validate_frame(frame, args.expected_stages, args.expected_stage_fractions)
    if frame.empty:
        print("OK empty valid partition")
    else:
        print(
            f"OK {len(frame)} stage rows; "
            f"years={frame.harvest_year.min()}–{frame.harvest_year.max()}"
        )


if __name__ == "__main__":
    main()
