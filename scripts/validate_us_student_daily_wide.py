#!/usr/bin/env python3
"""Independently audit the student-facing wide daily weather/yield CSV."""
from __future__ import annotations

import argparse
import calendar
from collections import Counter
import csv
from datetime import date
import gzip
import hashlib
import json
from pathlib import Path

import pandas as pd

from export_us_student_daily_wide import PANEL, ROOT, header, month_days


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    args = parser.parse_args()
    path = args.input.resolve()
    if not path.is_relative_to(ROOT / "data/interim"):
        raise ValueError("input is outside isolated ignored project data")
    panel = pd.read_parquet(PANEL, columns=["outcome_crop", "county_geoid",
        "harvest_year", "yield_bu_acre", "state", "season_start", "season_end",
        "precip_mm"])
    expected = {(r.outcome_crop, r.county_geoid, int(r.harvest_year)): r
                for r in panel.itertuples(index=False)}
    if len(expected) != 34288:
        raise ValueError("source panel keys changed")
    expected_header = header()
    days = month_days()
    widths = len(days)
    seen = set()
    by_year = Counter()
    by_crop = Counter()
    leap_present = 0
    with gzip.open(path, "rt", newline="", encoding="utf-8") as stream:
        reader = csv.reader(stream)
        actual_header = next(reader)
        if actual_header != expected_header or len(actual_header) != 1483:
            raise ValueError("CSV header differs from registered export schema")
        offsets = {name: actual_header.index(f"{name}_0101") for name in
                   ("prcp_mm", "tmax_c", "tmin_c", "tavg_c")}
        feb29 = days.index("0229")
        for row in reader:
            if len(row) != len(actual_header):
                raise ValueError("CSV row width changed")
            year = int(row[3])
            key = (row[4], row[0], year)
            ref = expected.get(key)
            if ref is None or key in seen:
                raise ValueError(f"missing or duplicate source key {key}")
            seen.add(key)
            by_year[year] += 1
            by_crop[row[4]] += 1
            if (row[2] != ref.state or row[9] != ref.season_start or
                row[10] != ref.season_end or abs(float(row[5])-ref.yield_bu_acre) > 1e-9):
                raise ValueError(f"yield/state/calendar mismatch {key}")
            blocks = {}
            for name, offset in offsets.items():
                block = row[offset:offset+widths]
                if len(block) != widths or (block[feb29] == "") == calendar.isleap(year):
                    raise ValueError(f"leap-day or block-width mismatch {key}")
                values = [float(v) for v in block if v != ""]
                if len(values) != (366 if calendar.isleap(year) else 365):
                    raise ValueError(f"missing/non-numeric daily value {key}")
                blocks[name] = block
            if calendar.isleap(year):
                leap_present += 1
            rain = [float(v) if v else 0.0 for v in blocks["prcp_mm"]]
            if min(rain) < 0:
                raise ValueError(f"negative daily precipitation {key}")
            for day in range(widths):
                if day == feb29 and not calendar.isleap(year):
                    continue
                low = float(blocks["tmin_c"][day])
                mid = float(blocks["tavg_c"][day])
                high = float(blocks["tmax_c"][day])
                if low > mid + 0.011 or mid > high + 0.011:
                    raise ValueError(f"temperature ordering failed {key}, {days[day]}")
            first = date.fromisoformat(row[9])
            last = date.fromisoformat(row[10])
            if first.year != year or last.year != year:
                raise ValueError(f"crop window crosses calendar year {key}")
            season_days = (last-first).days + 1
            start = (first-date(year, 1, 1)).days
            rain_in_year = rain if calendar.isleap(year) else rain[:feb29]+rain[feb29+1:]
            if abs(sum(rain_in_year[start:start+season_days])-float(row[11])) > 0.02:
                raise ValueError(f"season rainfall does not match daily data {key}")
    if seen != set(expected) or sorted(by_year) != list(range(1981, 2026)):
        raise ValueError("CSV omitted or added panel rows/years")
    print(json.dumps({"status": "passed", "rows": len(seen),
                      "columns": len(expected_header), "years": [1981, 2025],
                      "rows_by_crop": dict(by_crop), "leap_rows": leap_present,
                      "compressed_bytes": path.stat().st_size,
                      "sha256": digest(path)}, indent=2))


if __name__ == "__main__":
    main()
