#!/usr/bin/env python3
"""Validate one crop-stage CRU scPDSI latitude partition."""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from build_crop_stage_scpdsi_features import COLUMNS, KEYS
from scpdsi_partition_provenance import (
    PARTITION_CONTRACT_ID,
    read_manifest,
    require_sha256,
    same_path,
    sha256_file,
)


def validate_frame(frame: pd.DataFrame, threshold: float, expected_stages: int) -> None:
    if expected_stages < 1:
        raise ValueError("expected_stages must be positive")
    if set(frame.columns) != set(COLUMNS):
        raise ValueError(
            f"Stage-scPDSI schema mismatch: missing={sorted(set(COLUMNS) - set(frame.columns))}, "
            f"extra={sorted(set(frame.columns) - set(COLUMNS))}"
        )
    if frame.empty:
        return
    if frame.duplicated(KEYS + ["stage_id"]).any():
        raise ValueError("Duplicate crop-year/grid/stage rows")
    expected = set(range(1, expected_stages + 1))
    stage_sets = frame.groupby(KEYS, observed=True).stage_id.agg(lambda values: set(values))
    if not stage_sets.map(lambda observed: observed == expected).all():
        raise ValueError("A crop-year/grid does not have exactly the expected stages")
    numeric = [
        "plant_year", "plant_doy", "maturity_doy", "season_days",
        "stage_id", "stage_start_offset_day", "stage_end_offset_day", "stage_days",
        "scpdsi_mean", "scpdsi_min", "scpdsi_days_at_or_below_threshold",
        "scpdsi_threshold", "monthly_index_days_covered",
    ]
    if not np.isfinite(frame[numeric].to_numpy(dtype=float)).all():
        raise ValueError("Stage scPDSI partition contains nonfinite metrics")
    if not np.allclose(frame.scpdsi_threshold.to_numpy(dtype=float), threshold, rtol=0, atol=1e-12):
        raise ValueError("Stage scPDSI threshold differs from the declared threshold")
    stage_days = frame.stage_days.to_numpy(dtype=float)
    if (stage_days <= 0).any() or not np.equal(stage_days, np.floor(stage_days)).all():
        raise ValueError("Stage lengths must be positive integers")
    if not frame.monthly_index_days_covered.equals(frame.stage_days):
        raise ValueError("Monthly scPDSI coverage does not equal stage length")
    days = frame.scpdsi_days_at_or_below_threshold.to_numpy(dtype=float)
    if (days < 0).any() or not np.equal(days, np.floor(days)).all():
        raise ValueError("scPDSI threshold-day counts must be nonnegative integers")
    if (days > frame.stage_days.to_numpy(dtype=float)).any():
        raise ValueError("scPDSI threshold-day count exceeds stage length")
    if (frame.scpdsi_min > frame.scpdsi_mean + 1e-12).any():
        raise ValueError("Minimum scPDSI exceeds its day-weighted stage mean")
    if set(frame.drought_index_name.astype(str)) != {"CRU_TS_scpdsi"}:
        raise ValueError("Unexpected drought-index identity")
    if set(frame.drought_source_role.astype(str)) != {"historical_benchmark_not_future_scc_input"}:
        raise ValueError("CRU scPDSI role must remain historical-benchmark-only")
    if not frame["cross_year"].isin([True, False]).all():
        raise ValueError("cross_year must be Boolean")
    integer_columns = [
        "harvest_year", "plant_year", "plant_doy", "maturity_doy", "season_days",
        "stage_id", "stage_start_offset_day", "stage_end_offset_day",
    ]
    integers = frame[integer_columns].to_numpy(dtype=float)
    if not np.equal(integers, np.floor(integers)).all():
        raise ValueError("Calendar and stage-index fields must be integers")
    if ((frame.plant_doy < 1) | (frame.plant_doy > 366)).any() or (
        (frame.maturity_doy < 1) | (frame.maturity_doy > 366)
    ).any():
        raise ValueError("Planting and maturity day-of-year must lie in [1, 366]")
    if (frame.season_days <= 0).any():
        raise ValueError("Crop-season duration must be positive")
    expected_plant_year = frame.harvest_year.astype(int) - frame.cross_year.astype(int)
    if not frame.plant_year.astype(int).equals(expected_plant_year):
        raise ValueError("plant_year is inconsistent with harvest_year/cross_year")
    constant_calendar = ["plant_year", "cross_year", "plant_doy", "maturity_doy", "season_days"]
    if not frame.groupby(KEYS, observed=True)[constant_calendar].nunique(dropna=False).eq(1).all().all():
        raise ValueError("Calendar fields vary across stages within one crop-year/grid")
    ordered = frame.sort_values(KEYS + ["stage_id"])
    starts = ordered.stage_start_offset_day.astype(int)
    ends = ordered.stage_end_offset_day.astype(int)
    first = ordered.stage_id.astype(int).eq(1)
    last = ordered.stage_id.astype(int).eq(expected_stages)
    if not starts.loc[first].eq(1).all() or not ends.loc[last].eq(
        ordered.loc[last, "season_days"].astype(int)
    ).all():
        raise ValueError("Stage offsets do not span the complete crop season")
    previous_end = ordered.groupby(KEYS, observed=True, sort=False).stage_end_offset_day.shift(1)
    if not starts.loc[~first].eq(previous_end.loc[~first].astype(int) + 1).all():
        raise ValueError("Stage offsets are not contiguous")
    if not (ends - starts + 1).eq(ordered.stage_days.astype(int)).all():
        raise ValueError("Stage offsets and stage lengths differ")


