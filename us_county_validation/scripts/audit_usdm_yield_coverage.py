#!/usr/bin/env python3
"""Audit county-year overlap between prepared NASS yields and USDM seasons.

This is a descriptive coverage gate. It requires an explicit NASS commodity
to exposure-crop mapping, preserves suppressed outcomes in the denominator,
and emits counts only. It does not estimate a crop response or authorize an
SCC input.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


YIELD_COLUMNS = {
    "county_geoid",
    "harvest_year",
    "commodity",
    "yield_unit",
    "yield_reported",
}
EXPOSURE_COLUMNS = {
    "county_geoid",
    "harvest_year",
    "crop",
    "analysis_role",
    "scc_authorized",
}
KEYS = ["county_geoid", "harvest_year"]


def read_table(path: str) -> pd.DataFrame:
    source = Path(path)
    if source.suffix.lower() in {".parquet", ".pq"}:
        return pd.read_parquet(source)
    return pd.read_csv(source, dtype="string")


def normalize_keys(frame: pd.DataFrame, source_name: str) -> pd.DataFrame:
    frame = frame.copy()
    frame["county_geoid"] = frame.county_geoid.astype("string")
    if (
        frame.county_geoid.isna().any()
        or frame.county_geoid.str.fullmatch(r"\d{5}").ne(True).any()
    ):
        raise ValueError(f"{source_name} county_geoid must contain five-digit GEOIDs")
    years = pd.to_numeric(frame.harvest_year, errors="coerce")
    if years.isna().any() or (years % 1 != 0).any():
        raise ValueError(f"{source_name} harvest_year must contain integers")
    frame["harvest_year"] = years.astype("int64")
    return frame


def parse_boolean(series: pd.Series, label: str) -> pd.Series:
    if pd.api.types.is_bool_dtype(series.dtype):
        if series.isna().any():
            raise ValueError(f"{label} contains missing values")
        return series.astype(bool)
    normalized = series.astype("string").str.strip().str.lower()
    mapping = {"true": True, "false": False, "1": True, "0": False}
    parsed = normalized.map(mapping)
    if parsed.isna().any():
        raise ValueError(f"{label} must contain only true/false values")
    return parsed.astype(bool)


def validate_yields(frame: pd.DataFrame, commodity: str) -> tuple[pd.DataFrame, str]:
    if missing := YIELD_COLUMNS - set(frame.columns):
        raise ValueError(f"Prepared NASS yields missing columns {sorted(missing)}")
    if frame.empty:
        raise ValueError("Prepared NASS yields are empty")
    frame = normalize_keys(frame, "NASS yield")
    frame["commodity"] = frame.commodity.astype("string").str.strip().str.upper()
    requested = commodity.strip().upper()
    selected = frame.loc[frame.commodity.eq(requested)].copy()
    if selected.empty:
        raise ValueError(f"No prepared NASS rows match commodity {requested}")
    selected["yield_unit"] = selected.yield_unit.astype("string").str.strip()
    if selected.yield_unit.isna().any() or selected.yield_unit.eq("").any():
        raise ValueError("Prepared NASS yield_unit must be nonblank")
    units = sorted(selected.yield_unit.unique())
    if len(units) != 1:
        raise ValueError(
            "Requested NASS commodity has multiple yield units; standardize or narrow before audit"
        )
    selected["yield_reported"] = parse_boolean(selected.yield_reported, "yield_reported")
    if selected.duplicated(KEYS).any():
        raise ValueError("Duplicate NASS county-year rows for requested commodity")
    return selected, units[0]


def validate_exposures(frame: pd.DataFrame, crop: str) -> pd.DataFrame:
    if missing := EXPOSURE_COLUMNS - set(frame.columns):
        raise ValueError(f"Prepared USDM seasons missing columns {sorted(missing)}")
    if frame.empty:
        raise ValueError("Prepared USDM seasons are empty")
    frame = normalize_keys(frame, "USDM exposure")
    frame["crop"] = frame.crop.astype("string").str.strip().str.lower()
    requested = crop.strip().lower()
    selected = frame.loc[frame.crop.eq(requested)].copy()
    if selected.empty:
        raise ValueError(f"No prepared USDM rows match crop {requested}")
    roles = selected.analysis_role.astype("string").str.strip()
    if roles.isna().any() or roles.ne("historical_county_validation_only").any():
        raise ValueError("USDM exposure analysis_role violates the validation-only boundary")
    authorized = parse_boolean(selected.scc_authorized, "scc_authorized")
    if authorized.any():
        raise ValueError("USDM exposure rows must not be SCC-authorized")
    if selected.duplicated(KEYS).any():
        raise ValueError("Duplicate USDM county-year rows for requested crop")
    return selected


def summarize_coverage(yields: pd.DataFrame, exposures: pd.DataFrame) -> pd.DataFrame:
    joined = yields[KEYS + ["yield_reported"]].merge(
        exposures[KEYS], on=KEYS, how="outer", indicator=True, validate="one_to_one"
    )
    joined["has_yield"] = joined._merge.ne("right_only")
    joined["has_exposure"] = joined._merge.ne("left_only")
    joined["yield_reported"] = joined.yield_reported.fillna(False).astype(bool)

    def one_summary(subset: pd.DataFrame, scope: str, year: int | None) -> dict[str, object]:
        has_yield = subset.has_yield
        has_exposure = subset.has_exposure
        matched = has_yield & has_exposure
        reported = has_yield & subset.yield_reported
        counts = {
            "yield_rows": int(has_yield.sum()),
            "reported_yield_rows": int(reported.sum()),
            "exposure_rows": int(has_exposure.sum()),
            "matched_rows": int(matched.sum()),
            "matched_reported_yield_rows": int((matched & reported).sum()),
            "yield_only_rows": int((has_yield & ~has_exposure).sum()),
            "exposure_only_rows": int((has_exposure & ~has_yield).sum()),
        }

        def share(numerator: int, denominator: int) -> float | None:
            return numerator / denominator if denominator else None

        return {
            "coverage_scope": scope,
            "harvest_year": year,
            **counts,
            "yield_match_share": share(counts["matched_rows"], counts["yield_rows"]),
            "reported_yield_match_share": share(
                counts["matched_reported_yield_rows"], counts["reported_yield_rows"]
            ),
            "exposure_match_share": share(counts["matched_rows"], counts["exposure_rows"]),
            "analysis_role": "historical_county_validation_only",
            "scc_authorized": False,
        }

    rows = [one_summary(joined, "overall", None)]
    rows.extend(
        one_summary(group, "harvest_year", int(year))
        for year, group in joined.groupby("harvest_year", sort=True, observed=True)
    )
    result = pd.DataFrame(rows)
    result["harvest_year"] = result.harvest_year.astype("Int64")
    return result


def write_table(frame: pd.DataFrame, path: str) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.suffix.lower() in {".parquet", ".pq"}:
        frame.to_parquet(destination, index=False)
    else:
        frame.to_csv(destination, index=False)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--yields", required=True, help="prepared NASS county-yield table")
    parser.add_argument("--exposures", required=True, help="prepared USDM crop-season table")
    parser.add_argument("--commodity", required=True, help="exact NASS commodity label")
    parser.add_argument("--crop", required=True, help="exact crop label in the USDM season table")
    parser.add_argument("--out", required=True, help="coverage summary CSV or Parquet")
    args = parser.parse_args()

    yields, yield_unit = validate_yields(read_table(args.yields), args.commodity)
    exposures = validate_exposures(read_table(args.exposures), args.crop)
    result = summarize_coverage(yields, exposures)
    result.insert(2, "commodity", args.commodity.strip().upper())
    result.insert(3, "crop", args.crop.strip().lower())
    result.insert(4, "yield_unit", yield_unit)
    write_table(result, args.out)
    overall = result.iloc[0]
    print(
        f"wrote coverage audit; matched={overall.matched_rows}/{overall.yield_rows} yield rows; "
        f"reported matched={overall.matched_reported_yield_rows}/"
        f"{overall.reported_yield_rows}"
    )


if __name__ == "__main__":
    main()
