#!/usr/bin/env python3
"""Build cell-year long-run-climate moderator inputs for Hultgren transport.

This alternative-product builder reproduces the definitions documented in the
authors' historical Stata file: growing-season maximum temperature and
precipitation expressed as an average over crop-season months. It does not
reproduce the authors' GMFD/SAGE 30-year triangular moving averages.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import xarray as xr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_hultgren_grid_weather_basis import crop_month_keys, load_support, recorded_path


def digest(path: Path, algorithm: str = "sha256") -> str:
    value = hashlib.new(algorithm)
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def validate_source(dataset: xr.Dataset, variable: str, units: str, start_year: int, end_year: int) -> pd.DatetimeIndex:
    require(variable in dataset and dataset[variable].dims == ("time", "lat", "lon"), f"{variable} schema changed")
    require(dataset[variable].attrs.get("units") == units, f"{variable} units changed")
    require(np.array_equal(dataset.lat.values, 89.75 - 0.5 * np.arange(360)), f"{variable} latitude changed")
    require(np.array_equal(dataset.lon.values, -179.75 + 0.5 * np.arange(720)), f"{variable} longitude changed")
    dates = pd.DatetimeIndex(dataset.time.values).normalize()
    expected = pd.date_range(f"{start_year}-01-01", f"{end_year}-12-31", freq="D")
    require(dates.equals(expected), f"{variable} chronology differs")
    return dates


def stream_monthly(
    pr_path: Path, tasmax_path: Path, support: pd.DataFrame, start_year: int, end_year: int
) -> tuple[pd.DatetimeIndex, np.ndarray, np.ndarray, dict[str, object]]:
    flat = (
        support.native_lat_index.to_numpy(dtype=np.int64) * 720
        + support.native_lon_index.to_numpy(dtype=np.int64)
    )
    months = pd.date_range(f"{start_year}-01-01", f"{end_year}-12-01", freq="MS")
    shape = (len(months), len(support))
    rain = np.zeros(shape, dtype=np.float64)
    tmax_sum = np.zeros(shape, dtype=np.float64)
    counts = np.zeros(shape, dtype=np.int16)
    missing_pairs = 0
    with xr.open_dataset(pr_path, engine="h5netcdf", decode_times=True, cache=False) as pr, xr.open_dataset(
        tasmax_path, engine="h5netcdf", decode_times=True, cache=False
    ) as tasmax:
        dates = validate_source(pr, "pr", "kg m-2 s-1", start_year, end_year)
        require(dates.equals(validate_source(tasmax, "tasmax", "K", start_year, end_year)), "pr/tasmax dates differ")
        for position, day in enumerate(dates):
            daily_rain = np.asarray(pr.pr.isel(time=position).values, dtype=np.float64).reshape(-1)[flat] * 86_400.0
            daily_tmax = np.asarray(tasmax.tasmax.isel(time=position).values, dtype=np.float64).reshape(-1)[flat] - 273.15
            complete = np.isfinite(daily_rain) & np.isfinite(daily_tmax)
            missing_pairs += int(np.count_nonzero(~complete))
            require(not np.any(daily_rain[complete] < -1e-10), "negative precipitation on crop support")
            month_index = (day.year - start_year) * 12 + day.month - 1
            rain[month_index, complete] += np.maximum(daily_rain[complete], 0.0)
            tmax_sum[month_index, complete] += daily_tmax[complete]
            counts[month_index, complete] += 1
    expected = months.days_in_month.to_numpy(dtype=np.int16)[:, None]
    complete_months = counts == expected
    rain[~complete_months] = np.nan
    monthly_tmax = np.full(shape, np.nan, dtype=np.float64)
    monthly_tmax[complete_months] = tmax_sum[complete_months] / counts[complete_months]
    return months, rain, monthly_tmax, {
        "daily_steps": len(dates), "support_cells": len(support),
        "support_missing_daily_pairs": missing_pairs,
        "incomplete_cell_months": int(np.count_nonzero(~complete_months)),
    }


def annual_frame(
    year: int, months: pd.DatetimeIndex, rain: np.ndarray, monthly_tmax: np.ndarray, support: pd.DataFrame
) -> pd.DataFrame:
    lookup = {(value.year, value.month): index for index, value in enumerate(months)}
    records = []
    for cell, row in support.iterrows():
        keys = crop_month_keys(year, int(row.plant_month), int(row.harvest_month))
        require(all(key in lookup for key in keys), f"source period lacks crop season {keys}")
        indices = [lookup[key] for key in keys]
        cell_rain = rain[indices, cell]
        cell_tmax = monthly_tmax[indices, cell]
        complete = bool(np.isfinite(cell_rain).all() and np.isfinite(cell_tmax).all())
        records.append({
            "harvest_year": year,
            "native_lat_index": int(row.native_lat_index),
            "native_lon_index": int(row.native_lon_index),
            "latitude": float(row.latitude), "longitude": float(row.longitude),
            "plant_month": int(row.plant_month), "harvest_month": int(row.harvest_month),
            "season_months": len(keys), "cross_year": int(row.plant_month) >= int(row.harvest_month),
            "mirca_area_ha": float(row.mirca_area_ha), "complete": complete,
            "season_mean_monthly_tmax_c": float(np.mean(cell_tmax)) if complete else np.nan,
            "season_mean_monthly_precip_mm": float(np.mean(cell_rain)) if complete else np.nan,
        })
    return pd.DataFrame(records)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pr", type=Path, required=True)
    parser.add_argument("--tasmax", type=Path, required=True)
    parser.add_argument("--calendar", type=Path, required=True)
    parser.add_argument("--area", type=Path, required=True)
    parser.add_argument("--regime", choices=("rainfed", "irrigated"), required=True)
    parser.add_argument("--source-start-year", type=int, required=True)
    parser.add_argument("--source-end-year", type=int, required=True)
    parser.add_argument("--harvest-year-start", type=int, required=True)
    parser.add_argument("--harvest-year-end", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result_path = args.output.with_suffix(args.output.suffix + ".result.json")
    partial_path = args.output.with_suffix(args.output.suffix + ".partial")
    require(not args.output.exists() and not result_path.exists() and not partial_path.exists(), "fresh outputs required")
    require(args.source_start_year <= args.harvest_year_start <= args.harvest_year_end <= args.source_end_year, "year range invalid")

    support, support_audit = load_support(args.calendar, args.area)
    months, rain, monthly_tmax, stream_audit = stream_monthly(
        args.pr, args.tasmax, support, args.source_start_year, args.source_end_year
    )
    writer: pq.ParquetWriter | None = None
    rows = 0
    try:
        for year in range(args.harvest_year_start, args.harvest_year_end + 1):
            frame = annual_frame(year, months, rain, monthly_tmax, support)
            require(frame.complete.all(), f"incomplete moderator seasons in {year}")
            require(np.isfinite(frame[["season_mean_monthly_tmax_c", "season_mean_monthly_precip_mm"]].to_numpy()).all(), "nonfinite moderators")
            table = pa.Table.from_pandas(frame, preserve_index=False)
            if writer is None:
                args.output.parent.mkdir(parents=True, exist_ok=True)
                writer = pq.ParquetWriter(partial_path, table.schema, compression="zstd")
            writer.write_table(table)
            rows += len(frame)
    except Exception:
        if writer is not None:
            writer.close()
        if partial_path.exists():
            partial_path.unlink()
        raise
    require(writer is not None, "no harvest years requested")
    writer.close()
    os.replace(partial_path, args.output)
    result = {
        "schema": "hultgren_grid_climate_moderator_input/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "alternative_product_cell_year_moderators_not_author_30yr_triangular_average",
        "regime": args.regime,
        "source_period": [args.source_start_year, args.source_end_year],
        "harvest_years": [args.harvest_year_start, args.harvest_year_end],
        "sources": {
            "pr": {"path": recorded_path(args.pr), "bytes": args.pr.stat().st_size, "sha512": digest(args.pr, "sha512")},
            "tasmax": {"path": recorded_path(args.tasmax), "bytes": args.tasmax.stat().st_size, "sha512": digest(args.tasmax, "sha512")},
            "calendar": {"path": recorded_path(args.calendar), "bytes": args.calendar.stat().st_size, "sha256": digest(args.calendar)},
            "area": {"path": recorded_path(args.area), "bytes": args.area.stat().st_size, "sha256": digest(args.area)},
        },
        "support_audit": support_audit, "stream_audit": stream_audit,
        "output": {"path": recorded_path(args.output), "bytes": args.output.stat().st_size, "sha256": digest(args.output), "rows": rows},
        "definitions": {
            "season_mean_monthly_tmax_c": "unweighted mean of daily-mean monthly Tmax over whole crop-season months",
            "season_mean_monthly_precip_mm": "unweighted mean of monthly precipitation totals over whole crop-season months",
        },
        "claim_gates": {"cell_year_transformation_complete": True, "author_long_run_moderator_reproduction": False, "response_damage_or_scc": False},
        "implementation": {"path": str(Path(__file__).resolve().relative_to(ROOT)), "sha256": digest(Path(__file__).resolve())},
    }
    result_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "output": result["output"], "stream_audit": stream_audit}, indent=2))


if __name__ == "__main__":
    main()
