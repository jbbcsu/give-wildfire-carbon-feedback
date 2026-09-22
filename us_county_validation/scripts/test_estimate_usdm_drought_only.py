#!/usr/bin/env python3
"""Synthetic fixed-effect recovery test for the sparse drought estimator."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd


SCRIPT = Path(__file__).with_name("estimate_usdm_drought_only.py")
SPEC = importlib.util.spec_from_file_location("estimate_usdm", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load estimator")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

rng = np.random.default_rng(82)
terms = [f"d{i}_weeks" for i in range(5)]
beta = np.array([-0.01, -0.02, -0.03, -0.04, -0.05])
rows = []
for county in range(30):
    state = f"S{county % 5}"
    county_effect = rng.normal()
    for year in range(2001, 2014):
        x = rng.uniform(0, 10, size=5)
        log_yield = county_effect + 0.02 * (year - 2001) * (county % 5) + x @ beta
        rows.append({
            "county_geoid": f"{county:05d}", "state": state,
            "harvest_year": year, "yield_bu_acre": np.exp(log_yield),
            **dict(zip(terms, x)),
        })
frame = pd.DataFrame(rows)
result = MODULE.fit_one(frame, terms)
estimated = np.array([
    row["estimate_log_points_per_area_equivalent_week"]
    for row in result["coefficients"]
])
assert np.allclose(estimated, beta, rtol=0, atol=1e-9)
assert result["residualization_audit"]["outcome"]["maximum_absolute_nuisance_orthogonality"] < 1e-6
print("sparse drought-only estimator recovery test passed")
