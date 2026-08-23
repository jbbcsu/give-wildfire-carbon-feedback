#!/usr/bin/env python3
"""Synthetic checks for the NASS--USDM county-year coverage audit."""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

import pandas as pd


SCRIPT = Path(__file__).with_name("audit_usdm_yield_coverage.py")


def run_audit(yields: Path, exposures: Path, output: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--yields",
            str(yields),
            "--exposures",
            str(exposures),
            "--commodity",
            "CORN",
            "--crop",
            "maize",
            "--out",
            str(output),
        ],
        capture_output=True,
        text=True,
    )


with tempfile.TemporaryDirectory() as directory:
    temp = Path(directory)
    yields_path = temp / "yields.parquet"
    exposures_path = temp / "exposures.parquet"
    output = temp / "coverage.csv"
    yields = pd.DataFrame(
        {
            "county_geoid": ["19001", "19003", "19001"],
            "harvest_year": [2020, 2020, 2021],
            "commodity": ["CORN", "CORN", "CORN"],
            "yield_unit": ["BU / ACRE", "BU / ACRE", "BU / ACRE"],
            "yield_reported": [True, False, True],
        }
    )
    exposures = pd.DataFrame(
        {
            "county_geoid": ["19001", "19005", "19001"],
            "harvest_year": [2020, 2020, 2021],
            "crop": ["maize", "maize", "maize"],
            "analysis_role": ["historical_county_validation_only"] * 3,
            "scc_authorized": [False, False, False],
        }
    )
    yields.to_parquet(yields_path, index=False)
    exposures.to_parquet(exposures_path, index=False)
    result = run_audit(yields_path, exposures_path, output)
    assert result.returncode == 0, result.stderr
    audit = pd.read_csv(output)
    overall = audit.loc[audit.coverage_scope.eq("overall")].iloc[0]
    assert overall.commodity == "CORN"
    assert overall.crop == "maize"
    assert overall.yield_unit == "BU / ACRE"
    assert overall.yield_rows == 3
    assert overall.reported_yield_rows == 2
    assert overall.exposure_rows == 3
    assert overall.matched_rows == 2
    assert overall.matched_reported_yield_rows == 2
    assert overall.yield_only_rows == 1
    assert overall.exposure_only_rows == 1
    assert abs(overall.yield_match_share - 2 / 3) < 1e-12
    assert overall.reported_yield_match_share == 1
    assert abs(overall.exposure_match_share - 2 / 3) < 1e-12
    assert overall.analysis_role == "historical_county_validation_only"
    assert not overall.scc_authorized

    by_year = audit.loc[audit.coverage_scope.eq("harvest_year")].set_index("harvest_year")
    assert by_year.loc[2020, "matched_rows"] == 1
    assert by_year.loc[2020, "yield_only_rows"] == 1
    assert by_year.loc[2020, "exposure_only_rows"] == 1
    assert by_year.loc[2021, "yield_match_share"] == 1

    invalid_cases = [
        (
            yields,
            pd.concat([exposures, exposures.iloc[[0]]], ignore_index=True),
            "Duplicate USDM county-year rows",
        ),
        (
            yields,
            exposures.assign(scc_authorized=[True, False, False]),
            "must not be SCC-authorized",
        ),
        (
            yields,
            exposures.assign(
                analysis_role=[
                    None,
                    "historical_county_validation_only",
                    "historical_county_validation_only",
                ]
            ),
            "analysis_role violates the validation-only boundary",
        ),
        (
            yields.assign(yield_unit=["BU / ACRE", "TONS / ACRE", "BU / ACRE"]),
            exposures,
            "multiple yield units",
        ),
        (
            yields.assign(yield_reported=["true", "unknown", "true"]),
            exposures,
            "yield_reported must contain only true/false values",
        ),
    ]
    for invalid_yields, invalid_exposures, expected_error in invalid_cases:
        invalid_yields.to_parquet(yields_path, index=False)
        invalid_exposures.to_parquet(exposures_path, index=False)
        result = run_audit(yields_path, exposures_path, output)
        assert result.returncode != 0
        assert expected_error in result.stderr, result.stderr

print("NASS--USDM coverage audit tests passed")
