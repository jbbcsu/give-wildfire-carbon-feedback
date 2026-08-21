#!/usr/bin/env python3
"""Build explicit daily maximum-temperature heat features by crop-year.

Thresholds are required command-line inputs: this script deliberately has no
universal heat threshold default.  Its output is a separate key-compatible
table, so temperature-extreme choices can be pre-specified and joined only in
the designated response specification.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

from build_crop_year_features import climate_array, date_from_doy, normalize_temperature


BASE_COLUMNS = [
    "harvest_year", "plant_year", "lat", "lon", "lon_360", "crop", "irrigation",
    "cross_year", "plant_doy", "maturity_doy", "season_days", "tmax_mean_c",
]


def threshold_name(threshold: float) -> str:
    value = f"{threshold:g}".replace("-", "m").replace(".", "p")
    return f"tmax_{value}c"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tasmax", required=True)
    parser.add_argument("--calendar", required=True)
    parser.add_argument("--crop", required=True)
    parser.add_argument("--irrigation", required=True, choices=["firr", "noirr"])
    parser.add_argument("--year-start", type=int, required=True)
    parser.add_argument("--year-end", type=int, required=True)
    parser.add_argument("--lat-start", type=int, required=True)
    parser.add_argument("--lat-stop", type=int, required=True)
    parser.add_argument("--threshold-c", action="append", type=float, required=True,
                        help="repeatable, explicitly pre-specified daily-maximum threshold in Celsius")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    thresholds = sorted(set(args.threshold_c))
    if args.year_end < args.year_start or args.lat_start < 0 or args.lat_stop <= args.lat_start:
        raise ValueError("Invalid year or latitude bounds")
    if any(not np.isfinite(value) for value in thresholds):
        raise ValueError("Heat thresholds must be finite")

    metric_columns = [item for threshold in thresholds for item in (
        f"{threshold_name(threshold)}_days", f"{threshold_name(threshold)}_degree_days",
    )]
    with xr.open_dataset(args.calendar, engine="h5netcdf", decode_timedelta=False) as calendar, \
         xr.open_dataset(args.tasmax, engine="h5netcdf") as maximum_ds:
        maximum = climate_array(maximum_ds, "tasmax").isel(lat=slice(args.lat_start, args.lat_stop))
        cal = calendar.isel(lat=slice(args.lat_start, args.lat_stop))
        required = {"planting_day", "maturity_day"}
        if missing := required - set(cal.data_vars):
            raise ValueError(f"Calendar missing {sorted(missing)}")
        if not (np.array_equal(maximum.lat, cal.lat) and np.array_equal(maximum.lon, cal.lon)):
            raise ValueError("tasmax and calendar coordinates differ; regrid explicitly before construction")
        dates = pd.DatetimeIndex(maximum.time.values)
        tmax = normalize_temperature(maximum.values, maximum.attrs.get("units", ""))
        planting, maturity = cal.planting_day.values, cal.maturity_day.values
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
                start = pd.Timestamp(date_from_doy(plant_year, plant_doy))
                end = pd.Timestamp(date_from_doy(harvest_year, maturity_doy))
                where = (dates >= start) & (dates <= end)
                if where.sum() != (end - start).days + 1:
                    continue
                values = tmax[where, ilat, ilon]
                if not np.isfinite(values).all():
                    continue
                row: dict[str, object] = {
                    "harvest_year": harvest_year, "plant_year": plant_year,
                    "lat": float(cal.lat.values[ilat]), "lon": float(cal.lon.values[ilon]),
                    "lon_360": float(cal.lon.values[ilon] % 360), "crop": args.crop,
                    "irrigation": args.irrigation, "cross_year": cross_year,
                    "plant_doy": plant_doy, "maturity_doy": maturity_doy,
                    "season_days": len(values), "tmax_mean_c": float(np.mean(values, dtype=np.float64)),
                }
                for threshold in thresholds:
                    name = threshold_name(threshold)
                    excess = np.maximum(values.astype(np.float64) - threshold, 0)
                    row[f"{name}_days"] = int((values >= threshold).sum())
                    row[f"{name}_degree_days"] = float(excess.sum())
                rows.append(row)
    result = pd.DataFrame(rows, columns=BASE_COLUMNS + metric_columns)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    result.to_parquet(args.out, index=False)
    print(f"wrote {len(result)} crop-year heat rows; thresholds={','.join(f'{x:g}' for x in thresholds)} C")


if __name__ == "__main__":
    main()
