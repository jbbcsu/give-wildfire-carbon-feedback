#!/usr/bin/env python3
"""Align monthly CRU scPDSI to crop years and transparent stage windows.

This historical benchmark is deliberately separate from projected drought
inputs. Monthly index values are day-weighted over each crop-stage interval;
there is no interpolation or silent filling of missing months.
"""
from __future__ import annotations

import argparse
import calendar as month_calendar
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

from build_crop_stage_heat_features import parse_fractions
from build_crop_year_features import climate_array, date_from_doy


KEYS = ["harvest_year", "lat", "lon_360", "crop", "irrigation"]
COLUMNS = [
    "harvest_year", "plant_year", "lat", "lon", "lon_360", "crop", "irrigation",
    "cross_year", "stage_id", "stage_start_offset_day", "stage_end_offset_day",
    "stage_days", "stage_fractions", "scpdsi_mean", "scpdsi_min",
    "scpdsi_days_at_or_below_threshold", "scpdsi_threshold",
    "monthly_index_days_covered", "drought_index_name", "drought_source_role",
]


def _canonicalize(array: xr.DataArray) -> xr.DataArray:
    rename: dict[str, str] = {}
    if "latitude" in array.dims:
        rename["latitude"] = "lat"
    if "longitude" in array.dims:
        rename["longitude"] = "lon"
    array = array.rename(rename)
    if set(array.dims) != {"time", "lat", "lon"}:
        raise ValueError("scPDSI must have exactly time, latitude, and longitude dimensions")
    array = array.assign_coords(lon=np.mod(array.lon.values.astype(float), 360.0))
    if len(np.unique(array.lat.values)) != array.sizes["lat"] or len(np.unique(array.lon.values)) != array.sizes["lon"]:
        raise ValueError("scPDSI grid coordinates must be unique")
    return array.sortby(["lat", "lon"]).transpose("time", "lat", "lon")


def _align_index(index: xr.DataArray, calendar: xr.Dataset) -> xr.DataArray:
    index = _canonicalize(index)
    target_lat = np.sort(calendar.lat.values.astype(float))
    target_lon = np.sort(np.mod(calendar.lon.values.astype(float), 360.0))
    if index.sizes["lon"] != len(target_lon) or not np.allclose(index.lon.values, target_lon, rtol=0, atol=1e-6):
        raise ValueError("scPDSI and crop calendar longitude grids differ; regrid explicitly")
    selected = index.sel(lat=xr.DataArray(target_lat, dims="lat"), method="nearest", tolerance=1e-6)
    if not np.allclose(selected.lat.values, target_lat, rtol=0, atol=1e-6):
        raise ValueError("scPDSI and crop calendar latitude grids differ; regrid explicitly")
    return selected.assign_coords(lat=target_lat, lon=target_lon)


def _month_overlaps(start: date, end: date) -> list[tuple[tuple[int, int], int]]:
    overlaps: list[tuple[tuple[int, int], int]] = []
    current = date(start.year, start.month, 1)
    while current <= end:
        month_end = date(current.year, current.month, month_calendar.monthrange(current.year, current.month)[1])
        left, right = max(start, current), min(end, month_end)
        if left <= right:
            overlaps.append(((current.year, current.month), (right - left).days + 1))
        current = date(current.year + int(current.month == 12), current.month % 12 + 1, 1)
    return overlaps


