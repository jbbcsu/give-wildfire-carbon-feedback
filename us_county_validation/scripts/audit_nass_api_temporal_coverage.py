#!/usr/bin/env python3
"""Audit temporal support in a prepared NASS API county-yield panel.

This counts outcome coverage only.  It does not estimate a weather response,
identify rainfed production, or authorize an SCC input.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


REQUIRED = {
    "harvest_year",
    "county_geoid",
    "commodity",
    "yield_unit",
    "yield_value",
    "yield_reported",
    "prodn_practice_desc",
}


def audit(path: Path, *, year_start: int, year_end: int) -> dict[str, object]:
    if year_start > year_end:
        raise ValueError("year range is reversed")
    frame = pd.read_parquet(path)
    missing = sorted(REQUIRED - set(frame.columns))
    if missing:
        raise ValueError(f"prepared NASS panel lacks columns: {missing}")
    if frame.empty:
        raise ValueError("prepared NASS panel is empty")

    years = pd.to_numeric(frame["harvest_year"], errors="coerce")
    if years.isna().any() or (years % 1 != 0).any():
        raise ValueError("harvest years must be finite integers")
    frame = frame.assign(harvest_year=years.astype(int))
    expected_years = list(range(year_start, year_end + 1))
    observed_years = sorted(frame["harvest_year"].unique().tolist())
    if observed_years != expected_years:
        raise ValueError(f"panel years differ: expected {expected_years}, got {observed_years}")
    if not frame["county_geoid"].astype("string").str.fullmatch(r"\d{5}", na=False).all():
        raise ValueError("county GEOIDs must be five digits")
    if frame.duplicated(["county_geoid", "harvest_year"]).any():
        raise ValueError("panel contains duplicate county-years")
    for column in ("commodity", "yield_unit", "prodn_practice_desc"):
        if frame[column].astype("string").str.strip().nunique() != 1:
            raise ValueError(f"panel mixes {column}")
    reported = frame["yield_reported"]
    if not pd.api.types.is_bool_dtype(reported.dtype):
        raise ValueError("yield_reported must be boolean")
    values = pd.to_numeric(frame["yield_value"], errors="coerce")
    if not reported.equals(values.notna()):
        raise ValueError("yield_reported does not match numeric yield availability")
    numeric = values[reported].to_numpy(dtype=float)
    if not np.isfinite(numeric).all() or (numeric <= 0).any():
        raise ValueError("reported yields must be finite and positive")

    presence = (
        frame.assign(reported=reported.to_numpy())
        .pivot(index="county_geoid", columns="harvest_year", values="reported")
        .reindex(columns=expected_years, fill_value=False)
        .eq(True)
    )
    adjacent = {
        f"{left}_{right}": int((presence[left] & presence[right]).sum())
        for left, right in zip(expected_years, expected_years[1:])
    }
    counts = frame.groupby("harvest_year", sort=True).size().reindex(expected_years).astype(int)
    reported_counts = (
        frame.groupby("harvest_year", sort=True)["yield_reported"]
        .sum()
        .reindex(expected_years)
        .astype(int)
    )
    return {
        "role": "outcome_temporal_coverage_not_weather_response_or_scc",
        "year_start": year_start,
        "year_end": year_end,
        "commodity": str(frame["commodity"].iloc[0]),
        "yield_unit": str(frame["yield_unit"].iloc[0]),
        "production_practice": str(frame["prodn_practice_desc"].iloc[0]),
        "county_year_rows": int(len(frame)),
        "reported_county_year_rows": int(reported.sum()),
        "counties_any_year": int(len(presence)),
        "counties_complete_all_years": int(presence.all(axis=1).sum()),
        "county_rows_by_year": {str(year): int(counts.loc[year]) for year in expected_years},
        "reported_rows_by_year": {
            str(year): int(reported_counts.loc[year]) for year in expected_years
        },
        "adjacent_reported_pairs_by_interval": adjacent,
        "adjacent_reported_pairs_total": int(sum(adjacent.values())),
        "result": "passed",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("panel", type=Path)
    parser.add_argument("--year-start", type=int, required=True)
    parser.add_argument("--year-end", type=int, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.panel, year_start=args.year_start, year_end=args.year_end)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        f"NASS temporal coverage passed: rows={result['county_year_rows']}, "
        f"complete_counties={result['counties_complete_all_years']}, "
        f"adjacent_pairs={result['adjacent_reported_pairs_total']}"
    )


if __name__ == "__main__":
    main()
