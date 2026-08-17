#!/usr/bin/env python3
"""Fit a transparent pilot grid/year fixed-effects yield response.

This validates the estimation plumbing; it is not the final hierarchical,
crop-stage response or an SCC coefficient source. It uses exact dummy fixed
effects and standardized continuous features to expose conditioning and
coefficient labels in the output.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


def dummy_frame(values: pd.Series, prefix: str) -> pd.DataFrame:
    dummies = pd.get_dummies(values.astype(str), prefix=prefix, dtype=float)
    return dummies.iloc[:, 1:]  # reference category avoids exact collinearity


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
    scaled = (panel[features] - panel[features].mean()) / panel[features].std(ddof=0)
    scaled.columns = [f"z_{name}" for name in features]
    grid = panel.lat.astype(str) + "_" + panel.lon_360.astype(str) + "_" + panel.crop + "_" + panel.irrigation
    design = pd.concat([
        pd.DataFrame({"intercept": np.ones(len(panel))}, index=panel.index), scaled,
        dummy_frame(grid, "grid"), dummy_frame(panel.harvest_year, "year"),
    ], axis=1)
    coefficients, _, rank, _ = np.linalg.lstsq(design.to_numpy(), panel.log_yield_t_ha.to_numpy(), rcond=None)
    fitted = design.to_numpy() @ coefficients
    residual = panel.log_yield_t_ha.to_numpy() - fitted
    total = ((panel.log_yield_t_ha - panel.log_yield_t_ha.mean()) ** 2).sum()
    output = {
        "n_observations": int(len(panel)), "n_grids": int(grid.nunique()),
        "n_years": int(panel.harvest_year.nunique()), "matrix_rank": int(rank),
        "r_squared_in_sample": float(1 - (residual @ residual) / total),
        "coefficients_standardized": {name: float(value) for name, value in zip(design.columns[:len(features) + 1], coefficients[:len(features) + 1])},
        "warning": "Pilot-only in-sample diagnostic. Do not use these coefficients for SCC or causal interpretation.",
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
