#!/usr/bin/env python3
"""Synthetic checks for USDM categorical shares, keys, and dates."""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

import pandas as pd


SCRIPT = Path(__file__).with_name("prepare_usdm_county_weeks.py")


def run_preparer(source: Path, output: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--input", str(source), "--out", str(output)],
        capture_output=True,
        text=True,
    )


with tempfile.TemporaryDirectory() as directory:
    temp = Path(directory)
    source = temp / "usdm.csv"
    output = temp / "usdm.parquet"
    valid = pd.DataFrame(
        {
            "MapDate": [20240102, 20240109],
            # Exercise both spreadsheet-style numeric text and a leading-zero GEOID.
            "FIPS": ["19001.0", "01003"],
            "County": ["Adair County", "Baldwin County"],
            "State": ["IA", "AL"],
            "None": [20.0, 100.0],
            "D0": [10.0, 0.0],
            "D1": [20.0, 0.0],
            "D2": [20.0, 0.0],
            "D3": [20.0, 0.0],
            "D4": [10.0, 0.0],
            "ValidStart": ["2024-01-02", "2024-01-09"],
            "ValidEnd": ["2024-01-08", "2024-01-15"],
            "StatisticFormatID": [2, 2],
        }
    )
    valid.to_csv(source, index=False)
    result = run_preparer(source, output)
    assert result.returncode == 0, result.stderr
    weeks = pd.read_parquet(output).sort_values("county_geoid").reset_index(drop=True)
    assert weeks.county_geoid.tolist() == ["01003", "19001"]
    drought = weeks.loc[weeks.county_geoid.eq("19001")].iloc[0]
    assert drought.d1plus_pct == 70.0
    assert drought.d2plus_pct == 50.0
    assert drought.d3plus_pct == 30.0
    assert drought.drought_severity_area_pct == 160.0

    malformed = temp / "malformed.csv"
    invalid_cases = [
        (valid.assign(StatisticFormatID=1), "Expected official county area-percent statistic format 2"),
        (valid.assign(D4=[11.0, 0.0]), "do not sum to 100"),
        (valid.assign(FIPS=["not-a-fips", "01003"]), "five-digit county GEOIDs"),
        (valid.assign(ValidStart=["2024-01-03", "2024-01-09"]), "outside its validity interval"),
        (pd.concat([valid, valid.iloc[[0]]], ignore_index=True), "Duplicate county-week rows"),
    ]
    for frame, expected_error in invalid_cases:
        frame.to_csv(malformed, index=False)
        result = run_preparer(malformed, output)
        assert result.returncode != 0
        assert expected_error in result.stderr, result.stderr

print("USDM county-week preparation tests passed")
