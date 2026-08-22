#!/usr/bin/env python3
"""Prepare one crop's county-year yield extract from NASS Quick Stats.

The source CSV must be a documented Quick Stats/bulk extract. Suppressed,
withheld, or nonnumeric NASS values are retained as flags and never converted
to zero. This script intentionally does not combine commodities or units.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def normalize_fips(series: pd.Series, width: int, label: str) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce")
    if numeric.isna().any() or (numeric % 1 != 0).any():
        raise ValueError(f"{label} contains missing or non-integer codes")
    maximum = 10 ** width - 1
    if ((numeric < 0) | (numeric > maximum)).any():
        raise ValueError(f"{label} contains codes outside {width}-digit range")
    return numeric.astype("int64").astype(str).str.zfill(width)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--commodity", required=True)
    parser.add_argument("--year-min", type=int, default=1981)
    parser.add_argument("--year-max", type=int, default=2024)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    frame = pd.read_csv(args.input, low_memory=False)
    required = {"year", "commodity_desc", "statisticcat_desc", "agg_level_desc", "state_ansi", "county_ansi", "value", "unit_desc"}
    normalized = {column.lower(): column for column in frame.columns}
    if missing := required - set(normalized):
        raise ValueError(f"NASS extract missing columns {sorted(missing)}")
    col = normalized.__getitem__
    is_yield = frame[col("statisticcat_desc")].astype(str).str.upper().eq("YIELD")
    is_county = frame[col("agg_level_desc")].astype(str).str.upper().eq("COUNTY")
    is_crop = frame[col("commodity_desc")].astype(str).str.upper().eq(args.commodity.upper())
    years = pd.to_numeric(frame[col("year")], errors="coerce")
    selected = frame.loc[is_yield & is_county & is_crop & years.between(args.year_min, args.year_max)].copy()
    if selected.empty:
        raise ValueError("No county yield rows after requested filters")
    raw = selected[col("value")].astype(str).str.strip()
    selected["yield_value_raw"] = raw
    selected["yield_value"] = pd.to_numeric(raw.str.replace(",", "", regex=False), errors="coerce")
    selected["yield_reported"] = selected.yield_value.notna()
    selected["nass_value_flag"] = raw.where(~selected.yield_reported, "reported")
    selected = selected.rename(columns={
        col("year"): "harvest_year", col("state_ansi"): "state_fips", col("county_ansi"): "county_fips",
        col("commodity_desc"): "commodity", col("unit_desc"): "yield_unit",
    })
    selected["state_fips"] = normalize_fips(selected.state_fips, 2, "state_ansi")
    selected["county_fips"] = normalize_fips(selected.county_fips, 3, "county_ansi")
    selected["county_geoid"] = selected.state_fips + selected.county_fips
    keys = ["harvest_year", "county_geoid", "commodity", "yield_unit"]
    if selected.duplicated(keys).any():
        raise ValueError("Duplicate county-year-commodity-unit rows; narrow NASS domain/practice filters before use")
    keep = keys + ["yield_value_raw", "yield_value", "yield_reported", "nass_value_flag"]
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    selected[keep].sort_values(keys).to_parquet(args.out, index=False)
    print(f"wrote {len(selected)} county-yield rows; reported share={selected.yield_reported.mean():.3f}")


if __name__ == "__main__":
    main()
