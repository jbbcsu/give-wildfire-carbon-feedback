#!/usr/bin/env python3
"""Independently validate exact-support climate-only county SPEI panels."""
from __future__ import annotations

import argparse
import calendar
from datetime import date
import hashlib
import json
import math
from pathlib import Path
import re
import tomllib

import h5py
import numpy as np
import pandas as pd
import xarray as xr

ROOT = Path(__file__).resolve().parents[2]
SCALES = (1, 3, 6)
FORBIDDEN = re.compile(r"(^|_)(yield|production|source_value_raw|outcome_value)(_|$)", re.IGNORECASE)
FALSE_GATES = ("bridge_to_nass_response", "fit_outcomes", "future_yield_projection", "causal_claim", "damage", "scc")
SAMPLE_COLUMNS = [
    "county_geoid", "state", "outcome_crop", "harvest_year", "irrigation_practice",
    "feature_construction_eligible", "season_start", "season_end", "calendar_source_id",
    "calendar_vintage", "calendar_boundary_rule", "stage_definition",
]


def check(condition: bool, message: str, checks: list[str]) -> None:
    if not condition:
        raise ValueError(message)
    checks.append(message)


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def resolve(path: str | Path) -> Path:
    value = Path(path)
    if value.is_absolute() and value.exists():
        return value
    if value.is_absolute() and "data" in value.parts:
        relocated = ROOT / Path(*value.parts[value.parts.index("data"):])
        if relocated.exists():
            return relocated
    return value if value.is_absolute() else ROOT / value


def _month_parts(start: pd.Timestamp, end: pd.Timestamp) -> list[tuple[pd.Timestamp, int]]:
    current = date(start.year, start.month, 1)
    parts = []
    while current <= end.date():
        month_end = date(current.year, current.month, calendar.monthrange(current.year, current.month)[1])
        left, right = max(current, start.date()), min(month_end, end.date())
        if left <= right:
            parts.append((pd.Timestamp(current), (right - left).days + 1))
        current = date(current.year + int(current.month == 12), current.month % 12 + 1, 1)
    return parts


def independent_metrics(group: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp, scale: int) -> tuple[float, float, int]:
    values = dict(zip(pd.to_datetime(group.date), pd.to_numeric(group[f"spei_{scale}"])))
    parts = _month_parts(start, end)
    selected = []
    for month, days in parts:
        if month not in values or not math.isfinite(float(values[month])):
            raise ValueError("monthly climate panel is incomplete within a frozen season")
        selected.append((float(values[month]), days))
    denominator = (end - start).days + 1
    if sum(days for _value, days in selected) != denominator:
        raise ValueError("independent calendar overlap accounting differs")
    return math.fsum(value * days for value, days in selected) / denominator, min(value for value, _ in selected), len(selected)


def validate_panel_pair(monthly: pd.DataFrame, season: pd.DataFrame, expected_monthly: int, expected_season: int,
                        case_keys: list[str], checks: list[str]) -> None:
    check(len(monthly) == expected_monthly, f"monthly rows {expected_monthly}", checks)
    check(len(season) == expected_season, f"season rows {expected_season}", checks)
    check(not any(FORBIDDEN.search(column) for column in monthly.columns), "monthly output has no outcome columns", checks)
    check(not any(FORBIDDEN.search(column) for column in season.columns), "season output has no outcome columns", checks)
    monthly_keys = [*case_keys, "county_geoid", "date"]
    season_keys = [*case_keys, "county_geoid", "harvest_year"]
    check(not monthly.duplicated(monthly_keys).any(), "monthly keys unique", checks)
    check(not season.duplicated(season_keys).any(), "season keys unique", checks)
    check(not season[[f"spei_{scale}_day_weighted_mean" for scale in SCALES]
                     + [f"spei_{scale}_monthly_minimum" for scale in SCALES]].isna().any().any(),
          "season metrics finite", checks)
    grouped = {key if isinstance(key, tuple) else (key,): group for key, group in monthly.groupby(case_keys + ["county_geoid"], sort=False)}
    for row in season.itertuples(index=False):
        key = tuple(getattr(row, name) for name in case_keys + ["county_geoid"])
        group = grouped[key]
        for scale in SCALES:
            mean, minimum, count = independent_metrics(group, row.season_start, row.season_end, scale)
            check(math.isclose(mean, getattr(row, f"spei_{scale}_day_weighted_mean"), abs_tol=2e-12, rel_tol=0),
                  f"independent SPEI-{scale} seasonal mean", checks)
            check(math.isclose(minimum, getattr(row, f"spei_{scale}_monthly_minimum"), abs_tol=2e-12, rel_tol=0),
                  f"independent SPEI-{scale} monthly minimum", checks)
            check(count == getattr(row, f"spei_{scale}_source_months"), f"independent SPEI-{scale} month count", checks)


