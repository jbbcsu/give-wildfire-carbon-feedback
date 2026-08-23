#!/usr/bin/env python3
"""Aggregate prepared county-week USDM shares over explicit crop seasons.

This bridge is deliberately descriptive. It requires a documented state/crop
calendar, checks complete non-overlapping daily coverage, and does not infer a
crop calendar, estimate a yield response, or authorize an SCC input.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


CATEGORY_COLUMNS = ["none_pct", "d0_pct", "d1_pct", "d2_pct", "d3_pct", "d4_pct"]
DERIVED_COLUMNS = ["d1plus_pct", "d2plus_pct", "d3plus_pct", "drought_severity_area_pct"]
WEEK_COLUMNS = {
    "county_geoid",
    "state",
    "map_date",
    "valid_start",
    "valid_end",
    *CATEGORY_COLUMNS,
    *DERIVED_COLUMNS,
}
CALENDAR_COLUMNS = {
    "state",
    "crop",
    "harvest_year",
    "season_start",
    "season_end",
    "calendar_source",
}


def read_table(path: str) -> pd.DataFrame:
    source = Path(path)
    if source.suffix.lower() in {".parquet", ".pq"}:
        return pd.read_parquet(source)
    # Preserve identifiers such as leading-zero county GEOIDs before explicit
    # schema validation and numeric conversion.
    return pd.read_csv(source, dtype="string")


def parse_date_column(frame: pd.DataFrame, column: str) -> pd.Series:
    values = pd.to_datetime(frame[column], errors="raise")
    if values.isna().any():
        raise ValueError(f"{column} contains missing dates")
    return values.dt.normalize()


def validate_weeks(weeks: pd.DataFrame, tolerance: float) -> pd.DataFrame:
    if missing := WEEK_COLUMNS - set(weeks.columns):
        raise ValueError(f"Prepared USDM weeks missing columns {sorted(missing)}")
    if weeks.empty:
        raise ValueError("Prepared USDM weeks are empty")
    weeks = weeks.copy()
    weeks["county_geoid"] = weeks.county_geoid.astype("string")
    if weeks.county_geoid.isna().any() or weeks.county_geoid.str.fullmatch(r"\d{5}").ne(True).any():
        raise ValueError("county_geoid must contain five-digit county GEOIDs")
    weeks["state"] = weeks.state.astype("string").str.strip().str.upper()
    if weeks.state.isna().any() or weeks.state.str.fullmatch(r"[A-Z]{2}").ne(True).any():
        raise ValueError("state must contain two-letter postal codes")
    if weeks.groupby("county_geoid", observed=True).state.nunique().gt(1).any():
        raise ValueError("A county_geoid is associated with multiple states")
    for column in ["map_date", "valid_start", "valid_end"]:
        weeks[column] = parse_date_column(weeks, column)
    if (weeks.valid_end < weeks.valid_start).any():
        raise ValueError("USDM validity interval ends before it starts")
    if ((weeks.map_date < weeks.valid_start) | (weeks.map_date > weeks.valid_end)).any():
        raise ValueError("USDM map date falls outside its validity interval")
    if weeks.duplicated(["county_geoid", "map_date"]).any():
        raise ValueError("Duplicate county-week rows")

    numeric_columns = CATEGORY_COLUMNS + DERIVED_COLUMNS
    weeks[numeric_columns] = weeks[numeric_columns].apply(pd.to_numeric, errors="raise")
    if not np.isfinite(weeks[numeric_columns].to_numpy(dtype=float)).all():
        raise ValueError("USDM exposure columns contain non-finite values")
    categories = weeks[CATEGORY_COLUMNS]
    if ((categories < -tolerance) | (categories > 100 + tolerance)).any().any():
        raise ValueError("USDM category percentage is outside [0, 100] within tolerance")
    if ((categories.sum(axis=1) - 100).abs() > tolerance).any():
        raise ValueError("USDM mutually exclusive category shares do not sum to 100")
    expected = pd.DataFrame(
        {
            "d1plus_pct": weeks[["d1_pct", "d2_pct", "d3_pct", "d4_pct"]].sum(axis=1),
            "d2plus_pct": weeks[["d2_pct", "d3_pct", "d4_pct"]].sum(axis=1),
            "d3plus_pct": weeks[["d3_pct", "d4_pct"]].sum(axis=1),
            "drought_severity_area_pct": (
                weeks.d1_pct + 2 * weeks.d2_pct + 3 * weeks.d3_pct + 4 * weeks.d4_pct
            ),
        }
    )
    if not np.allclose(
        weeks[DERIVED_COLUMNS].to_numpy(dtype=float),
        expected[DERIVED_COLUMNS].to_numpy(dtype=float),
        rtol=0,
        atol=tolerance,
    ):
        raise ValueError("Prepared USDM derived exposures do not reconcile with categories")
    return weeks


def validate_calendar(calendar: pd.DataFrame) -> pd.DataFrame:
    if missing := CALENDAR_COLUMNS - set(calendar.columns):
        raise ValueError(f"Crop calendar missing columns {sorted(missing)}")
    if calendar.empty:
        raise ValueError("Crop calendar is empty")
    calendar = calendar.copy()
    calendar["state"] = calendar.state.astype("string").str.strip().str.upper()
    if calendar.state.isna().any() or calendar.state.str.fullmatch(r"[A-Z]{2}").ne(True).any():
        raise ValueError("Calendar state must contain two-letter postal codes")
    calendar["crop"] = calendar.crop.astype("string").str.strip().str.lower()
    calendar["calendar_source"] = calendar.calendar_source.astype("string").str.strip()
    if calendar.crop.isna().any() or calendar.crop.eq("").any():
        raise ValueError("Calendar crop must be nonblank")
    if calendar.calendar_source.isna().any() or calendar.calendar_source.eq("").any():
        raise ValueError("calendar_source must be nonblank")
    years = pd.to_numeric(calendar.harvest_year, errors="coerce")
    if years.isna().any() or (years % 1 != 0).any():
        raise ValueError("harvest_year must contain integers")
    calendar["harvest_year"] = years.astype("int64")
    calendar["season_start"] = parse_date_column(calendar, "season_start")
    calendar["season_end"] = parse_date_column(calendar, "season_end")
    if (calendar.season_end < calendar.season_start).any():
        raise ValueError("Crop season ends before it starts")
    if calendar.season_end.dt.year.ne(calendar.harvest_year).any():
        raise ValueError("Crop season_end year must equal harvest_year")
    keys = ["state", "crop", "harvest_year"]
    if calendar.duplicated(keys).any():
        raise ValueError("Duplicate state-crop-harvest-year calendar rows")
    return calendar


def aggregate_seasons(weeks: pd.DataFrame, calendar: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    counties_by_state = weeks.groupby("state", observed=True).county_geoid.unique().to_dict()
    for season in calendar.itertuples(index=False):
        counties = counties_by_state.get(season.state, [])
        if len(counties) == 0:
            raise ValueError(f"No prepared USDM counties match calendar state {season.state}")
        season_days = (season.season_end - season.season_start).days + 1
        state_weeks = weeks.loc[weeks.state.eq(season.state)]
        for county_geoid in counties:
            overlapping = state_weeks.loc[
                state_weeks.county_geoid.eq(county_geoid)
                & state_weeks.valid_end.ge(season.season_start)
                & state_weeks.valid_start.le(season.season_end)
            ].copy()
            if overlapping.empty:
                raise ValueError(
                    f"No USDM coverage for {county_geoid} {season.crop} {season.harvest_year}"
                )
            overlapping["clip_start"] = overlapping.valid_start.clip(lower=season.season_start)
            overlapping["clip_end"] = overlapping.valid_end.clip(upper=season.season_end)
            overlapping = overlapping.sort_values(["clip_start", "clip_end", "map_date"])
            starts = overlapping.clip_start.reset_index(drop=True)
            ends = overlapping.clip_end.reset_index(drop=True)
            if starts.iloc[0] != season.season_start or ends.iloc[-1] != season.season_end:
                raise ValueError(
                    f"Incomplete USDM boundary coverage for {county_geoid} {season.crop} "
                    f"{season.harvest_year}"
                )
            if len(overlapping) > 1:
                expected_starts = ends.iloc[:-1].reset_index(drop=True) + pd.Timedelta(days=1)
                actual_starts = starts.iloc[1:].reset_index(drop=True)
                if not actual_starts.equals(expected_starts):
                    raise ValueError(
                        f"Gapped or overlapping USDM intervals for {county_geoid} {season.crop} "
                        f"{season.harvest_year}"
                    )
            overlap_days = (overlapping.clip_end - overlapping.clip_start).dt.days + 1
            if int(overlap_days.sum()) != season_days:
                raise ValueError("Internal season-day coverage reconciliation failed")
            weights = overlap_days.to_numpy(dtype=float) / season_days
            pct_columns = CATEGORY_COLUMNS + ["d1plus_pct", "d2plus_pct", "d3plus_pct"]
            means = {
                f"{column.removesuffix('_pct')}_season_mean_pct": float(
                    np.dot(overlapping[column].to_numpy(dtype=float), weights)
                )
                for column in pct_columns
            }
            means["drought_severity_area_index_mean"] = float(
                np.dot(overlapping.drought_severity_area_pct.to_numpy(dtype=float), weights)
            )
            row: dict[str, object] = {
                "county_geoid": county_geoid,
                "state": season.state,
                "crop": season.crop,
                "harvest_year": season.harvest_year,
                "season_start": season.season_start,
                "season_end": season.season_end,
                "season_days": season_days,
                "usdm_intervals": len(overlapping),
                "calendar_source": season.calendar_source,
                "analysis_role": "historical_county_validation_only",
                "scc_authorized": False,
                **means,
            }
            row["d1plus_area_equivalent_days"] = season_days * means["d1plus_season_mean_pct"] / 100
            row["d2plus_area_equivalent_days"] = season_days * means["d2plus_season_mean_pct"] / 100
            row["d0plus_area_equivalent_days"] = season_days * (
                means["d0_season_mean_pct"] + means["d1plus_season_mean_pct"]
            ) / 100
            rows.append(row)
    result = pd.DataFrame(rows)
    keys = ["county_geoid", "crop", "harvest_year"]
    if result.duplicated(keys).any():
        raise ValueError("Duplicate county-crop-harvest-year exposure rows")
    return result.sort_values(keys).reset_index(drop=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--weeks", required=True, help="prepared USDM county-week CSV or Parquet")
    parser.add_argument("--calendar", required=True, help="documented state/crop calendar CSV or Parquet")
    parser.add_argument("--out", required=True, help="output Parquet path")
    parser.add_argument("--area-tolerance", type=float, default=0.15)
    args = parser.parse_args()
    if args.area_tolerance < 0:
        raise ValueError("--area-tolerance must be nonnegative")
    weeks = validate_weeks(read_table(args.weeks), args.area_tolerance)
    calendar = validate_calendar(read_table(args.calendar))
    result = aggregate_seasons(weeks, calendar)
    destination = Path(args.out)
    destination.parent.mkdir(parents=True, exist_ok=True)
    result.to_parquet(destination, index=False)
    print(
        f"wrote {len(result)} county-crop-season rows; "
        f"counties={result.county_geoid.nunique()}; crops={result.crop.nunique()}"
    )


if __name__ == "__main__":
    main()
