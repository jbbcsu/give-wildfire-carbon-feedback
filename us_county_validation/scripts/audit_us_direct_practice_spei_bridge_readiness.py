#!/usr/bin/env python3
"""Audit exact county coverage of existing historical/future SPEI cells without outcomes."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
import tomllib

import numpy as np
import pandas as pd
import shapefile
from pyproj import Transformer
from shapely.geometry import box, shape
from shapely.ops import transform
from shapely.strtree import STRtree

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from summarize_isimip3b_late_drought_crop_windows import frozen_support  # noqa: E402

ALLOWED_PANEL_COLUMNS = [
    "county_geoid", "state", "outcome_crop", "harvest_year", "irrigation_practice",
    "feature_construction_eligible", "season_start", "season_end", "calendar_source_id",
    "calendar_vintage", "calendar_boundary_rule", "stage_definition",
]


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def native_indices(latitude: float, longitude_360: float) -> tuple[int, int]:
    longitude = longitude_360 if longitude_360 < 180 else longitude_360 - 360
    lat_index = int(round((89.75 - latitude) / 0.5))
    lon_index = int(round((longitude + 179.75) / 0.5))
    require(math.isclose(89.75 - 0.5 * lat_index, latitude, abs_tol=1e-10), "latitude is off ISIMIP grid")
    require(math.isclose((-179.75 + 0.5 * lon_index) % 360, longitude_360, abs_tol=1e-10), "longitude is off ISIMIP grid")
    return lat_index, lon_index


def validate_contract(contract: dict) -> None:
    auth = contract["authorization"]
    require(not any(auth.values()), "all scientific and outcome gates must remain closed")
    require(contract["decision"]["moisture_family_rule"] == "SPEI_and_direct_rainfall_are_competing_families_and_must_not_be_stacked_or_added", "moisture-family rule changed")
    require(contract["geography"]["minimum_geometric_coverage"] == 0.999, "coverage gate changed")


def load_key_only_sample(contract: dict) -> pd.DataFrame:
    sample = contract["sample"]
    path = ROOT / sample["panel"]
    require(digest(path) == sample["panel_sha256"], "direct-practice panel hash changed")
    require(not set(sample["outcome_columns_forbidden"]) & set(ALLOWED_PANEL_COLUMNS), "outcome column entered allowed projection")
    frame = pd.read_parquet(path, columns=ALLOWED_PANEL_COLUMNS)
    frame = frame.loc[
        frame.outcome_crop.eq(sample["crop"])
        & frame.irrigation_practice.eq(sample["practice"])
        & frame.harvest_year.between(sample["year_min"], sample["year_max"])
    ].copy()
    require(len(frame) == sample["expected_rows"], "sample row count changed")
    require(frame.county_geoid.nunique() == sample["expected_counties"] and frame.state.nunique() == sample["expected_states"], "sample geography changed")
    require(frame.feature_construction_eligible.all(), "ineligible sample row")
    calendar = contract["calendar"]
    require(set(frame.calendar_source_id) == {calendar["source_id"]}, "calendar source changed")
    require(set(frame.calendar_vintage) == {calendar["vintage"]}, "calendar vintage changed")
    require(set(frame.calendar_boundary_rule) == {calendar["boundary_rule"]}, "calendar boundary rule changed")
    require(set(frame.stage_definition) == {calendar["stage_definition"]}, "stage rule changed")
    require(frame.season_start.notna().all() and frame.season_end.notna().all(), "missing NASS calendar boundary")
    require((frame.season_start.dt.year == frame.harvest_year).all(), "season start is not in harvest year")
    require((frame.season_end.dt.year == frame.harvest_year).all(), "season end is not in harvest year")
    require((frame.season_end > frame.season_start).all(), "non-positive NASS season")
    month_day = frame.assign(start_mmdd=frame.season_start.dt.strftime("%m-%d"),
                             end_mmdd=frame.season_end.dt.strftime("%m-%d"))
    require((month_day.groupby("state")[["start_mmdd", "end_mmdd"]].nunique() == 1).all().all(),
            "NASS state calendar is not fixed across sample years")
    return frame


def load_counties(path: Path, geoids: set[str]) -> list[tuple[str, object]]:
    reader = shapefile.Reader(str(path))
    fields = [field[0] for field in reader.fields[1:]]
    index = fields.index("GEOID")
    counties = []
    for item in reader.iterShapeRecords():
        geoid = str(item.record[index])
        if geoid in geoids:
            counties.append((geoid, shape(item.shape.__geo_interface__)))
    require(len(counties) == len(geoids), "TIGER does not contain every sample county")
    return sorted(counties)


def audit_coverage(counties: list[tuple[str, object]], available: set[tuple[float, float]], threshold: float) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    project = Transformer.from_crs("EPSG:4326", "EPSG:5070", always_xy=True).transform
    minimum_lon = min(geometry.bounds[0] for _, geometry in counties)
    minimum_lat = min(geometry.bounds[1] for _, geometry in counties)
    maximum_lon = max(geometry.bounds[2] for _, geometry in counties)
    maximum_lat = max(geometry.bounds[3] for _, geometry in counties)
    latitudes = np.arange(np.floor((minimum_lat - 0.25) * 2) / 2 + 0.25, np.ceil((maximum_lat + 0.25) * 2) / 2, 0.5)
    longitudes = np.arange(np.floor((minimum_lon - 0.25) * 2) / 2 + 0.25, np.ceil((maximum_lon + 0.25) * 2) / 2, 0.5)
    grid_geometries = []
    centers = []
    for latitude in latitudes:
        for longitude in longitudes:
            grid_geometries.append(transform(project, box(longitude - 0.25, latitude - 0.25, longitude + 0.25, latitude + 0.25)))
            centers.append((round(float(latitude), 2), round(float(longitude % 360), 2)))
    tree = STRtree(grid_geometries)
    coverage_rows = []
    weight_rows = []
    missing_rows = []
    for geoid, geographic in counties:
        geometry = transform(project, geographic)
        county_area = float(geometry.area)
        intersections = []
        for grid_index in tree.query(geometry, predicate="intersects"):
            area = float(geometry.intersection(grid_geometries[int(grid_index)]).area)
            if area <= 1e-6:
                continue
            latitude, longitude_360 = centers[int(grid_index)]
            intersections.append((latitude, longitude_360, area))
        covered_area = math.fsum(area for latitude, longitude, area in intersections if (latitude, longitude) in available)
        coverage = covered_area / county_area
        passed = coverage >= threshold
        coverage_rows.append({"county_geoid": geoid, "county_area_m2": county_area,
                              "available_intersection_area_m2": covered_area, "coverage_fraction": coverage,
                              "intersecting_grid_cells": len(intersections),
                              "available_grid_cells": sum((lat, lon) in available for lat, lon, _ in intersections),
                              "passes_0_999_gate": passed})
        for latitude, longitude_360, area in intersections:
            lat_index, lon_index = native_indices(latitude, longitude_360)
            if (latitude, longitude_360) in available:
                weight_rows.append({"county_geoid": geoid, "latitude": latitude, "longitude_360": longitude_360,
                                    "native_lat_index": lat_index, "native_lon_index": lon_index,
                                    "intersection_area_m2": area, "spatial_weight_within_available": area / covered_area,
                                    "county_coverage_fraction": coverage, "county_passes_gate": passed})
            else:
                missing_rows.append({"county_geoid": geoid, "latitude": latitude, "longitude_360": longitude_360,
                                     "native_lat_index": lat_index, "native_lon_index": lon_index,
                                     "missing_intersection_area_m2": area, "missing_county_area_fraction": area / county_area,
                                     "county_coverage_fraction": coverage, "county_passes_gate": passed})
    return pd.DataFrame(coverage_rows).sort_values("county_geoid"), pd.DataFrame(weight_rows).sort_values(["county_geoid", "native_lat_index", "native_lon_index"]), pd.DataFrame(missing_rows).sort_values(["county_geoid", "native_lat_index", "native_lon_index"])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "config/us_direct_practice_spei_bridge_readiness_v1.toml")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    config_path = args.config if args.config.is_absolute() else ROOT / args.config
    output_dir = args.output_dir if args.output_dir.is_absolute() else ROOT / args.output_dir
    require(not output_dir.exists(), "fresh output directory required")
    contract = tomllib.loads(config_path.read_text()); validate_contract(contract)
    sample = load_key_only_sample(contract)
    historical = contract["historical_spei"]
    manifest_path, validation_path = ROOT / historical["candidate_manifest"], ROOT / historical["candidate_validation"]
    require(digest(manifest_path) == historical["candidate_manifest_sha256"], "historical manifest changed")
    require(digest(validation_path) == historical["candidate_validation_sha256"], "historical validation changed")
    validation = json.loads(validation_path.read_text())
    require(validation["status"] == "passed" and validation["cells"] == historical["cells"] and validation["months"] == historical["months"], "historical candidate validation failed")
    future_evidence_path = ROOT / contract["future_spei"]["evidence"]
    require(digest(future_evidence_path) == contract["future_spei"]["evidence_sha256"], "future evidence changed")
    future_evidence = json.loads(future_evidence_path.read_text())
    require(future_evidence["gates"]["stage1_scenario_exposure"] and not future_evidence["gates"]["bridge_to_nass_response"], "future evidence gate changed")
    future = contract["future_spei"]
    case_records = []
    for model in future["models"]:
        for scenario in future["scenarios"]:
            directory = ROOT / future["pair_root"] / f"{model}_{scenario}"
            result_path, pair_validation_path = directory / "result.json", directory / "validation.json"
            pair_result, pair_validation = json.loads(result_path.read_text()), json.loads(pair_validation_path.read_text())
            require(pair_result["schema"] == "isimip3b_late_drought_pair_result_v1", "future pair schema changed")
            require(pair_result["esm"] == model and pair_result["scenario"] == scenario, "future case identity changed")
            require(pair_result["support_cells"] == historical["cells"], "future case support size changed")
            require(pair_result["fit_manifest"]["sha256"] == historical["candidate_manifest_sha256"], "future case support binding changed")
            require(pair_result["daily_audit"]["support_missing_triplets"] == 0, "future case has missing support")
            require(pair_validation["status"] == "passed" and pair_validation["pair_result_sha256"] == digest(result_path), "future case validation failed")
            require(pair_validation["output_sha256"] == pair_result["output"]["sha256"], "future pair output binding changed")
            require(pair_validation["gates"]["future_drought_exposure"] and not pair_validation["gates"]["yield_response"], "future pair gates changed")
            case_records.append({"model": model, "scenario": scenario, "result_sha256": digest(result_path),
                                 "validation_sha256": digest(pair_validation_path), "support_cells": pair_result["support_cells"]})
    require(len(case_records) == future["expected_cases"], "future case count changed")
    geography = contract["geography"]
    shapefile_path = ROOT / geography["tiger_shapefile"]
    for suffix, key in ((".shp", "tiger_shp_sha256"), (".shx", "tiger_shx_sha256"), (".dbf", "tiger_dbf_sha256"), (".prj", "tiger_prj_sha256")):
        require(digest(shapefile_path.with_suffix(suffix)) == geography[key], f"TIGER {suffix} changed")
    support = frozen_support().drop_duplicates("cell_id")
    require(len(support) == historical["cells"], "candidate cell inventory changed")
    available = set(zip(support.lat.round(2), support.lon_360.round(2)))
    counties = load_counties(shapefile_path, set(sample.county_geoid.astype(str)))
    coverage, weights, missing = audit_coverage(counties, available, geography["minimum_geometric_coverage"])
    failing = coverage.loc[~coverage.passes_0_999_gate]
    missing_for_failures = missing.loc[missing.county_geoid.isin(failing.county_geoid)]
    unique_missing = missing_for_failures[["latitude", "longitude_360", "native_lat_index", "native_lon_index"]].drop_duplicates().sort_values(["native_lat_index", "native_lon_index"])
    all_pass = len(failing) == 0
    require(not all_pass, "exact support unexpectedly passed; separate scientific review required")
    calendar_windows = []
    for state, group in sample.groupby("state", sort=True):
        calendar_windows.append({"state": state, "start_mmdd": group.season_start.iloc[0].strftime("%m-%d"),
                                 "end_mmdd": group.season_end.iloc[0].strftime("%m-%d"),
                                 "rows": len(group)})
    output_dir.mkdir(parents=True)
    coverage.to_csv(output_dir / "county_coverage.csv", index=False)
    weights.to_parquet(output_dir / "available_cell_weights.parquet", index=False, compression="zstd")
    missing.to_csv(output_dir / "missing_cell_intersections.csv", index=False)
    unique_missing.to_csv(output_dir / "unique_missing_cells_for_failed_counties.csv", index=False)
    result = {
        "schema": "us_direct_practice_spei_bridge_readiness_v1", "status": "blocked_exact_361_county_support_incomplete",
        "role": "outcome_blind_source_and_geographic_readiness_audit_no_panel_no_fit",
        "contract": {"path": str(config_path.relative_to(ROOT)), "sha256": digest(config_path)},
        "sample": {"rows": len(sample), "counties": sample.county_geoid.nunique(), "states": sample.state.nunique(),
                   "year_min": int(sample.harvest_year.min()), "year_max": int(sample.harvest_year.max()),
                   "columns_read": ALLOWED_PANEL_COLUMNS, "outcome_columns_read": [],
                   "calendar_windows": calendar_windows},
        "historical_candidate": {"cells": len(support), "months": validation["months"], "manifest_sha256": digest(manifest_path),
                                 "validation_sha256": digest(validation_path), "all_candidate_cells_validated": True},
        "future_candidate": {"cases": len(case_records), "cells_per_case": historical["cells"],
                             "all_cases_independently_validated": True, "case_records": case_records},
        "coverage": {"threshold": geography["minimum_geometric_coverage"], "passing_counties": int(coverage.passes_0_999_gate.sum()),
                     "failing_counties": len(failing), "minimum": float(coverage.coverage_fraction.min()),
                     "median": float(coverage.coverage_fraction.median()), "unique_missing_cells_for_failed_counties": len(unique_missing),
                     "failing_county_records": failing.sort_values("coverage_fraction").to_dict("records"),
                     "unique_missing_cells": unique_missing.to_dict("records")},
        "outputs": {},
        "gates": {"historical_exact_361_county_support": all_pass, "future_exact_361_county_support": all_pass,
                  "historical_county_spei_panel": False, "future_county_spei_panel": False,
                  "bridge_to_nass_response": False, "fit_outcomes": False, "future_yield_projection": False,
                  "causal_claim": False, "damage": False, "scc": False},
        "blocker": "The validated historical and future SPEI cubes share the same sparse crop-cell footprint. Ten NASS counties fail the frozen 0.999 county-area coverage gate; the eleven missing native cells are absent from both eras. Historical raw GSWP3-W5E5 can regenerate them, but the evicted future tasmin/tasmax inputs must be reacquired and processed for the same cells before an exact-support bridge is possible.",
        "next_step": "Acquire/process the eleven listed native cells for historical observations and all fifteen future model-scenario cases, validate identical county weights and NASS calendar allocation, then build a 361-county SPEI-1/3/6 panel without reading outcomes.",
        "implementation": {"path": str(Path(__file__).resolve().relative_to(ROOT)), "sha256": digest(Path(__file__).resolve())},
    }
    for name in ("county_coverage.csv", "available_cell_weights.parquet", "missing_cell_intersections.csv", "unique_missing_cells_for_failed_counties.csv"):
        path = output_dir / name
        result["outputs"][name] = {"path": str(path.relative_to(ROOT)), "bytes": path.stat().st_size, "sha256": digest(path)}
    (output_dir / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": result["status"], "coverage": result["coverage"], "gates": result["gates"]}))


if __name__ == "__main__":
    main()
