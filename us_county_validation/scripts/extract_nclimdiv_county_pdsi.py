#!/usr/bin/env python3
"""Extract Census-GEOID monthly PDSI rows from NOAA's internal county keys."""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from download_nclimdiv_county_pdsi import BULK_NAME, DEFAULT_PROVENANCE, load_pins, validate_bulk_schema, validate_local


# NOAA's reviewed county README assigns sequential internal codes in this
# order. The values below translate that table to Census STATEFP and USPS.
INTERNAL_STATE_TO_CENSUS = {
    "01": ("01", "AL"), "02": ("04", "AZ"), "03": ("05", "AR"),
    "04": ("06", "CA"), "05": ("08", "CO"), "06": ("09", "CT"),
    "07": ("10", "DE"), "08": ("12", "FL"), "09": ("13", "GA"),
    "10": ("16", "ID"), "11": ("17", "IL"), "12": ("18", "IN"),
    "13": ("19", "IA"), "14": ("20", "KS"), "15": ("21", "KY"),
    "16": ("22", "LA"), "17": ("23", "ME"), "18": ("24", "MD"),
    "19": ("25", "MA"), "20": ("26", "MI"), "21": ("27", "MN"),
    "22": ("28", "MS"), "23": ("29", "MO"), "24": ("30", "MT"),
    "25": ("31", "NE"), "26": ("32", "NV"), "27": ("33", "NH"),
    "28": ("34", "NJ"), "29": ("35", "NM"), "30": ("36", "NY"),
    "31": ("37", "NC"), "32": ("38", "ND"), "33": ("39", "OH"),
    "34": ("40", "OK"), "35": ("41", "OR"), "36": ("42", "PA"),
    "37": ("44", "RI"), "38": ("45", "SC"), "39": ("46", "SD"),
    "40": ("47", "TN"), "41": ("48", "TX"), "42": ("49", "UT"),
    "43": ("50", "VT"), "44": ("51", "VA"), "45": ("53", "WA"),
    "46": ("54", "WV"), "47": ("55", "WI"), "48": ("56", "WY"),
}
STATE_FIPS_TO_INTERNAL = {value[0]: key for key, value in INTERNAL_STATE_TO_CENSUS.items()}

OUTPUT_COLUMNS = [
    "county_geoid", "state_alpha", "state_fips", "county_fips", "date",
    "year", "month", "index_value", "drought_family", "index_name",
    "index_scale_months", "index_scale_role", "index_distribution",
    "index_source_id", "index_calibration_start_year", "index_calibration_end_year",
    "index_calibration_role", "source_role", "irrigation_in_index",
    "geography_crosswalk_role", "response_estimation_authorized", "scc_authorized",
]

INVENTORY_COLUMNS = {
    "county_geoid", "state", "boundary_source_id", "boundary_vintage",
    "historical_status", "crosswalk_source_id", "feature_construction_eligible",
    "scc_authorized",
}


def _parse_bool(series: pd.Series, label: str) -> pd.Series:
    if pd.api.types.is_bool_dtype(series):
        if series.isna().any():
            raise ValueError(f"{label} contains missing values")
        return series.astype(bool)
    values = series.astype("string").str.strip().str.lower()
    if values.isna().any() or (~values.isin(["true", "false"])).any():
        raise ValueError(f"{label} must contain only true/false")
    return values.eq("true")


