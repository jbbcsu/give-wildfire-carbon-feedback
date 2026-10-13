#!/usr/bin/env python3
"""Preregister a compact outcome-blind LOCA2 county-strata expansion."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import resource
import tomllib
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import shapefile


ROOT = Path(__file__).resolve().parents[2]
PANEL_COLUMNS = (
    "county_geoid", "state", "county_name", "outcome_crop", "harvest_year",
    "irrigation_practice", "irrigation_share", "outcome_value_eligible",
    "feature_construction_authorized",
)
CALENDAR_COLUMNS = (
    "state", "calendar_crop", "harvest_year", "season_start", "season_end",
    "calendar_source_id", "calendar_vintage", "calendar_role",
    "feature_construction_eligible",
)
FORBIDDEN_COLUMNS = {
    "yield_bu_acre", "yield_value", "yield_value_raw", "source_value_raw",
    "precip_mm", "tmean_c", "tmin_mean_c", "tmax_mean_c", "cdd_max_days",
    "rx1day_mm", "rx5day_mm",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def peak_rss_bytes() -> int:
    return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)


def haversine_km(first: tuple[float, float], second: tuple[float, float]) -> float:
    latitude_1, longitude_1 = map(math.radians, first)
    latitude_2, longitude_2 = map(math.radians, second)
    delta_latitude = latitude_2 - latitude_1
    delta_longitude = longitude_2 - longitude_1
    value = math.sin(delta_latitude / 2) ** 2 + math.cos(latitude_1) * math.cos(latitude_2) * math.sin(delta_longitude / 2) ** 2
    return 6371.0088 * 2 * math.atan2(math.sqrt(value), math.sqrt(1 - value))


def load_internal_points(path: Path) -> dict[str, dict]:
    reader = shapefile.Reader(str(path))
    fields = [item[0] for item in reader.fields[1:]]
    result = {}
    for record in reader.iterRecords():
        row = dict(zip(fields, record))
        geoid = str(row["GEOID"]).zfill(5)
        result[geoid] = {
            "latitude": float(row["INTPTLAT"]),
            "longitude": float(row["INTPTLON"]),
            "tiger_county_name": str(row["NAME"]),
            "state_fips": str(row["STATEFP"]).zfill(2),
        }
    return result


def load_weight_readiness(root: Path) -> tuple[dict[str, dict], str]:
    ready: dict[str, dict] = {}
    fingerprint = hashlib.sha256()
    for receipt_path in sorted(root.glob("county_geoid=*/receipt.json")):
        record = json.loads(receipt_path.read_text())
        geoid = str(record["county_geoid"]).zfill(5)
        output_path = Path(record["output_path"])
        if not output_path.is_absolute():
            output_path = ROOT / output_path
        valid = (
            record.get("schema") == "us_national_county_nclimgrid_weight_partition_v1"
            and float(record.get("coverage_fraction", 0)) >= 0.999
            and float(record.get("weather_valid_area_relative_to_declared_land", 0)) >= 0.95
            and int(record.get("positive_weather_cells", 0)) > 0
            and record.get("response_estimation_authorized") is False
            and record.get("scc_authorized") is False
            and output_path.is_file()
        )
        if not valid:
            continue
        receipt_sha256 = digest(receipt_path)
        fingerprint.update(f"{geoid}\t{receipt_sha256}\t{record['output_sha256']}\n".encode())
        ready[geoid] = {
            "receipt_path": str(receipt_path.relative_to(ROOT)),
            "receipt_sha256": receipt_sha256,
            "output_path": str(output_path.relative_to(ROOT)),
            "output_sha256": record["output_sha256"],
            "positive_weather_cells": int(record["positive_weather_cells"]),
            "coverage_fraction": float(record["coverage_fraction"]),
            "weather_valid_area_relative_to_declared_land": float(record["weather_valid_area_relative_to_declared_land"]),
        }
    return ready, fingerprint.hexdigest()


def build_candidates(config: dict) -> tuple[pd.DataFrame, dict]:
    require(not (FORBIDDEN_COLUMNS & set(PANEL_COLUMNS)), "panel read contract contains forbidden columns")
    require(not (FORBIDDEN_COLUMNS & set(CALENDAR_COLUMNS)), "calendar read contract contains forbidden columns")
    inputs = config["inputs"]
    selection = config["selection"]
    years = list(range(int(selection["year_min"]), int(selection["year_max"]) + 1))

    panel_path = ROOT / inputs["panel"]
    panel = pd.read_parquet(panel_path, columns=list(PANEL_COLUMNS))
    panel["county_geoid"] = panel.county_geoid.astype(str).str.zfill(5)
    panel = panel.loc[
        panel.outcome_crop.eq(selection["crop"])
        & panel.irrigation_practice.eq(selection["practice"])
        & panel.harvest_year.isin(years)
    ].copy()
    rows = []
    for geoid, county in panel.groupby("county_geoid", sort=True):
        if len(county) != len(years) or county.harvest_year.nunique() != len(years) or set(county.harvest_year) != set(years):
            continue
        if not county.outcome_value_eligible.all() or not county.feature_construction_authorized.all():
            continue
        if county.irrigation_share.isna().any() or not np.isfinite(county.irrigation_share).all():
            continue
        require(county.state.nunique() == 1 and county.county_name.nunique() == 1, f"county metadata vary: {geoid}")
        rows.append({
            "county_geoid": geoid,
            "state": county.state.iloc[0],
            "county_name": county.county_name.iloc[0],
            "irrigation_share_median": float(county.irrigation_share.median()),
            "irrigation_share_minimum": float(county.irrigation_share.min()),
            "irrigation_share_maximum": float(county.irrigation_share.max()),
            "support_years": int(county.harvest_year.nunique()),
        })
    candidates = pd.DataFrame(rows)

    geography_path = ROOT / inputs["geography_gate"]
    geography = pd.read_csv(
        geography_path,
        dtype={"county_geoid": str},
        usecols=["county_geoid", "geography_gate_status", "feature_construction_eligible"],
    )
    geography["county_geoid"] = geography.county_geoid.str.zfill(5)
    geography = geography.loc[
        geography.geography_gate_status.eq(selection["geography_status"])
        & geography.feature_construction_eligible.eq(True)
    ]
    candidates = candidates.merge(geography[["county_geoid", "geography_gate_status"]], on="county_geoid", how="inner", validate="one_to_one")

    calendar_path = ROOT / inputs["calendar"]
    calendar = pd.read_csv(calendar_path, usecols=list(CALENDAR_COLUMNS), parse_dates=["season_start", "season_end"])
    calendar = calendar.loc[
        calendar.calendar_crop.eq(selection["crop"])
        & calendar.calendar_role.eq(selection["calendar_role"])
        & calendar.harvest_year.isin(years)
        & calendar.feature_construction_eligible.eq(True)
    ].copy()
    calendar["start_month_day"] = calendar.season_start.dt.strftime("%m-%d")
    calendar["end_month_day"] = calendar.season_end.dt.strftime("%m-%d")
    calendar["start_doy"] = calendar.season_start.dt.dayofyear
    calendar["season_days"] = (calendar.season_end - calendar.season_start).dt.days + 1
    calendar_rows = []
    for state, state_calendar in calendar.groupby("state", sort=True):
        if len(state_calendar) != len(years) or set(state_calendar.harvest_year) != set(years):
            continue
        require(state_calendar.start_month_day.nunique() == 1, f"primary start varies: {state}")
        require(state_calendar.end_month_day.nunique() == 1, f"primary end varies: {state}")
        require(state_calendar.calendar_source_id.nunique() == 1, f"calendar source varies: {state}")
        calendar_rows.append({
            "state": state,
            "primary_start_month_day": state_calendar.start_month_day.iloc[0],
            "primary_end_month_day": state_calendar.end_month_day.iloc[0],
            "primary_start_doy": int(round(state_calendar.start_doy.median())),
            "primary_season_days": int(round(state_calendar.season_days.median())),
            "calendar_source_id": state_calendar.calendar_source_id.iloc[0],
            "calendar_vintage": str(state_calendar.calendar_vintage.iloc[0]),
        })
    candidates = candidates.merge(pd.DataFrame(calendar_rows), on="state", how="inner", validate="many_to_one")

    readiness_root = ROOT / inputs["nclimgrid_weight_root"]
    readiness, readiness_set_sha256 = load_weight_readiness(readiness_root)
    candidates = candidates.loc[candidates.county_geoid.isin(readiness)].copy()
    candidates = candidates.loc[~candidates.state.isin(selection["exclude_states"])].copy()

    tiger_path = ROOT / inputs["tiger_shapefile"]
    points = load_internal_points(tiger_path)
    require(set(candidates.county_geoid) <= set(points), "candidate missing TIGER internal point")
    candidates["latitude"] = candidates.county_geoid.map(lambda geoid: points[geoid]["latitude"])
    candidates["longitude"] = candidates.county_geoid.map(lambda geoid: points[geoid]["longitude"])
    candidates = candidates.sort_values("county_geoid").reset_index(drop=True)
    audit = {
        "panel_complete_support_before_other_gates": len(rows),
        "candidate_count_after_all_gates": len(candidates),
        "states_after_all_gates": candidates.groupby("state").size().sort_index().to_dict(),
        "nclimgrid_ready_count": len(readiness),
        "nclimgrid_ready_receipt_set_sha256": readiness_set_sha256,
        "readiness": readiness,
        "points": points,
        "input_files": {
            "panel": {"path": inputs["panel"], "bytes": panel_path.stat().st_size, "sha256": digest(panel_path)},
            "geography_gate": {"path": inputs["geography_gate"], "bytes": geography_path.stat().st_size, "sha256": digest(geography_path)},
            "calendar": {"path": inputs["calendar"], "bytes": calendar_path.stat().st_size, "sha256": digest(calendar_path)},
        },
    }
    return candidates, audit


def select_counties(candidates: pd.DataFrame, config: dict, points: dict[str, dict]) -> tuple[list[dict], dict[str, int]]:
    selection = config["selection"]
    anchors = [str(value).zfill(5) for value in selection["existing_anchor_geoids"]]
    require(set(anchors) <= set(points), "anchor missing TIGER internal point")
    chosen_geoids = list(anchors)
    selected = []
    counts: dict[str, int] = {}
    for stratum_name in selection["stratum_order"]:
        rule = config["strata"][stratum_name]
        eligible = candidates.loc[
            candidates.state.isin(rule["states"])
            & candidates.irrigation_share_median.between(float(rule["minimum_irrigation_share"]), float(rule["maximum_irrigation_share"]), inclusive="both")
            & candidates.primary_start_doy.between(int(rule["minimum_primary_start_doy"]), int(rule["maximum_primary_start_doy"]), inclusive="both")
            & ~candidates.county_geoid.isin(chosen_geoids)
        ].copy()
        counts[stratum_name] = len(eligible)
        require(len(eligible) > 0, f"empty stratum: {stratum_name}")
        ranked = []
        for row in eligible.to_dict("records"):
            point = (row["latitude"], row["longitude"])
            distances = {
                geoid: haversine_km(point, (points[geoid]["latitude"], points[geoid]["longitude"]))
                for geoid in chosen_geoids
            }
            ranked.append((min(distances.values()), row["county_geoid"], row, distances))
        ranked.sort(key=lambda item: (-item[0], item[1]))
        minimum_distance, geoid, row, distances = ranked[0]
        row.update({
            "stratum": stratum_name,
            "stratum_role": rule["role"],
            "minimum_distance_to_prior_design_km": minimum_distance,
            "distances_to_prior_design_km": distances,
            "stratum_candidate_count": len(eligible),
        })
        selected.append(row)
        chosen_geoids.append(geoid)
    require(len({row["county_geoid"] for row in selected}) == len(selected), "duplicate selection")
    require(all(row["state"] not in selection["exclude_states"] for row in selected), "excluded state selected")
    return selected, counts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    config_path = args.config if args.config.is_absolute() else ROOT / args.config
    output_path = args.output if args.output.is_absolute() else ROOT / args.output
    require(not output_path.exists(), "fresh output required")
    config = tomllib.loads(config_path.read_text())
    require(config["status"] == "frozen_before_loca2_or_observed_climate_value_access", "config is not frozen")
    require(config["execution"]["large_download_launched_by_preregistration"] is False, "preregistration cannot launch downloads")
    require(all(value is False for value in config["claim_gates"].values()), "config claim gates must start closed")

    candidates, audit = build_candidates(config)
    selected, stratum_counts = select_counties(candidates, config, audit["points"])
    selected_readiness = {}
    for row in selected:
        ready = audit["readiness"][row["county_geoid"]]
        output = ROOT / ready["output_path"]
        require(digest(output) == ready["output_sha256"], f"selected nClimGrid weights changed: {row['county_geoid']}")
        selected_readiness[row["county_geoid"]] = ready

    jobs = []
    for row in selected:
        for model_name, model in config["models"].items():
            for year_min, year_max in config["execution"]["year_partitions"]:
                jobs.append({
                    "county_geoid": row["county_geoid"], "county_name": row["county_name"], "state": row["state"],
                    "stratum": row["stratum"], "model_key": model_name, "source_id": model["source_id"],
                    "variant_label": model["variant_label"], "year_min": year_min, "year_max": year_max,
                    "status": "blocked_until_loca2_weights_and_observed_features_exist",
                })

    tiger_path = ROOT / config["inputs"]["tiger_shapefile"]
    tiger_components = []
    for suffix in (".shp", ".shx", ".dbf", ".prj", ".cpg"):
        path = tiger_path.with_suffix(suffix)
        if path.is_file():
            tiger_components.append({"path": str(path.relative_to(ROOT)), "bytes": path.stat().st_size, "sha256": digest(path)})
    rss = peak_rss_bytes()
    require(rss <= int(config["execution"]["worker_memory_mib"]) * 1024**2, "selection exceeded memory cap")
    result = {
        "schema": "loca2_us_compact_strata_expansion_preregistration/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "compact_outcome_blind_county_design_selected_execution_deferred",
        "config": {"path": str(config_path.relative_to(ROOT)), "bytes": config_path.stat().st_size, "sha256": digest(config_path)},
        "input_access_contract": {
            "panel_columns_read": list(PANEL_COLUMNS), "calendar_columns_read": list(CALENDAR_COLUMNS),
            "forbidden_columns": sorted(FORBIDDEN_COLUMNS), "yield_magnitudes_read": False,
            "nclimgrid_climate_values_read": False, "loca2_climate_values_read": False,
        },
        "input_files": audit["input_files"],
        "tiger_components": tiger_components,
        "support": {
            "crop": config["selection"]["crop"], "practice": config["selection"]["practice"],
            "years": list(range(config["selection"]["year_min"], config["selection"]["year_max"] + 1)),
            "complete_panel_support_before_other_gates": audit["panel_complete_support_before_other_gates"],
            "candidates_after_all_gates": audit["candidate_count_after_all_gates"],
            "candidate_states": audit["states_after_all_gates"], "stratum_candidate_counts": stratum_counts,
            "nclimgrid_ready_count": audit["nclimgrid_ready_count"],
            "nclimgrid_ready_receipt_set_sha256": audit["nclimgrid_ready_receipt_set_sha256"],
        },
        "selection_rule": config["selection"]["selection_rule"],
        "selected": selected,
        "selected_nclimgrid_weight_readiness": selected_readiness,
        "execution_plan": {
            "status": "not_started_to_avoid_competing_with_11_cell_spei_bridge",
            "phase_1": "Build and validate one LOCA2 TIGER-2019 weight table per selected county sequentially.",
            "phase_2": "Build outcome-free nClimGrid primary-calendar features for only the three selected counties and 2001-2012 from the existing validated county weights; this prerequisite is not resident today.",
            "phase_3": "Run metadata-only LOCA2 preflights for every planned model/partition and require the direct-native-chunk plan below 512 MiB.",
            "phase_4": "Run the 12 climate jobs strictly sequentially, independently validate each partition, combine exact nonoverlapping years by county/model, and summarize signs without skill weighting.",
            "planned_climate_jobs": jobs,
            "planned_climate_job_count": len(jobs),
            "resources": config["execution"],
            "downloads_launched": False,
        },
        "resources": {"peak_rss_bytes": rss, "memory_cap_mib": config["execution"]["worker_memory_mib"], "memory_gate_passed": True},
        "implementation": {"path": str(Path(__file__).resolve().relative_to(ROOT)), "sha256": digest(Path(__file__).resolve())},
        "claim_gates": {**config["claim_gates"], "compact_county_design_selected": True},
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": result["status"], "selected": selected, "planned_jobs": len(jobs), "peak_rss_bytes": rss}, indent=2))


if __name__ == "__main__":
    main()
