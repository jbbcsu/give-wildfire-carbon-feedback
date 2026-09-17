#!/usr/bin/env python3
"""Independently validate global tile identities and fixed raw daily samples."""
from __future__ import annotations

from datetime import datetime, timedelta
import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

from validate_gfdl_single_year_global_tile_pilot import ROOT, PILOT, close
from continue_gfdl_2032_maize_global_tiles import locked_source_file, receipt_for_year
import tomllib


SAMPLE_TILE_STARTS = (20, 50, 100, 150, 200, 250, 290)


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def daily_sample(row: pd.Series, pr_ds: xr.Dataset, tas_ds: xr.Dataset, label: str) -> None:
    start = datetime(int(row.plant_year), 1, 1) + timedelta(days=int(row.plant_doy) - 1)
    end = datetime(int(row.harvest_year), 1, 1) + timedelta(days=int(row.maturity_doy) - 1)
    # Some registered ISIMIP ESMs timestamp daily values at 12:00 rather
    # than 00:00. Select the entire maturity calendar day, not midnight only.
    end_of_day = end + timedelta(days=1) - timedelta(microseconds=1)
    pr_raw = pr_ds.pr.sel(lat=float(row.lat), lon=float(row.lon), time=slice(start, end_of_day)).values
    tas_raw = tas_ds.tas.sel(lat=float(row.lat), lon=float(row.lon), time=slice(start, end_of_day)).values
    if pr_raw.dtype != np.float32 or tas_raw.dtype != np.float32:
        raise AssertionError(f"{label}: source dtype changed")
    rain = (pr_raw * 86400).astype(np.float64)
    temp = (tas_raw - 273.15).astype(np.float64)
    if len(rain) != int(row.season_days) or len(temp) != len(rain):
        raise AssertionError(f"{label}: crop-year daily length differs")
    wet = rain >= 1.0
    run = longest = 0
    for value in wet:
        run = 0 if value else run + 1
        longest = max(longest, run)
    for field, value in (
        ("precip_mm", math.fsum(map(float, rain))),
        ("tmean_c", float(np.mean(temp.astype(np.float32)))),
        ("rx1day_mm", max(rain)),
        ("rx5day_mm", max(math.fsum(map(float, rain[i:i + 5])) for i in range(len(rain) - 4))),
    ):
        close(float(row[field]), float(value), f"{label} {field}")
    if int(row.wet_days_n) != int(sum(wet)) or int(row.cdd_max_days) != longest:
        raise AssertionError(f"{label}: wet/dry count differs")
    # The source is float32.  Verify any difference from a float64-first
    # conversion is bounded by observable pointwise conversion roundoff.
    precise = pr_raw.astype(np.float64) * 86400
    discrepancy = abs(float(row.precip_mm) - math.fsum(map(float, precise)))
    bound = math.fsum(map(float, np.abs(rain - precise))) + 1e-8
    if discrepancy > bound:
        raise AssertionError(f"{label}: rain differs beyond conversion roundoff")


