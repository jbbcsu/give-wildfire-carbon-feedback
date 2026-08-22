#!/usr/bin/env python3
"""Validate one crop-stage CRU scPDSI latitude partition."""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from build_crop_stage_scpdsi_features import COLUMNS, KEYS


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
        "stage_days", "scpdsi_mean", "scpdsi_min", "scpdsi_days_at_or_below_threshold",
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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("partition")
    parser.add_argument("--threshold", type=float, required=True)
    parser.add_argument("--expected-stages", type=int, default=3)
    args = parser.parse_args()
    validate_frame(pd.read_parquet(Path(args.partition)), args.threshold, args.expected_stages)
    print(f"valid stage-scPDSI partition: {args.partition}")


if __name__ == "__main__":
    main()
