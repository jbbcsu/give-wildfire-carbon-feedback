#!/usr/bin/env python3
"""Run a stage-resolved pilot two-way fixed-effects yield-response diagnostic.

This is an estimation-plumbing and conditioning check.  It is explicitly not
the final causal response, a substitute for crop-model validation, or a source
of SCC coefficients.  The final design must add multi-crop coverage, year or
climate controls chosen before outcome fitting, adaptation treatment, spatial
holdouts, uncertainty, and a welfare mapping.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from fit_fixed_effects_response import two_way_within


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--panel", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--expected-stages", type=int, default=3)
    args = parser.parse_args()
    panel = pd.read_parquet(args.panel)
    panel = panel.loc[panel.yield_observed].copy()
    if len(panel) == 0:
        raise ValueError("No observed GDHY yields in panel")
    panel["log_yield_t_ha"] = np.log(panel.yield_t_ha)
    features: list[str] = []
    for stage in range(1, args.expected_stages + 1):
        precip = f"stage{stage}_precip_mm"
        log_precip = f"stage{stage}_log1p_precip_mm"
        temp = f"stage{stage}_tmean_c"
        interaction = f"stage{stage}_tmean_x_log1p_precip"
        panel[log_precip] = np.log1p(panel[precip])
        panel[interaction] = panel[temp] * panel[log_precip]
        features.extend([temp, log_precip, f"stage{stage}_cdd_max_days", f"stage{stage}_rx1day_mm", interaction])
    panel = panel.dropna(subset=features + ["log_yield_t_ha"])
    if panel.harvest_year.nunique() < 3 or len(panel) < 100:
        raise ValueError("Pilot needs at least three years and 100 observations")
    grid = panel.lat.astype(str) + "_" + panel.lon_360.astype(str) + "_" + panel.crop + "_" + panel.irrigation
    transformed = two_way_within(panel, ["log_yield_t_ha"] + features, grid, panel.harvest_year)
    scales = panel[features].std(ddof=0)
    if (scales <= 0).any():
        raise ValueError(f"Zero-variation features: {scales.loc[scales <= 0].index.tolist()}")
    matrix = (transformed[features] / scales).to_numpy(dtype=float)
    outcome = transformed.log_yield_t_ha.to_numpy()
    coefficients, _, rank, singular_values = np.linalg.lstsq(matrix, outcome, rcond=1e-12)
    # Some sandboxed BLAS builds leave floating-point status flags set despite
    # finite inputs and output; validate the values explicitly below.
    with np.errstate(over="ignore", divide="ignore", invalid="ignore"):
        fitted = matrix @ coefficients
    if not (np.isfinite(coefficients).all() and np.isfinite(fitted).all()):
        raise ValueError("Nonfinite pilot fit; inspect design conditioning")
    residual = outcome - fitted
    total = float(np.dot(outcome, outcome))
    with np.errstate(over="ignore", divide="ignore", invalid="ignore"):
        rss = float(np.dot(residual, residual))
    output = {
        "n_observations": int(len(panel)), "n_grids": int(grid.nunique()),
        "n_years": int(panel.harvest_year.nunique()), "n_features": len(features),
        "matrix_rank": int(rank), "condition_number": float(singular_values[0] / singular_values[-1]),
        "within_r_squared": float(1 - rss / total),
        "coefficients_one_standard_deviation_feature": {name: float(value) for name, value in zip(features, coefficients)},
        "warning": "Pilot-only stage within-estimator diagnostic. Do not use these coefficients for SCC or causal interpretation.",
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps({key: value for key, value in output.items() if key != "coefficients_one_standard_deviation_feature"}, indent=2))


if __name__ == "__main__":
    main()
