#!/usr/bin/env python3
"""Build stage-resolved daily maximum-temperature features by crop-year.

Thresholds are explicit inputs. Fractional stages are transparent temporal
proxies and use the same boundary rule as ``build_crop_stage_features.py``.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

from build_crop_heat_features import threshold_name
from build_crop_year_features import date_from_doy, normalize_temperature
from climate_inputs import open_daily_crop_window


BASE_COLUMNS = [
    "harvest_year", "plant_year", "lat", "lon", "lon_360", "crop", "irrigation",
    "cross_year", "stage_id", "stage_start_offset_day", "stage_end_offset_day",
    "stage_days", "stage_fractions", "tmax_mean_c",
]


def parse_fractions(value: str) -> list[float]:
    fractions = [float(item) for item in value.split(",")]
    if (
        len(fractions) < 2
        or not np.isfinite(fractions).all()
        or fractions[0] != 0
        or fractions[-1] != 1
        or any(left >= right for left, right in zip(fractions, fractions[1:]))
    ):
        raise ValueError("Stage fractions must start at 0, end at 1, and strictly increase")
    return fractions


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tasmax", required=True, nargs="+")
    parser.add_argument("--calendar", required=True)
    parser.add_argument("--crop", required=True)
    parser.add_argument("--irrigation", required=True, choices=["firr", "noirr"])
    parser.add_argument("--year-start", type=int, required=True)
    parser.add_argument("--year-end", type=int, required=True)
    parser.add_argument("--lat-start", type=int, required=True)
    parser.add_argument("--lat-stop", type=int, required=True)
    parser.add_argument("--threshold-c", action="append", type=float, required=True)
    parser.add_argument("--stage-fractions", default="0,0.3,0.7,1")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    thresholds = sorted(set(args.threshold_c))
    fractions = parse_fractions(args.stage_fractions)
    if args.year_end < args.year_start or args.lat_start < 0 or args.lat_stop <= args.lat_start:
        raise ValueError("Invalid year or latitude bounds")
    if any(not np.isfinite(value) for value in thresholds):
        raise ValueError("Heat thresholds must be finite")

    metric_columns = [item for threshold in thresholds for item in (
        f"{threshold_name(threshold)}_days", f"{threshold_name(threshold)}_degree_days",
    )]
    with ExitStack() as stack:
        calendar = stack.enter_context(xr.open_dataset(args.calendar, engine="h5netcdf", decode_timedelta=False))
        maximum = open_daily_crop_window(
            stack, args.tasmax, "tasmax", args.year_start, args.year_end,
            args.lat_start, args.lat_stop,
        )
        cal = calendar.isel(lat=slice(args.lat_start, args.lat_stop))
        required = {"planting_day", "maturity_day"}
        if missing := required - set(cal.data_vars):
            raise ValueError(f"Calendar missing {sorted(missing)}")
        if not (np.array_equal(maximum.lat, cal.lat) and np.array_equal(maximum.lon, cal.lon)):
            raise ValueError("tasmax and calendar coordinates differ; regrid explicitly before construction")
        # Keep date semantics identical to the direct-weather builders.  A
        # daily field stamped after midnight must still include the calendar
        # maturity date.
        dates = pd.DatetimeIndex(maximum.time.values).normalize()
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
                n_days = int(where.sum())
                if n_days != (end - start).days + 1:
                    continue
                values = tmax[where, ilat, ilon]
                if not np.isfinite(values).all():
                    continue
                for stage_id, (left, right) in enumerate(zip(fractions, fractions[1:]), start=1):
                    i0, i1 = int(np.floor(left * n_days)), int(np.floor(right * n_days))
                    stage_values = values[i0:i1]
                    if len(stage_values) == 0:
                        continue
                    row: dict[str, object] = {
                        "harvest_year": harvest_year, "plant_year": plant_year,
                        "lat": float(cal.lat.values[ilat]), "lon": float(cal.lon.values[ilon]),
                        "lon_360": float(cal.lon.values[ilon] % 360), "crop": args.crop,
                        "irrigation": args.irrigation, "cross_year": cross_year,
                        "stage_id": stage_id, "stage_start_offset_day": i0 + 1,
                        "stage_end_offset_day": i1, "stage_days": len(stage_values),
                        "stage_fractions": args.stage_fractions,
                        "tmax_mean_c": float(np.mean(stage_values, dtype=np.float64)),
                    }
                    for threshold in thresholds:
                        name = threshold_name(threshold)
                        excess = np.maximum(stage_values.astype(np.float64) - threshold, 0)
                        row[f"{name}_days"] = int((stage_values >= threshold).sum())
                        row[f"{name}_degree_days"] = float(excess.sum())
                    rows.append(row)
    result = pd.DataFrame(rows, columns=BASE_COLUMNS + metric_columns)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    result.to_parquet(args.out, index=False)
    print(
        f"wrote {len(result)} crop-stage heat rows; "
        f"thresholds={','.join(f'{value:g}' for value in thresholds)} C"
    )


if __name__ == "__main__":
    main()
