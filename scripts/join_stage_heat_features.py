#!/usr/bin/env python3
"""Join long stage-heat features to a one-row-per-crop-year panel safely."""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


KEYS = ["harvest_year", "lat", "lon_360", "crop", "irrigation"]
STAGE_METADATA = {
    "plant_year", "lon", "cross_year", "stage_id", "stage_start_offset_day",
    "stage_end_offset_day", "stage_days", "stage_fractions",
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--panel", required=True)
    parser.add_argument("--stage-heat", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--expected-stages", type=int, default=3)
    args = parser.parse_args()
    panel = pd.read_parquet(args.panel)
    heat = pd.read_parquet(args.stage_heat)
    required = set(KEYS) | STAGE_METADATA | {"tmax_mean_c"}
    if missing := required - set(heat.columns):
        raise ValueError(f"Stage heat input missing {sorted(missing)}")
    if panel.duplicated(KEYS).any() or heat.duplicated(KEYS + ["stage_id"]).any():
        raise ValueError("Duplicate crop-year/grid or stage keys")
    expected = set(range(1, args.expected_stages + 1))
    stage_sets = heat.groupby(KEYS, observed=True).stage_id.agg(lambda values: set(values))
    if not stage_sets.map(lambda observed: observed == expected).all():
        raise ValueError("Stage heat input does not have exactly the expected stages")
    metric_columns = sorted(set(heat.columns) - set(KEYS) - STAGE_METADATA)
    if not metric_columns or any(not pd.api.types.is_numeric_dtype(heat[name]) for name in metric_columns):
        raise ValueError("Heat metrics must be nonempty and numeric")
    if not np.isfinite(heat[metric_columns].to_numpy(dtype=float)).all():
        raise ValueError("Heat metrics contain nonfinite values")
    if (heat[[name for name in metric_columns if name != "tmax_mean_c"]].to_numpy() < 0).any():
        raise ValueError("Heat count or degree-day metric is negative")

    wide = heat.pivot(index=KEYS, columns="stage_id", values=metric_columns)
    wide.columns = [f"stage{stage_id}_{name}" for name, stage_id in wide.columns]
    wide = wide.reset_index()
    joined = panel.merge(wide, on=KEYS, how="left", validate="one_to_one", indicator=True)
    if not joined._merge.eq("both").all() or len(joined) != len(panel):
        raise ValueError("Stage heat join does not cover every panel row exactly once")
    joined = joined.drop(columns="_merge")
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    joined.to_parquet(args.out, index=False)
    print(f"wrote {len(joined)} rows with {len(metric_columns)} heat metrics across {args.expected_stages} stages")


if __name__ == "__main__":
    main()
