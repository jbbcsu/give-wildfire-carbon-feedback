#!/usr/bin/env python3
"""Synthetic checks for NASS suppression and county-key handling."""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

import pandas as pd


SCRIPT = Path(__file__).with_name("prepare_nass_county_yields.py")


with tempfile.TemporaryDirectory() as directory:
    temp = Path(directory)
    source = temp / "nass.csv"
    output = temp / "corn.parquet"
    pd.DataFrame(
        {
            "year": [2020, 2021, 2020],
            "commodity_desc": ["CORN", "CORN", "SOYBEANS"],
            "statisticcat_desc": ["YIELD", "YIELD", "YIELD"],
            "agg_level_desc": ["COUNTY", "COUNTY", "COUNTY"],
            "state_ansi": [19.0, 19.0, 19.0],
            "county_ansi": [1.0, 1.0, 1.0],
            "value": ["1,234", "(D)", "50"],
            "unit_desc": ["BU / ACRE", "BU / ACRE", "BU / ACRE"],
        }
    ).to_csv(source, index=False)
    subprocess.run(
        [
            sys.executable, str(SCRIPT), "--input", str(source), "--commodity", "CORN",
            "--year-min", "2020", "--year-max", "2021", "--out", str(output),
        ],
        check=True,
    )
    panel = pd.read_parquet(output).sort_values("harvest_year").reset_index(drop=True)
    assert panel.county_geoid.tolist() == ["19001", "19001"]
    assert panel.yield_reported.tolist() == [True, False]
    assert panel.loc[0, "yield_value"] == 1234
    assert pd.isna(panel.loc[1, "yield_value"])
    assert panel.loc[1, "nass_value_flag"] == "(D)"

    malformed = temp / "malformed.csv"
    pd.read_csv(source).assign(county_ansi=1000).to_csv(malformed, index=False)
    result = subprocess.run(
        [
            sys.executable, str(SCRIPT), "--input", str(malformed), "--commodity", "CORN",
            "--year-min", "2020", "--year-max", "2021", "--out", str(output),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "outside 3-digit range" in result.stderr

print("NASS county-yield preparation tests passed")