def _stage_metrics(
    values: np.ndarray,
    month_lookup: dict[tuple[int, int], int],
    start: date,
    end: date,
    threshold: float,
) -> tuple[float, float, int, int] | None:
    weighted_sum = 0.0
    covered = 0
    below_days = 0
    observed: list[float] = []
    for key, days in _month_overlaps(start, end):
        if key not in month_lookup:
            return None
        value = float(values[month_lookup[key]])
        if not np.isfinite(value):
            return None
        weighted_sum += value * days
        covered += days
        below_days += days * int(value <= threshold)
        observed.append(value)
    expected = (end - start).days + 1
    if covered != expected or not observed:
        return None
    return weighted_sum / covered, min(observed), below_days, covered


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scpdsi", required=True)
    parser.add_argument("--variable", default="scpdsi")
    parser.add_argument("--calendar", required=True)
    parser.add_argument("--crop", required=True)
    parser.add_argument("--irrigation", required=True, choices=["firr", "noirr"])
    parser.add_argument("--year-start", type=int, required=True)
    parser.add_argument("--year-end", type=int, required=True)
    parser.add_argument("--lat-start", type=int, required=True)
    parser.add_argument("--lat-stop", type=int, required=True)
    parser.add_argument("--threshold", type=float, required=True)
    parser.add_argument("--stage-fractions", default="0,0.3,0.7,1")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    fractions = parse_fractions(args.stage_fractions)
    if args.year_end < args.year_start or args.lat_start < 0 or args.lat_stop <= args.lat_start:
        raise ValueError("Invalid year or latitude bounds")
    if not np.isfinite(args.threshold):
        raise ValueError("scPDSI threshold must be finite")

    with xr.open_dataset(args.calendar, engine="h5netcdf", decode_timedelta=False) as calendar_ds, \
         xr.open_dataset(args.scpdsi, engine="h5netcdf") as drought_ds:
        calendar = calendar_ds.isel(lat=slice(args.lat_start, args.lat_stop))
        calendar = calendar.assign_coords(lon=np.mod(calendar.lon.values.astype(float), 360.0)).sortby(["lat", "lon"])
        if missing := {"planting_day", "maturity_day"} - set(calendar.data_vars):
            raise ValueError(f"Calendar missing {sorted(missing)}")
        index = _align_index(climate_array(drought_ds, args.variable), calendar)
        try:
            timestamps = pd.DatetimeIndex(index.time.values)
        except (TypeError, ValueError) as error:
            raise ValueError("CRU historical scPDSI requires a standard monthly datetime axis") from error
        month_keys = [(int(value.year), int(value.month)) for value in timestamps]
        if len(month_keys) != len(set(month_keys)):
            raise ValueError("scPDSI time axis has duplicate year-month values")
        month_lookup = {key: position for position, key in enumerate(month_keys)}
        index_values = index.values
        planting = calendar.planting_day.values
        maturity = calendar.maturity_day.values
        latitudes = calendar.lat.values.astype(float)
        longitudes = calendar.lon.values.astype(float)
        rows: list[dict[str, object]] = []

        for harvest_year in range(args.year_start, args.year_end + 1):
            for ilat, ilon in np.ndindex(planting.shape):
                plant_doy, maturity_doy = planting[ilat, ilon], maturity[ilat, ilon]
                if not (np.isfinite(plant_doy) and np.isfinite(maturity_doy)):
                    continue
                plant_doy, maturity_doy = int(plant_doy), int(maturity_doy)
                if plant_doy < 1 or maturity_doy < 1:
                    continue
                cross_year = maturity_doy < plant_doy
                plant_year = harvest_year - int(cross_year)
                season_start = date_from_doy(plant_year, plant_doy)
                season_end = date_from_doy(harvest_year, maturity_doy)
                season_days = (season_end - season_start).days + 1
                pending: list[dict[str, object]] = []
                for stage_id, (left, right) in enumerate(zip(fractions, fractions[1:]), start=1):
                    i0, i1 = int(np.floor(left * season_days)), int(np.floor(right * season_days))
                    if i1 <= i0:
                        pending = []
                        break
                    stage_start = season_start + timedelta(days=i0)
                    stage_end = season_start + timedelta(days=i1 - 1)
                    metrics = _stage_metrics(index_values[:, ilat, ilon], month_lookup, stage_start, stage_end, args.threshold)
                    if metrics is None:
                        pending = []
                        break
                    mean_value, minimum, below_days, covered = metrics
                    pending.append({
                        "harvest_year": harvest_year, "plant_year": plant_year,
                        "lat": float(latitudes[ilat]), "lon": float(longitudes[ilon]),
                        "lon_360": float(longitudes[ilon] % 360), "crop": args.crop,
                        "irrigation": args.irrigation, "cross_year": cross_year,
                        "stage_id": stage_id, "stage_start_offset_day": i0 + 1,
                        "stage_end_offset_day": i1, "stage_days": i1 - i0,
                        "stage_fractions": args.stage_fractions, "scpdsi_mean": mean_value,
                        "scpdsi_min": minimum,
                        "scpdsi_days_at_or_below_threshold": below_days,
                        "scpdsi_threshold": args.threshold,
                        "monthly_index_days_covered": covered,
                        "drought_index_name": "CRU_TS_scpdsi",
                        "drought_source_role": "historical_benchmark_not_future_scc_input",
                    })
                if len(pending) == len(fractions) - 1:
                    rows.extend(pending)

    result = pd.DataFrame(rows, columns=COLUMNS)
    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    result.to_parquet(output, index=False)
    print(f"wrote {len(result)} crop-stage scPDSI rows; threshold={args.threshold:g}")


if __name__ == "__main__":
    main()