def validate_year(year: int = 2032) -> None:
    receipt = tomllib.loads(receipt_for_year(year).read_text(encoding="utf-8"))
    if receipt["scenario"] != "ssp126" or receipt["esm"] != "GFDL-ESM4":
        raise ValueError("source identity changed")
    pr_source = locked_source_file(receipt, "precipitation", "pr")
    tas_source = locked_source_file(receipt, "paired_temperature", "tas")
    full_dir = ROOT / f"data/interim/gfdl_ssp126_global_{year}_maize_full_20260917"
    out_path = full_dir / "independent_global_validation.json"
    if out_path.exists():
        raise FileExistsError(out_path)
    manifest = json.loads((full_dir / "global_manifest.json").read_text())
    if manifest["schema"] != f"gfdl_ssp126_{year}_maize_global_tile_engineering_v1":
        raise AssertionError("wrong global manifest year/schema")
    tiles = manifest["tiles"]
    if len(tiles) != 36 or manifest["status"] != "complete_engineering_pending_independent_global_validation_not_damage_or_scc":
        raise AssertionError("global tile manifest incomplete")
    if [(x["lat_start"], x["lat_stop"]) for x in tiles] != [(i, i + 10) for i in range(0, 360, 10)]:
        raise AssertionError("global latitude partition changed")
    all_keys: set[tuple[int, float, float]] = set()
    selected_rows: list[tuple[str, pd.Series]] = []
    total_seasons = total_stages = 0
    for record in tiles:
        start, stop = record["lat_start"], record["lat_stop"]
        tile = full_dir / f"lat{start:03d}_{stop:03d}"
        if json.loads((tile / "validation.json").read_text()) != record:
            raise AssertionError(f"tile receipt/manifest mismatch: {tile}")
        season_path, stage_path = tile / "season.parquet", tile / "stages.parquet"
        if digest(season_path) != record["season_sha256"] or digest(stage_path) != record["stages_sha256"]:
            raise AssertionError(f"tile file changed: {tile}")
        season = pd.read_parquet(season_path)
        stages = pd.read_parquet(stage_path)
        if len(season) != record["season_rows"] or len(stages) != record["stage_rows"]:
            raise AssertionError(f"tile row count changed: {tile}")
        for row in season.itertuples(index=False):
            key = (int(row.harvest_year), float(row.lat), float(row.lon))
            if key in all_keys:
                raise AssertionError(f"cross-tile duplicate cell: {key}")
            all_keys.add(key)
        if start in SAMPLE_TILE_STARTS:
            ordered = season.sort_values(["lat", "lon"]).reset_index(drop=True)
            if len(ordered) == 0:
                raise AssertionError(f"fixed raw-sample tile empty: {tile}")
            for position in sorted({0, len(ordered) // 2, len(ordered) - 1}):
                selected_rows.append((f"lat{start:03d}_{stop:03d} row{position}", ordered.iloc[position]))
        total_seasons += len(season)
        total_stages += len(stages)
    if total_seasons != manifest["season_rows"] or total_stages != manifest["stage_rows"]:
        raise AssertionError("global aggregate rows differ from manifest")

    # Exact full-tile overlap with the earlier independently checked pilot.
    if year == 2032:
        for label in ("season", "stages"):
            full = pd.read_parquet(full_dir / "lat100_110" / f"{label}.parquet")
            pilot = pd.read_parquet(PILOT / f"{label}_lat100_110.parquet")
            pd.testing.assert_frame_equal(full, pilot, check_exact=True)

    with xr.open_dataset(pr_source, engine="h5netcdf") as pr_ds, xr.open_dataset(tas_source, engine="h5netcdf") as tas_ds:
        if pr_ds.pr.attrs.get("units") != "kg m-2 s-1" or tas_ds.tas.attrs.get("units") != "K":
            raise AssertionError("source units changed")
        for label, row in selected_rows:
            daily_sample(row, pr_ds, tas_ds, label)
    result = {
        "schema": f"gfdl_ssp126_{year}_maize_global_independent_validation_v1",
        "status": "passed_one_year_one_esm_climate_features_only_not_response_damage_or_scc",
        "tiles": len(tiles), "season_rows": total_seasons, "stage_rows": total_stages,
        "unique_cell_year_keys": len(all_keys), "fixed_raw_daily_sample_count": len(selected_rows),
        "raw_sample_tiles": list(SAMPLE_TILE_STARTS),
        "exact_prior_pilot_full_tile_parity": True if year == 2032 else None,
        "global_manifest_sha256": digest(full_dir / "global_manifest.json"), "no_yield_data_read": True,
    }
    out_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, sort_keys=True))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--year", type=int, default=2032)
    args = parser.parse_args()
    validate_year(args.year)


if __name__ == "__main__":
    main()
