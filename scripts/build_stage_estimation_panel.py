#!/usr/bin/env python3
"""Join validated long stage features to a season-level GDHY outcome panel.

The input season panel must already have completed its coordinate-checked GDHY
join.  Stages are pivoted to explicit columns, so one observed yield remains a
single regression observation.  This is an estimation-panel utility only; it
does not calibrate welfare damages or modify GIVE.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


KEYS = ["harvest_year", "lat", "lon_360", "crop", "irrigation"]
STAGE_VALUES = ["tmean_c", "precip_mm", "wet_days_n", "cdd_max_days", "rx1day_mm", "rx5day_mm", "stage_days"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stages", required=True)
    parser.add_argument("--season-panel", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--expected-stages", type=int, default=3)
    args = parser.parse_args()
    stages = pd.read_parquet(args.stages)
    season = pd.read_parquet(args.season_panel)
    if stages.duplicated(KEYS + ["stage_id"]).any():
        raise ValueError("Stage input has duplicate keys")
    if season.duplicated(KEYS).any():
        raise ValueError("Season panel has duplicate keys")
    expected = set(range(1, args.expected_stages + 1))
    sets = stages.groupby(KEYS, observed=True).stage_id.agg(lambda values: set(values))
    if not sets.map(lambda observed: observed == expected).all():
        raise ValueError("Stage input does not have exactly the expected stages per crop-year/grid")
    missing_values = set(STAGE_VALUES) - set(stages.columns)
    if missing_values:
        raise ValueError(f"Stage input missing {sorted(missing_values)}")
    wide = stages.pivot(index=KEYS, columns="stage_id", values=STAGE_VALUES)
    wide.columns = [f"stage{stage_id}_{name}" for name, stage_id in wide.columns]
    wide = wide.reset_index()
    panel = season.merge(wide, on=KEYS, how="inner", validate="one_to_one")
    if len(panel) != len(season):
        raise ValueError(f"Stage merge dropped {len(season) - len(panel)} season-panel rows")
    stage_day_cols = [f"stage{i}_stage_days" for i in range(1, args.expected_stages + 1)]
    if (panel[stage_day_cols].sum(axis=1) != panel.season_days).any():
        raise ValueError("Stage days do not sum to season_days")
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    panel.to_parquet(args.out, index=False)
    print(f"wrote {len(panel)} stage-resolved estimation rows; yield coverage={panel.yield_observed.mean():.3f}")


if __name__ == "__main__":
    main()
