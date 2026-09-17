#!/usr/bin/env python3
"""Independent bounded cross-year audit of source-only maize weather features."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tomllib

import numpy as np
import pandas as pd
import xarray as xr

from run_gfdl_single_year_global_tile_pilot import ROOT, CALENDAR, SOURCE_RECEIPT, source_file


YEARS = tuple(range(2032, 2040))
OUT = ROOT / "data/interim/gfdl_ssp126_maize_2032_2039_crossyear_qc_20260917.json"


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def check_features(frame: pd.DataFrame, period: str, label: str) -> None:
    days = frame[period].to_numpy(dtype=np.int64)
    rain = frame.precip_mm.to_numpy(dtype=np.float64)
    rx1 = frame.rx1day_mm.to_numpy(dtype=np.float64)
    rx5 = frame.rx5day_mm.to_numpy(dtype=np.float64)
    wet = frame.wet_days_n.to_numpy(dtype=np.int64)
    dry = frame.cdd_max_days.to_numpy(dtype=np.int64)
    temp = frame.tmean_c.to_numpy(dtype=np.float64)
    require(np.isfinite(temp).all() and np.isfinite(rain).all()
            and np.isfinite(rx1).all(), f"nonfinite basic feature: {label}")
    require(((days > 0) & (rain >= 0) & (rx1 >= 0) & (rx1 <= rain + 1e-8)
             & (wet >= 0) & (wet <= days) & (dry >= 0) & (dry <= days)).all(),
            f"invalid physical bounds: {label}")
    long = days >= 5
    require((np.isfinite(rx5[long]) & (rx5[long] >= 0)
             & (rx5[long] + 1e-8 >= rx1[long])
             & (rx5[long] <= rain[long] + 1e-8)).all(),
            f"invalid five-day maximum: {label}")
    require(np.isnan(rx5[~long]).all(), f"short-period Rx5day definition changed: {label}")


def main() -> None:
    if OUT.exists():
        raise FileExistsError(OUT)
    receipt = tomllib.loads(SOURCE_RECEIPT.read_text(encoding="utf-8"))
    require((receipt["scenario"], receipt["esm"], receipt["member"],
             receipt["period_start_year"], receipt["period_end_year"])
            == ("ssp126", "GFDL-ESM4", "r1i1p1f1", 2031, 2040), "wrong daily source")
    pr = source_file(receipt, "precipitation", "pr")
    source_file(receipt, "paired_temperature", "tas")
    manifests: dict[int, dict] = {}
    for year in YEARS:
        directory = ROOT / f"data/interim/gfdl_ssp126_global_{year}_maize_full_20260917"
        manifest = directory / "global_manifest.json"
        independent = json.loads((directory / "independent_global_validation.json").read_text())
        resource = json.loads((directory / "independent_validation.resource.json").read_text()) if year != 2032 else None
        payload = json.loads(manifest.read_text())
        require(payload["schema"] == f"gfdl_ssp126_{year}_maize_global_tile_engineering_v1"
                and len(payload["tiles"]) == 36, f"year manifest malformed: {year}")
        require(independent["status"] == "passed_one_year_one_esm_climate_features_only_not_response_damage_or_scc"
                and independent["global_manifest_sha256"] == digest(manifest)
                and independent["fixed_raw_daily_sample_count"] == 21
                and independent["exact_prior_pilot_full_tile_parity"] is (True if year == 2032 else None),
                f"independent receipt mismatch: {year}")
        if resource is not None:
            require(resource["status"] == "completed"
                    and resource["sampled_peak_group_rss_bytes"] <= 512 * 2**20
                    and resource["sampled_peak_new_disk_bytes"] <= 64 * 2**20,
                    f"independent worker resource gate failed: {year}")
        manifests[year] = payload

    count_season = count_stage = rain_changed = temperature_changed = 0
    with xr.open_dataset(CALENDAR, engine="h5netcdf") as cal, xr.open_dataset(pr, engine="h5netcdf") as source:
        require(np.array_equal(cal.lat.values, source.lat.values)
                and np.array_equal(cal.lon.values, source.lon.values),
                "source/calendar full coordinate identity failed")
        latitudes, longitudes = source.lat.values, source.lon.values
        for start in range(0, 360, 10):
            stop = start + 10
            planting = cal.planting_day.isel(lat=slice(start, stop)).values
            maturity = cal.maturity_day.isel(lat=slice(start, stop)).values
            valid = np.isfinite(planting) & np.isfinite(maturity) & (planting >= 1) & (maturity >= 1)
            row_index, col_index = np.where(valid)
            expected = set(zip(latitudes[start:stop][row_index].astype(float),
                               longitudes[col_index].astype(float)))
            baseline: pd.DataFrame | None = None
            for year in YEARS:
                directory = ROOT / f"data/interim/gfdl_ssp126_global_{year}_maize_full_20260917"
                tile = directory / f"lat{start:03d}_{stop:03d}"
                manifest_record = manifests[year]["tiles"][start // 10]
                require((manifest_record["lat_start"], manifest_record["lat_stop"]) == (start, stop)
                        and json.loads((tile / "validation.json").read_text()) == manifest_record,
                        f"tile/manifest discrepancy: {year} {start}")
                paths = (tile / "season.parquet", tile / "stages.parquet")
                require(digest(paths[0]) == manifest_record["season_sha256"]
                        and digest(paths[1]) == manifest_record["stages_sha256"],
                        f"tile content changed: {year} {start}")
                season, stages = (pd.read_parquet(path) for path in paths)
                pairs = list(zip(season.lat.astype(float), season.lon.astype(float)))
                require(len(pairs) == len(expected) == len(set(pairs))
                        and set(pairs) == expected, f"exact calendar coordinate mask differs: {year} {start}")
                require(len(stages) == 3 * len(expected), f"stage row support differs: {year} {start}")
                for name, frame, period in (("season", season, "season_days"),
                                            ("stage", stages, "stage_days")):
                    require(set(frame.harvest_year) <= {year} and set(frame.crop) <= {"mai"}
                            and set(frame.irrigation) <= {"noirr"},
                            f"{name} identity mismatch: {year} {start}")
                    check_features(frame, period, f"{year} {start} {name}")
                if year == 2032:
                    baseline = season.sort_values(["lat", "lon"]).reset_index(drop=True)
                elif baseline is not None and len(season):
                    ordered = season.sort_values(["lat", "lon"]).reset_index(drop=True)
                    require(np.array_equal(ordered[["lat", "lon"]].values,
                                           baseline[["lat", "lon"]].values),
                            f"cross-year calendar keys shifted: {year} {start}")
                    rain_changed += int(np.count_nonzero(
                        ordered.precip_mm.to_numpy() != baseline.precip_mm.to_numpy()))
                    temperature_changed += int(np.count_nonzero(
                        ordered.tmean_c.to_numpy() != baseline.tmean_c.to_numpy()))
                count_season += len(season)
                count_stage += len(stages)
    require(rain_changed > 0 and temperature_changed > 0, "cross-year climate features unchanged")
    require(count_season == sum(manifests[y]["season_rows"] for y in YEARS)
            and count_stage == sum(manifests[y]["stage_rows"] for y in YEARS),
            "cross-year count/manifest mismatch")
    result = {
        "schema": "gfdl_ssp126_maize_2032_2039_source_only_crossyear_qc_v1",
        "status": "passed_engineering_only_not_gmt_response_yield_damage_or_scc",
        "years": list(YEARS), "tiles_per_year": 36,
        "season_rows": count_season, "stage_rows": count_stage,
        "rain_values_different_from_2032": rain_changed,
        "temperature_values_different_from_2032": temperature_changed,
        "no_yield_data_read": True,
    }
    OUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
