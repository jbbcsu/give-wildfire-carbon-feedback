#!/usr/bin/env python3
"""Synthetic core test for bounded whole-scenario holdout scoring."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from evaluate_isimip3b_five_esm_holdout_smoke import FEATURES  # noqa: E402
from evaluate_isimip3b_gfdl_scenario_holdout_smoke import (  # noqa: E402
    evaluate_leave_one_scenario_out,
)


rows = []
for scenario_index, scenario in enumerate(("historical", "ssp126", "ssp370", "ssp585")):
    for year_index, year in enumerate((2016, 2017)):
        gmst = 287.0 + 0.2 * scenario_index + 0.1 * year_index
        for lon in (10.25, 10.75):
            for feature_index, feature in enumerate(FEATURES):
                rows.append({
                    "harvest_year": year, "year": year, "lat": 1.25, "lon_360": lon,
                    "crop": "mai", "irrigation": "noirr", "esm_id": "GFDL-ESM4",
                    "member_id": "r1i1p1f1", "scenario": scenario,
                    "gmst_source_id": f"source-{scenario}", "gmst_value_k": gmst,
                    "gmst_esm_id": "GFDL-ESM4", "gmst_member_id": "r1i1p1f1",
                    "feature_family": feature, "feature_value": feature_index + 2.0 * gmst + lon,
                })
training = pd.DataFrame(rows)
result = evaluate_leave_one_scenario_out(training)
assert len(result) == 4 * len(FEATURES)
assert set(result["holdout_excluded"]) == {True}
assert np.isfinite(result[["rmse", "mae", "benchmark_rmse", "benchmark_mae"]]).all().all()

bad = training.loc[training["scenario"] != "historical"].copy()
try:
    evaluate_leave_one_scenario_out(bad)
except ValueError:
    pass
else:
    raise AssertionError("incomplete scenario training was accepted")

print("bounded GFDL scenario holdout smoke synthetic tests passed")