def _keys(dataset) -> list[tuple[int, int]]:
    return list(zip(np.asarray(dataset["native_lat_index"], dtype=np.int64).tolist(),
                    np.asarray(dataset["native_lon_index"], dtype=np.int64).tolist()))


def _extract_historical(result: dict, wanted: set[tuple[int, int]], month_positions: list[int]) -> dict[tuple[int, int], np.ndarray]:
    manifest_record = result["upstream"]["historical_base_manifest"]
    manifest_path = resolve(manifest_record["path"])
    if digest(manifest_path) != manifest_record["sha256"]:
        raise ValueError("historical manifest hash changed")
    manifest = json.loads(manifest_path.read_text())
    found = {}
    for record in manifest["records"]:
        path = resolve(record["output"]["path"])
        with xr.open_dataset(path, engine="h5netcdf", cache=False) as dataset:
            keys = _keys(dataset)
            local = [i for i, key in enumerate(keys) if key in wanted]
            if not local:
                continue
            if digest(path) != record["output"]["sha256"]:
                raise ValueError("historical source block hash changed")
            values = np.asarray(dataset.spei.values[:, month_positions, :], dtype=np.float64)
            for index in local:
                found[keys[index]] = values[:, :, index]
    ext_record = result["upstream"]["historical_extension_cube"]
    ext_path = resolve(ext_record["path"])
    if digest(ext_path) != ext_record["sha256"]:
        raise ValueError("historical extension cube hash changed")
    with xr.open_dataset(ext_path, engine="h5netcdf", cache=False) as dataset:
        keys = _keys(dataset); values = np.asarray(dataset.spei.values[:, month_positions, :], dtype=np.float64)
        for index, key in enumerate(keys):
            if key in wanted:
                found[key] = values[:, :, index]
    if set(found) != wanted:
        raise ValueError("historical sentinel support incomplete")
    return found


def _extract_future(case: dict, wanted: set[tuple[int, int]], month_position: int) -> dict[tuple[int, int], np.ndarray]:
    found = {}
    base = resolve(case["base_cube"]["path"])
    if digest(base) != case["base_cube"]["sha256"]:
        raise ValueError("future base cube hash changed")
    with h5py.File(base, "r") as handle:
        keys = list(zip(handle["native_lat_index"][:].astype(int).tolist(), handle["native_lon_index"][:].astype(int).tolist()))
        for index, key in enumerate(keys):
            if key in wanted:
                found[key] = np.asarray(handle["spei"][:, month_position, index], dtype=np.float64)
    extension = resolve(case["extension_cube"]["path"])
    if digest(extension) != case["extension_cube"]["sha256"]:
        raise ValueError("future extension cube hash changed")
    with xr.open_dataset(extension, engine="h5netcdf", cache=False) as dataset:
        keys = _keys(dataset); values = np.asarray(dataset.spei.values[:, month_position, :], dtype=np.float64)
        for index, key in enumerate(keys):
            if key in wanted:
                found[key] = values[:, index]
    if set(found) != wanted:
        raise ValueError("future sentinel support incomplete")
    return found


