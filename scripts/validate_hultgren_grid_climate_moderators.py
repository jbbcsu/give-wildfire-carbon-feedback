#!/usr/bin/env python3
"""Independently recompute sampled moderator rows from raw daily files."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import xarray as xr

ROOT = Path(__file__).resolve().parents[1]


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def month_keys(harvest_year: int, plant_month: int, harvest_month: int) -> list[tuple[int, int]]:
    if plant_month < harvest_month:
        months = list(range(plant_month, harvest_month + 1))
    else:
        months = list(range(plant_month, 13)) + list(range(1, harvest_month + 1))
    return [(harvest_year - 1 if plant_month >= harvest_month and month >= plant_month else harvest_year, month)
            for month in months]


def raw_recompute(
    pr: xr.Dataset, tasmax: xr.Dataset, row: pd.Series,
) -> tuple[float, float]:
    rain_months: list[float] = []
    tmax_months: list[float] = []
    lat = int(row.native_lat_index)
    lon = int(row.native_lon_index)
    for year, month in month_keys(int(row.harvest_year), int(row.plant_month), int(row.harvest_month)):
        start = f"{year:04d}-{month:02d}-01"
        end = (pd.Timestamp(start) + pd.offsets.MonthEnd(0)).strftime("%Y-%m-%d")
        rain = np.asarray(pr.pr.sel(time=slice(start, end)).isel(lat=lat, lon=lon).values, dtype=np.float64)
        heat = np.asarray(tasmax.tasmax.sel(time=slice(start, end)).isel(lat=lat, lon=lon).values, dtype=np.float64)
        require(len(rain) == pd.Period(start).days_in_month == len(heat), "raw month is incomplete")
        require(np.isfinite(rain).all() and np.isfinite(heat).all(), "raw sample is nonfinite")
        rain_months.append(float(np.maximum(rain * 86_400.0, 0.0).sum()))
        tmax_months.append(float((heat - 273.15).mean()))
    return float(np.mean(tmax_months)), float(np.mean(rain_months))


def selected_rows(path: Path) -> pd.DataFrame:
    parquet = pq.ParquetFile(path)
    years = sorted(pq.read_table(path, columns=["harvest_year"]).column(0).unique().to_pylist())
    selected_years = sorted({years[0], years[len(years) // 2], years[-1]})
    pieces = []
    for year in selected_years:
        frame = pq.read_table(path, filters=[("harvest_year", "=", year)]).to_pandas()
        positions = sorted({0, len(frame) // 2, len(frame) - 1})
        pieces.append(frame.iloc[positions])
    return pd.concat(pieces, ignore_index=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", action="append", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--absolute-tolerance", type=float, default=1e-8)
    args = parser.parse_args()
    require(not args.receipt.exists(), "fresh receipt required")

    audits = []
    overall_maximum = 0.0
    for path in args.input:
        source_receipt_path = path.with_suffix(path.suffix + ".result.json")
        source = json.loads(source_receipt_path.read_text(encoding="utf-8"))
        require(source["status"] == "alternative_product_cell_year_moderators_not_author_30yr_triangular_average", "source failed")
        require(digest(path) == source["output"]["sha256"], "source output hash differs")
        rows = selected_rows(path)
        pr_path = ROOT / source["sources"]["pr"]["path"]
        tasmax_path = ROOT / source["sources"]["tasmax"]["path"]
        require(pr_path.stat().st_size == source["sources"]["pr"]["bytes"], "raw precipitation size differs")
        require(tasmax_path.stat().st_size == source["sources"]["tasmax"]["bytes"], "raw Tmax size differs")
        errors = []
        with xr.open_dataset(pr_path, engine="h5netcdf", decode_times=True, cache=False) as pr, xr.open_dataset(
            tasmax_path, engine="h5netcdf", decode_times=True, cache=False
        ) as tasmax:
            for _, row in rows.iterrows():
                expected_tmax, expected_precip = raw_recompute(pr, tasmax, row)
                errors.extend([
                    abs(expected_tmax - float(row.season_mean_monthly_tmax_c)),
                    abs(expected_precip - float(row.season_mean_monthly_precip_mm)),
                ])
        maximum = max(errors)
        require(maximum <= args.absolute_tolerance, f"raw recomputation differs for {path}: {maximum}")
        overall_maximum = max(overall_maximum, maximum)
        audits.append({
            "path": str(path), "sha256": digest(path), "regime": source["regime"],
            "source_period": source["source_period"], "sampled_rows": len(rows),
            "maximum_absolute_difference": maximum,
        })
    receipt = {
        "schema": "hultgren_grid_climate_moderator_validation/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "independent_raw_daily_sample_validation_passed",
        "absolute_tolerance": args.absolute_tolerance,
        "maximum_absolute_difference": overall_maximum,
        "inputs": audits,
        "method": "deterministic first/middle/last cell samples in first/middle/last harvest years recomputed directly from scalar raw daily precipitation and Tmax series",
        "claim_gates": {
            "raw_daily_sample_arithmetic_validated": True,
            "author_long_run_moderator_reproduced": False,
            "damage_or_scc_validated": False,
        },
        "implementation": {"path": str(Path(__file__).resolve().relative_to(ROOT)), "sha256": digest(Path(__file__).resolve())},
    }
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
