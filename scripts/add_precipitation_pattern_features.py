#!/usr/bin/env python3
"""Add fixed-total precipitation-distribution features to a stage-wide panel.

Seasonal precipitation quantity remains an explicit regressor.  Stage shares,
timing centroid, concentration, wet-day frequency, and wet-day intensity then
describe distribution conditional on (or normalized by) that quantity.  The
script does not estimate a response; it makes the accounting distinction
available to a pre-specified response model.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--panel", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--stages", type=int, default=3)
    args = parser.parse_args()
    panel = pd.read_parquet(args.panel)
    precipitation = [f"stage{i}_precip_mm" for i in range(1, args.stages + 1)]
    wet_days = [f"stage{i}_wet_days_n" for i in range(1, args.stages + 1)]
    needed = {"precip_mm", "season_days"} | set(precipitation) | set(wet_days)
    if missing := needed - set(panel.columns):
        raise ValueError(f"Panel missing {sorted(missing)}")
    values = panel[precipitation].to_numpy(dtype=float)
    total = panel.precip_mm.to_numpy(dtype=float)
    if (total < 0).any() or (values < 0).any():
        raise ValueError("Negative precipitation")
    if not np.allclose(values.sum(axis=1), total, rtol=0, atol=1e-3):
        raise ValueError("Stage precipitation does not reproduce seasonal total")
    # A zero-total season has no defined composition; retain an explicit flag
    # and zero-normalize rather than silently divide by zero.
    panel["zero_precipitation_season"] = total == 0
    shares = np.divide(values, total[:, None], out=np.zeros_like(values), where=total[:, None] > 0)
    for index in range(args.stages):
        panel[f"stage{index + 1}_precip_share"] = shares[:, index]
    panel["precipitation_concentration_hhi"] = (shares ** 2).sum(axis=1)
    stage_midpoints = (np.arange(args.stages, dtype=float) + 0.5) / args.stages
    # Explicit finite check is more reliable than spurious floating-point
    # status warnings from some sandboxed BLAS builds.
    with np.errstate(over="ignore", divide="ignore", invalid="ignore"):
        timing_centroid = shares @ stage_midpoints
    if not np.isfinite(timing_centroid).all():
        raise ValueError("Nonfinite precipitation timing centroid")
    panel["precipitation_timing_centroid"] = timing_centroid
    wet_total = panel[wet_days].sum(axis=1).to_numpy(dtype=float)
    panel["wet_day_frequency"] = wet_total / panel.season_days.to_numpy(dtype=float)
    panel["mean_wet_day_intensity_mm"] = np.divide(total, wet_total, out=np.zeros_like(total), where=wet_total > 0)
    if (panel.wet_day_frequency > 1 + 1e-12).any():
        raise ValueError("Wet-day frequency exceeds one")
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    panel.to_parquet(args.out, index=False)
    print(f"wrote {len(panel)} rows; zero-precipitation share={panel.zero_precipitation_season.mean():.6f}")


if __name__ == "__main__":
    main()
