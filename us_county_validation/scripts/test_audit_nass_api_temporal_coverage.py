#!/usr/bin/env python3
"""Synthetic failure-mode checks for NASS API temporal coverage."""
from __future__ import annotations

import tempfile
from pathlib import Path

import pandas as pd

from audit_nass_api_temporal_coverage import audit


def write(path: Path, frame: pd.DataFrame) -> None:
    frame.to_parquet(path, index=False)


def expect_failure(path: Path, frame: pd.DataFrame, message: str) -> None:
    write(path, frame)
    try:
        audit(path, year_start=2020, year_end=2022)
    except ValueError as error:
        assert message in str(error)
    else:
        raise AssertionError(f"expected failure containing {message!r}")


rows = []
for geoid, years in {"01001": [2020, 2021, 2022], "01003": [2020, 2022]}.items():
    for year in years:
        rows.append(
            {
                "harvest_year": year,
                "county_geoid": geoid,
                "commodity": "CORN",
                "yield_unit": "BU / ACRE",
                "yield_value": float(year - 1900),
                "yield_reported": True,
                "prodn_practice_desc": "ALL PRODUCTION PRACTICES",
            }
        )
valid = pd.DataFrame(rows)

with tempfile.TemporaryDirectory() as directory:
    path = Path(directory) / "panel.parquet"
    write(path, valid)
    result = audit(path, year_start=2020, year_end=2022)
    assert result["role"] == "outcome_temporal_coverage_not_weather_response_or_scc"
    assert result["county_year_rows"] == 5
    assert result["counties_any_year"] == 2
    assert result["counties_complete_all_years"] == 1
    assert result["adjacent_reported_pairs_by_interval"] == {"2020_2021": 1, "2021_2022": 1}

    expect_failure(path, valid[valid.harvest_year != 2021], "panel years differ")
    expect_failure(path, pd.concat([valid, valid.iloc[[0]]], ignore_index=True), "duplicate county-years")
    mixed = valid.copy()
    mixed.loc[0, "prodn_practice_desc"] = "IRRIGATED"
    expect_failure(path, mixed, "mixes prodn_practice_desc")
    invalid = valid.copy()
    invalid.loc[0, "yield_value"] = 0.0
    expect_failure(path, invalid, "finite and positive")

print("NASS API temporal coverage synthetic tests passed")
