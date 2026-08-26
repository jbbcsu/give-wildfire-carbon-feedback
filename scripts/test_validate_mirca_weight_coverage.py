#!/usr/bin/env python3
"""Synthetic tests for MIRCA/GDHY weight-support audit."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd


PROJECT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "validate_mirca_weight_coverage", PROJECT / "scripts" / "validate_mirca_weight_coverage.py"
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

weights = pd.DataFrame(
    [
        [0.25, 0.25, "mai", "firr", 0.2],
        [0.25, 0.25, "mai", "noirr", 0.8],
        [0.75, 0.25, "mai", "firr", 0.0],
        [0.75, 0.25, "mai", "noirr", 1.0],
    ],
    columns=MODULE.CELL_KEYS + ["irrigation", "area_share"],
)
weights["share_year"] = 2000
weights["production_eligible"] = True
weights["weight_source_id"] = "synthetic"
weights["source_role"] = "independent_fixed_baseline_crop_area_share"
panel = pd.DataFrame(
    [
        [0.25, 0.25, "mai", 1982, True],
        [0.25, 0.25, "mai", 1983, True],
        [0.75, 0.25, "mai", 1982, True],
        [1.25, 0.25, "mai", 1982, True],
        [1.25, 0.25, "mai", 1983, False],
    ],
    columns=MODULE.CELL_KEYS + ["harvest_year", "yield_observed"],
)
audit = MODULE.audit_coverage(weights, [panel])
summary = audit["crop_summaries"][0]
assert summary["observed_cells"] == 3 and summary["matched_cells"] == 2
assert summary["observed_crop_grid_years"] == 4 and summary["matched_crop_grid_years"] == 3
assert not audit["scc_authorized"]

bad = weights.copy()
bad["production_eligible"] = False
try:
    MODULE.audit_coverage(bad, [panel])
except ValueError as error:
    assert "No production-eligible" in str(error)
else:
    raise AssertionError("Ineligible source mapping was accepted")

print("MIRCA weight coverage synthetic tests passed")
