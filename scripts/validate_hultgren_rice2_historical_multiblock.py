#!/usr/bin/env python3
"""Independently validate the 1982--2019 strict-support Rice2 weather basis."""
from __future__ import annotations

import argparse
import gc
import hashlib
import json
import resource
import sys
import tomllib
from collections import Counter
from contextlib import ExitStack
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import rasterio
import xarray as xr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.hultgren_crop_calendar import calendar_months_for_report_year, season_months, source_month_from_day
from src.hultgren_rice_weather import build_rice_weather_basis_from_daily

CONFIG_DEFAULT = ROOT / "config/hultgren_rice2_historical_multiblock_v1.toml"
CONTRACT_ID = "hultgren_rice2_historical_multiblock_v1"
KEYS = ["harvest_year", "native_lat_index", "native_lon_index"]
CALENDAR = ["plant_month", "harvest_month", "season_months", "cross_year"]
WEATHER = [
    "gdd", "kdd", "tmin",
    "prcp_poly_1_bin1", "prcp_poly_2_bin1",
    "prcp_poly_1_bin2", "prcp_poly_2_bin2",
    "prcp_poly_1_bin3", "prcp_poly_2_bin3",
]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def resolve(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def recorded_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path.resolve())


def digest(path: Path, algorithm: str = "sha256") -> str:
    value = hashlib.new(algorithm)
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 << 20), b""):
            value.update(block)
    return value.hexdigest()


def peak_rss_bytes() -> int:
    value = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    return value if sys.platform == "darwin" else value * 1024


def load_config(path: Path) -> tuple[dict[str, Any], str]:
    raw = path.read_bytes()
    config = tomllib.loads(raw.decode("utf-8"))
    require(config.get("schema_version") == 1, "config schema changed")
    require(config.get("contract_id") == CONTRACT_ID, "contract id changed")
    require(config.get("harvest_years") == [1982, 2019], "harvest-year contract changed")
    require(config.get("source_years") == [1981, 2019], "source-year contract changed")
    branches = {row["branch"]: row for row in config["branches"]}
    require(set(branches) == {"ri2_noirr", "ri2_firr"}, "branch registry changed")
    for branch, record in branches.items():
        for key in ("calendar", "basis", "build_receipt"):
            source = resolve(record[f"{key}_path"])
            require(source.is_file(), f"missing {branch} {key}")
            require(digest(source) == record[f"{key}_sha256"], f"{branch} {key} hash differs")
    rice1 = config["rice1_regression"]
    for key in ("calendar", "annual_irrigated", "annual_rainfed", "preserved_basis"):
        source = resolve(rice1[f"{key}_path"])
        require(source.is_file(), f"missing Rice1 regression source: {key}")
        require(digest(source) == rice1[f"{key}_sha256"], f"Rice1 regression source hash differs: {key}")
    for key, expected in config["implementation"].items():
        if key.endswith("_path"):
            stem = key.removesuffix("_path")
            source = resolve(expected)
            require(source.is_file(), f"missing implementation file: {stem}")
            require(digest(source) == config["implementation"][f"{stem}_sha256"], f"implementation hash differs: {stem}")
    support = config["support"]
    require(support["rice1_substitution_authorized"] is False, "Rice1 substitution opened")
    require(support["calendar_fill_authorized"] is False, "calendar fill opened")
    require(support["support_values_as_weights_authorized"] is False, "support weighting opened")
    gates = config["claim_gates"]
    require(gates["unweighted_historical_weather_basis_authorized"] is True, "historical weather basis not authorized")
    for key, value in gates.items():
        if key != "unweighted_historical_weather_basis_authorized":
            require(value is False, f"claim gate opened: {key}")
    return config, hashlib.sha256(raw).hexdigest()


