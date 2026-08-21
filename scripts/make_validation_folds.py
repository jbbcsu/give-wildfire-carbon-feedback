#!/usr/bin/env python3
"""Create outcome-independent spatial, temporal, and climate-extreme labels.

The labels are constructed from keys and climate features only.  They are
written alongside (rather than used to fit) the yield panel, which prevents
post-outcome selection of the held-out cases used by the final response model.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

import numpy as np
import pandas as pd


def stable_fold(value: str, folds: int, seed: str) -> int:
    digest = hashlib.sha256(f"{seed}:{value}".encode()).digest()
    return int.from_bytes(digest[:8], "big") % folds


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--panel", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--spatial-folds", type=int, default=5)
    parser.add_argument("--block-degrees", type=float, default=5.0)
    parser.add_argument("--temporal-holdout-years", type=int, default=2)
    parser.add_argument("--extreme-quantile", type=float, default=0.95)
    parser.add_argument("--seed", default="precipitation-scc-v1")
    args = parser.parse_args()
    if args.spatial_folds < 2 or args.block_degrees <= 0 or not 0.5 < args.extreme_quantile < 1:
        raise ValueError("Invalid fold/block/quantile setting")
    panel = pd.read_parquet(args.panel)
    required = {"harvest_year", "lat", "lon_360", "crop", "irrigation", "cdd_max_days", "rx1day_mm"}
    if missing := required - set(panel.columns):
        raise ValueError(f"Panel missing {sorted(missing)}")
    lat_block = np.floor((panel.lat + 90) / args.block_degrees).astype(int)
    lon_block = np.floor(panel.lon_360 / args.block_degrees).astype(int)
    panel["spatial_block_id"] = lat_block.astype(str) + "_" + lon_block.astype(str)
    panel["spatial_fold"] = panel.spatial_block_id.map(lambda x: stable_fold(x, args.spatial_folds, args.seed))
    final_holdout_start = int(panel.harvest_year.max()) - args.temporal_holdout_years + 1
    panel["is_temporal_holdout"] = panel.harvest_year >= final_holdout_start
    grid = panel.lat.astype(str) + "_" + panel.lon_360.astype(str) + "_" + panel.crop + "_" + panel.irrigation
    # Use pandas' grouped quantile transform rather than a Python lambda per
    # grid. The semantics are identical, but the vectorized path is necessary
    # for the full multi-crop panel.
    cdd_cutoff = panel.groupby(grid, observed=True).cdd_max_days.transform("quantile", q=args.extreme_quantile)
    rx1_cutoff = panel.groupby(grid, observed=True).rx1day_mm.transform("quantile", q=args.extreme_quantile)
    panel["is_dry_extreme"] = panel.cdd_max_days >= cdd_cutoff
    panel["is_wet_extreme"] = panel.rx1day_mm >= rx1_cutoff
    panel["is_climate_extreme"] = panel.is_dry_extreme | panel.is_wet_extreme
    panel["validation_design"] = (
        f"block={args.block_degrees:g};folds={args.spatial_folds};"
        f"temporal_last={args.temporal_holdout_years};q={args.extreme_quantile:g};seed={args.seed}"
    )
    if panel.spatial_fold.nunique() != args.spatial_folds:
        raise ValueError("Not all requested spatial folds populated")
    if not panel.is_temporal_holdout.any() or not panel.is_climate_extreme.any():
        raise ValueError("A required holdout class is empty")
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    panel.to_parquet(args.out, index=False)
    print(
        f"wrote {len(panel)} rows; spatial folds={panel.spatial_fold.nunique()}; "
        f"temporal holdout share={panel.is_temporal_holdout.mean():.3f}; "
        f"climate-extreme share={panel.is_climate_extreme.mean():.3f}"
    )


if __name__ == "__main__":
    main()
