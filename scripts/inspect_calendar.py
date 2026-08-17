#!/usr/bin/env python3
"""Print the schema and valid-date coverage of one GGCMI crop-calendar file."""
from __future__ import annotations

import argparse
import xarray as xr


parser = argparse.ArgumentParser()
parser.add_argument("calendar")
args = parser.parse_args()

with xr.open_dataset(args.calendar, engine="h5netcdf") as ds:
    required = {"planting_day", "maturity_day", "growing_season_length"}
    missing = required - set(ds.data_vars)
    if missing:
        raise SystemExit(f"Calendar missing required variables: {sorted(missing)}")
    valid = ds.planting_day.notnull() & ds.maturity_day.notnull()
    print(f"dimensions={dict(ds.sizes)}")
    print(f"variables={list(ds.data_vars)}")
    print(f"valid_cells={int(valid.sum())}")
    print(f"cross_year_cells={int(((ds.maturity_day < ds.planting_day) & valid).sum())}")