def load_county_inventory(path: Path) -> pd.DataFrame:
    frame = pd.read_parquet(path) if path.suffix.lower() in {".parquet", ".pq"} else pd.read_csv(path, dtype="string")
    if missing := INVENTORY_COLUMNS - set(frame.columns):
        raise ValueError(f"county inventory lacks {sorted(missing)}")
    if frame.empty:
        raise ValueError("county inventory is empty")
    result = frame.copy()
    result["county_geoid"] = result.county_geoid.astype("string").str.strip()
    result["state"] = result.state.astype("string").str.strip().str.upper()
    if result.county_geoid.str.fullmatch(r"\d{5}").ne(True).any() or result.state.str.fullmatch(r"[A-Z]{2}").ne(True).any():
        raise ValueError("county inventory has malformed GEOID/state values")
    if result.duplicated("county_geoid").any():
        raise ValueError("county inventory contains duplicate GEOIDs")
    for column in [
        "boundary_source_id", "boundary_vintage", "historical_status", "crosswalk_source_id",
    ]:
        result[column] = result[column].astype("string").str.strip()
        if result[column].isna().any() or result[column].eq("").any():
            raise ValueError(f"county inventory {column} must be nonblank")
    result["feature_construction_eligible"] = _parse_bool(
        result.feature_construction_eligible, "county inventory feature flag"
    )
    result["scc_authorized"] = _parse_bool(result.scc_authorized, "county inventory SCC flag")
    if not result.feature_construction_eligible.all() or result.scc_authorized.any():
        raise ValueError("county inventory contains an ineligible or SCC-authorized row")
    allowed_status = {"stable", "explicit_crosswalk"}
    if (~result.historical_status.isin(allowed_status)).any():
        raise ValueError("county inventory contains an unresolved historical geography")
    explicit = result.historical_status.eq("explicit_crosswalk")
    if (explicit & result.crosswalk_source_id.eq("not_applicable")).any():
        raise ValueError("explicit county crosswalk rows require a named crosswalk source")
    expected_state = result.county_geoid.str[:2].map(
        {value[0]: value[1] for value in INTERNAL_STATE_TO_CENSUS.values()}
    )
    if expected_state.isna().any() or not expected_state.astype("string").eq(result.state).all():
        raise ValueError("county inventory GEOID/state values do not reconcile")
    return result.sort_values("county_geoid").reset_index(drop=True)


def requested_internal_keys(county_geoids: list[str]) -> dict[str, tuple[str, str, str]]:
    if not county_geoids:
        raise ValueError("at least one county_geoid from a validated inventory is required")
    result: dict[str, tuple[str, str, str]] = {}
    for geoid in county_geoids:
        if not isinstance(geoid, str) or not geoid.isdigit() or len(geoid) != 5:
            raise ValueError(f"county_geoid must be five digits: {geoid!r}")
        state_fips, county_fips = geoid[:2], geoid[2:]
        if state_fips not in STATE_FIPS_TO_INTERNAL:
            raise ValueError(f"county_geoid is outside the 48-state nClimDiv county domain: {geoid}")
        internal = STATE_FIPS_TO_INTERNAL[state_fips] + county_fips
        if internal in result:
            raise ValueError(f"duplicate requested county_geoid: {geoid}")
        state_alpha = INTERNAL_STATE_TO_CENSUS[internal[:2]][1]
        result[internal] = (geoid, state_fips, state_alpha)
    return result


