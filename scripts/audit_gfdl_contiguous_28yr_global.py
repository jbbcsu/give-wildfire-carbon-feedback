#!/usr/bin/env python3
"""Independent streamed audit of GFDL SSP126 2032--2059 global maize features.

Must run only after the serial missing-year builder exits successfully.
No response, yield, damage or SCC quantity is computed.
"""
from __future__ import annotations

from contextlib import ExitStack
from datetime import datetime, timedelta
import json
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

from audit_gfdl_2032_2039_maize_crossyear import check_features, digest, require
from continue_gfdl_contiguous_global_missing_years import YEAR_SOURCES
from pilot_gfdl_contiguous_global_boundary import OUT, ROOT, CALENDAR, source_decade
from validate_gfdl_2032_maize_global_tiles import SAMPLE_TILE_STARTS, daily_sample


YEARS = tuple(range(2032, 2060))
OUTPUT = ROOT / "data/interim/gfdl_ssp126_2032_2059_global_contiguous_qc_v2_20260917.json"
SOURCE_STATUS = "passed_source_only_not_gmt_response_yield_damage_or_scc"
KEY = ["harvest_year", "lat", "lon", "crop", "irrigation"]


def directory(year: int) -> Path:
    if 2032 <= year <= 2039:
        return ROOT / f"data/interim/gfdl_ssp126_global_{year}_maize_full_20260917"
    if 2042 <= year <= 2049:
        return ROOT / f"data/interim/isimip3b_global_gfdl-esm4_ssp126_{year}_mai_noirr_full_20260917"
    return OUT / str(year)


def check_prior_blocks() -> None:
    early = json.loads((ROOT / "data/interim/gfdl_ssp126_maize_2032_2039_crossyear_qc_20260917.json").read_text())
    early_resource = json.loads((ROOT / "data/interim/gfdl_ssp126_maize_2032_2039_crossyear_qc.resource.json").read_text())
    require(early["status"] == "passed_engineering_only_not_gmt_response_yield_damage_or_scc"
            and early["years"] == list(range(2032, 2040))
            and early_resource["status"] == "completed",
            "previous 2032-39 independent source audit")
    mid = json.loads((ROOT / "data/interim/gfdl-esm4_ssp126_2042_2049_mai_noirr_crossyear_qc_20260917.json").read_text())
    mid_resource = json.loads((ROOT / "data/interim/gfdl-esm4_ssp126_2042_2049_crossyear_qc_20260917.resource.json").read_text())
    require(mid["status"] == SOURCE_STATUS
            and mid["years"] == list(range(2042, 2050))
            and mid_resource["status"] == "completed",
            "previous 2042-49 independent source audit")


def manifest(year: int) -> dict:
    path = directory(year) / "global_manifest.json"
    info = json.loads(path.read_text())
    expected_schema = (
        f"gfdl_ssp126_{year}_maize_global_tile_engineering_v1"
        if year <= 2039 else
        "isimip3b_global_mai_noirr_source_only_tiles_v1"
        if 2042 <= year <= 2049 else
        "gfdl_ssp126_global_contiguous_source_year_v1"
    )
    # The first (2032--39) tile schema predates the explicit harvest-year
    # manifest field. Its year is pinned by its directory and independent
    # validation receipt below; later schemas carry the field directly.
    require(info["schema"] == expected_schema
            and (year <= 2039 or info["harvest_year"] == year)
            and info["season_rows"] == 67420 and info["stage_rows"] == 202260
            and len(info["tiles"]) == 36,
            f"{year}: global manifest identity/support")
    if year in YEAR_SOURCES:
        require(info["status"] == "passed_source_feature_year_only_not_response_damage_or_scc"
                and info["source_decades"] == list(YEAR_SOURCES[year])
                and info["calendar_sha256"] == digest(CALENDAR)
                and info["peak_sampled_worker_rss_bytes"] <= 512 * 2**20,
                f"{year}: new source/worker gate")
        for decade, pinned in zip(YEAR_SOURCES[year], info["source_receipts"]):
            current = source_decade(decade)[2]
            require(pinned == current, f"{year}: source hash/receipt changed")
    else:
        validator = json.loads((directory(year) / "independent_global_validation.json").read_text())
        require(validator["global_manifest_sha256"] == digest(path)
                and validator["fixed_raw_daily_sample_count"] == 21,
                f"{year}: previous independent raw-cell validation")
    return info