def validate_partition(
    partition_path: Path,
    manifest_path: Path,
    *,
    threshold: float,
    expected_stages: int,
    expected_crop: str,
    expected_irrigation: str,
    expected_year_start: int,
    expected_year_end: int,
    expected_lat_start: int,
    expected_lat_stop: int,
    expected_stage_fractions: str,
    expected_scpdsi_sha256: str,
    expected_calendar_sha256: str,
) -> tuple[pd.DataFrame, dict[str, object]]:
    manifest = read_manifest(manifest_path)
    if manifest.get("contract_id") != PARTITION_CONTRACT_ID:
        raise ValueError("Unexpected stage-scPDSI partition manifest contract")
    if not same_path(manifest.get("output_file"), partition_path):
        raise ValueError("Partition manifest points to another output file")
    if require_sha256(manifest.get("output_sha256"), "output_sha256") != sha256_file(partition_path):
        raise ValueError("Partition hash differs from its source manifest")
    expected = {
        "crop": expected_crop,
        "irrigation": expected_irrigation,
        "year_start": int(expected_year_start),
        "year_end": int(expected_year_end),
        "lat_start": int(expected_lat_start),
        "lat_stop": int(expected_lat_stop),
        "stage_fractions": expected_stage_fractions,
        "expected_stages": int(expected_stages),
        "drought_source_role": "historical_benchmark_not_future_scc_input",
    }
    for field, value in expected.items():
        if manifest.get(field) != value:
            raise ValueError(f"Partition manifest {field} differs from expectation")
    if abs(float(manifest.get("threshold")) - float(threshold)) > 1e-12:
        raise ValueError("Partition manifest threshold differs from expectation")
    if require_sha256(manifest.get("scpdsi_source_sha256"), "scpdsi_source_sha256") != require_sha256(
        expected_scpdsi_sha256, "expected_scpdsi_sha256"
    ):
        raise ValueError("Partition scPDSI source hash differs from the current source")
    if require_sha256(manifest.get("calendar_source_sha256"), "calendar_source_sha256") != require_sha256(
        expected_calendar_sha256, "expected_calendar_sha256"
    ):
        raise ValueError("Partition calendar source hash differs from the current source")
    frame = pd.read_parquet(partition_path)
    validate_frame(frame, threshold, expected_stages)
    if int(manifest.get("output_rows", -1)) != len(frame):
        raise ValueError("Partition row count differs from its manifest")
    if not frame.empty:
        if set(frame.crop.astype(str)) != {expected_crop}:
            raise ValueError("Partition crop differs from expectation")
        if set(frame.irrigation.astype(str)) != {expected_irrigation}:
            raise ValueError("Partition irrigation differs from expectation")
        if set(frame.harvest_year.astype(int)) != set(range(expected_year_start, expected_year_end + 1)):
            raise ValueError("Partition year coverage differs from expectation")
        if set(frame.stage_fractions.astype(str)) != {expected_stage_fractions}:
            raise ValueError("Partition stage fractions differ from expectation")
    return frame, manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("partition")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--threshold", type=float, required=True)
    parser.add_argument("--expected-stages", type=int, default=3)
    parser.add_argument("--expected-crop", required=True)
    parser.add_argument("--expected-irrigation", required=True)
    parser.add_argument("--expected-year-start", type=int, required=True)
    parser.add_argument("--expected-year-end", type=int, required=True)
    parser.add_argument("--expected-lat-start", type=int, required=True)
    parser.add_argument("--expected-lat-stop", type=int, required=True)
    parser.add_argument("--expected-stage-fractions", required=True)
    parser.add_argument("--expected-scpdsi-sha256", required=True)
    parser.add_argument("--expected-calendar-sha256", required=True)
    args = parser.parse_args()
    validate_partition(
        Path(args.partition), Path(args.manifest), threshold=args.threshold,
        expected_stages=args.expected_stages, expected_crop=args.expected_crop,
        expected_irrigation=args.expected_irrigation,
        expected_year_start=args.expected_year_start, expected_year_end=args.expected_year_end,
        expected_lat_start=args.expected_lat_start, expected_lat_stop=args.expected_lat_stop,
        expected_stage_fractions=args.expected_stage_fractions,
        expected_scpdsi_sha256=args.expected_scpdsi_sha256,
        expected_calendar_sha256=args.expected_calendar_sha256,
    )
    print(f"valid stage-scPDSI partition: {args.partition}")


if __name__ == "__main__":
    main()
