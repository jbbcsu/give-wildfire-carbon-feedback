#!/usr/bin/env python3
"""Primitive tests for expanded GFDL FAIR temperature support."""

from __future__ import annotations

import pandas as pd

from audit_gfdl_later_century_temperature_support import classify, horizon, validate_gmst_coverage


years = pd.Series([2020, 2021, 2022, 2023])
values = pd.Series([287.0, 288.0, 289.0, 290.0])
states = classify(values, 287.5, 289.5)
assert states.tolist() == ["below", "within", "within", "above"]
assert horizon(years, states) == {
    "first_within_year": 2021,
    "last_within_year": 2022,
    "within_year_count": 2,
    "last_below_year": 2020,
    "first_above_year": 2023,
}

try:
    horizon(pd.Series([2020, 2020]), pd.Series(["within", "above"]))
except ValueError as exc:
    assert "invalid" in str(exc)
else:
    raise AssertionError("duplicate horizon years should fail")

coverage_rows = [
    {"scenario": scenario, "year": year}
    for scenario, years_for_scenario in {
        "historical": range(2011, 2015),
        "ssp126": list(range(2015, 2021)) + list(range(2041, 2051)) + list(range(2091, 2101)),
        "ssp370": list(range(2015, 2021)) + list(range(2041, 2051)),
        "ssp585": range(2015, 2021),
    }.items()
    for year in years_for_scenario
]
assert set(validate_gmst_coverage(pd.DataFrame(coverage_rows))) == {"historical", "ssp126", "ssp370", "ssp585"}
try:
    validate_gmst_coverage(pd.DataFrame(coverage_rows[:-1]))
except ValueError as exc:
    assert "coverage" in str(exc)
else:
    raise AssertionError("incomplete fixed GMST coverage should fail")

print("GFDL expanded FAIR temperature-support primitive tests passed")
