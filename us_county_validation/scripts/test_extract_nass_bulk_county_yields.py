#!/usr/bin/env python3
"""Synthetic test for the streaming, explicitly filtered NASS bulk extractor."""
from __future__ import annotations

import gzip
import subprocess
import sys
import tempfile
from pathlib import Path

import pandas as pd

SCRIPT = Path(__file__).with_name("extract_nass_bulk_county_yields.py")

rows = [
    # Desired reported row.
    [2020, "CORN", "YIELD", "COUNTY", 19, 1, "200", "BU / ACRE", "TOTAL", "NOT SPECIFIED", "ALL PRODUCTION PRACTICES", "ALL UTILIZATION PRACTICES", "YEAR"],
    # Desired suppression: must survive as non-reported, not zero.
    [2021, "CORN", "YIELD", "COUNTY", 19, 1, "(D)", "BU / ACRE", "TOTAL", "NOT SPECIFIED", "ALL PRODUCTION PRACTICES", "ALL UTILIZATION PRACTICES", "YEAR"],
    # Excluded domain and commodity rows.
    [2020, "CORN", "YIELD", "COUNTY", 19, 3, "190", "BU / ACRE", "IRRIGATION STATUS", "IRRIGATED", "ALL PRODUCTION PRACTICES", "ALL UTILIZATION PRACTICES", "YEAR"],
    [2020, "SOYBEANS", "YIELD", "COUNTY", 19, 1, "50", "BU / ACRE", "TOTAL", "NOT SPECIFIED", "ALL PRODUCTION PRACTICES", "ALL UTILIZATION PRACTICES", "YEAR"],
]
columns = [
    "YEAR", "COMMODITY_DESC", "STATISTICCAT_DESC", "AGG_LEVEL_DESC",
    "STATE_ANSI", "COUNTY_ANSI", "VALUE", "UNIT_DESC", "DOMAIN_DESC",
    "DOMAINCAT_DESC", "PRODN_PRACTICE_DESC", "UTIL_PRACTICE_DESC",
    "REFERENCE_PERIOD_DESC",
]

with tempfile.TemporaryDirectory() as directory:
    temp = Path(directory)
    source = temp / "nass.txt.gz"
    with gzip.open(source, "wt", encoding="utf-8") as stream:
        pd.DataFrame(rows, columns=columns).to_csv(stream, sep="\t", index=False)
    output = temp / "corn.parquet"
    subprocess.run(
        [sys.executable, str(SCRIPT), "--input", str(source), "--commodity", "CORN",
         "--year-min", "2020", "--year-max", "2021", "--chunksize", "1", "--out", str(output)],
        check=True,
    )
    result = pd.read_parquet(output).sort_values("harvest_year").reset_index(drop=True)
    assert result.county_geoid.tolist() == ["19001", "19001"]
    assert result.yield_reported.tolist() == [True, False]
    assert result.yield_value.tolist()[0] == 200
    assert pd.isna(result.yield_value.iloc[1])
    assert result.nass_value_flag.tolist() == ["reported", "(D)"]
    assert result.domain_desc.tolist() == ["TOTAL", "TOTAL"]

    duplicate_source = temp / "duplicate.txt.gz"
    with gzip.open(duplicate_source, "wt", encoding="utf-8") as stream:
        pd.DataFrame(rows + [rows[0]], columns=columns).to_csv(stream, sep="\t", index=False)
    duplicate = subprocess.run(
        [sys.executable, str(SCRIPT), "--input", str(duplicate_source),
         "--commodity", "CORN", "--year-min", "2020", "--year-max", "2021",
         "--out", str(temp / "duplicate.parquet")],
        text=True, capture_output=True,
    )
    assert duplicate.returncode != 0
    assert "Duplicate county-year yields" in duplicate.stderr

    mixed_unit_rows = rows + [[
        2020, "CORN", "YIELD", "COUNTY", 19, 5, "12.5", "TONS / ACRE",
        "TOTAL", "NOT SPECIFIED", "ALL PRODUCTION PRACTICES",
        "ALL UTILIZATION PRACTICES", "YEAR",
    ]]
    mixed_source = temp / "mixed_unit.txt.gz"
    with gzip.open(mixed_source, "wt", encoding="utf-8") as stream:
        pd.DataFrame(mixed_unit_rows, columns=columns).to_csv(stream, sep="\t", index=False)
    mixed = subprocess.run(
        [sys.executable, str(SCRIPT), "--input", str(mixed_source),
         "--commodity", "CORN", "--year-min", "2020", "--year-max", "2021",
         "--out", str(temp / "mixed.parquet")],
        text=True, capture_output=True,
    )
    assert mixed.returncode != 0
    assert "multiple yield units" in mixed.stderr

print("NASS bulk streaming extractor tests passed")
