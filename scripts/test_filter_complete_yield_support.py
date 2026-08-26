#!/usr/bin/env python3
"""Synthetic tests for the complete-GDHY-support sensitivity."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd


PROJECT = Path(__file__).resolve().parents[1]
MODULE_PATH = PROJECT / "scripts" / "filter_complete_yield_support.py"
SPEC = importlib.util.spec_from_file_location("filter_complete_yield_support", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


rows = []
for lon, observed_years in [(0.25, {2012, 2013, 2014}), (0.75, {2012, 2014})]:
    for year in (2012, 2013, 2014):
        observed = year in observed_years
        rows.append(
            {
                "crop": "mai",
                "irrigation": "area_weighted",
                "lat": 0.25,
                "lon_360": lon,
                "harvest_year": year,
                "yield_observed": observed,
                "yield_t_ha": 1.0 if observed else float("nan"),
                "scc_authorized": False,
            }
        )

panel = pd.DataFrame(rows)
output, audit = MODULE.filter_complete_support(panel, 2012, 2014)
assert len(output) == 3
assert output["lon_360"].eq(0.25).all()
assert output["yield_observed"].all()
assert not output["yield_support_conditioning_is_primary"].any()
assert not output["missing_yield_imputed"].any()
assert audit["complete_support_cells"] == 1
assert audit["excluded_incomplete_support_cells"] == 1
assert audit["source_observed_yields_by_year"] == {"2012": 2, "2013": 1, "2014": 2}
assert audit["source_observed_yield_levels"] == 5
assert audit["output_observed_yield_levels"] == 3
assert audit["source_consecutive_observed_pairs_by_transition"] == {
    "2012-2013": 1,
    "2013-2014": 1,
}
assert audit["complete_support_consecutive_pairs_by_transition"] == {
    "2012-2013": 1,
    "2013-2014": 1,
}
assert audit["observed_level_retained_fraction"] == 3 / 5
assert audit["consecutive_pair_retained_fraction"] == 1.0
assert audit["scc_authorized"] is False

duplicate = pd.concat([panel, panel.iloc[[0]]], ignore_index=True)
try:
    MODULE.filter_complete_support(duplicate, 2012, 2014)
except ValueError as error:
    assert "duplicate" in str(error)
else:
    raise AssertionError("Duplicate outcome keys must fail")

try:
    MODULE.filter_complete_support(panel.loc[panel.harvest_year.ne(2013)], 2012, 2014)
except ValueError as error:
    assert "complete declared period" in str(error)
else:
    raise AssertionError("Incomplete declared year range must fail")

nonfinite = panel.copy()
first_observed = nonfinite.index[nonfinite.yield_observed][0]
nonfinite.loc[first_observed, "yield_t_ha"] = float("inf")
try:
    MODULE.filter_complete_support(nonfinite, 2012, 2014)
except ValueError as error:
    assert "finite and positive" in str(error)
else:
    raise AssertionError("An infinite observed yield must fail")

missing_key = panel.copy()
missing_key.loc[0, "lat"] = float("nan")
try:
    MODULE.filter_complete_support(missing_key, 2012, 2014)
except ValueError as error:
    assert "Cell keys" in str(error)
else:
    raise AssertionError("A missing cell key must fail")

nonfinite_year = panel.copy()
nonfinite_year["harvest_year"] = nonfinite_year["harvest_year"].astype(float)
nonfinite_year.loc[0, "harvest_year"] = float("inf")
try:
    MODULE.filter_complete_support(nonfinite_year, 2012, 2014)
except ValueError as error:
    assert "finite integers" in str(error)
else:
    raise AssertionError("An infinite harvest year must fail")

print("complete-yield-support sensitivity tests passed")
