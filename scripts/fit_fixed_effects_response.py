#!/usr/bin/env python3
"""Fit a transparent pilot grid/year fixed-effects yield response.

This validates the estimation plumbing; it is not the final hierarchical,
crop-stage response or an SCC coefficient source. It uses an iterative two-way
within transformation, avoiding an infeasible dense grid-dummy matrix for a
global panel.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


def two_way_within(frame: pd.DataFrame, columns: list[str], grid: pd.Series, years: pd.Series, iterations: int = 100) -> pd.DataFrame:
    """Alternating projection for unbalanced grid/year fixed effects."""
    result = frame[columns].astype(float).copy()
    for _ in range(iterations):
        prior = result.to_numpy(copy=True)
        result = result - result.groupby(grid, observed=True).transform("mean")
        result = result - result.groupby(years, observed=True).transform("mean")
        if np.max(np.abs(result.to_numpy() - prior)) < 1e-10:
            break
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--panel", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    panel = pd.read_parquet(args.panel)
    panel = panel.loc[panel.yield_observed].copy()
    if len(panel) == 0:
        raise ValueError("No observed GDHY yields in panel")
    panel["log_yield_t_ha"] = np.log(panel.yield_t_ha)
    panel["log1p_precip_mm"] = np.log1p(panel.precip_mm)
    panel["tmean_c_x_log1p_precip_mm"] = panel.tmean_c * panel.log1p_precip_mm
    features = ["tmean_c", "log1p_precip_mm", "cdd_max_days", "rx1day_mm", "tmean_c_x_log1p_precip_mm"]
    panel = panel.dropna(subset=features + ["log_yield_t_ha"])
    if panel.harvest_year.nunique() < 3 or len(panel) < 100:
        raise ValueError("Pilot needs at least three years and 100 observations")
    grid = panel.lat.astype(str) + "_" + panel.lon_360.astype(str) + "_" + panel.crop + "_" + panel.irrigation
    transformed = two_way_within(panel, ["log_yield_t_ha"] + features, grid, panel.harvest_year)
    feature_scales = panel[features].std(ddof=0)
    matrix = (transformed[features] / feature_scales).to_numpy(dtype=float)
    outcome = transformed.log_yield_t_ha.to_numpy()
    coefficients, _, rank, singular_values = np.linalg.lstsq(matrix, outcome, rcond=1e-12)
    if not np.isfinite(coefficients).all():
        raise ValueError("Nonfinite pilot coefficients; inspect design conditioning")
    # Some sandboxed BLAS builds leave floating-point status flags set after
    # matrix multiplication despite finite output; validate values explicitly.
    with np.errstate(over="ignore", divide="ignore", invalid="ignore"):
        fitted = matrix @ coefficients
    if not np.isfinite(fitted).all():
        raise ValueError("Nonfinite fitted values; inspect design conditioning")
    residual = outcome - fitted
    total = float(np.dot(outcome, outcome))
    with np.errstate(over="ignore", divide="ignore", invalid="ignore"):
        rss = float(np.dot(residual, residual))
    if not np.isfinite(rss):
        raise ValueError("Nonfinite residual sum of squares")
    output = {
        "n_observations": int(len(panel)), "n_grids": int(grid.nunique()),
        "n_years": int(panel.harvest_year.nunique()), "matrix_rank": int(rank),
        "condition_number": float(singular_values[0] / singular_values[-1]),
        "within_r_squared": float(1 - rss / total),
        "coefficients_one_standard_deviation_feature": {name: float(value) for name, value in zip(features, coefficients)},
        "warning": "Pilot-only within-estimator diagnostic. Do not use these coefficients for SCC or causal interpretation.",
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
