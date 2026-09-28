#!/usr/bin/env python3
"""Independently validate the strict-support 1982 Rice2 weather pilot."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import resource
import sys
import tomllib
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import rasterio
import xarray as xr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.hultgren_crop_calendar import calendar_months_for_report_year, season_months, source_month_from_day
from src.hultgren_rice_weather import build_rice_weather_basis_from_daily

CONFIG_DEFAULT = ROOT / "config/hultgren_rice2_one_year_pilot_v1.toml"
CONTRACT_ID = "hultgren_rice2_one_year_pilot_v1"
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
    require(config.get("harvest_year") == 1982, "pilot harvest year changed")
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
    implementation = config["implementation"]
    for key in ("weather_module", "builder", "weather_test", "builder_test"):
        source = resolve(implementation[f"{key}_path"])
        require(digest(source) == implementation[f"{key}_sha256"], f"implementation hash differs: {key}")
    support = config["support"]
    require(support["rice1_substitution_authorized"] is False, "Rice1 substitution opened")
    require(support["calendar_fill_authorized"] is False, "calendar fill opened")
    require(support["support_values_as_weights_authorized"] is False, "support weighting opened")
    gates = config["claim_gates"]
    require(gates["unweighted_weather_pilot_authorized"] is True, "pilot not authorized")
    for key, value in gates.items():
        if key != "unweighted_weather_pilot_authorized":
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


def load_branch(config: dict[str, Any], record: dict[str, Any]) -> tuple[pd.DataFrame, dict[str, Any], dict[str, Any]]:
    branch = record["branch"]
    receipt = json.loads(resolve(record["build_receipt_path"]).read_text(encoding="utf-8"))
    require(receipt["status"] == "complete_unweighted_rice_calendar_branch_basis_not_response_damage_or_scc", f"build failed: {branch}")
    require(receipt["calendar_branch"] == branch, f"receipt branch differs: {branch}")
    require(receipt["harvest_years"] == [1982, 1982], f"harvest year differs: {branch}")
    require(receipt["implementation"]["sha256"] == config["implementation"]["builder_sha256"], f"builder hash differs: {branch}")
    for variable in ("pr", "tasmin", "tasmax"):
        require(receipt["sources"][variable]["sha512"] == config["weather"][f"{variable}_sha512"], f"weather hash differs: {variable}")
    support_audit = receipt["support_audit"]
    require(support_audit["publisher_fraction_used_only_as_boolean_support"] is True, f"strict support absent: {branch}")
    require(support_audit["support_magnitudes_used_as_weights"] is False, f"support weighting used: {branch}")
    require(support_audit["rice1_calendar_or_weather_substituted"] is False, f"Rice1 substituted: {branch}")
    require(support_audit["annual_mirca_inputs_used"] is False, f"annual MIRCA used: {branch}")
    schema = pq.read_schema(resolve(record["basis_path"])).names
    prohibited = [column for column in schema if any(part in column.lower() for part in ("area", "weight", "production", "yield", "response", "damage", "scc"))]
    require(not prohibited, f"prohibited output columns: {prohibited}")
    frame = pd.read_parquet(resolve(record["basis_path"]))
    require(frame.calendar_branch.eq(branch).all(), f"output branch differs: {branch}")
    require(frame.complete.all(), f"incomplete weather rows: {branch}")
    require(frame.harvest_year.eq(1982).all(), f"output year differs: {branch}")
    require(np.isfinite(frame[WEATHER].to_numpy(dtype=np.float64)).all(), f"nonfinite weather: {branch}")
    require(not frame.duplicated(KEYS).any(), f"duplicate keys: {branch}")
    expected, distribution = calendar_support(resolve(record["calendar_path"]), 3)
    observed = frame[["native_lat_index", "native_lon_index", "latitude", "longitude", *CALENDAR]].sort_values(["native_lat_index", "native_lon_index"]).reset_index(drop=True)
    require(len(expected) == len(observed) == int(config["support"]["required_cells_per_branch"]), f"strict support count differs: {branch}")
    for column in expected.columns:
        require(
            np.array_equal(expected[column].to_numpy(), observed[column].to_numpy()),
            f"output strict calendar field differs: {branch} {column}",
        )
    short = frame.season_months.lt(6)
    structural_zero = frame.loc[short, ["prcp_poly_1_bin3", "prcp_poly_2_bin3"]].to_numpy(dtype=np.float64)
    require(np.count_nonzero(structural_zero) == 0, f"short-season third phase is nonzero: {branch}")
    summary = {
        "path": record["basis_path"], "sha256": record["basis_sha256"],
        "rows": len(frame), "calendar_month_distribution": distribution,
        "cross_year_rows": int(frame.cross_year.sum()),
        "three_to_five_month_rows": int(short.sum()),
        "short_season_third_phase_nonzero_values": int(np.count_nonzero(structural_zero)),
        "build_peak_rss_bytes": int(receipt["resources"]["peak_rss_bytes"]),
        "build_wall_seconds": float(receipt["wall_seconds"]),
    }
    return frame.sort_values(KEYS).reset_index(drop=True), summary, receipt


def select_sentinels(frame: pd.DataFrame) -> list[tuple[str, pd.Series]]:
    ordered = frame.sort_values(["native_lat_index", "native_lon_index"]).reset_index(drop=True)
    result: list[tuple[str, pd.Series]] = []
    for label, length in (("three_month", 3), ("four_month", 4), ("five_month", 5)):
        candidates = ordered.loc[ordered.season_months.eq(length) & ~ordered.cross_year]
        require(not candidates.empty, f"no {label} same-year sentinel")
        result.append((label, candidates.iloc[0]))
    cross = ordered.loc[ordered.cross_year]
    require(not cross.empty, "no cross-year sentinel")
    result.append(("cross_year", cross.iloc[0]))
    return result


def direct_checks(frames: dict[str, pd.DataFrame], config: dict[str, Any]) -> list[dict[str, Any]]:
    weather = config["weather"]
    paths = {name: resolve(weather[f"{name}_path"]) for name in ("pr", "tasmin", "tasmax")}
    tolerance = float(config["validation"]["maximum_absolute_weather_error"])
    results: list[dict[str, Any]] = []
    with xr.open_dataset(paths["pr"], engine="h5netcdf", decode_times=True, cache=False) as pr, xr.open_dataset(
        paths["tasmin"], engine="h5netcdf", decode_times=True, cache=False
    ) as tasmin, xr.open_dataset(paths["tasmax"], engine="h5netcdf", decode_times=True, cache=False) as tasmax:
        dates = pd.DatetimeIndex(pr.time.values).normalize()
        require(dates.equals(pd.DatetimeIndex(tasmin.time.values).normalize()), "pr/tasmin chronology differs")
        require(dates.equals(pd.DatetimeIndex(tasmax.time.values).normalize()), "pr/tasmax chronology differs")
        lookup = {stamp.date(): position for position, stamp in enumerate(dates)}
        for branch, frame in frames.items():
            for kind, row in select_sentinels(frame):
                records = []
                month_keys = calendar_months_for_report_year(
                    int(row.harvest_year), int(row.plant_month), int(row.harvest_month), "USA"
                )
                for year, month in month_keys:
                    start = pd.Timestamp(year=year, month=month, day=1)
                    for stamp in pd.date_range(start, start + pd.offsets.MonthEnd(0), freq="D"):
                        position = lookup[stamp.date()]
                        i, j = int(row.native_lat_index), int(row.native_lon_index)
                        records.append((
                            date(stamp.year, stamp.month, stamp.day),
                            float(pr.pr.isel(time=position, lat=i, lon=j).values) * 86_400.0,
                            float(tasmin.tasmin.isel(time=position, lat=i, lon=j).values) - 273.15,
                            float(tasmax.tasmax.isel(time=position, lat=i, lon=j).values) - 273.15,
                        ))
                rebuilt = build_rice_weather_basis_from_daily(
                    records, report_year=int(row.harvest_year),
                    plant_month=int(row.plant_month), harvest_month=int(row.harvest_month), iso="USA",
                )
                expected = {
                    "gdd": rebuilt.gdd, "kdd": rebuilt.kdd, "tmin": rebuilt.tmin,
                    **{f"prcp_poly_1_bin{index}": value for index, value in enumerate(rebuilt.prcp_poly_1_bins, 1)},
                    **{f"prcp_poly_2_bin{index}": value for index, value in enumerate(rebuilt.prcp_poly_2_bins, 1)},
                }
                errors = {column: abs(float(row[column]) - value) for column, value in expected.items()}
                maximum = max(errors.values())
                require(maximum <= tolerance, f"direct reaggregation differs: {branch} {kind} {errors}")
                results.append({
                    "branch": branch, "sentinel_kind": kind,
                    "native_lat_index": int(row.native_lat_index),
                    "native_lon_index": int(row.native_lon_index),
                    "latitude": float(row.latitude), "longitude": float(row.longitude),
                    "plant_month": int(row.plant_month), "harvest_month": int(row.harvest_month),
                    "season_months": int(row.season_months), "cross_year": bool(row.cross_year),
                    "daily_records_reaggregated": len(records),
                    "maximum_absolute_weather_error": maximum,
                    "absolute_errors": errors,
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
    preserved = pd.read_parquet(
        resolve(record["preserved_basis_path"]), columns=["native_lat_index", "native_lon_index"]
    ).drop_duplicates().sort_values(["native_lat_index", "native_lon_index"]).reset_index(drop=True)
    require(len(expected) == len(preserved) == int(record["expected_cells"]), "Rice1 cell count changed")
    require(
        np.array_equal(expected.to_numpy(), preserved.to_numpy()),
        "Rice1 legacy cell support changed",
    )
    return {
        "preserved_basis": record["preserved_basis_path"],
        "exact_cell_support_unchanged": True,
        "cells": len(expected), "minimum_months": 6,
        "broad_annual_mirca_boolean_mask_retained": True,
    }


def validate(config_path: Path) -> dict[str, Any]:
    config, config_hash = load_config(config_path)
    frames: dict[str, pd.DataFrame] = {}
    branch_summaries: dict[str, Any] = {}
    build_receipts: dict[str, Any] = {}
    for record in config["branches"]:
        frame, summary, receipt = load_branch(config, record)
        frames[record["branch"]] = frame
        branch_summaries[record["branch"]] = summary
        build_receipts[record["branch"]] = {
            "path": record["build_receipt_path"], "sha256": record["build_receipt_sha256"]
        }
    left = frames["ri2_noirr"].drop(columns=["calendar_branch"])
    right = frames["ri2_firr"].drop(columns=["calendar_branch"])
    require(left.equals(right), "paired Rice2 branches differ despite identical source calendar arrays")
    sentinels = direct_checks(frames, config)
    require({row["sentinel_kind"] for row in sentinels} == set(config["validation"]["sentinel_kinds"]), "sentinel registry differs")
    require(len(sentinels) == 8, "expected four direct sentinels per branch")
    rice1 = rice1_regression(config)
    maximum_rss = peak_rss_bytes()
    cap = int(config["memory_cap_bytes"])
    require(maximum_rss < cap, "validator exceeded 512 MiB RSS cap")
    return {
        "schema": "hultgren_rice2_one_year_pilot_validation/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "validated_unweighted_strict_support_rice2_weather_pilot_not_response_damage_or_scc",
        "contract_id": CONTRACT_ID,
        "config": {"path": recorded_path(config_path), "sha256": config_hash},
        "harvest_year": 1982,
        "branches": branch_summaries,
        "build_receipts": build_receipts,
        "branch_comparison": {
            "exact_support_calendar_and_weather_equal_except_branch_label": True,
            "reason": "resident GGCMI ri2_noirr and ri2_firr calendar arrays are identical",
        },
        "direct_daily_reaggregation": {
            "sentinels": sentinels,
            "sentinel_count": len(sentinels),
            "maximum_absolute_weather_error": max(row["maximum_absolute_weather_error"] for row in sentinels),
        },
        "rice1_regression": rice1,
        "weighting": {
            "publisher_fraction_used_only_as_boolean_support": True,
            "publisher_fraction_values_emitted": False,
            "mirca_area_or_production_weight_attached": False,
            "weighted_statistics_reported": False,
        },
        "claim_gates": {
            "scalar_three_to_twelve_month_weather_method_validated": True,
            "strict_support_rice2_one_year_weather_pilot_validated": True,
            "prior_rice1_support_preserved": True,
            "multi_year_rice2_basis_validated": False,
            "mirca_weight_attachment_authorized": False,
            "published_response_evaluated": False,
            "response_fit_authorized": False,
            "damage_calculated": False,
            "scc_calculated": False,
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
        "direct_daily_reaggregation": result["direct_daily_reaggregation"],
        "rice1_regression": result["rice1_regression"], "resources": result["resources"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