def calendar_support(path: Path, minimum_months: int) -> tuple[pd.DataFrame, dict[str, int]]:
    with xr.open_dataset(path, engine="h5netcdf", decode_timedelta=False, cache=False) as dataset:
        latitude = np.asarray(dataset.lat.values, dtype=np.float64)
        longitude = np.asarray(dataset.lon.values, dtype=np.float64)
        planting = np.asarray(dataset.planting_day.values, dtype=np.float64)
        maturity = np.asarray(dataset.maturity_day.values, dtype=np.float64)
        fraction = np.asarray(dataset.fraction_of_harvested_area.values, dtype=np.float64)
    finite = np.isfinite(planting) & np.isfinite(maturity)
    direct = finite & np.isfinite(fraction) & (fraction > 0.0)
    rows, columns = np.nonzero(direct)
    plant_month = np.fromiter(
        (source_month_from_day(planting[row, column]) for row, column in zip(rows, columns, strict=True)),
        dtype=np.int16,
    )
    harvest_month = np.fromiter(
        (source_month_from_day(maturity[row, column]) for row, column in zip(rows, columns, strict=True)),
        dtype=np.int16,
    )
    month_count = np.fromiter(
        (len(season_months(plant, harvest)) for plant, harvest in zip(plant_month, harvest_month, strict=True)),
        dtype=np.int16,
    )
    eligible = (month_count >= minimum_months) & (month_count <= 12)
    frame = pd.DataFrame({
        "native_lat_index": rows[eligible].astype(np.int16),
        "native_lon_index": columns[eligible].astype(np.int16),
        "latitude": latitude[rows[eligible]],
        "longitude": longitude[columns[eligible]],
        "plant_month": plant_month[eligible],
        "harvest_month": harvest_month[eligible],
        "season_months": month_count[eligible],
        "cross_year": plant_month[eligible] >= harvest_month[eligible],
    })
    distribution = {str(k): int(v) for k, v in sorted(Counter(month_count[eligible].tolist()).items())}
    return frame.sort_values(["native_lat_index", "native_lon_index"]).reset_index(drop=True), distribution


def validate_source_blocks(config: dict[str, Any], receipt: dict[str, Any], branch: str) -> None:
    blocks = config["weather"]["blocks"]
    require(len(blocks) == 4, "weather block registry changed")
    for variable in ("pr", "tasmin", "tasmax"):
        files = receipt["sources"][variable]["files"]
        require(len(files) == len(blocks), f"source block count differs: {branch} {variable}")
        for block, observed in zip(blocks, files, strict=True):
            require(observed["path"] == block[f"{variable}_path"], f"source path differs: {branch} {variable}")
            require(observed["sha512"] == block[f"{variable}_sha512"], f"source hash differs: {branch} {variable}")
    observed_blocks = receipt["stream_audit"]["source_blocks"]
    require(len(observed_blocks) == len(blocks), f"stream block count differs: {branch}")
    prior_end: date | None = None
    for expected, observed in zip(blocks, observed_blocks, strict=True):
        start = date.fromisoformat(expected["start_date"])
        end = date.fromisoformat(expected["end_date"])
        require(observed["start_date"] == expected["start_date"], f"stream start differs: {branch}")
        require(observed["end_date"] == expected["end_date"], f"stream end differs: {branch}")
        require(observed["daily_steps"] == (end - start).days + 1, f"stream length differs: {branch}")
        if prior_end is not None:
            require(start == prior_end + timedelta(days=1), f"weather blocks are not contiguous: {branch}")
        prior_end = end
    require(receipt["stream_audit"]["daily_steps"] == 14244, f"total daily steps differ: {branch}")


def branch_content_digest(path: Path) -> str:
    """Hash logical rows without holding both branch outputs in memory."""
    value = hashlib.sha256()
    parquet = pq.ParquetFile(path)
    for batch in parquet.iter_batches(batch_size=32768):
        frame = batch.to_pandas().drop(columns=["calendar_branch"])
        row_hashes = pd.util.hash_pandas_object(frame, index=False).to_numpy(dtype=np.uint64)
        value.update(row_hashes.tobytes())
    return value.hexdigest()


