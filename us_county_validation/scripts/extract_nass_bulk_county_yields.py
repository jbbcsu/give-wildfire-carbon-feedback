#!/usr/bin/env python3
"""Stream a documented county-yield subset from a NASS Quick Stats bulk archive.

The raw dated archive is too large to decompress into an untracked temporary
file. This reader processes its tab-delimited gzip stream in chunks and emits
only a fully specified, one-row-per-county-year commodity yield extract. It
does not turn suppressed values into zero or label an outcome non-irrigated.

Defaults select the total/all-practice annual county-yield series. They are
deliberate filters, recorded in the output, and must be reviewed against the
archive's values before using the result in a panel.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

REQUIRED = {
    "year", "commodity_desc", "statisticcat_desc", "agg_level_desc",
    "state_ansi", "county_ansi", "value", "unit_desc", "domain_desc",
    "domaincat_desc", "prodn_practice_desc", "util_practice_desc",
    "reference_period_desc",
}
OUTPUT = [
    "harvest_year", "county_geoid", "commodity", "yield_unit",
    "yield_value_raw", "yield_value", "yield_reported", "nass_value_flag",
    "domain_desc", "domaincat_desc", "prodn_practice_desc",
    "util_practice_desc", "reference_period_desc",
]


def column_map(columns: list[str]) -> dict[str, str]:
    mapping = {column.lower(): column for column in columns}
    missing = REQUIRED - set(mapping)
    if missing:
        raise ValueError(f"NASS bulk archive missing required columns {sorted(missing)}")
    return mapping


def normalize_fips(series: pd.Series, width: int, label: str) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce")
    if numeric.isna().any() or (numeric % 1 != 0).any():
        raise ValueError(f"{label} contains missing or non-integer codes")
    upper = 10 ** width - 1
    if ((numeric < 0) | (numeric > upper)).any():
        raise ValueError(f"{label} has values outside {width}-digit range")
    return numeric.astype("int64").astype(str).str.zfill(width)


def equal(frame: pd.DataFrame, column: str, value: str) -> pd.Series:
    return frame[column].astype("string").str.strip().str.upper().eq(value.upper())


def extract(args: argparse.Namespace) -> pd.DataFrame:
    parts: list[pd.DataFrame] = []
    saw_columns = False
    reader = pd.read_csv(
        args.input, sep="\t", compression="infer", dtype="string",
        chunksize=args.chunksize, low_memory=False,
    )
    for chunk in reader:
        names = column_map(list(chunk.columns))
        saw_columns = True
        c = names.__getitem__
        years = pd.to_numeric(chunk[c("year")], errors="coerce")
        mask = (
            equal(chunk, c("commodity_desc"), args.commodity)
            & equal(chunk, c("statisticcat_desc"), "YIELD")
            & equal(chunk, c("agg_level_desc"), "COUNTY")
            & years.between(args.year_min, args.year_max)
            & equal(chunk, c("domain_desc"), args.domain)
            & equal(chunk, c("domaincat_desc"), args.domain_category)
            & equal(chunk, c("prodn_practice_desc"), args.production_practice)
            & equal(chunk, c("util_practice_desc"), args.utilization_practice)
            & equal(chunk, c("reference_period_desc"), args.reference_period)
        )
        selected = chunk.loc[mask].copy()
        if selected.empty:
            continue
        raw = selected[c("value")].astype("string").str.strip()
        result = pd.DataFrame({
            "harvest_year": pd.to_numeric(selected[c("year")], errors="raise").astype("int64"),
            "county_geoid": (
                normalize_fips(selected[c("state_ansi")], 2, "state_ansi")
                + normalize_fips(selected[c("county_ansi")], 3, "county_ansi")
            ),
            "commodity": selected[c("commodity_desc")].astype("string").str.strip().str.upper(),
            "yield_unit": selected[c("unit_desc")].astype("string").str.strip(),
            "yield_value_raw": raw,
            "yield_value": pd.to_numeric(
                raw.str.replace(",", "", regex=False), errors="coerce"
            ).astype("Float64"),
            "domain_desc": selected[c("domain_desc")].astype("string").str.strip(),
            "domaincat_desc": selected[c("domaincat_desc")].astype("string").str.strip(),
            "prodn_practice_desc": selected[c("prodn_practice_desc")].astype("string").str.strip(),
            "util_practice_desc": selected[c("util_practice_desc")].astype("string").str.strip(),
            "reference_period_desc": selected[c("reference_period_desc")].astype("string").str.strip(),
        })
        result["yield_reported"] = result.yield_value.notna()
        result["nass_value_flag"] = result.yield_value_raw.where(
            ~result.yield_reported, "reported"
        )
        parts.append(result[OUTPUT])
    if not saw_columns:
        raise ValueError("NASS archive has no readable header")
    if not parts:
        raise ValueError("No rows match the fully specified NASS filter")
    output = pd.concat(parts, ignore_index=True)
    keys = ["harvest_year", "county_geoid", "commodity", "yield_unit"]
    if output.duplicated(keys).any():
        examples = output.loc[output.duplicated(keys, keep=False), keys].head(5).to_dict("records")
        raise ValueError(f"Duplicate county-year yields after explicit filters: {examples}")
    if output.yield_unit.isna().any() or output.yield_unit.eq("").any():
        raise ValueError("NASS selected yield unit is blank")
    if output.yield_unit.nunique() != 1:
        raise ValueError("NASS selected rows have multiple yield units; choose a narrower series")
    return output.sort_values(keys).reset_index(drop=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="dated NASS Quick Stats .txt.gz archive")
    parser.add_argument("--commodity", required=True)
    parser.add_argument("--year-min", type=int, default=1981)
    parser.add_argument("--year-max", type=int, default=2024)
    parser.add_argument("--domain", default="TOTAL")
    parser.add_argument("--domain-category", default="NOT SPECIFIED")
    parser.add_argument("--production-practice", default="ALL PRODUCTION PRACTICES")
    parser.add_argument("--utilization-practice", default="ALL UTILIZATION PRACTICES")
    parser.add_argument("--reference-period", default="YEAR")
    parser.add_argument("--chunksize", type=int, default=250_000)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    if args.year_min > args.year_max or args.chunksize < 1:
        raise ValueError("year range and chunksize must be valid")
    result = extract(args)
    destination = Path(args.out)
    destination.parent.mkdir(parents=True, exist_ok=True)
    result.to_parquet(destination, index=False)
    print(
        f"wrote {len(result)} county-yield rows; counties={result.county_geoid.nunique()}; "
        f"reported_share={result.yield_reported.mean():.3f}; unit={result.yield_unit.iloc[0]}"
    )


if __name__ == "__main__":
    main()
