#!/usr/bin/env python3
"""Build annual same-realization GMST from pinned ISIMIP3b daily tas files."""
from __future__ import annotations

import argparse
from contextlib import ExitStack
from pathlib import Path

import numpy as np
import pandas as pd

from climate_inputs import crop_year_window, open_daily_series


def build(
    paths: list[str],
    *,
    esm_id: str,
    member_id: str,
    scenario: str,
    source_id: str,
    year_start: int,
    year_end: int,
) -> pd.DataFrame:
    identifiers = [esm_id, member_id, scenario, source_id]
    if any(not value.strip() for value in identifiers):
        raise ValueError("ESM, member, scenario, and GMST source ID must be explicit")
    if year_start > year_end:
        raise ValueError("GMST year range is reversed")
    with ExitStack() as stack:
        tas = crop_year_window(open_daily_series(stack, paths, "tas"), year_start, year_end)
        if tas.dims != ("time", "lat", "lon"):
            raise ValueError(f"tas must use time/lat/lon dimensions, got {tas.dims}")
        if tas.attrs.get("units") not in {"K", "kelvin"}:
            raise ValueError("tas must retain Kelvin units")
        latitude = tas["lat"].values.astype(float)
        longitude = tas["lon"].values.astype(float)
        if not np.isfinite(latitude).all() or not np.isfinite(longitude).all():
            raise ValueError("GMST grid coordinates must be finite")
        if len(np.unique(latitude)) != len(latitude) or len(np.unique(longitude)) != len(longitude):
            raise ValueError("GMST grid coordinates must be unique")
        weights = np.cos(np.deg2rad(tas["lat"]))
        if not np.isfinite(weights).all() or (weights <= 0).any():
            raise ValueError("latitude cell weights are invalid")
        daily = tas.weighted(weights).mean(("lat", "lon"), skipna=False).load()
        values = daily.values.astype(float)
        if not np.isfinite(values).all() or not ((values > 150.0) & (values < 350.0)).all():
            raise ValueError("daily global temperature means are missing or outside physical bounds")
        dates = pd.DatetimeIndex(daily["time"].values)
    output = (
        pd.DataFrame({"date": dates, "gmst_daily_k": values})
        .assign(year=lambda frame: frame.date.dt.year)
        .groupby("year", as_index=False, sort=True)["gmst_daily_k"]
        .mean()
        .rename(columns={"gmst_daily_k": "gmst_value_k"})
    )
    expected_years = list(range(year_start, year_end + 1))
    if output["year"].tolist() != expected_years:
        raise ValueError("annual GMST output lacks the exact requested year sequence")
    output.insert(0, "gmst_source_id", source_id)
    output.insert(0, "scenario", scenario)
    output.insert(0, "member_id", member_id)
    output.insert(0, "esm_id", esm_id)
    output["daily_count"] = [
        int(((dates.year == year)).sum()) for year in expected_years
    ]
    expected_counts = [len(pd.date_range(f"{year}-01-01", f"{year}-12-31", freq="D")) for year in expected_years]
    if output["daily_count"].tolist() != expected_counts:
        raise ValueError("annual GMST daily counts do not match the decoded calendar")
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tas", nargs="+", required=True)
    parser.add_argument("--esm-id", required=True)
    parser.add_argument("--member-id", required=True)
    parser.add_argument("--scenario", required=True)
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--year-start", type=int, required=True)
    parser.add_argument("--year-end", type=int, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    output = build(
        args.tas,
        esm_id=args.esm_id,
        member_id=args.member_id,
        scenario=args.scenario,
        source_id=args.source_id,
        year_start=args.year_start,
        year_end=args.year_end,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    output.to_parquet(args.out, index=False)
    print(f"wrote {len(output)} annual same-realization GMST rows to {args.out}")


if __name__ == "__main__":
    main()
