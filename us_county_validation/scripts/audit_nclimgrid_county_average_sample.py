#!/usr/bin/env python3
"""Audit one official nClimGrid-Daily county-area-average month.

This is an outcome-free source preflight. It does not replace the registered
polygon-weight route or authorize response estimation, damages, or SCC use.
"""

from __future__ import annotations

import argparse
import calendar
import csv
import hashlib
import json
from pathlib import Path

import numpy as np


SCHEMA = "us_nclimgrid_county_average_sample_audit_v1"
VARIABLES = ("PRCP", "TAVG", "TMIN", "TMAX")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_crosswalk(path: Path) -> dict[str, str]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    require(rows and set(rows[0]) == {"state_name", "postal_code", "NCEI_code", "FIPS_code"},
            "NCEI/FIPS state crosswalk schema changed")
    mapping = {row["NCEI_code"].zfill(2): row["FIPS_code"].zfill(2) for row in rows}
    require(len(mapping) == len(rows), "NCEI/FIPS state crosswalk duplicates an NCEI code")
    require(all(len(key) == 2 and key.isdigit() and len(value) == 2 and value.isdigit()
                for key, value in mapping.items()), "NCEI/FIPS state codes are invalid")
    require(len(set(mapping.values())) == len(mapping), "NCEI/FIPS state mapping is not one-to-one")
    return mapping


def load_area_average(path: Path, expected_variable: str, state_map: dict[str, str]) -> dict[str, object]:
    records: dict[str, dict[str, object]] = {}
    expected_year_month: tuple[int, int] | None = None
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.reader(handle):
            require(len(row) == 37, f"{expected_variable} county row width changed")
            region, source_code, name, year_text, month_text, variable, *day_text = row
            require(region == "cty" and variable == expected_variable, f"{expected_variable} identity changed")
            require(len(source_code) == 5 and source_code.isdigit(), "NCEI county code is invalid")
            require(source_code[:2] in state_map, "NCEI county state code lacks a FIPS mapping")
            year, month = int(year_text), int(month_text)
            identity = (year, month)
            if expected_year_month is None:
                expected_year_month = identity
            require(identity == expected_year_month, f"{expected_variable} mixes year-months")
            days = calendar.monthrange(year, month)[1]
            values = np.asarray([float(value) for value in day_text[:days]], dtype=float)
            require(np.isfinite(values).all() and not np.isclose(values, -999.99).any(),
                    f"{expected_variable} has missing/nonfinite real-day values")
            require(all(np.isclose(float(value), -999.99) for value in day_text[days:]),
                    f"{expected_variable} nonexistent-day sentinels changed")
            fips = state_map[source_code[:2]] + source_code[2:]
            require(fips not in records, f"{expected_variable} duplicates mapped FIPS {fips}")
            records[fips] = {"source_code": source_code, "name": name, "values": values}
    require(records and expected_year_month is not None, f"{expected_variable} file is empty")
    return {"records": records, "year_month": expected_year_month}


def audit(inputs: dict[str, Path], version_path: Path, crosswalk_path: Path, target_fips: str) -> dict[str, object]:
    require(set(inputs) == set(VARIABLES), "exact PRCP/TAVG/TMIN/TMAX inputs are required")
    require(len(target_fips) == 5 and target_fips.isdigit(), "target FIPS must be five digits")
    state_map = load_crosswalk(crosswalk_path)
    loaded = {variable: load_area_average(inputs[variable], variable, state_map) for variable in VARIABLES}
    identities = {value["year_month"] for value in loaded.values()}
    require(len(identities) == 1, "county averages do not share one year-month")
    key_sets = {variable: set(value["records"]) for variable, value in loaded.items()}
    require(all(keys == key_sets["PRCP"] for keys in key_sets.values()), "county support differs by variable")
    require(target_fips in key_sets["PRCP"], "target county is absent")
    target = {variable: loaded[variable]["records"][target_fips] for variable in VARIABLES}
    source_codes = {str(value["source_code"]) for value in target.values()}
    names = {str(value["name"]) for value in target.values()}
    require(len(source_codes) == 1 and len(names) == 1, "target county identity differs by variable")
    tavg = np.asarray(target["TAVG"]["values"], dtype=float)
    tmin = np.asarray(target["TMIN"]["values"], dtype=float)
    tmax = np.asarray(target["TMAX"]["values"], dtype=float)
    require((tmin <= tavg).all() and (tavg <= tmax).all(), "target temperature ordering failed")
    midpoint_error = np.abs(tavg - (tmin + tmax) / 2)
    require(float(midpoint_error.max()) <= 0.011, "target rounded TAVG midpoint identity failed")
    year, month = next(iter(identities))
    source_root = f"https://www.ncei.noaa.gov/data/nclimgrid-daily/access/averages/{year}"
    return {
        "schema": SCHEMA,
        "status": "passed_source_sample_not_registered_route_replacement",
        "source_product": "NOAA NCEI nClimGrid-Daily v1.0.0 county area averages",
        "year": year,
        "month": month,
        "county_rows_per_variable": len(key_sets["PRCP"]),
        "identical_county_support_across_variables": True,
        "target_fips": target_fips,
        "target_ncei_county_code": next(iter(source_codes)),
        "target_name": next(iter(names)),
        "target_real_days": calendar.monthrange(year, month)[1],
        "target_missing_real_day_values": 0,
        "target_precipitation_sum_mm": float(np.asarray(target["PRCP"]["values"], dtype=float).sum()),
        "target_temperature_midpoint_max_abs_error_c": float(midpoint_error.max()),
        "numeric_ncei_to_fips_state_mapping_only": True,
        "source_urls": {
            variable.lower(): f"{source_root}/{variable.lower()}-{year}{month:02d}-cty-scaled.csv"
            for variable in VARIABLES
        } | {
            "version": f"{source_root}/ncdd-{year}{month:02d}-version.txt",
            "state_crosswalk": "https://www.ncei.noaa.gov/data/nclimgrid-daily/doc/us-state-codes_ncei-to-fips.csv",
            "user_guide": "https://www.ncei.noaa.gov/data/nclimgrid-daily/doc/nclimgrid-daily_v1-0-0_user-guide.pdf",
        },
        "inputs": {
            variable.lower(): {"bytes": path.stat().st_size, "sha256": sha256(path)}
            for variable, path in inputs.items()
        } | {
            "version": {"bytes": version_path.stat().st_size, "sha256": sha256(version_path),
                        "text": version_path.read_text(encoding="utf-8").strip()},
            "state_crosswalk": {"bytes": crosswalk_path.stat().st_size, "sha256": sha256(crosswalk_path)},
        },
        "registered_polygon_weight_route_replaced": False,
        "historical_boundary_vintage_validated": False,
        "response_damage_or_scc_authorized": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    for variable in VARIABLES:
        parser.add_argument(f"--{variable.lower()}", type=Path, required=True)
    parser.add_argument("--version", type=Path, required=True)
    parser.add_argument("--state-crosswalk", type=Path, required=True)
    parser.add_argument("--target-fips", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = audit(
        {variable: getattr(args, variable.lower()) for variable in VARIABLES},
        args.version,
        args.state_crosswalk,
        args.target_fips,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.out.with_suffix(args.out.suffix + ".partial")
    temporary.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(args.out)
    print(f"validated {result['county_rows_per_variable']} county rows; target={result['target_fips']}")


if __name__ == "__main__":
    main()
