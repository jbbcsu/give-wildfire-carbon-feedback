#!/usr/bin/env python3
"""Synthetic parsing and cross-year tests for NASS usual-date calendars."""
from __future__ import annotations

import pandas as pd

from build_nass_usual_date_calendars import expand_calendars, floor_midpoint, parse_table_text


sample = """
Corn for Grain Usual Planting and Harvesting Dates – States
Nebraska ........................ 8,850   Apr 19    Apr 27 - May 15   May 21   Sep 18   Oct 4 - Nov 10   Nov 20
"""
# Patch the expected row count only within this focused parser test.
import build_nass_usual_date_calendars as module

original = module.TABLES["corn_grain"]["expected_rows"]
module.TABLES["corn_grain"]["expected_rows"] = 1
try:
    definition = parse_table_text(sample, "corn_grain")
finally:
    module.TABLES["corn_grain"]["expected_rows"] = original
assert definition.loc[0, "state"] == "NE"
assert definition.loc[0, "planting_active_start"] == "04-27"
calendar = expand_calendars(definition, 1981, 1982)
primary = calendar.loc[calendar.calendar_role.eq("fixed_primary")].set_index("harvest_year")
assert primary.loc[1981, "season_start"] == "1981-05-06"
assert primary.loc[1981, "season_end"] == "1981-10-22"
assert primary.loc[1982, "season_start"] == "1982-05-06"

winter = definition.copy()
winter["calendar_crop"] = "winter_wheat"
winter.loc[0, [
    "planting_begin", "planting_active_start", "planting_active_end", "planting_end",
    "harvest_begin", "harvest_active_start", "harvest_active_end", "harvest_end",
]] = ["09-03", "09-09", "10-02", "10-12", "06-28", "07-03", "07-21", "07-27"]
winter_calendar = expand_calendars(winter, 1981, 1981)
winter_primary = winter_calendar.loc[winter_calendar.calendar_role.eq("fixed_primary")].iloc[0]
assert winter_primary.season_start.startswith("1980-")
assert winter_primary.season_end == "1981-07-12"

try:
    floor_midpoint(pd.Timestamp("1981-01-02").date(), pd.Timestamp("1981-01-01").date())
    raise AssertionError("Reversed midpoint intervals should fail")
except ValueError:
    pass

print("NASS usual-date calendar tests passed")
