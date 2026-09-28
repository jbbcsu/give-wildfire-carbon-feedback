#!/usr/bin/env python3
"""Build fixed NASS usual-date calendars for sorghum grain and all cotton."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SOURCE_SHA512 = (
    "32038684035bc4e7e4191ad58ff45657db93da0da6c0a3da4d4dfbe3ad34aa805"
    "cd9aee7e500efa8d045580b9a847d9dbff7921c1a62f78122536bd152731e41"
)
SOURCE_SIZE = 2_051_038
SOURCE_ID = "usda_nass_field_crops_usual_dates_2010"
SOURCE_URL = "https://www.nass.usda.gov/Publications/Todays_Reports/reports/fcdate10.pdf"
TABLES = {
    "cotton_upland": {"page": 11, "rows": 17, "source_crop": "all_cotton"},
    "sorghum_grain": {"page": 23, "rows": 14, "source_crop": "sorghum_for_grain"},
}
STATE_ALPHA = {
    "Alabama": "AL", "Arizona": "AZ", "Arkansas": "AR", "California": "CA",
    "Colorado": "CO", "Florida": "FL", "Georgia": "GA", "Illinois": "IL",
    "Kansas": "KS", "Louisiana": "LA", "Mississippi": "MS", "Missouri": "MO",
    "Nebraska": "NE", "New Mexico": "NM", "North Carolina": "NC",
    "Oklahoma": "OK", "South Carolina": "SC", "South Dakota": "SD",
    "Tennessee": "TN", "Texas": "TX", "Virginia": "VA",
}
MONTH = {name: number for number, name in enumerate(
    ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
)}
MONTH["Sept"] = 9
DATE_TOKEN = re.compile(r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\s+\d{1,2}\b")
ROW = re.compile(r"^\s*(?P<state>[A-Za-z ]+?)\s+\.{2,}\s+(?P<acres>[\d,.]+)\s+(?P<rest>.*)$")
DATE_FIELDS = [
    "planting_begin", "planting_active_start", "planting_active_end", "planting_end",
    "harvest_begin", "harvest_active_start", "harvest_active_end", "harvest_end",
]


def digest(path: Path, algorithm: str = "sha512") -> str:
    value = hashlib.new(algorithm)
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 << 20), b""):
            value.update(block)
    return value.hexdigest()


def token_md(token: str) -> tuple[int, int]:
    month, day = token.split()
    return MONTH[month], int(day)


def extract_page(pdf: Path, page: int) -> str:
    return subprocess.run(
        ["pdftotext", "-f", str(page), "-l", str(page), "-layout", str(pdf), "-"],
        check=True, capture_output=True, text=True,
    ).stdout


def parse_page(text: str, crop: str) -> pd.DataFrame:
    rows = []
    for line in text.splitlines():
        match = ROW.match(line)
        if not match:
            continue
        state_name = " ".join(match.group("state").split())
        if state_name not in STATE_ALPHA:
            continue
        tokens = DATE_TOKEN.findall(match.group("rest"))
        if len(tokens) != 8:
            raise ValueError(f"{crop}/{state_name} has {len(tokens)} date tokens")
        item = {
            "state": STATE_ALPHA[state_name], "state_name": state_name,
            "calendar_crop": crop, "source_crop_scope": TABLES[crop]["source_crop"],
            "published_harvested_acres_2009_thousand": float(match.group("acres").replace(",", "")),
            "published_source_page": TABLES[crop]["page"],
        }
        item.update(zip(DATE_FIELDS, tokens, strict=True))
        rows.append(item)
    frame = pd.DataFrame(rows)
    if len(frame) != TABLES[crop]["rows"] or frame.duplicated(["state", "calendar_crop"]).any():
        raise ValueError(f"unexpected {crop} source rows")
    return frame.sort_values("state").reset_index(drop=True)


def dated_interval(start_token: str, end_token: str, year: int) -> tuple[date, date]:
    start_month, start_day = token_md(start_token)
    end_month, end_day = token_md(end_token)
    start = date(year, start_month, start_day)
    end = date(year, end_month, end_day)
    if end < start:
        end = date(year + 1, end_month, end_day)
    return start, end


def midpoint(start: date, end: date) -> date:
    return start + timedelta(days=(end - start).days // 2)


def expand(definitions: pd.DataFrame, year_min: int, year_max: int) -> pd.DataFrame:
    rows = []
    for definition in definitions.itertuples(index=False):
        for year in range(year_min, year_max + 1):
            planting_active = dated_interval(definition.planting_active_start, definition.planting_active_end, year)
            harvest_active = dated_interval(definition.harvest_active_start, definition.harvest_active_end, year)
            primary_start, primary_end = midpoint(*planting_active), midpoint(*harvest_active)
            if primary_end < primary_start:
                primary_end = date(primary_end.year + 1, primary_end.month, primary_end.day)
            broad_start = date(year, *token_md(definition.planting_begin))
            harvest_begin_md = token_md(definition.harvest_begin)
            broad_end_md = token_md(definition.harvest_end)
            broad_end = date(year + int(broad_end_md < harvest_begin_md), *broad_end_md)
            candidates = [
                ("fixed_primary", primary_start, primary_end,
                 "floor_midpoint_of_most_active_planting_and_harvest_intervals"),
                ("fixed_broad_window_sensitivity", broad_start, broad_end,
                 "published_planting_begin_through_harvest_end"),
            ]
            for role, start, end, rule in candidates:
                duration = (end - start).days + 1
                if end.year not in {year, year + 1} or not 30 <= duration <= 500:
                    raise ValueError("calendar chronology/duration gate failed")
                rows.append({
                    "state": definition.state, "state_name": definition.state_name,
                    "calendar_crop": definition.calendar_crop, "harvest_year": year,
                    "season_start": start.isoformat(), "season_end": end.isoformat(),
                    "calendar_source_id": SOURCE_ID, "calendar_source_url": SOURCE_URL,
                    "calendar_vintage": 2010, "calendar_role": role, "boundary_rule": rule,
                    "stage_definition": "equal_duration_0_30_70_100_engineering_proxy",
                    "published_source_page": definition.published_source_page,
                    "feature_construction_eligible": True,
                    "response_estimation_authorized": False, "scc_authorized": False,
                })
    result = pd.DataFrame(rows).sort_values(["calendar_crop", "state", "harvest_year", "calendar_role"])
    if result.duplicated(["calendar_crop", "state", "harvest_year", "calendar_role"]).any():
        raise ValueError("duplicate calendar key")
    return result.reset_index(drop=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", type=Path, required=True)
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--year-min", type=int, default=1981)
    parser.add_argument("--year-max", type=int, default=2018)
    parser.add_argument("--definitions-out", type=Path, required=True)
    parser.add_argument("--calendar-out", type=Path, required=True)
    parser.add_argument("--receipt-out", type=Path, required=True)
    args = parser.parse_args()
    if args.pdf.stat().st_size != SOURCE_SIZE or digest(args.pdf) != SOURCE_SHA512:
        raise ValueError("calendar PDF differs from pinned source")
    definitions = pd.concat(
        [parse_page(extract_page(args.pdf, spec["page"]), crop) for crop, spec in TABLES.items()],
        ignore_index=True,
    )
    calendar = expand(definitions, args.year_min, args.year_max)
    panel = pd.read_parquet(args.panel)
    support = panel[["crop", "state_alpha", "harvest_year", "county_geoid"]].drop_duplicates()
    joined = support.merge(
        calendar[["calendar_crop", "state", "harvest_year", "calendar_role"]],
        left_on=["crop", "state_alpha", "harvest_year"],
        right_on=["calendar_crop", "state", "harvest_year"], how="left", validate="many_to_many",
    )
    if joined.calendar_role.isna().any() or joined.groupby(["crop", "state_alpha", "harvest_year", "county_geoid"]).calendar_role.nunique().ne(2).any():
        raise ValueError("not every outcome support key receives both calendar roles")
    args.definitions_out.parent.mkdir(parents=True, exist_ok=True)
    definitions.to_csv(args.definitions_out, index=False)
    args.calendar_out.parent.mkdir(parents=True, exist_ok=True)
    calendar.to_csv(args.calendar_out, index=False)
    receipt = {
        "status": "calendar_source_and_outcome_state_support_pass",
        "implementation": {
            "path": str(Path(__file__).resolve().relative_to(ROOT)),
            "sha256": digest(Path(__file__), "sha256"),
        },
        "source": {"path": str(args.pdf), "bytes": SOURCE_SIZE, "sha512": SOURCE_SHA512},
        "definitions": {"path": str(args.definitions_out), "rows": len(definitions), "sha256": digest(args.definitions_out, "sha256")},
        "calendar": {"path": str(args.calendar_out), "rows": len(calendar), "sha256": digest(args.calendar_out, "sha256")},
        "definition_rows_by_crop": {k: int(v) for k, v in definitions.groupby("calendar_crop").size().items()},
        "outcome_states_by_crop": {k: sorted(v.unique().tolist()) for k, v in support.groupby("crop").state_alpha},
        "paired_outcome_keys": int(len(support)), "paired_outcome_keys_with_both_roles": int(len(support)),
        "same_calendar_for_both_practices": True, "realized_phenology": False,
        "weather_joined": False, "response_estimation_authorized": False, "scc_authorized": False,
    }
    args.receipt_out.parent.mkdir(parents=True, exist_ok=True)
    args.receipt_out.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