def extract_rows(
    path: Path,
    year_start: int,
    year_end: int,
    county_geoids: list[str],
) -> pd.DataFrame:
    if year_end < year_start:
        raise ValueError("year_end must not precede year_start")
    targets = requested_internal_keys(county_geoids)
    rows: list[dict[str, object]] = []
    observed_internal: set[str] = set()
    with path.open("r", encoding="ascii", newline="") as stream:
        for raw in stream:
            if not raw.endswith("\n") or len(raw) != 99:
                raise ValueError("nClimDiv input differs from the exact 99-byte record contract")
            line = raw[:-1]
            internal, element, year = line[:5], line[5:7], int(line[7:11])
            if element != "05" or not year_start <= year <= year_end:
                continue
            if internal not in targets:
                continue
            internal_state, county_fips = internal[:2], internal[2:]
            if internal_state not in INTERNAL_STATE_TO_CENSUS:
                raise ValueError(f"unknown NOAA internal state code {internal_state}")
            state_fips, state_alpha = INTERNAL_STATE_TO_CENSUS[internal_state]
            geoid = state_fips + county_fips
            if targets[internal] != (geoid, state_fips, state_alpha):
                raise ValueError("NOAA internal state-to-Census GEOID crosswalk does not reconcile")
            observed_internal.add(internal)
            for month in range(1, 13):
                value = float(line[11 + 7 * (month - 1):18 + 7 * (month - 1)])
                if value == -99.99:
                    raise ValueError(f"requested period contains missing PDSI for {geoid} {year}-{month:02d}")
                if not np.isfinite(value):
                    raise ValueError("requested PDSI value is nonfinite")
                rows.append({
                    "county_geoid": geoid,
                    "state_alpha": state_alpha,
                    "state_fips": state_fips,
                    "county_fips": county_fips,
                    "date": pd.Timestamp(year=year, month=month, day=1),
                    "year": year,
                    "month": month,
                    "index_value": value,
                    "drought_family": "pdsi",
                    "index_name": "nclimdiv_county_pdsi",
                    "index_scale_months": 0,
                    "index_scale_role": "stateful_palmer_index_not_fixed_accumulation",
                    "index_distribution": "palmer_water_balance",
                    "index_source_id": "noaa_nclimdiv_county_pdsi_v1_0_0_20260806",
                    "index_calibration_start_year": 1931,
                    "index_calibration_end_year": 1990,
                    "index_calibration_role": "publisher_fixed_independent_of_crop_outcomes",
                    "source_role": "historical_county_benchmark_not_future_scc_input",
                    "irrigation_in_index": False,
                    "geography_crosswalk_role": "noaa_internal_state_code_to_census_statefp",
                    "response_estimation_authorized": False,
                    "scc_authorized": False,
                })
    if observed_internal != set(targets):
        missing = sorted(set(targets) - observed_internal)
        raise ValueError(f"requested county keys are absent from nClimDiv: {missing}")
    frame = pd.DataFrame(rows, columns=OUTPUT_COLUMNS)
    if frame.empty:
        raise ValueError("no PDSI rows matched the requested counties and years")
    keys = ["county_geoid", "year", "month"]
    if frame.duplicated(keys).any():
        raise ValueError("extracted PDSI contains duplicate county/year/month rows")
    expected = (year_end - year_start + 1) * 12
    if not frame.groupby("county_geoid", observed=True).size().eq(expected).all():
        raise ValueError("extracted PDSI does not have twelve months for every requested county-year")
    return frame.sort_values(keys).reset_index(drop=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default=f"data/raw/us_county/nclimdiv_pdsicy/{BULK_NAME}")
    parser.add_argument("--provenance-record", default=str(DEFAULT_PROVENANCE))
    parser.add_argument("--year-start", type=int, required=True)
    parser.add_argument("--year-end", type=int, required=True)
    parser.add_argument("--county-inventory", required=True)
    parser.add_argument(
        "--county-geoid", action="append",
        help="optional subset of the validated inventory; default is every inventory row",
    )
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    provenance_path = Path(args.provenance_record)
    _, pins = load_pins(provenance_path)
    bulk_pin = next(item for item in pins if item["name"] == BULK_NAME)
    input_path = Path(args.input)
    validate_local(input_path, bulk_pin)
    validation = bulk_pin.get("validation")
    if not isinstance(validation, dict):
        raise RuntimeError("nClimDiv bulk provenance lacks decoded validation expectations")
    validate_bulk_schema(input_path, validation)
    inventory = load_county_inventory(Path(args.county_inventory))
    requested = args.county_geoid or inventory.county_geoid.astype(str).tolist()
    missing_inventory = sorted(set(requested) - set(inventory.county_geoid.astype(str)))
    if missing_inventory:
        raise ValueError(f"requested counties are absent from the validated inventory: {missing_inventory}")
    frame = extract_rows(
        input_path,
        args.year_start,
        args.year_end,
        requested,
    )
    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(output, index=False)
    print(
        f"wrote {len(frame)} monthly PDSI rows for {frame.county_geoid.nunique()} counties; "
        "response_estimation_authorized=false; scc_authorized=false"
    )


if __name__ == "__main__":
    main()
