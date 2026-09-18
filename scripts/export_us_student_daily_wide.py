#!/usr/bin/env python3
"""Export the validated U.S. corn/soy panel with daily NOAA county weather.

The output is a gzip-compressed CSV. Each row is one crop/county/harvest year;
weather columns use fixed month-day labels, with February 29 blank in nonleap
years. Humidity and hail are not in the acquired NOAA source and are omitted.
"""
from __future__ import annotations

import argparse
import calendar
import csv
from datetime import date, timedelta
import gzip
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from build_us_county_average_crop_year_features import BASE, CROSSWALK, ROOT, sha, source_year
from audit_nclimgrid_county_average_sample import load_crosswalk

PANEL_DIR = ROOT / "data/interim/us_county/noaa_county_average_nass_panel_20260916"
PANEL = PANEL_DIR / "panel.parquet"
VARS = (("PRCP", "prcp_mm"), ("TMAX", "tmax_c"),
        ("TMIN", "tmin_c"), ("TAVG", "tavg_c"))
BASE_FIELDS = (
    "county_fips", "county_name", "state", "year", "crop", "yield_bu_acre",
    "nass_production_practice", "irrigation_share_2017", "sample_period",
    "season_start", "season_end", "season_precip_mm",
    "season_tmean_c", "season_wet_days_ge_1mm", "season_longest_dry_spell_days",
    "season_max_5day_rain_mm", "season_stage1_precip_share",
    "season_stage2_precip_share", "season_stage3_precip_share",
)


def month_days() -> list[str]:
    start = date(2020, 1, 1)  # leap reference preserves February 29
    return [(start + timedelta(days=i)).strftime("%m%d") for i in range(366)]


def header() -> list[str]:
    return list(BASE_FIELDS) + [f"{short}_{day}" for _, short in VARS for day in month_days()]


def county_names(year: int) -> dict[str, str]:
    state_map = load_crosswalk(CROSSWALK)
    source = BASE / f"{year}_h1" / f"{year}01" / f"prcp-{year}01-cty-scaled.csv"
    names = {}
    with source.open(newline="", encoding="utf-8") as stream:
        for row in csv.reader(stream):
            fips = state_map[row[1][:2]] + row[1][2:]
            names[fips] = row[2].split(": ", 1)[-1]
    if len(names) != 3107:
        raise ValueError("NOAA county-name support changed")
    return names


def values_for_row(arrays: dict[str, np.ndarray], idx: int, year: int) -> list[str]:
    output = []
    for variable, _ in VARS:
        values = arrays[variable][idx]
        if len(values) != (366 if calendar.isleap(year) else 365):
            raise ValueError("unexpected number of daily weather values")
        if calendar.isleap(year):
            ordered = values
        else:
            ordered = np.concatenate((values[:59], np.array([np.nan], dtype=values.dtype), values[59:]))
        output.extend("" if np.isnan(v) else f"{v:.2f}" for v in ordered)
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start-year", type=int, required=True)
    parser.add_argument("--end-year", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--append", action="store_true")
    args = parser.parse_args()
    output = args.output.resolve()
    if not 1981 <= args.start_year <= args.end_year <= 2025:
        raise ValueError("year range is outside the downloaded panel")
    if not output.is_relative_to(ROOT / "data/interim") or output.suffixes[-2:] != [".csv", ".gz"]:
        raise ValueError("output must be an ignored interim .csv.gz file")
    if args.append != output.exists():
        raise ValueError("append flag and existing output state disagree")
    if args.append:
        expected_header = header()
        with gzip.open(output, "rt", newline="", encoding="utf-8") as existing:
            rows = csv.reader(existing)
            if next(rows, None) != expected_header:
                raise ValueError("existing CSV header differs")
            last_year = None
            for previous in rows:
                if len(previous) != len(expected_header):
                    raise ValueError("existing CSV has a malformed row")
                current_year = int(previous[3])
                if last_year is not None and current_year < last_year:
                    raise ValueError("existing CSV years are out of order")
                last_year = current_year
            if last_year != args.start_year - 1:
                raise ValueError("append must start immediately after the final exported year")
    if sha(PANEL) != json.loads((PANEL_DIR / "result.json").read_text())["panel_sha256"]:
        raise ValueError("NASS/weather panel hash changed")
    panel = pd.read_parquet(PANEL)
    if len(panel) != 34288 or panel.duplicated(["outcome_crop", "county_geoid", "harvest_year"]).any():
        raise ValueError("NASS/weather panel support changed")
    if (panel["irrigation_share"].max() > 0.100000001 or
        panel["yield_bu_acre"].min() <= 0 or panel["yield_bu_acre"].isna().any()):
        raise ValueError("NASS sample/yield gate failed")
    summary = json.loads((BASE / "acquisition_summary.json").read_text())
    if summary["status"] != "complete" or summary["completed_batches"] != 90:
        raise ValueError("NOAA full acquisition receipt changed")
    batch_hashes = {(item["year"], item["half"]): item["result_sha256"] for item in summary["batches"]}
    if len(batch_hashes) != 90:
        raise ValueError("NOAA batch receipt support changed")
    output.parent.mkdir(parents=True, exist_ok=True)
    mode = "at" if args.append else "xt"
    written = 0
    with gzip.open(output, mode, newline="", encoding="utf-8", compresslevel=6) as compressed:
        writer = csv.writer(compressed)
        if not args.append:
            writer.writerow(header())
        for year in range(args.start_year, args.end_year + 1):
            records = panel.loc[panel.harvest_year.eq(year)].sort_values(
                ["outcome_crop", "county_geoid"])
            counties, arrays, _ = source_year(year, batch_hashes)
            positions = {fips: idx for idx, fips in enumerate(counties)}
            names = county_names(year)
            if len(records) == 0 or records.county_geoid.nunique() > len(counties):
                raise ValueError("NASS annual support invalid")
            for row in records.itertuples(index=False):
                idx = positions.get(row.county_geoid)
                if idx is None or row.county_geoid not in names:
                    raise ValueError("NASS county lacks matching NOAA daily weather")
                base = [row.county_geoid, names[row.county_geoid], row.state,
                        year, row.outcome_crop, row.yield_bu_acre,
                        "ALL PRODUCTION PRACTICES", row.irrigation_share,
                        row.period, row.season_start, row.season_end,
                        row.precip_mm, row.tmean_c, row.wet_days_ge_1mm,
                        row.cdd_max_days, row.rx5day_mm,
                        row.stage1_precip_share, row.stage2_precip_share,
                        row.stage3_precip_share]
                writer.writerow(base + values_for_row(arrays, idx, year))
                written += 1
            print(json.dumps({"year": year, "rows": len(records), "total_written": written}), flush=True)
    print(json.dumps({"status": "exported", "start_year": args.start_year,
                      "end_year": args.end_year, "rows": written,
                      "output": str(output), "bytes": output.stat().st_size}), flush=True)


if __name__ == "__main__":
    main()