def load_branch(config: dict[str, Any], record: dict[str, Any]) -> tuple[pd.DataFrame, dict[str, Any], str]:
    branch = record["branch"]
    receipt = json.loads(resolve(record["build_receipt_path"]).read_text(encoding="utf-8"))
    require(receipt["status"] == "complete_unweighted_rice_calendar_branch_basis_not_response_damage_or_scc", f"build failed: {branch}")
    require(receipt["calendar_branch"] == branch, f"receipt branch differs: {branch}")
    require(receipt["harvest_years"] == [1982, 2019], f"harvest years differ: {branch}")
    require(receipt["source_period"] == [1981, 2019], f"source period differs: {branch}")
    require(receipt["implementation"]["sha256"] == config["implementation"]["builder_sha256"], f"builder hash differs: {branch}")
    validate_source_blocks(config, receipt, branch)
    support_audit = receipt["support_audit"]
    require(support_audit["publisher_fraction_used_only_as_boolean_support"] is True, f"strict support absent: {branch}")
    require(support_audit["support_magnitudes_used_as_weights"] is False, f"support weighting used: {branch}")
    require(support_audit["rice1_calendar_or_weather_substituted"] is False, f"Rice1 substituted: {branch}")
    require(support_audit["annual_mirca_inputs_used"] is False, f"annual MIRCA used: {branch}")
    schema = pq.read_schema(resolve(record["basis_path"])).names
    prohibited = [column for column in schema if any(part in column.lower() for part in ("area", "weight", "production", "yield", "response", "damage", "scc"))]
    require(not prohibited, f"prohibited output columns: {prohibited}")
    frame = pd.read_parquet(resolve(record["basis_path"]))
    require(len(frame) == int(config["support"]["required_rows_per_branch"]), f"row count differs: {branch}")
    require(frame.calendar_branch.eq(branch).all(), f"output branch differs: {branch}")
    require(frame.complete.all(), f"incomplete weather rows: {branch}")
    require(np.isfinite(frame[WEATHER].to_numpy(dtype=np.float64)).all(), f"nonfinite weather: {branch}")
    require(not frame.duplicated(KEYS).any(), f"duplicate keys: {branch}")
    expected_years = list(range(1982, 2020))
    require(sorted(frame.harvest_year.unique().tolist()) == expected_years, f"year coverage differs: {branch}")
    expected, distribution = calendar_support(resolve(record["calendar_path"]), 3)
    required_cells = int(config["support"]["required_cells_per_year"])
    require(len(expected) == required_cells, f"strict support count differs: {branch}")
    per_year: dict[str, int] = {}
    for year, group in frame.groupby("harvest_year", sort=True):
        observed = group[["native_lat_index", "native_lon_index", "latitude", "longitude", *CALENDAR]].sort_values(["native_lat_index", "native_lon_index"]).reset_index(drop=True)
        require(len(observed) == required_cells, f"year row count differs: {branch} {year}")
        for column in expected.columns:
            require(np.array_equal(expected[column].to_numpy(), observed[column].to_numpy()), f"strict calendar field differs: {branch} {year} {column}")
        per_year[str(int(year))] = len(observed)
    short = frame.season_months.lt(6)
    structural_zero = frame.loc[short, ["prcp_poly_1_bin3", "prcp_poly_2_bin3"]].to_numpy(dtype=np.float64)
    require(np.count_nonzero(structural_zero) == 0, f"short-season third phase is nonzero: {branch}")
    cross_per_year = frame.groupby("harvest_year").cross_year.sum().astype(int)
    require(cross_per_year.eq(int(config["support"]["cross_year_cells_per_year"])).all(), f"cross-year coverage differs: {branch}")
    summary = {
        "path": record["basis_path"], "sha256": record["basis_sha256"],
        "rows": len(frame), "harvest_year_first": 1982, "harvest_year_last": 2019,
        "harvest_year_count": len(expected_years), "rows_per_year": per_year,
        "calendar_month_distribution_per_year": distribution,
        "cross_year_rows": int(frame.cross_year.sum()),
        "three_to_five_month_rows": int(short.sum()),
        "short_season_third_phase_nonzero_values": int(np.count_nonzero(structural_zero)),
        "build_peak_rss_bytes": int(receipt["resources"]["peak_rss_bytes"]),
        "build_wall_seconds": float(receipt["wall_seconds"]),
        "daily_steps_streamed": int(receipt["stream_audit"]["daily_steps"]),
    }
    sentinels = pd.DataFrame([row for _, row in select_sentinels(frame)])
    logical_digest = branch_content_digest(resolve(record["basis_path"]))
    return sentinels.sort_values(KEYS).reset_index(drop=True), summary, logical_digest


