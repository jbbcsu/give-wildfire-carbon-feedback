#!/usr/bin/env python3
"""Synthetic arithmetic tests for calendar-year USDM exposure weeks."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd


SCRIPT = Path(__file__).with_name("aggregate_usdm_calendar_year_exposures.py")
SPEC = importlib.util.spec_from_file_location("annual_usdm", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load annual exposure builder")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

rows = []
for start, end, d0, d2 in [
    ("2000-12-26", "2001-01-01", 100.0, 0.0),
    ("2001-01-02", "2001-12-31", 0.0, 100.0),
]:
    rows.append({
        "county_geoid": "01001", "state": "AL", "county_name": "AUTAUGA",
        "map_date": pd.Timestamp(start), "valid_start": pd.Timestamp(start),
        "valid_end": pd.Timestamp(end), "none_pct": 0.0, "d0_pct": d0,
        "d1_pct": 0.0, "d2_pct": d2, "d3_pct": 0.0, "d4_pct": 0.0,
    })
frame = pd.DataFrame(rows)
result = MODULE.aggregate_state_year(frame, "AL", 2001, ("corn_grain", "soybeans"))
assert len(result) == 2
assert abs(result.iloc[0].d0_weeks - 1 / 7) < 1e-12
assert abs(result.iloc[0].d2_weeks - 364 / 7) < 1e-12
assert abs(result.iloc[0].all_category_weeks - 365 / 7) < 1e-12
assert result.scc_authorized.eq(False).all()

broken = frame.iloc[1:].copy()
try:
    MODULE.aggregate_state_year(broken, "AL", 2001, ("corn_grain",))
except ValueError as error:
    assert "incomplete" in str(error)
else:
    raise AssertionError("accepted incomplete calendar-year coverage")

print("calendar-year USDM exposure tests passed")
