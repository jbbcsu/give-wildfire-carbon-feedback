#!/usr/bin/env python3
"""Synthetic tests for exact-series NASS API county preparation."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from prepare_nass_api_county_yields import prepare


def record(year: int, county_ansi: str, value: str, *, unit: str = "BU / ACRE") -> dict[str, object]:
    return {
        "source_desc": "SURVEY",
        "sector_desc": "CROPS",
        "commodity_desc": "CORN",
        "statisticcat_desc": "YIELD",
        "agg_level_desc": "COUNTY",
        "freq_desc": "ANNUAL",
        "reference_period_desc": "YEAR",
        "domain_desc": "TOTAL",
        "domaincat_desc": "NOT SPECIFIED",
        "prodn_practice_desc": "ALL PRODUCTION PRACTICES",
        "util_practice_desc": "GRAIN",
        "unit_desc": unit,
        "state_ansi": "01",
        "county_ansi": county_ansi,
        "state_alpha": "AL",
        "state_name": "ALABAMA",
        "county_name": "AUTAUGA" if county_ansi else "OTHER (COMBINED) COUNTIES",
        "Value": value,
        "year": year,
    }


def write(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_text(json.dumps({"data": rows}), encoding="utf-8")


def failure(paths: list[Path], message: str, **changes: object) -> None:
    kwargs = {
        "commodity": "CORN",
        "unit": "BU / ACRE",
        "utilization_practice": "GRAIN",
        "year_start": 2019,
        "year_end": 2020,
    }
    kwargs.update(changes)
    try:
        prepare(paths, **kwargs)
    except ValueError as error:
        assert message in str(error), error
    else:
        raise AssertionError(f"expected failure containing {message!r}")


with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    first = root / "2019.json"
    second = root / "2020.json"
    write(first, [record(2019, "001", "129.1"), record(2019, "", "150.0")])
    write(second, [record(2020, "001", "(D)")])
    output, audit = prepare(
        [first, second],
        commodity="CORN",
        unit="BU / ACRE",
        utilization_practice="GRAIN",
        year_start=2019,
        year_end=2020,
    )
    assert output["county_geoid"].tolist() == ["01001", "01001"]
    assert output["yield_reported"].tolist() == [True, False]
    assert output["nass_value_flag"].tolist() == ["reported", "(D)"]
    assert audit["excluded_non_fips_records_by_year"] == {"2019": 1, "2020": 0}
    assert audit["role"].endswith("not_response_or_scc")

    failure([first], "exact requested years")

    bad = root / "bad_unit.json"
    write(bad, [record(2020, "003", "5.0", unit="TONS / ACRE")])
    failure([first, bad], "unit_desc differs")

    duplicate = root / "duplicate.json"
    write(duplicate, [record(2020, "001", "1.0"), record(2020, "001", "2.0")])
    failure([first, duplicate], "duplicate county-year")

print("NASS API county preparation synthetic tests passed")