def sample_from_sources(row: pd.Series, sources: tuple[int, ...], datasets: dict) -> None:
    start = datetime(int(row.plant_year), 1, 1) + timedelta(days=int(row.plant_doy) - 1)
    end = datetime(int(row.harvest_year), 1, 1) + timedelta(days=int(row.maturity_doy) - 1)
    end_of_day = end + timedelta(days=1) - timedelta(microseconds=1)
    pr_parts, tas_parts, time_parts = [], [], []
    for decade in sources:
        pr_ds, tas_ds = datasets[decade]
        pr_slice = pr_ds.pr.sel(lat=float(row.lat), lon=float(row.lon), time=slice(start, end_of_day))
        tas_slice = tas_ds.tas.sel(lat=float(row.lat), lon=float(row.lon), time=slice(start, end_of_day))
        if pr_slice.sizes["time"]:
            require(np.array_equal(pr_slice.time.values, tas_slice.time.values),
                    "raw sample paired dates differ")
            pr_parts.append(pr_slice.values)
            tas_parts.append(tas_slice.values)
            time_parts.append(pr_slice.time.values)
    require(len(pr_parts) > 0, "raw sample not covered")
    rain = np.concatenate(pr_parts)
    temperature = np.concatenate(tas_parts)
    times = np.concatenate(time_parts)
    require(len(times) == int(row.season_days)
            and np.all(np.diff(times.astype("datetime64[ns]")) == np.timedelta64(1, "D")),
            "raw sample cross-file chronology/season support")
    coords = {"time": times, "lat": [float(row.lat)], "lon": [float(row.lon)]}
    pr_tiny = xr.Dataset({"pr": xr.DataArray(rain.reshape(-1, 1, 1),
                                             coords=coords, dims=("time", "lat", "lon"))})
    tas_tiny = xr.Dataset({"tas": xr.DataArray(temperature.reshape(-1, 1, 1),
                                               coords=coords, dims=("time", "lat", "lon"))})
    daily_sample(row, pr_tiny, tas_tiny,
                 f"year{int(row.harvest_year)} lat{float(row.lat)} lon{float(row.lon)}")