def validate_source_sentinels(result: dict, weights: pd.DataFrame, historical_monthly: pd.DataFrame,
                              future_monthly: pd.DataFrame, checks: list[str]) -> None:
    counties = sorted(weights.county_geoid.unique())
    sentinels = [counties[0], counties[len(counties)//2], counties[-1]]
    selected_weights = weights.loc[weights.county_geoid.isin(sentinels)].copy()
    wanted = set(zip(selected_weights.native_lat_index.astype(int), selected_weights.native_lon_index.astype(int)))
    periods = pd.to_datetime(["1981-06-01", "2000-08-01", "2018-09-01"])
    axis = pd.date_range("1981-01-01", "2019-12-01", freq="MS")
    positions = [axis.get_loc(period) for period in periods]
    source = _extract_historical(result, wanted, positions)
    for county in sentinels:
        county_weights = selected_weights.loc[selected_weights.county_geoid.eq(county)]
        for period_index, period in enumerate(periods):
            saved = historical_monthly.loc[(historical_monthly.county_geoid == county)
                                            & (historical_monthly.date == period)].iloc[0]
            for scale_index, scale in enumerate(SCALES):
                expected = math.fsum(float(row.spatial_weight_within_available)
                                     * float(source[(int(row.native_lat_index), int(row.native_lon_index))][scale_index, period_index])
                                     for row in county_weights.itertuples(index=False))
                check(math.isclose(expected, float(saved[f"spei_{scale}"]), abs_tol=3e-7, rel_tol=0),
                      f"historical source sentinel {county} {period.date()} SPEI-{scale}", checks)

    future_axis = pd.date_range("2091-01-01", "2100-12-01", freq="MS")
    period = pd.Timestamp("2095-07-01"); position = future_axis.get_loc(period)
    case_lookup = {(item["model"], item["scenario"]): item for item in result["upstream"]["future_cases"]}
    for case_key, case in sorted(case_lookup.items()):
        source = _extract_future(case, wanted, position)
        for county in sentinels:
            county_weights = selected_weights.loc[selected_weights.county_geoid.eq(county)]
            saved = future_monthly.loc[(future_monthly.model == case_key[0]) & (future_monthly.scenario == case_key[1])
                                       & (future_monthly.county_geoid == county) & (future_monthly.date == period)].iloc[0]
            for scale_index, scale in enumerate(SCALES):
                expected = math.fsum(float(row.spatial_weight_within_available)
                                     * float(source[(int(row.native_lat_index), int(row.native_lon_index))][scale_index])
                                     for row in county_weights.itertuples(index=False))
                check(math.isclose(expected, float(saved[f"spei_{scale}"]), abs_tol=3e-7, rel_tol=0),
                      f"future source sentinel {case_key[0]} {case_key[1]} {county} SPEI-{scale}", checks)


def validate(result_path: Path, resource_path: Path) -> dict:
    checks: list[str] = []
    result, resource = json.loads(result_path.read_text()), json.loads(resource_path.read_text())
    check(result["schema"] == "us_spei_bridge_post_queue_result_v1", "result schema", checks)
    check(result["status"] == "climate_panels_completed_pending_independent_validation", "result pending status", checks)
    check(result["role"] == "climate_only_exact_support_county_panel_no_outcomes_no_fit", "climate-only role", checks)
    check(result["all_15_extension_gate"] == {"passed": True, "cases": 15}, "all-15 gate", checks)
    check(all(result["gates"][name] is False for name in FALSE_GATES), "all outcome/downstream gates closed", checks)
    check(resource["status"] == "completed" and resource["returncode"] == 0, "bounded job completed", checks)
    check(resource["sampled_peak_group_rss_bytes"] <= 512 * 1024**2 and resource["max_mib"] == 512.0,
          "512 MiB sampled memory gate", checks)
    contract_path = resolve(result["contract"]["path"])
    check(digest(contract_path) == result["contract"]["sha256"], "contract identity", checks)
    contract = tomllib.loads(contract_path.read_text())
    check(not any(contract["authorization"].values()), "contract authorizations closed", checks)
    sample_contract = contract["sample"]
    expected_counties = int(sample_contract["expected_counties"])
    expected_rows = int(sample_contract["expected_rows"])
    sample_path = resolve(sample_contract["panel"])
    check(digest(sample_path) == sample_contract["panel_sha256"], "metadata-only sample identity", checks)
    sample = pd.read_parquet(sample_path, columns=SAMPLE_COLUMNS)
    sample = sample.loc[
        sample.outcome_crop.eq(sample_contract["crop"])
        & sample.irrigation_practice.eq(sample_contract["practice"])
        & sample.harvest_year.between(sample_contract["year_min"], sample_contract["year_max"])
    ].copy()
    sample["county_geoid"] = sample.county_geoid.astype(str).str.zfill(5)
    sample["season_start"] = pd.to_datetime(sample.season_start); sample["season_end"] = pd.to_datetime(sample.season_end)
    check(len(sample) == expected_rows and sample.county_geoid.nunique() == expected_counties,
          "exact metadata-only NASS sample", checks)
    implementation = resolve(result["implementation"]["path"])
    check(digest(implementation) == result["implementation"]["sha256"], "builder identity", checks)
    for record in [result["upstream"][name] for name in (
        "historical_base_manifest", "historical_base_validation", "historical_extension_result",
        "historical_extension_validation", "historical_extension_cube",
    )]:
        check(digest(resolve(record["path"])) == record["sha256"], f"upstream identity {record['path']}", checks)
    check(len(result["upstream"]["future_cases"]) == 15, "15 future upstream records", checks)
    expected_cases = {(model, scenario) for model in contract["future"]["models"] for scenario in contract["future"]["scenarios"]}
    check({(item["model"], item["scenario"]) for item in result["upstream"]["future_cases"]} == expected_cases,
          "exact future case family", checks)
    for item in result["upstream"]["future_cases"]:
        validation = json.loads(resolve(item["extension_validation"]["path"]).read_text())
        check(validation["status"] == "passed", f"extension validation passed {item['model']} {item['scenario']}", checks)
        for name in ("base_result", "base_validation", "base_cube", "extension_result", "extension_validation", "extension_cube"):
            record = item[name]
            check(digest(resolve(record["path"])) == record["sha256"],
                  f"future upstream identity {item['model']} {item['scenario']} {name}", checks)

    paths = {}
    for name, record in result["outputs"].items():
        path = resolve(record["path"])
        check(path.stat().st_size == record["bytes"] and digest(path) == record["sha256"], f"output identity {name}", checks)
        paths[name] = path
    coverage = pd.read_csv(paths["county_coverage"], dtype={"county_geoid": str})
    weights = pd.read_parquet(paths["county_cell_weights"]); weights["county_geoid"] = weights.county_geoid.astype(str).str.zfill(5)
    check(len(coverage) == coverage.county_geoid.nunique() == expected_counties and coverage.passes_0_999_gate.all(),
          f"{expected_counties} counties pass 0.999 coverage", checks)
    recomputed = coverage.available_intersection_area_m2 / coverage.county_area_m2
    check(float((recomputed - coverage.coverage_fraction).abs().max()) < 2e-15, "coverage arithmetic", checks)
    check(float((weights.groupby("county_geoid").spatial_weight_within_available.sum() - 1).abs().max()) < 2e-15,
          "county weights normalize", checks)
    check(not weights.duplicated(["county_geoid", "native_lat_index", "native_lon_index"]).any(), "weight keys unique", checks)

    historical_monthly = pd.read_parquet(paths["historical_monthly"])
    historical_season = pd.read_parquet(paths["historical_season"])
    future_monthly = pd.read_parquet(paths["future_monthly"])
    future_season = pd.read_parquet(paths["future_season"])
    for frame in (historical_monthly, future_monthly):
        frame["county_geoid"] = frame.county_geoid.astype(str).str.zfill(5); frame["date"] = pd.to_datetime(frame.date)
    for frame in (historical_season, future_season):
        frame["county_geoid"] = frame.county_geoid.astype(str).str.zfill(5)
        frame["season_start"] = pd.to_datetime(frame.season_start); frame["season_end"] = pd.to_datetime(frame.season_end)
    validate_panel_pair(historical_monthly, historical_season,
                        int(contract["outputs"]["expected_historical_monthly_rows"]),
                        int(contract["outputs"]["expected_historical_season_rows"]), [], checks)
    validate_panel_pair(future_monthly, future_season,
                        int(contract["outputs"]["expected_future_monthly_rows"]),
                        int(contract["outputs"]["expected_future_season_rows"]), ["model", "scenario"], checks)
    historical_axis = pd.date_range("1981-01-01", "2019-12-01", freq="MS")
    future_axis = pd.date_range("2091-01-01", "2100-12-01", freq="MS")
    check(pd.DatetimeIndex(sorted(historical_monthly.date.unique())).equals(historical_axis)
          and historical_monthly.groupby("county_geoid").size().eq(468).all(), "exact historical monthly axes", checks)
    check(pd.DatetimeIndex(sorted(future_monthly.date.unique())).equals(future_axis)
          and future_monthly.groupby(["model", "scenario", "county_geoid"]).size().eq(120).all(),
          "exact future monthly axes", checks)
    sample_calendar = sample[["county_geoid", "harvest_year", "state", "season_start", "season_end",
                              "calendar_source_id", "calendar_vintage", "calendar_boundary_rule", "stage_definition"]]
    observed_calendar = historical_season[sample_calendar.columns]
    check(sample_calendar.sort_values(["county_geoid", "harvest_year"]).reset_index(drop=True).equals(
              observed_calendar.sort_values(["county_geoid", "harvest_year"]).reset_index(drop=True)),
          "historical panel keys and calendars equal the frozen metadata-only sample", checks)
    frozen_windows = sample.assign(start_mmdd=sample.season_start.dt.strftime("%m-%d"),
                                   end_mmdd=sample.season_end.dt.strftime("%m-%d"))
    frozen_windows = frozen_windows[["state", "start_mmdd", "end_mmdd"]].drop_duplicates()
    future_windows = future_season.assign(start_mmdd=future_season.season_start.dt.strftime("%m-%d"),
                                          end_mmdd=future_season.season_end.dt.strftime("%m-%d"))
    future_windows = future_windows[["state", "start_mmdd", "end_mmdd"]].drop_duplicates()
    check(frozen_windows.sort_values("state").reset_index(drop=True).equals(
              future_windows.sort_values("state").reset_index(drop=True)),
          "future calendars transport frozen state month-days exactly", checks)
    check(set(historical_season.harvest_year) == set(range(int(sample_contract["year_min"]),
                                                           int(sample_contract["year_max"]) + 1)),
          "historical harvest-year support", checks)
    check(set(future_season.harvest_year) == set(range(2092, 2100)), "future harvest-year support", checks)
    check(len(future_season.groupby(["model", "scenario"])) == 15, "future panel case count", checks)
    check(historical_monthly.spei_1.notna().all() and historical_monthly.spei_3.isna().sum() == 2 * expected_counties
          and historical_monthly.spei_6.isna().sum() == 5 * expected_counties,
          "historical structural leading missingness", checks)
    check(future_monthly.spei_1.notna().all() and future_monthly.spei_3.isna().sum() == 2 * expected_counties * 15
          and future_monthly.spei_6.isna().sum() == 5 * expected_counties * 15,
          "future structural leading missingness", checks)
    validate_source_sentinels(result, weights, historical_monthly, future_monthly, checks)
    return {
        "schema": "us_spei_bridge_post_queue_validation_v1", "status": "passed", "checks": len(checks),
        "result": {"path": str(result_path.relative_to(ROOT)), "sha256": digest(result_path)},
        "resource": {"path": str(resource_path.relative_to(ROOT)), "sha256": digest(resource_path),
                     "sampled_peak_group_rss_bytes": resource["sampled_peak_group_rss_bytes"]},
        "validated": {"historical_season_rows": len(historical_season), "future_season_rows": len(future_season),
                      "counties": expected_counties, "future_cases": 15},
        "gates": {"historical_climate_panel_independently_validated": True,
                  "future_climate_panel_independently_validated": True,
                  **{name: False for name in FALSE_GATES}},
        "implementation": {"path": str(Path(__file__).resolve().relative_to(ROOT)),
                           "sha256": digest(Path(__file__).resolve())},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--resource", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result_path, resource_path, output = resolve(args.result), resolve(args.resource), resolve(args.output)
    if output.exists():
        raise ValueError("fresh validation output required")
    validation = validate(result_path, resource_path)
    output.write_text(json.dumps(validation, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": validation["status"], "checks": validation["checks"], "validated": validation["validated"]}))


if __name__ == "__main__":
    main()
