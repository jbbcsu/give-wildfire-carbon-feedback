#!/usr/bin/env python3
"""Standardize documented U.S. Drought Monitor county-week area shares.

This is an observed-data validation input for the U.S. county analysis.  It
does not turn USDM categories into future climate projections, choose crop
seasons, or attach county yields.  Those operations require an explicit crop
calendar and crop-area weighting choice in a later step.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


AREA_COLUMNS = ["None", "D0", "D1", "D2", "D3", "D4"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", action="append", required=True, help="raw USDM CSV; repeatable")
    parser.add_argument("--out", required=True)
    parser.add_argument("--area-sum-tolerance", type=float, default=0.15)
    args = parser.parse_args()
    if args.area_sum_tolerance < 0:
        raise ValueError("--area-sum-tolerance must be nonnegative")

    frames = [pd.read_csv(path, dtype={"FIPS": "string"}) for path in args.input]
    weekly = pd.concat(frames, ignore_index=True)
    required = {"MapDate", "FIPS", "County", "State", "ValidStart", "ValidEnd", "StatisticFormatID", *AREA_COLUMNS}
    if missing := required - set(weekly.columns):
        raise ValueError(f"USDM extract missing columns {sorted(missing)}")
    if not weekly["StatisticFormatID"].eq(2).all():
        raise ValueError("Expected official county area-percent statistic format 2")

    weekly["county_geoid"] = weekly["FIPS"].astype("string").str.replace(r"\.0$", "", regex=True).str.zfill(5)
    if weekly.county_geoid.str.len().ne(5).any() or ~weekly.county_geoid.str.isnumeric().all():
        raise ValueError("FIPS values are not five-digit county GEOIDs")
    weekly["map_date"] = pd.to_datetime(weekly["MapDate"].astype(str), format="%Y%m%d", errors="raise")
    weekly["valid_start"] = pd.to_datetime(weekly["ValidStart"], errors="raise")
    weekly["valid_end"] = pd.to_datetime(weekly["ValidEnd"], errors="raise")
    if (weekly.valid_end < weekly.valid_start).any():
        raise ValueError("USDM validity interval ends before it starts")
    if ((weekly.map_date < weekly.valid_start) | (weekly.map_date > weekly.valid_end)).any():
        raise ValueError("USDM map date falls outside its validity interval")
    areas = weekly[AREA_COLUMNS].apply(pd.to_numeric, errors="raise")
    if ((areas < -args.area_sum_tolerance) | (areas > 100 + args.area_sum_tolerance)).any().any():
        raise ValueError("USDM area percentage is outside [0, 100] within tolerance")
    area_sum_error = (areas.sum(axis=1) - 100).abs()
    if (area_sum_error > args.area_sum_tolerance).any():
        raise ValueError("USDM mutually exclusive area shares do not sum to 100 within tolerance")

    result = pd.DataFrame({
        "county_geoid": weekly.county_geoid,
        "state": weekly.State.astype(str).str.upper(),
        "county_name": weekly.County.astype(str),
        "map_date": weekly.map_date,
        "valid_start": weekly.valid_start,
        "valid_end": weekly.valid_end,
        "none_pct": areas["None"],
        "d0_pct": areas["D0"],
        "d1_pct": areas["D1"],
        "d2_pct": areas["D2"],
        "d3_pct": areas["D3"],
        "d4_pct": areas["D4"],
    })
    # USDM categories are mutually exclusive shares. D1+ is drought exposure;
    # D0 is retained separately as "abnormally dry", rather than relabeled.
    result["d1plus_pct"] = result[["d1_pct", "d2_pct", "d3_pct", "d4_pct"]].sum(axis=1)
    result["d2plus_pct"] = result[["d2_pct", "d3_pct", "d4_pct"]].sum(axis=1)
    result["d3plus_pct"] = result[["d3_pct", "d4_pct"]].sum(axis=1)
    result["drought_severity_area_pct"] = (
        result.d1_pct + 2 * result.d2_pct + 3 * result.d3_pct + 4 * result.d4_pct
    )
    keys = ["county_geoid", "map_date"]
    if result.duplicated(keys).any():
        raise ValueError("Duplicate county-week rows; inputs overlap or queries must be narrowed")
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    result.sort_values(keys).to_parquet(args.out, index=False)
    print(
        f"wrote {len(result)} county-week rows; counties={result.county_geoid.nunique()}; "
        f"mean D1+ area={result.d1plus_pct.mean():.2f}%"
    )


if __name__ == "__main__":
    main()