def select_sentinels(frame: pd.DataFrame) -> list[tuple[str, pd.Series]]:
    ordered = frame.sort_values(KEYS).reset_index(drop=True)
    result: list[tuple[str, pd.Series]] = []
    for year in (1982, 1991, 2001, 2011, 2019):
        candidates = ordered.loc[ordered.harvest_year.eq(year) & ordered.cross_year]
        require(not candidates.empty, f"no cross-year sentinel for {year}")
        result.append((f"cross_year_{year}", candidates.iloc[0]))
    for length in (3, 4, 5):
        candidates = ordered.loc[ordered.harvest_year.eq(2019) & ordered.season_months.eq(length) & ~ordered.cross_year]
        require(not candidates.empty, f"no {length}-month same-year sentinel")
        result.append((f"{length}_month_2019", candidates.iloc[0]))
    return result


def direct_checks(frames: dict[str, pd.DataFrame], config: dict[str, Any]) -> list[dict[str, Any]]:
    tolerance = float(config["validation"]["maximum_absolute_weather_error"])
    results: list[dict[str, Any]] = []
    with ExitStack() as stack:
        datasets: dict[str, list[xr.Dataset]] = {name: [] for name in ("pr", "tasmin", "tasmax")}
        lookup: dict[date, tuple[int, int]] = {}
        for block_index, block in enumerate(config["weather"]["blocks"]):
            dates_by_variable: dict[str, pd.DatetimeIndex] = {}
            for variable in datasets:
                dataset = stack.enter_context(xr.open_dataset(resolve(block[f"{variable}_path"]), engine="h5netcdf", decode_times=True, cache=False))
                datasets[variable].append(dataset)
                dates_by_variable[variable] = pd.DatetimeIndex(dataset.time.values).normalize()
            require(dates_by_variable["pr"].equals(dates_by_variable["tasmin"]), f"pr/tasmin chronology differs in block {block_index}")
            require(dates_by_variable["pr"].equals(dates_by_variable["tasmax"]), f"pr/tasmax chronology differs in block {block_index}")
            for position, stamp in enumerate(dates_by_variable["pr"]):
                day = stamp.date()
                require(day not in lookup, f"duplicate daily weather date: {day}")
                lookup[day] = (block_index, position)
        require(len(lookup) == 14244, "daily weather lookup length differs")
        for branch, frame in frames.items():
            for kind, row in select_sentinels(frame):
                records = []
                month_keys = calendar_months_for_report_year(int(row.harvest_year), int(row.plant_month), int(row.harvest_month), "USA")
                source_years = set()
                for year, month in month_keys:
                    source_years.add(year)
                    start = pd.Timestamp(year=year, month=month, day=1)
                    for stamp in pd.date_range(start, start + pd.offsets.MonthEnd(0), freq="D"):
                        block_index, position = lookup[stamp.date()]
                        i, j = int(row.native_lat_index), int(row.native_lon_index)
                        records.append((
                            date(stamp.year, stamp.month, stamp.day),
                            float(datasets["pr"][block_index].pr.isel(time=position, lat=i, lon=j).values) * 86_400.0,
                            float(datasets["tasmin"][block_index].tasmin.isel(time=position, lat=i, lon=j).values) - 273.15,
                            float(datasets["tasmax"][block_index].tasmax.isel(time=position, lat=i, lon=j).values) - 273.15,
                        ))
                rebuilt = build_rice_weather_basis_from_daily(
                    records, report_year=int(row.harvest_year), plant_month=int(row.plant_month),
                    harvest_month=int(row.harvest_month), iso="USA",
                )
                expected = {
                    "gdd": rebuilt.gdd, "kdd": rebuilt.kdd, "tmin": rebuilt.tmin,
                    **{f"prcp_poly_1_bin{index}": value for index, value in enumerate(rebuilt.prcp_poly_1_bins, 1)},
                    **{f"prcp_poly_2_bin{index}": value for index, value in enumerate(rebuilt.prcp_poly_2_bins, 1)},
                }
                errors = {column: abs(float(row[column]) - value) for column, value in expected.items()}
                maximum = max(errors.values())
                require(maximum <= tolerance, f"direct reaggregation differs: {branch} {kind} {errors}")
                if bool(row.cross_year):
                    require(int(row.harvest_year) - 1 in source_years, f"cross-year sentinel omitted prior-year weather: {branch} {kind}")
                results.append({
                    "branch": branch, "sentinel_kind": kind, "harvest_year": int(row.harvest_year),
                    "native_lat_index": int(row.native_lat_index), "native_lon_index": int(row.native_lon_index),
                    "latitude": float(row.latitude), "longitude": float(row.longitude),
                    "plant_month": int(row.plant_month), "harvest_month": int(row.harvest_month),
                    "season_months": int(row.season_months), "cross_year": bool(row.cross_year),
                    "source_years": sorted(source_years), "daily_records_reaggregated": len(records),
                    "maximum_absolute_weather_error": maximum, "absolute_errors": errors,
                })
    return results


