#!/usr/bin/env python3
"""Independently validate the outcome-blind U.S. SPEI bridge audit receipt."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def check(condition: bool, message: str, checks: list[str]) -> None:
    if not condition:
        raise ValueError(message)
    checks.append(message)


def validate(result_path: Path, resource_path: Path) -> dict:
    checks: list[str] = []
    result = json.loads(result_path.read_text())
    resource = json.loads(resource_path.read_text())
    check(result["schema"] == "us_direct_practice_spei_bridge_readiness_v1", "schema", checks)
    check(result["status"] == "blocked_exact_361_county_support_incomplete", "fail-closed status", checks)
    check(result["role"] == "outcome_blind_source_and_geographic_readiness_audit_no_panel_no_fit", "outcome-blind role", checks)
    expected_windows = [
        {"state": "CO", "start_mmdd": "05-09", "end_mmdd": "10-26", "rows": 320},
        {"state": "DE", "start_mmdd": "05-08", "end_mmdd": "10-02", "rows": 12},
        {"state": "KS", "start_mmdd": "04-30", "end_mmdd": "10-02", "rows": 2059},
        {"state": "ND", "start_mmdd": "05-15", "end_mmdd": "10-29", "rows": 609},
        {"state": "NE", "start_mmdd": "05-06", "end_mmdd": "10-22", "rows": 3008},
        {"state": "NM", "start_mmdd": "04-30", "end_mmdd": "10-15", "rows": 30},
        {"state": "OK", "start_mmdd": "04-20", "end_mmdd": "09-18", "rows": 1},
        {"state": "SD", "start_mmdd": "05-14", "end_mmdd": "10-26", "rows": 784},
        {"state": "TX", "start_mmdd": "04-07", "end_mmdd": "09-05", "rows": 164},
        {"state": "WY", "start_mmdd": "05-12", "end_mmdd": "11-05", "rows": 26},
    ]
    expected_sample = {
        "columns_read": ["county_geoid", "state", "outcome_crop", "harvest_year", "irrigation_practice",
                         "feature_construction_eligible", "season_start", "season_end", "calendar_source_id",
                         "calendar_vintage", "calendar_boundary_rule", "stage_definition"],
        "counties": 361, "outcome_columns_read": [], "rows": 7013, "states": 10,
        "year_max": 2018, "year_min": 1981, "calendar_windows": expected_windows,
    }
    check(result["sample"] == expected_sample, "exact metadata-only sample and NASS calendars", checks)
    check(not any(result["gates"].values()), "all scientific gates closed", checks)
    check(resource["status"] == "completed" and resource["returncode"] == 0, "bounded job completed", checks)
    check(resource["sampled_peak_group_rss_bytes"] <= 512 * 2**20 and resource["max_mib"] == 512.0,
          "memory gate", checks)

    contract_path = ROOT / result["contract"]["path"]
    implementation_path = ROOT / result["implementation"]["path"]
    check(digest(contract_path) == result["contract"]["sha256"], "contract hash", checks)
    check(digest(implementation_path) == result["implementation"]["sha256"], "implementation hash", checks)

    resolved = {}
    for name, record in result["outputs"].items():
        path = ROOT / record["path"]
        check(path.stat().st_size == record["bytes"], f"{name} byte count", checks)
        check(digest(path) == record["sha256"], f"{name} hash", checks)
        resolved[name] = path

    coverage = pd.read_csv(resolved["county_coverage.csv"], dtype={"county_geoid": str})
    weights = pd.read_parquet(resolved["available_cell_weights.parquet"])
    weights["county_geoid"] = weights.county_geoid.astype(str).str.zfill(5)
    missing = pd.read_csv(resolved["missing_cell_intersections.csv"], dtype={"county_geoid": str})
    cells = pd.read_csv(resolved["unique_missing_cells_for_failed_counties.csv"])
    check(len(coverage) == coverage.county_geoid.nunique() == 361, "361 unique county coverage rows", checks)
    recomputed = coverage.available_intersection_area_m2 / coverage.county_area_m2
    check(float((recomputed - coverage.coverage_fraction).abs().max()) < 2e-15, "coverage arithmetic", checks)
    expected_pass = coverage.coverage_fraction.ge(0.999)
    check(expected_pass.equals(coverage.passes_0_999_gate), "coverage threshold decisions", checks)
    check(int(expected_pass.sum()) == result["coverage"]["passing_counties"] == 351, "passing county count", checks)
    check(int((~expected_pass).sum()) == result["coverage"]["failing_counties"] == 10, "failing county count", checks)
    check(math.isclose(float(coverage.coverage_fraction.min()), result["coverage"]["minimum"], abs_tol=1e-15),
          "minimum coverage", checks)

    area_by_county = weights.groupby("county_geoid", sort=False).intersection_area_m2.sum()
    coverage_indexed = coverage.set_index("county_geoid")
    aligned_area = coverage_indexed.loc[area_by_county.index, "available_intersection_area_m2"]
    check(float((area_by_county - aligned_area).abs().max()) < 1e-5, "available-area reconstruction", checks)
    weight_sums = weights.groupby("county_geoid", sort=False).spatial_weight_within_available.sum()
    check(float((weight_sums - 1.0).abs().max()) < 2e-15, "county weights normalize", checks)
    check(not weights.duplicated(["county_geoid", "native_lat_index", "native_lon_index"]).any(),
          "unique available county-cell records", checks)

    for frame, area_name in ((weights, "intersection_area_m2"), (missing, "missing_intersection_area_m2")):
        expected_lat = 89.75 - 0.5 * frame.native_lat_index
        expected_lon = (-179.75 + 0.5 * frame.native_lon_index) % 360
        check(float((frame.latitude - expected_lat).abs().max()) < 1e-12, f"{area_name} latitude indices", checks)
        check(float((frame.longitude_360 - expected_lon).abs().max()) < 1e-12, f"{area_name} longitude indices", checks)
        check((frame[area_name] > 0).all(), f"{area_name} positive", checks)

    failing_geoids = set(coverage.loc[~expected_pass, "county_geoid"])
    missing_failed = missing.loc[missing.county_geoid.isin(failing_geoids)]
    independent_cells = (missing_failed[["latitude", "longitude_360", "native_lat_index", "native_lon_index"]]
                         .drop_duplicates().sort_values(["native_lat_index", "native_lon_index"]).reset_index(drop=True))
    check(independent_cells.equals(cells.sort_values(["native_lat_index", "native_lon_index"]).reset_index(drop=True)),
          "failed-county missing-cell inventory", checks)
    check(len(cells) == result["coverage"]["unique_missing_cells_for_failed_counties"] == 11,
          "eleven unique missing cells", checks)
    check(set(failing_geoids) == {str(item["county_geoid"]).zfill(5) for item in result["coverage"]["failing_county_records"]},
          "failing county receipt records", checks)
    check(result["historical_candidate"] == {
        "all_candidate_cells_validated": True, "cells": 31208,
        "manifest_sha256": "459f6968685b1ec828a68b7dc0a4fb54a3c32096ccad5a2f8ef460d19f866b3e",
        "months": 468,
        "validation_sha256": "78fc1411d5e900b9c78af0fbdf096f66d9706216263e062eaa3e4eb9f140c97f",
    }, "historical candidate binding", checks)
    future = result["future_candidate"]
    check(future["cases"] == 15 and future["cells_per_case"] == 31208
          and future["all_cases_independently_validated"], "fifteen validated future support cases", checks)
    check(len({(item["model"], item["scenario"]) for item in future["case_records"]}) == 15,
          "unique future case identities", checks)
    for item in future["case_records"]:
        directory = ROOT / "data/interim/five_esm_late_drought_20260921" / f"{item['model']}_{item['scenario']}"
        check(digest(directory / "result.json") == item["result_sha256"],
              f"future result hash {item['model']} {item['scenario']}", checks)
        check(digest(directory / "validation.json") == item["validation_sha256"],
              f"future validation hash {item['model']} {item['scenario']}", checks)
        check(item["support_cells"] == 31208, f"future support count {item['model']} {item['scenario']}", checks)
    return {
        "schema": "us_direct_practice_spei_bridge_readiness_validation_v1",
        "status": "passed", "checks": len(checks),
        "result": {"path": str(result_path.relative_to(ROOT)), "sha256": digest(result_path)},
        "resource": {"path": str(resource_path.relative_to(ROOT)), "sha256": digest(resource_path),
                     "sampled_peak_group_rss_bytes": resource["sampled_peak_group_rss_bytes"]},
        "validated": {"counties": len(coverage), "passing_counties": int(expected_pass.sum()),
                      "failing_counties": int((~expected_pass).sum()), "unique_missing_cells": len(cells)},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--resource", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = validate(args.result.resolve(), args.resource.resolve())
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(text)
    print(text, end="")


if __name__ == "__main__":
    main()