def main() -> None:
    if OUTPUT.exists():
        raise FileExistsError(OUTPUT)
    check_prior_blocks()
    manifests = {year: manifest(year) for year in YEARS}
    require(set(manifests) == set(YEARS), "28 contiguous harvest years missing")
    total_season = total_stage = raw_samples = rain_changed = 0
    retained_samples = []
    with (xr.open_dataset(CALENDAR, engine="h5netcdf") as calendar,
          ExitStack() as stack):
        datasets = {}
        for decade in (2031, 2041, 2051):
            pr, tas, _ = source_decade(decade)
            datasets[decade] = (stack.enter_context(xr.open_dataset(pr, engine="h5netcdf")),
                                stack.enter_context(xr.open_dataset(tas, engine="h5netcdf")))
            require(np.array_equal(calendar.lat.values, datasets[decade][0].lat.values)
                    and np.array_equal(calendar.lon.values, datasets[decade][0].lon.values)
                    and np.array_equal(datasets[decade][0].time.values,
                                       datasets[decade][1].time.values),
                    f"{decade}: climate/calendar coordinates")
        for start in range(0, 360, 10):
            stop = start + 10
            cal = calendar.isel(lat=slice(start, stop))
            valid = (np.isfinite(cal.planting_day.values)
                     & np.isfinite(cal.maturity_day.values)
                     & (cal.planting_day.values >= 1)
                     & (cal.maturity_day.values >= 1))
            rows, cols = np.where(valid)
            expected = set(zip(calendar.lat.values[start:stop][rows].astype(float),
                               calendar.lon.values[cols].astype(float)))
            baseline_keys = None
            baseline_rain = None
            for year in YEARS:
                tile = directory(year) / f"lat{start:03d}_{stop:03d}"
                record = manifests[year]["tiles"][start // 10]
                require((record["lat_start"], record["lat_stop"]) == (start, stop)
                        and json.loads((tile / "validation.json").read_text()) == record,
                        f"{year} {start}: tile receipt/manifest mismatch")
                season_path, stage_path = tile / "season.parquet", tile / "stages.parquet"
                require(digest(season_path) == record["season_sha256"]
                        and digest(stage_path) == record["stages_sha256"],
                        f"{year} {start}: feature digest mismatch")
                season, stages = pd.read_parquet(season_path), pd.read_parquet(stage_path)
                keys = list(zip(season.lat.astype(float), season.lon.astype(float)))
                require(len(keys) == len(expected) == len(set(keys))
                        and set(keys) == expected and len(stages) == 3 * len(expected),
                        f"{year} {start}: crop calendar exact-key support")
                for label, frame, period in (("season", season, "season_days"),
                                             ("stage", stages, "stage_days")):
                    require(set(frame.harvest_year) <= {year}
                            and set(frame.crop) <= {"mai"}
                            and set(frame.irrigation) <= {"noirr"},
                            f"{year} {start}: {label} identity")
                    check_features(frame, period, f"{year} {start} {label}")
                sums = stages.groupby(KEY, sort=False).agg(
                    rain=("precip_mm", "sum"), days=("stage_days", "sum"),
                    wet=("wet_days_n", "sum"), rx1=("rx1day_mm", "max"))
                joined = season.set_index(KEY).join(sums, validate="one_to_one")
                # Empty ocean/polar tiles have object-typed empty groupby
                # results; NumPy's isfinite rejects them. Row-count and
                # exact-key checks above already prove both tables empty.
                if len(joined):
                    require(np.allclose(joined.precip_mm, joined.rain, rtol=0, atol=1e-8)
                            and np.array_equal(joined.season_days, joined.days)
                            and np.array_equal(joined.wet_days_n, joined.wet)
                            and np.allclose(joined.rx1day_mm, joined.rx1, rtol=0, atol=1e-8),
                            f"{year} {start}: independent stage/season reconciliation")
                ordered = season.sort_values(["lat", "lon"]).reset_index(drop=True)
                current_keys = ordered[["lat", "lon"]].to_numpy()
                if baseline_keys is None:
                    baseline_keys, baseline_rain = current_keys, ordered.precip_mm.to_numpy()
                else:
                    require(np.array_equal(current_keys, baseline_keys),
                            f"{year} {start}: cross-year calendar keys shifted")
                    rain_changed += int(np.count_nonzero(ordered.precip_mm.to_numpy()
                                                         != baseline_rain))
                if year in YEAR_SOURCES and start in SAMPLE_TILE_STARTS:
                    for position in sorted({0, len(ordered) // 2, len(ordered) - 1}):
                        retained_samples.append((year, ordered.iloc[position]))
                total_season += len(season)
                total_stage += len(stages)
        require(total_season == 28 * 67420 and total_stage == 28 * 202260
                and rain_changed > 0,
                "28-year row count/distinct weather check")
        require(len(retained_samples) == len(YEAR_SOURCES) * 21,
                "new-year fixed raw-sample support")
        for year, row in retained_samples:
            sample_from_sources(row, YEAR_SOURCES[year], datasets)
            raw_samples += 1
    result = {
        "schema": "gfdl_ssp126_global_2032_2059_contiguous_source_audit_v1",
        "status": "passed_source_only_not_gmt_response_yield_damage_or_scc",
        "years": list(YEARS), "calendar_cells_per_year": 67420,
        "season_rows": total_season, "stage_rows": total_stage,
        "new_years_independent_raw_daily_samples": raw_samples,
        "old_years_previous_raw_daily_audits": 16,
        "rain_values_different_from_2032": rain_changed,
        "no_yield_data_read": True,
        "new_year_manifest_sha256": {
            str(year): digest(directory(year) / "global_manifest.json")
            for year in YEAR_SOURCES
        },
    }
    OUTPUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({key: value for key, value in result.items()
                      if key != "new_year_manifest_sha256"}, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
