#!/usr/bin/env python3
"""Build crop-stage daily climate features without altering season-level outputs.

Stages are fractions of each calendar-defined growing season. The default
0–30%, 30–70%, and 70–100% partitions are transparent temporal proxies, not
claimed phenological stages; replace them with crop-specific stage dates when
an approved source is available.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

from build_crop_year_features import climate_array, date_from_doy, max_run, normalize_precip, normalize_temperature, rolling_max


STAGE_FEATURE_COLUMNS = [
    "harvest_year", "plant_year", "lat", "lon", "lon_360", "crop", "irrigation", "cross_year",
    "stage_id", "stage_start_offset_day", "stage_end_offset_day", "stage_days", "stage_fractions",
    "tmean_c", "precip_mm", "wet_days_n", "cdd_max_days", "rx1day_mm", "rx5day_mm",
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--precip", required=True)
    parser.add_argument("--temperature", required=True)
    parser.add_argument("--calendar", required=True)
    parser.add_argument("--crop", required=True)
    parser.add_argument("--irrigation", required=True, choices=["firr", "noirr"])
    parser.add_argument("--year-start", required=True, type=int)
    parser.add_argument("--year-end", required=True, type=int)
    parser.add_argument("--lat-start", required=True, type=int)
    parser.add_argument("--lat-stop", required=True, type=int)
    parser.add_argument("--out", required=True)
    parser.add_argument("--stage-fractions", default="0,0.3,0.7,1")
    parser.add_argument("--wet-day-mm", type=float, default=1.0)
    args = parser.parse_args()
    fractions = [float(x) for x in args.stage_fractions.split(",")]
    if fractions[0] != 0 or fractions[-1] != 1 or any(a >= b for a, b in zip(fractions, fractions[1:])):
        raise ValueError("Stage fractions must start at 0, end at 1, and strictly increase")

    with xr.open_dataset(args.calendar, engine="h5netcdf") as calendar, \
         xr.open_dataset(args.precip, engine="h5netcdf") as precip_ds, \
         xr.open_dataset(args.temperature, engine="h5netcdf") as temp_ds:
        pr = climate_array(precip_ds, "pr").isel(lat=slice(args.lat_start, args.lat_stop))
        tas = climate_array(temp_ds, "tas").isel(lat=slice(args.lat_start, args.lat_stop))
        cal = calendar.isel(lat=slice(args.lat_start, args.lat_stop))
        if not (np.array_equal(pr.lat, cal.lat) and np.array_equal(pr.lon, cal.lon) and np.array_equal(pr.time, tas.time)):
            raise ValueError("Climate/calendar coordinates or time axes differ")
        dates = pd.DatetimeIndex(pr.time.values)
        pr_values = normalize_precip(pr.values, pr.attrs.get("units", ""))
        tas_values = normalize_temperature(tas.values, tas.attrs.get("units", ""))
        planting, maturity = cal.planting_day.values, cal.maturity_day.values
        rows = []
        for harvest_year in range(args.year_start, args.year_end + 1):
            for ilat, ilon in np.ndindex(planting.shape):
                pday, hday = planting[ilat, ilon], maturity[ilat, ilon]
                if not (np.isfinite(pday) and np.isfinite(hday)):
                    continue
                pday, hday = int(pday), int(hday)
                if pday < 1 or hday < 1:
                    continue
                cross_year = hday < pday
                plant_year = harvest_year - int(cross_year)
                start, end = pd.Timestamp(date_from_doy(plant_year, pday)), pd.Timestamp(date_from_doy(harvest_year, hday))
                mask = (dates >= start) & (dates <= end)
                n_days = int(mask.sum())
                if n_days != (end - start).days + 1:
                    continue
                rain, temp = pr_values[mask, ilat, ilon], tas_values[mask, ilat, ilon]
                if not (np.isfinite(rain).all() and np.isfinite(temp).all()) or (rain < 0).any():
                    continue
                for stage_id, (left, right) in enumerate(zip(fractions, fractions[1:]), start=1):
                    i0, i1 = int(np.floor(left * n_days)), int(np.floor(right * n_days))
                    stage_rain, stage_temp = rain[i0:i1], temp[i0:i1]
                    if len(stage_rain) == 0:
                        continue
                    rows.append({
                        "harvest_year": harvest_year, "plant_year": plant_year, "lat": float(cal.lat.values[ilat]),
                        "lon": float(cal.lon.values[ilon]), "lon_360": float(cal.lon.values[ilon] % 360),
                        "crop": args.crop, "irrigation": args.irrigation, "cross_year": cross_year,
                        "stage_id": stage_id, "stage_start_offset_day": i0 + 1, "stage_end_offset_day": i1,
                        "stage_days": len(stage_rain), "stage_fractions": args.stage_fractions,
                        "tmean_c": float(stage_temp.mean()), "precip_mm": float(stage_rain.sum()),
                        "wet_days_n": int((stage_rain >= args.wet_day_mm).sum()), "cdd_max_days": max_run(stage_rain < args.wet_day_mm),
                        "rx1day_mm": float(stage_rain.max()), "rx5day_mm": rolling_max(stage_rain, 5),
                    })
    output = pd.DataFrame(rows, columns=STAGE_FEATURE_COLUMNS)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    output.to_parquet(args.out, index=False)
    print(f"wrote {len(output)} crop-stage rows to {args.out}")


if __name__ == "__main__":
    main()
