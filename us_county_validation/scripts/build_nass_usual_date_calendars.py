#!/usr/bin/env python3
"""Parse the pinned NASS usual-date tables into fixed crop-year calendars.

The source supplies state-level begin/end and most-active planting/harvest
ranges, not one realized date. The selected engineering default is the floor
midpoint of each most-active range. The published planting-begin through
harvest-end envelope is emitted as a separate sensitivity. No annual crop
progress is inferred, no response is estimated, and no SCC use is authorized.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from validate_county_crop_weather_contract import validate_calendar


SOURCE_SHA512 = (
    "32038684035bc4e7e4191ad58ff45657db93da0da6c0a3da4d4dfbe3ad34aa805"
    "cd9aee7e500efa8d045580b9a847d9dbff7921c1a62f78122536bd152731e41"
)
SOURCE_SIZE_BYTES = 2_051_038
SOURCE_ID = "usda_nass_field_crops_usual_dates_2010"
SOURCE_URL = "https://www.nass.usda.gov/Publications/Todays_Reports/reports/fcdate10.pdf"
TABLES = {
    "corn_grain": {"page": 9, "expected_rows": 41},
    "soybeans": {"page": 25, "expected_rows": 31},
    "durum_wheat": {"page": 33, "expected_rows": 6},
    "spring_wheat": {"page": 33, "expected_rows": 10},
    "winter_wheat": {"page": 34, "expected_rows": 42},
}
STATE_NAME_TO_ALPHA = {
    "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR",
    "California": "CA", "Colorado": "CO", "Connecticut": "CT", "Delaware": "DE",
    "Florida": "FL", "Georgia": "GA", "Hawaii": "HI", "Idaho": "ID",
    "Illinois": "IL", "Indiana": "IN", "Iowa": "IA", "Kansas": "KS",
    "Kentucky": "KY", "Louisiana": "LA", "Maine": "ME", "Maryland": "MD",
    "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN", "Mississippi": "MS",
    "Missouri": "MO", "Montana": "MT", "Nebraska": "NE", "Nevada": "NV",
    "New Hampshire": "NH", "New Jersey": "NJ", "New Mexico": "NM", "New York": "NY",
    "North Carolina": "NC", "North Dakota": "ND", "Ohio": "OH", "Oklahoma": "OK",
    "Oregon": "OR", "Pennsylvania": "PA", "Rhode Island": "RI",
    "South Carolina": "SC", "South Dakota": "SD", "Tennessee": "TN", "Texas": "TX",
    "Utah": "UT", "Vermont": "VT", "Virginia": "VA", "Washington": "WA",
    "West Virginia": "WV", "Wisconsin": "WI", "Wyoming": "WY",
}
MONTH = {
    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
    "Jul": 7, "Aug": 8, "Sep": 9, "Sept": 9, "Oct": 10, "Nov": 11, "Dec": 12,
}
DATE_TOKEN = re.compile(
    r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\s+\d{1,2}\b"
)
ROW_START = re.compile(r"^\s*(?P<state>[A-Za-z ]+?)\s+\.{2,}\s+(?P<acres>[\d,]+)\s+(?P<rest>.*)$")
DATE_COLUMNS = [
    "planting_begin",
    "planting_active_start",
    "planting_active_end",
    "planting_end",
    "harvest_begin",
    "harvest_active_start",
    "harvest_active_end",
    "harvest_end",
]


def sha512(path: Path) -> str:
    digest = hashlib.sha512()
    with path.open("rb") as stream:
        while block := stream.read(8 * 1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def validate_source(path: Path) -> None:
    if path.stat().st_size != SOURCE_SIZE_BYTES or sha512(path) != SOURCE_SHA512:
        raise ValueError("NASS usual-date PDF differs from the pinned source object")


def normalize_date_token(token: str) -> str:
    month_text, day_text = token.split()
    month = MONTH.get(month_text)
    day = int(day_text)
    if month is None:
        raise ValueError(f"Unknown month token {month_text}")
    date(2000, month, day)
    return f"{month:02d}-{day:02d}"


def parse_table_text(text: str, crop: str) -> pd.DataFrame:
    if crop not in TABLES:
        raise ValueError(f"Unknown crop table {crop}")
    if crop == "durum_wheat":
        start_title, end_title = "Durum Wheat Usual", "Spring Wheat Usual"
    elif crop == "spring_wheat":
        start_title, end_title = "Spring Wheat Usual", "Field Crops Usual"
    else:
        start_title, end_title = None, None
    if start_title:
        if start_title not in text or end_title not in text:
            raise ValueError(f"Cannot isolate {crop} table titles")
        text = text.split(start_title, 1)[1].split(end_title, 1)[0]

    rows: list[dict[str, object]] = []
    for line in text.splitlines():
        match = ROW_START.match(line)
        if not match:
            continue
        state_name = " ".join(match.group("state").split())
        if state_name not in STATE_NAME_TO_ALPHA:
            continue
        tokens = DATE_TOKEN.findall(match.group("rest"))
        if len(tokens) != 8:
            raise ValueError(f"{crop}/{state_name} yielded {len(tokens)} dates, expected 8: {line}")
        row: dict[str, object] = {
            "state": STATE_NAME_TO_ALPHA[state_name],
            "state_name": state_name,
            "calendar_crop": crop,
            "published_harvested_acres_2009_thousand": int(match.group("acres").replace(",", "")),
            "source_page": int(TABLES[crop]["page"]),
        }
        row.update(zip(DATE_COLUMNS, map(normalize_date_token, tokens), strict=True))
        rows.append(row)
    frame = pd.DataFrame(rows)
    expected = int(TABLES[crop]["expected_rows"])
    if len(frame) != expected:
        raise ValueError(f"{crop} parsed {len(frame)} rows, expected {expected}")
    if frame.duplicated(["state", "calendar_crop"]).any():
        raise ValueError(f"{crop} table contains duplicate state rows")
    return frame.sort_values("state").reset_index(drop=True)


def extract_page(pdf: Path, page: int) -> str:
    try:
        result = subprocess.run(
            ["pdftotext", "-f", str(page), "-l", str(page), "-layout", str(pdf), "-"],
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as error:
        raise RuntimeError("pdftotext is required to parse the pinned NASS report") from error
    except subprocess.CalledProcessError as error:
        raise RuntimeError("pdftotext failed on the pinned NASS report") from error
    return result.stdout


def month_day(value: str) -> tuple[int, int]:
    month, day = value.split("-")
    return int(month), int(day)


def sequential_dates(values: list[str], initial_year: int) -> list[date]:
    result: list[date] = []
    current_year = initial_year
    for value in values:
        month, day = month_day(value)
        candidate = date(current_year, month, day)
        if result and candidate < result[-1]:
            current_year += 1
            candidate = date(current_year, month, day)
        result.append(candidate)
    return result


def floor_midpoint(start: date, end: date) -> date:
    if end < start:
        raise ValueError("Cannot midpoint a reversed interval")
    return start + timedelta(days=(end - start).days // 2)


def expand_calendars(definitions: pd.DataFrame, year_min: int, year_max: int) -> pd.DataFrame:
    if not 1900 <= year_min <= year_max <= 2100:
        raise ValueError("Requested harvest-year range is invalid")
    rows: list[dict[str, object]] = []
    for definition in definitions.itertuples(index=False):
        planting_values = [getattr(definition, column) for column in DATE_COLUMNS[:4]]
        harvest_values = [getattr(definition, column) for column in DATE_COLUMNS[4:]]
        for harvest_year in range(year_min, year_max + 1):
            planting_begin_md = month_day(planting_values[0])
            harvest_begin_md = month_day(harvest_values[0])
            planting_year = harvest_year - 1 if planting_begin_md > harvest_begin_md else harvest_year
            planting = sequential_dates(planting_values, planting_year)
            harvest = sequential_dates(harvest_values, harvest_year)
            if planting[-1] >= harvest[0]:
                raise ValueError(
                    f"Planting does not precede harvest for {definition.state}/{definition.calendar_crop}/{harvest_year}"
                )
            primary_start = floor_midpoint(planting[1], planting[2])
            primary_end = floor_midpoint(harvest[1], harvest[2])
            for role, season_start, season_end, boundary_rule in [
                (
                    "fixed_primary",
                    primary_start,
                    primary_end,
                    "floor_midpoint_of_most_active_planting_and_harvest_intervals",
                ),
                (
                    "fixed_broad_window_sensitivity",
                    planting[0],
                    harvest[3],
                    "published_planting_begin_through_harvest_end",
                ),
            ]:
                duration = (season_end - season_start).days + 1
                if season_end.year != harvest_year or not 30 <= duration <= 500:
                    raise ValueError("Expanded crop season fails year/duration guardrail")
                rows.append(
                    {
                        "state": definition.state,
                        "state_name": definition.state_name,
                        "calendar_crop": definition.calendar_crop,
                        "harvest_year": harvest_year,
                        "season_start": season_start.isoformat(),
                        "season_end": season_end.isoformat(),
                        "calendar_source_id": SOURCE_ID,
                        "calendar_source_url": SOURCE_URL,
                        "calendar_vintage": "2010",
                        "calendar_role": role,
                        "boundary_rule": boundary_rule,
                        "stage_definition": "equal_duration_0_30_70_100_engineering_proxy",
                        "published_source_page": int(definition.source_page),
                        "published_harvested_acres_2009_thousand": int(
                            definition.published_harvested_acres_2009_thousand
                        ),
                        "feature_construction_eligible": True,
                        "response_estimation_authorized": False,
                        "scc_authorized": False,
                    }
                )
    calendar = pd.DataFrame(rows)
    keys = ["state", "calendar_crop", "harvest_year", "calendar_role"]
    if calendar.duplicated(keys).any():
        raise ValueError("Expanded calendar contains duplicate state/crop/year/role keys")
    return calendar.sort_values(keys).reset_index(drop=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", required=True)
    parser.add_argument("--year-min", required=True, type=int)
    parser.add_argument("--year-max", required=True, type=int)
    parser.add_argument("--definitions-out", required=True)
    parser.add_argument("--calendar-out", required=True)
    parser.add_argument("--audit-out", required=True)
    args = parser.parse_args()

    pdf = Path(args.pdf)
    validate_source(pdf)
    page_text = {page: extract_page(pdf, page) for page in sorted({v["page"] for v in TABLES.values()})}
    definitions = pd.concat(
        [parse_table_text(page_text[int(spec["page"])], crop) for crop, spec in TABLES.items()],
        ignore_index=True,
    ).sort_values(["calendar_crop", "state"]).reset_index(drop=True)
    calendar = expand_calendars(definitions, args.year_min, args.year_max)

    # Source-to-rule QA anchors from the visually audited Nebraska rows.
    qa = calendar.loc[
        calendar.state.eq("NE")
        & calendar.harvest_year.eq(args.year_min)
        & calendar.calendar_role.eq("fixed_primary")
        & calendar.calendar_crop.isin(["corn_grain", "soybeans"])
    ].set_index("calendar_crop")
    expected = {
        "corn_grain": (f"{args.year_min}-05-06", f"{args.year_min}-10-22"),
        "soybeans": (f"{args.year_min}-05-21", f"{args.year_min}-10-11"),
    }
    for crop, dates in expected.items():
        if crop not in qa.index or (qa.loc[crop, "season_start"], qa.loc[crop, "season_end"]) != dates:
            raise ValueError(f"Nebraska {crop} midpoint QA anchor failed")

    calendar = validate_calendar(calendar)

    definitions_path = Path(args.definitions_out)
    definitions_path.parent.mkdir(parents=True, exist_ok=True)
    definitions.to_csv(definitions_path, index=False)
    calendar_path = Path(args.calendar_out)
    calendar_path.parent.mkdir(parents=True, exist_ok=True)
    calendar.to_csv(calendar_path, index=False)
    audit = {
        "source_pdf": str(pdf),
        "source_size_bytes": pdf.stat().st_size,
        "source_sha512": sha512(pdf),
        "definition_rows": int(len(definitions)),
        "definition_rows_by_crop": {
            str(key): int(value)
            for key, value in definitions.groupby("calendar_crop").size().items()
        },
        "harvest_year_min": args.year_min,
        "harvest_year_max": args.year_max,
        "calendar_rows": int(len(calendar)),
        "cross_year_rows": int(
            (pd.to_datetime(calendar.season_start).dt.year < calendar.harvest_year).sum()
        ),
        "calendar_roles": sorted(calendar.calendar_role.unique().tolist()),
        "primary_rule": "floor midpoint of published most-active boundaries",
        "broad_rule": "published planting begin through harvest end",
        "stage_status": "equal-duration engineering proxy, not phenology",
        "relationship_estimated": False,
        "response_estimation_authorized": False,
        "scc_authorized": False,
    }
    audit_path = Path(args.audit_out)
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        f"parsed {len(definitions)} NASS state/crop rows and wrote {len(calendar)} "
        "calendar rows; no response estimated"
    )


if __name__ == "__main__":
    main()
