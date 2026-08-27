#!/usr/bin/env python3
"""Build a latitude-chunk crop-year feature table from daily ISIMIP fields.

This deliberately works on bounded latitude chunks: global daily NetCDF files
are multi-gigabyte. It creates one row per valid cell/crop-year and must be run
before spatial aggregation. `pr` is converted to mm/day when units are a mass
flux; `tas` is converted from K to °C when appropriate.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

from climate_inputs import open_daily_crop_window, validate_daily_units

FEATURE_COLUMNS = [
    "harvest_year", "plant_year", "lat", "lon", "lon_360", "crop", "irrigation", "cross_year",
    "plant_doy", "maturity_doy", "season_days", "tmean_c", "precip_mm", "wet_days_n",
    "cdd_max_days", "rx1day_mm", "rx5day_mm", "wet_day_threshold_mm",
]

def normalize_precip(values: np.ndarray, units: str) -> np.ndarray:
    canonical = validate_daily_units("pr", units)
    flux_units = {"kgm-2s-1", "kgm**-2s**-1", "kg/m2/s", "kgm^-2s^-1"}
    if canonical in flux_units:
        return values * 86400.0
    return values


def normalize_temperature(values: np.ndarray, units: str) -> np.ndarray:
    canonical = validate_daily_units("tas", units)
    if canonical in {"k", "kelvin"}:
        return values - 273.15
    return values


def validate_wet_day_threshold(value: float) -> float:
    if not np.isfinite(value) or value <= 0:
        raise ValueError("Wet-day threshold must be finite and strictly positive")
    return float(value)


def date_from_doy(year: int, doy: int) -> date:
    return date(year, 1, 1) + timedelta(days=doy - 1)


def max_run(mask: np.ndarray) -> int:
    longest = current = 0
    for value in mask:
        current = current + 1 if bool(value) else 0
        longest = max(longest, current)
    return longest


def rolling_max(values: np.ndarray, width: int) -> float:
    if len(values) < width:
        return np.nan
    # ISIMIP arrays are commonly float32.  Accumulate in float64 so a
    # five-day subtotal cannot exceed the separately accumulated season total
    # purely because the two operations rounded differently.
    values64 = np.asarray(values, dtype=np.float64)
    return float(np.convolve(values64, np.ones(width), mode="valid").max())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--precip", required=True, nargs="+", help="Chronological daily ISIMIP pr NetCDF file(s) covering requested crop-years")
    parser.add_argument("--temperature", required=True, nargs="+", help="Chronological daily ISIMIP tas NetCDF file(s) covering requested crop-years")
    parser.add_argument("--calendar", required=True)
    parser.add_argument("--crop", required=True)
    parser.add_argument("--irrigation", required=True, choices=["firr", "noirr"])
    parser.add_argument("--year-start", required=True, type=int)
    parser.add_argument("--year-end", required=True, type=int)
    parser.add_argument("--lat-start", required=True, type=int)
    parser.add_argument("--lat-stop", required=True, type=int)
    parser.add_argument("--out", required=True)
    parser.add_argument("--wet-day-mm", type=float, default=1.0)
    args = parser.parse_args()
    args.wet_day_mm = validate_wet_day_threshold(args.wet_day_mm)

    with ExitStack() as stack:
        calendar = stack.enter_context(xr.open_dataset(args.calendar, engine="h5netcdf", decode_timedelta=False))
        required = {"planting_day", "maturity_day"}
        if missing := required - set(calendar.data_vars):
            raise ValueError(f"Calendar missing {sorted(missing)}")
        pr = open_daily_crop_window(
            stack, args.precip, "pr", args.year_start, args.year_end,
            args.lat_start, args.lat_stop,
        )
        tas = open_daily_crop_window(
            stack, args.temperature, "tas", args.year_start, args.year_end,
            args.lat_start, args.lat_stop,
        )
        cal = calendar.isel(lat=slice(args.lat_start, args.lat_stop))
        if not (np.array_equal(pr.lat, cal.lat) and np.array_equal(pr.lon, cal.lon)):
            raise ValueError("Climate and calendar coordinates differ; regrid explicitly before feature construction")
        if not np.array_equal(pr.time, tas.time):
            raise ValueError("Precipitation and temperature time axes differ")

        # Crop calendars are date (DOY) based.  ISIMIP daily timestamps can be
        # stamped at noon, so compare calendar dates rather than instants;
        # otherwise the final day of every season is silently excluded.
        dates = pd.DatetimeIndex(pr.time.values).normalize()
        pr_values = normalize_precip(pr.values, pr.attrs.get("units", ""))
        tas_values = normalize_temperature(tas.values, tas.attrs.get("units", ""))
        planting, maturity = cal.planting_day.values, cal.maturity_day.values
        rows: list[dict[str, float | int | str | bool]] = []

        for harvest_year in range(args.year_start, args.year_end + 1):
            for ilat, ilon in np.ndindex(planting.shape):
                plant_doy, harvest_doy = planting[ilat, ilon], maturity[ilat, ilon]
                if not (np.isfinite(plant_doy) and np.isfinite(harvest_doy)):
                    continue
                plant_doy, harvest_doy = int(plant_doy), int(harvest_doy)
                if plant_doy < 1 or harvest_doy < 1:
                    continue
                cross_year = harvest_doy < plant_doy
                plant_year = harvest_year - int(cross_year)
                start = pd.Timestamp(date_from_doy(plant_year, plant_doy))
                end = pd.Timestamp(date_from_doy(harvest_year, harvest_doy))
                where = (dates >= start) & (dates <= end)
                if where.sum() != (end - start).days + 1:
                    continue  # no silent infill at input-file edges
                rain = pr_values[where, ilat, ilon]
                temp = tas_values[where, ilat, ilon]
                if not (np.isfinite(rain).all() and np.isfinite(temp).all()) or (rain < 0).any():
                    continue
                rows.append({
                    "harvest_year": harvest_year, "plant_year": plant_year,
                    "lat": float(cal.lat.values[ilat]), "lon": float(cal.lon.values[ilon]),
                    "lon_360": float(cal.lon.values[ilon] % 360),
                    "crop": args.crop, "irrigation": args.irrigation, "cross_year": cross_year,
                    "plant_doy": plant_doy, "maturity_doy": harvest_doy,
                    "season_days": len(rain), "tmean_c": float(temp.mean()),
                    "precip_mm": float(np.sum(rain, dtype=np.float64)), "wet_days_n": int((rain >= args.wet_day_mm).sum()),
                    "cdd_max_days": max_run(rain < args.wet_day_mm),
                    "rx1day_mm": float(rain.max()), "rx5day_mm": rolling_max(rain, 5),
                    "wet_day_threshold_mm": args.wet_day_mm,
                })
    result = pd.DataFrame(rows, columns=FEATURE_COLUMNS)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    result.to_parquet(args.out, index=False)
    print(f"wrote {len(result)} crop-year rows to {args.out}")


if __name__ == "__main__":
    main()
