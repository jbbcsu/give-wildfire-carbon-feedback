#!/usr/bin/env python3
"""Synthetic checks for the crop-season USDM exposure bridge."""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

import pandas as pd


SCRIPT = Path(__file__).with_name("build_usdm_crop_season_exposures.py")


def run_builder(weeks: Path, calendar: Path, output: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--weeks",
            str(weeks),
            "--calendar",
            str(calendar),
            "--out",
            str(output),
        ],
        capture_output=True,
        text=True,
    )


def derive(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy()
    frame["d1plus_pct"] = frame[["d1_pct", "d2_pct", "d3_pct", "d4_pct"]].sum(axis=1)
    frame["d2plus_pct"] = frame[["d2_pct", "d3_pct", "d4_pct"]].sum(axis=1)
    frame["d3plus_pct"] = frame[["d3_pct", "d4_pct"]].sum(axis=1)
    frame["drought_severity_area_pct"] = (
        frame.d1_pct + 2 * frame.d2_pct + 3 * frame.d3_pct + 4 * frame.d4_pct
    )
    return frame


with tempfile.TemporaryDirectory() as directory:
    temp = Path(directory)
    weeks_path = temp / "weeks.parquet"
    calendar_path = temp / "calendar.csv"
    output = temp / "season.parquet"
    weeks = derive(
        pd.DataFrame(
            {
                "county_geoid": ["19001", "19001"],
                "state": ["IA", "IA"],
                "map_date": ["2023-12-26", "2024-01-02"],
                "valid_start": ["2023-12-26", "2024-01-02"],
                "valid_end": ["2024-01-01", "2024-01-08"],
                "none_pct": [70.0, 30.0],
                "d0_pct": [10.0, 10.0],
                "d1_pct": [10.0, 20.0],
                "d2_pct": [5.0, 20.0],
                "d3_pct": [5.0, 10.0],
                "d4_pct": [0.0, 10.0],
            }
        )
    )
    weeks.to_parquet(weeks_path, index=False)
    calendar = pd.DataFrame(
        {
            "state": ["IA"],
            "crop": ["maize"],
            "harvest_year": [2024],
            "season_start": ["2023-12-29"],
            "season_end": ["2024-01-04"],
            "calendar_source": ["synthetic-test-calendar-v1"],
        }
    )
    calendar.to_csv(calendar_path, index=False)
    result = run_builder(weeks_path, calendar_path, output)
    assert result.returncode == 0, result.stderr
    exposure = pd.read_parquet(output).iloc[0]
    # Four days at 20% D1+ and three days at 60% D1+.
    assert exposure.season_days == 7
    assert exposure.usdm_intervals == 2
    assert abs(exposure.d1plus_season_mean_pct - (260 / 7)) < 1e-12
    assert abs(exposure.d1plus_area_equivalent_days - 2.6) < 1e-12
    assert abs(exposure.d0plus_area_equivalent_days - 3.3) < 1e-12
    assert abs(exposure.drought_severity_area_index_mean - (530 / 7)) < 1e-12
    assert exposure.calendar_source == "synthetic-test-calendar-v1"
    assert exposure.analysis_role == "historical_county_validation_only"
    assert not exposure.scc_authorized

    bad_calendar = temp / "bad_calendar.csv"
    invalid_cases = [
        (
            derive(
                weeks.assign(
                    map_date=["2023-12-26", "2024-01-03"],
                    valid_start=["2023-12-26", "2024-01-03"],
                )
            ),
            calendar,
            "Gapped or overlapping USDM intervals",
        ),
        (
            derive(weeks.assign(valid_start=["2023-12-26", "2024-01-01"])),
            calendar,
            "Gapped or overlapping USDM intervals",
        ),
        (
            derive(weeks.assign(d1_pct=[11.0, 20.0])),
            calendar,
            "do not sum to 100",
        ),
        (
            weeks,
            calendar.assign(calendar_source=""),
            "calendar_source must be nonblank",
        ),
        (
            weeks,
            pd.concat([calendar, calendar], ignore_index=True),
            "Duplicate state-crop-harvest-year calendar rows",
        ),
    ]
    for invalid_weeks, invalid_calendar, expected_error in invalid_cases:
        invalid_weeks.to_parquet(weeks_path, index=False)
        invalid_calendar.to_csv(bad_calendar, index=False)
        result = run_builder(weeks_path, bad_calendar, output)
        assert result.returncode != 0
        assert expected_error in result.stderr, result.stderr

print("USDM crop-season exposure tests passed")
