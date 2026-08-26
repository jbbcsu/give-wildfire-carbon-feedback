#!/usr/bin/env python3
"""Prepare exact-series NASS API responses for county-panel validation.

The Quick Stats API returns some COUNTY-aggregation records for combined or
otherwise non-FIPS geographies.  Those rows are counted in the audit but are
not assigned invented county identifiers.  Suppressed values for real counties
remain present with a missing numeric yield and their original NASS flag.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


EXPECTED = {
    "source_desc": "SURVEY",
    "sector_desc": "CROPS",
    "statisticcat_desc": "YIELD",
    "agg_level_desc": "COUNTY",
    "freq_desc": "ANNUAL",
    "reference_period_desc": "YEAR",
    "domain_desc": "TOTAL",
    "domaincat_desc": "NOT SPECIFIED",
    "prodn_practice_desc": "ALL PRODUCTION PRACTICES",
}
OUTPUT = [
    "harvest_year",
    "county_geoid",
    "state_alpha",
    "state_name",
    "county_name",
    "commodity",
    "yield_unit",
    "yield_value_raw",
    "yield_value",
    "yield_reported",
    "nass_value_flag",
    "domain_desc",
    "domaincat_desc",
    "prodn_practice_desc",
    "util_practice_desc",
    "reference_period_desc",
]


def _text(series: pd.Series) -> pd.Series:
    return series.astype("string").str.strip()


def _load(path: Path) -> pd.DataFrame:
    with path.open(encoding="utf-8") as stream:
        payload = json.load(stream)
    if set(payload) != {"data"} or not isinstance(payload["data"], list) or not payload["data"]:
        raise ValueError(f"{path}: expected one nonempty Quick Stats data array")
    frame = pd.DataFrame(payload["data"])
    required = set(EXPECTED) | {
        "year", "commodity_desc", "unit_desc", "util_practice_desc",
        "state_ansi", "county_ansi", "state_alpha", "state_name",
        "county_name", "Value",
    }
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"{path}: missing Quick Stats fields {missing}")
    return frame


def prepare(
    paths: list[Path],
    *,
    commodity: str,
    unit: str,
    utilization_practice: str,
    year_start: int,
    year_end: int,
) -> tuple[pd.DataFrame, dict[str, object]]:
    if not paths or year_start > year_end:
        raise ValueError("input files and closed year range are required")
    commodity = commodity.strip().upper()
    unit = unit.strip().upper()
    utilization_practice = utilization_practice.strip().upper()
    frames: list[pd.DataFrame] = []
    raw_counts: dict[int, int] = {}
    for path in paths:
        frame = _load(path)
        years = pd.to_numeric(frame["year"], errors="coerce")
        if years.isna().any() or (years % 1 != 0).any() or years.nunique() != 1:
            raise ValueError(f"{path}: each API response must contain exactly one integer year")
        year = int(years.iloc[0])
        if year in raw_counts:
            raise ValueError(f"duplicate API response year: {year}")
        raw_counts[year] = len(frame)
        for column, expected in EXPECTED.items():
            observed = set(_text(frame[column]).str.upper())
            if observed != {expected}:
                raise ValueError(f"{path}: {column} differs from locked series: {sorted(observed)}")
        locked = {
            "commodity_desc": commodity,
            "unit_desc": unit,
            "util_practice_desc": utilization_practice,
        }
        for column, expected in locked.items():
            observed = set(_text(frame[column]).str.upper())
            if observed != {expected}:
                raise ValueError(f"{path}: {column} differs from requested series: {sorted(observed)}")
        frame["year"] = year
        frames.append(frame)

    expected_years = set(range(year_start, year_end + 1))
    if set(raw_counts) != expected_years:
        raise ValueError(
            f"API responses do not cover the exact requested years; "
            f"missing={sorted(expected_years - set(raw_counts))}, extra={sorted(set(raw_counts) - expected_years)}"
        )
    combined = pd.concat(frames, ignore_index=True)
    state = _text(combined["state_ansi"])
    county = _text(combined["county_ansi"])
    real_county = state.str.fullmatch(r"\d{2}", na=False) & county.str.fullmatch(r"\d{3}", na=False)
    excluded_by_year = (
        combined.loc[~real_county]
        .groupby("year", sort=True)
        .size()
        .reindex(sorted(expected_years), fill_value=0)
        .astype(int)
        .to_dict()
    )
    selected = combined.loc[real_county].copy()
    selected["county_geoid"] = state.loc[real_county].astype(str) + county.loc[real_county].astype(str)
    if selected["county_geoid"].str.fullmatch(r"\d{5}", na=False).eq(False).any():
        raise ValueError("selected county GEOIDs are not five digits")
    raw = _text(selected["Value"])
    numeric = pd.to_numeric(raw.str.replace(",", "", regex=False), errors="coerce").astype("Float64")
    selected["harvest_year"] = pd.to_numeric(selected["year"], errors="raise").astype("int64")
    selected["commodity"] = _text(selected["commodity_desc"]).str.upper()
    selected["yield_unit"] = _text(selected["unit_desc"])
    selected["yield_value_raw"] = raw
    selected["yield_value"] = numeric
    selected["yield_reported"] = numeric.notna()
    selected["nass_value_flag"] = raw.where(~selected["yield_reported"], "reported")
    for column in (
        "state_alpha", "state_name", "county_name", "domain_desc",
        "domaincat_desc", "prodn_practice_desc", "util_practice_desc",
        "reference_period_desc",
    ):
        selected[column] = _text(selected[column])
    keys = ["harvest_year", "county_geoid", "commodity", "yield_unit"]
    if selected.duplicated(keys).any():
        examples = selected.loc[selected.duplicated(keys, keep=False), keys].head(5).to_dict("records")
        raise ValueError(f"duplicate county-year rows in locked API series: {examples}")
    selected = selected[OUTPUT].sort_values(keys).reset_index(drop=True)
    audit = {
        "role": "national_county_outcome_acquisition_only_not_response_or_scc",
        "commodity": commodity,
        "unit": unit,
        "utilization_practice": utilization_practice,
        "year_start": year_start,
        "year_end": year_end,
        "raw_records_by_year": {str(key): raw_counts[key] for key in sorted(raw_counts)},
        "excluded_non_fips_records_by_year": {
            str(key): excluded_by_year[key] for key in sorted(excluded_by_year)
        },
        "county_records_by_year": {
            str(key): int(value)
            for key, value in selected.groupby("harvest_year", sort=True).size().items()
        },
        "reported_records_by_year": {
            str(key): int(value)
            for key, value in selected.groupby("harvest_year", sort=True)["yield_reported"].sum().items()
        },
        "total_county_records": len(selected),
        "reported_county_records": int(selected["yield_reported"].sum()),
        "suppressed_or_nonnumeric_county_records": int((~selected["yield_reported"]).sum()),
    }
    return selected, audit


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("inputs", type=Path, nargs="+")
    parser.add_argument("--commodity", required=True)
    parser.add_argument("--unit", required=True)
    parser.add_argument("--util-practice", required=True)
    parser.add_argument("--year-start", type=int, required=True)
    parser.add_argument("--year-end", type=int, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--audit-out", type=Path, required=True)
    args = parser.parse_args()
    output, audit = prepare(
        args.inputs,
        commodity=args.commodity,
        unit=args.unit,
        utilization_practice=args.util_practice,
        year_start=args.year_start,
        year_end=args.year_end,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.audit_out.parent.mkdir(parents=True, exist_ok=True)
    output.to_parquet(args.out, index=False)
    args.audit_out.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        f"wrote {len(output)} real-county rows for {args.year_start}-{args.year_end}; "
        f"reported={audit['reported_county_records']}; "
        f"suppressed_or_nonnumeric={audit['suppressed_or_nonnumeric_county_records']}"
    )


if __name__ == "__main__":
    main()