def rice1_regression(config: dict[str, Any]) -> dict[str, Any]:
    record = config["rice1_regression"]
    with xr.open_dataset(resolve(record["calendar_path"]), engine="h5netcdf", decode_timedelta=False, cache=False) as dataset:
        planting = np.asarray(dataset.planting_day.values, dtype=np.float64)
        maturity = np.asarray(dataset.maturity_day.values, dtype=np.float64)
    masks = []
    for key in ("annual_irrigated_path", "annual_rainfed_path"):
        with rasterio.open(resolve(record[key])) as source:
            masks.append(np.asarray(source.read(1), dtype=np.float64) > 0.0)
    support = (masks[0] | masks[1]) & np.isfinite(planting) & np.isfinite(maturity)
    rows, columns = np.nonzero(support)
    keep = []
    for row, column in zip(rows, columns, strict=True):
        plant = source_month_from_day(planting[row, column])
        harvest = source_month_from_day(maturity[row, column])
        keep.append(6 <= len(season_months(plant, harvest)) <= 12)
    expected = pd.DataFrame({
        "native_lat_index": rows[np.asarray(keep)].astype(np.int16),
        "native_lon_index": columns[np.asarray(keep)].astype(np.int16),
    }).sort_values(["native_lat_index", "native_lon_index"]).reset_index(drop=True)
    preserved = pd.read_parquet(resolve(record["preserved_basis_path"]), columns=["native_lat_index", "native_lon_index"]).drop_duplicates().sort_values(["native_lat_index", "native_lon_index"]).reset_index(drop=True)
    require(len(expected) == len(preserved) == int(record["expected_cells"]), "Rice1 cell count changed")
    require(np.array_equal(expected.to_numpy(), preserved.to_numpy()), "Rice1 legacy cell support changed")
    return {
        "preserved_basis": record["preserved_basis_path"], "exact_cell_support_unchanged": True,
        "cells": len(expected), "minimum_months": 6, "broad_annual_mirca_boolean_mask_retained": True,
    }


