#!/usr/bin/env python3
"""Synthetic checks for state-cluster and stability helpers."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd


SCRIPT = Path(__file__).with_name("estimate_usdm_weather_robustness.py")
SPEC = importlib.util.spec_from_file_location("weather_robustness", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load weather robustness estimator")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

rng = np.random.default_rng(622)
rows = []
for state_index, state in enumerate(("AA", "BB", "CC", "DD")):
    for county_index in range(3):
        county = f"{state_index + 1:02d}{county_index + 1:03d}"
        county_effect = rng.normal(scale=0.2)
        for year in range(2001, 2007):
            x1, x2 = rng.normal(size=2)
            outcome = (
                2.0 + county_effect + 0.03 * (year - 2001)
                + 0.35 * x1 - 0.22 * x2 + rng.normal(scale=0.03)
            )
            rows.append({
                "county_geoid": county, "state": state, "harvest_year": year,
                "yield_bu_acre": float(np.exp(outcome)), "x1": x1, "x2": x2,
            })
frame = pd.DataFrame(rows)
fit = MODULE.fit_core(frame, ["x1", "x2"])
assert np.max(np.abs(fit["beta"] - np.array([0.35, -0.22]))) < 0.03
covariance, clusters = MODULE.cluster_covariance(
    fit["residual_x"], fit["residual"], fit["gram_inverse"], frame.state
)
assert clusters == 4
assert covariance.shape == (2, 2)
assert np.allclose(covariance, covariance.T, rtol=0, atol=1e-14)
assert np.linalg.eigvalsh(covariance).min() > -1e-12
leaveouts = []
for state in sorted(frame.state.unique()):
    reduced = MODULE.fit_core(frame.loc[~frame.state.eq(state)], ["x1", "x2"])
    leaveouts.append({
        "left_out_state": state,
        "coefficients": {"x1": float(reduced["beta"][0]), "x2": float(reduced["beta"][1])},
    })
summary = MODULE.coefficient_summary(float(fit["beta"][0]), leaveouts, "x1")
assert summary["leaveout_fits"] == 4
assert summary["same_nonzero_sign_fraction"] == 1.0
assert summary["state_with_maximum_absolute_change"] in {"AA", "BB", "CC", "DD"}
print("USDM weather-robustness helper tests passed")
