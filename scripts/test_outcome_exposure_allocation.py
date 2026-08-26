#!/usr/bin/env python3
"""Synthetic failure-mode tests for irrigation-exposure allocation."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd


PROJECT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "allocate_outcome_exposures", PROJECT / "scripts/allocate_outcome_exposures.py"
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def expect_failure(panel: pd.DataFrame, weights: pd.DataFrame, message: str) -> None:
    try:
        MODULE.allocate(panel, weights, ["precip_mm", "cdd_max_days"], ["noirr", "firr"])
    except ValueError as exc:
        assert message in str(exc), str(exc)
    else:
        raise AssertionError(f"Expected failure containing {message!r}")


panel = pd.DataFrame(
    [
        [2000, 10.25, 20.25, "mai", "noirr", True, 2.0, 100.0, 8.0],
        [2000, 10.25, 20.25, "mai", "firr", True, 2.0, 60.0, 3.0],
        [2001, 10.25, 20.25, "mai", "noirr", True, 2.2, 120.0, 10.0],
        [2001, 10.25, 20.25, "mai", "firr", True, 2.2, 70.0, 4.0],
        [2000, 11.25, 20.25, "mai", "noirr", False, np.nan, 80.0, 7.0],
        [2000, 11.25, 20.25, "mai", "firr", False, np.nan, 50.0, 2.0],
    ],
    columns=[
        "harvest_year", "lat", "lon_360", "crop", "irrigation",
        "yield_observed", "yield_t_ha", "precip_mm", "cdd_max_days",
    ],
)
weights = pd.DataFrame(
    [
        [10.25, 20.25, "mai", "noirr", 0.75],
        [10.25, 20.25, "mai", "firr", 0.25],
        [11.25, 20.25, "mai", "noirr", 1.00],
        [11.25, 20.25, "mai", "firr", 0.00],
    ],
    columns=["lat", "lon_360", "crop", "irrigation", "area_share"],
)
weights["weight_source_id"] = "synthetic-independent-area-v1"
weights["weight_vintage"] = "baseline-1995"
weights["source_role"] = MODULE.REQUIRED_SOURCE_ROLE

output, audit = MODULE.allocate(
    panel, weights.copy(), ["precip_mm", "cdd_max_days"], ["noirr", "firr"]
)
assert len(output) == 3
assert not output.duplicated(MODULE.KEYS).any()
first = output.query("harvest_year == 2000 and lat == 10.25").iloc[0]
assert np.isclose(first.precip_mm, 90.0)
assert np.isclose(first.cdd_max_days, 6.75)
assert first.yield_t_ha == 2.0
assert output.irrigation.eq("area_weighted").all()
assert not output.scc_authorized.any()
assert audit["input_rows"] == 6 and audit["output_rows"] == 3
assert audit["one_row_per_outcome"] and not audit["scc_authorized"]

bad = weights.copy()
bad.loc[bad.irrigation == "firr", "area_share"] = 0.5
expect_failure(panel, bad, "sum to one")

bad = weights.copy()
bad["harvest_year"] = 2000
expect_failure(panel, bad, "fixed baseline")

bad = weights.copy()
bad["source_role"] = "derived_from_yield_outcome"
expect_failure(panel, bad, "source_role")

bad = weights.copy()
bad["production_eligible"] = True
bad.loc[bad.crop == "mai", "production_eligible"] = False
expect_failure(panel, bad, "not production-eligible")

bad_panel = panel.drop(index=1)
expect_failure(bad_panel, weights.copy(), "Every observed-outcome key")

bad_panel = panel.copy()
bad_panel.loc[1, "yield_t_ha"] = 3.0
expect_failure(bad_panel, weights.copy(), "Yield values differ")

bad_panel = pd.concat([panel, panel.iloc[[0]]], ignore_index=True)
expect_failure(bad_panel, weights.copy(), "duplicate crop-grid-year-irrigation")

print("outcome exposure allocation synthetic tests passed")