def validate(config_path: Path) -> dict[str, Any]:
    config, config_hash = load_config(config_path)
    frames: dict[str, pd.DataFrame] = {}
    summaries: dict[str, Any] = {}
    logical_digests: dict[str, str] = {}
    for record in config["branches"]:
        branch = record["branch"]
        frames[branch], summaries[branch], logical_digests[branch] = load_branch(config, record)
        gc.collect()
        pa.default_memory_pool().release_unused()
    require(logical_digests["ri2_noirr"] == logical_digests["ri2_firr"], "paired Rice2 branches differ despite identical source calendar arrays")
    sentinels = direct_checks(frames, config)
    expected_kinds = set(config["validation"]["sentinel_kinds"])
    require({row["sentinel_kind"] for row in sentinels} == expected_kinds, "sentinel registry differs")
    require(len(sentinels) == 2 * len(expected_kinds), "sentinel count differs")
    rice1 = rice1_regression(config)
    maximum_rss = peak_rss_bytes()
    cap = int(config["memory_cap_bytes"])
    require(maximum_rss < cap, "validator exceeded 512 MiB RSS cap")
    return {
        "schema": "hultgren_rice2_historical_multiblock_validation/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "validated_unweighted_strict_support_rice2_historical_weather_basis_not_response_damage_or_scc",
        "contract_id": CONTRACT_ID, "config": {"path": recorded_path(config_path), "sha256": config_hash},
        "source_years": [1981, 2019], "harvest_years": [1982, 2019], "harvest_year_count": 38,
        "boundary_handling": {
            "included_internal_cross_block_harvest_years": [1991, 2001, 2011],
            "excluded_harvest_years": [1981],
            "exclusion_reason": "A complete common-support 1981 harvest year is impossible because 1,616 cross-year Rice2 cells require unavailable 1980 daily weather; no partial-year support was emitted.",
        },
        "branches": summaries,
        "branch_comparison": {
            "exact_support_calendar_and_weather_equal_except_branch_label": True,
            "reason": "resident GGCMI ri2_noirr and ri2_firr calendar arrays are identical",
        },
        "direct_daily_reaggregation": {
            "sentinels": sentinels, "sentinel_count": len(sentinels),
            "tolerance": float(config["validation"]["maximum_absolute_weather_error"]),
            "maximum_absolute_weather_error": max(row["maximum_absolute_weather_error"] for row in sentinels),
        },
        "rice1_regression": rice1,
        "weighting": {
            "publisher_fraction_used_only_as_boolean_support": True, "publisher_fraction_values_emitted": False,
            "mirca_area_or_production_weight_attached": False, "weighted_statistics_reported": False,
        },
        "claim_gates": {
            "scalar_three_to_twelve_month_weather_method_validated": True,
            "strict_support_rice2_historical_weather_basis_validated": True,
            "prior_rice1_support_preserved": True,
            "mirca_weight_attachment_authorized": False, "published_response_evaluated": False,
            "response_fit_authorized": False, "damage_calculated": False, "scc_calculated": False,
        },
        "resources": {"maximum_rss_bytes": maximum_rss, "memory_cap_bytes": cap, "memory_gate_passed": True},
        "implementation": {"path": recorded_path(Path(__file__)), "sha256": digest(Path(__file__))},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=CONFIG_DEFAULT)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    require(not args.out.exists(), "fresh output required")
    result = validate(args.config)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": result["status"], "branches": result["branches"],
        "boundary_handling": result["boundary_handling"],
        "direct_daily_reaggregation": {
            "sentinel_count": result["direct_daily_reaggregation"]["sentinel_count"],
            "tolerance": result["direct_daily_reaggregation"]["tolerance"],
            "maximum_absolute_weather_error": result["direct_daily_reaggregation"]["maximum_absolute_weather_error"],
        },
        "rice1_regression": result["rice1_regression"], "resources": result["resources"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
