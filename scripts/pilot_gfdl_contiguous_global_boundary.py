#!/usr/bin/env python3
"""Bounded global-tile parity pilots at the 2040/41 and 2050/51 source seams.

No crop response, GMT emulator or SCC calculation is performed. See
GLOBAL_CONTIGUOUS_GFDL_RIMEX_SOURCE_PILOT_PROTOCOL_20260917.md.
"""
from __future__ import annotations

from contextlib import ExitStack
from functools import lru_cache
import json
from pathlib import Path
import sys
import tomllib

import numpy as np
import pandas as pd
import xarray as xr

from climate_inputs import daily_series_coordinates
from continue_gfdl_2032_maize_global_tiles import digest, locked_source_file, require, validate_tile
from run_bounded_job import run
from run_gfdl_single_year_global_tile_pilot import ROOT, CALENDAR


OUT = ROOT / "data/interim/gfdl_ssp126_global_contiguous_boundary_pilot_20260917"
BOUNDED = ROOT / "data/interim/isimip3b_gfdl_ssp126_2031_2060_contiguous_pilot"
RAW = ROOT / "data/raw/isimip3b/gfdl-esm4/ssp126"
RECEIPTS = {
    2031: ROOT / "data/provenance/isimip3b_rimex_contiguous_gfdl_ssp126_2031_2040.toml",
    2041: ROOT / "data/provenance/isimip3b_later_century_gfdl_ssp126_2041_2050.toml",
    2051: ROOT / "data/provenance/isimip3b_rimex_contiguous_gfdl_ssp126_complete_20260902.toml",
}


@lru_cache(maxsize=3)
def source_decade(year: int) -> tuple[Path, Path, dict]:
    receipt_path = RECEIPTS[year]
    receipt = tomllib.loads(receipt_path.read_text(encoding="utf-8"))
    if year == 2051:
        require(receipt["all_six_catalogue_files_byte_and_sha512_validated"]
                and receipt["all_six_files_full_content_validated"],
                "2051 source receipt not complete")
        block = receipt["second_bracketing_decade"]
        receipt = {
            "period_start_year": 2051,
            "period_end_year": 2060,
            "precipitation": block["precipitation"],
            "paired_temperature": block["temperature"],
        }
    else:
        require(receipt["period_start_year"] == year
                and receipt["period_end_year"] == year + 9,
                f"{year}: receipt period changed")
    pr = locked_source_file(receipt, "precipitation", "pr", RAW)
    tas = locked_source_file(receipt, "paired_temperature", "tas", RAW)
    return pr, tas, {
        "receipt_path": str(receipt_path.relative_to(ROOT)),
        "receipt_sha256": digest(receipt_path),
        "pr_sha512": receipt["precipitation"]["sha512"],
        "tas_sha512": receipt["paired_temperature"]["sha512"],
    }


def check_pair(pr_paths: list[Path], tas_paths: list[Path]) -> None:
    with ExitStack() as stack:
        pr_time, pr_lat, pr_lon = daily_series_coordinates(
            stack, [str(path) for path in pr_paths], "pr")
        tas_time, tas_lat, tas_lon = daily_series_coordinates(
            stack, [str(path) for path in tas_paths], "tas")
    require(np.array_equal(pr_time, tas_time)
            and np.array_equal(pr_lat, tas_lat)
            and np.array_equal(pr_lon, tas_lon)
            and len(pr_lat) == 360 and len(pr_lon) == 720,
            "boundary pr/tas time or grid mismatch")
    require(len(pr_time) in (7305, 7306)
            and np.all(np.diff(pr_time) == np.timedelta64(1, "D")),
            "two source decades must be strictly daily and contiguous")


def compare_bounded(tile: Path, year: int, label: str) -> int:
    source_name = ("mai_noirr_2032_2059_lat100_102_features.parquet"
                   if label == "season" else
                   "mai_noirr_2032_2059_lat100_102_stages.parquet")
    old = pd.read_parquet(BOUNDED / source_name)
    new = pd.read_parquet(tile / ("season.parquet" if label == "season" else "stages.parquet"))
    old = old.loc[old.harvest_year == year].copy()
    require(len(old) > 0, f"{year}: bounded reference absent")
    new = new.loc[new.lat.isin(old.lat.unique())].copy()
    keys = ["harvest_year", "lat", "lon", "crop", "irrigation"]
    if label == "stages":
        keys.append("stage_id")
    require(set(old.columns) == set(new.columns), f"{year}: {label} columns differ")
    old = old.sort_values(keys).reset_index(drop=True)
    new = new[old.columns].sort_values(keys).reset_index(drop=True)
    pd.testing.assert_frame_equal(old, new, check_dtype=False,
                                  check_exact=False, atol=1e-9, rtol=0)
    return len(old)


def main() -> None:
    require(BOUNDED.is_dir() and CALENDAR.is_file(), "reference/calendar missing")
    OUT.mkdir(parents=True, exist_ok=True)
    results = []
    # The selected 10-row tile includes both latitude rows in the earlier
    # two-row contiguous pilot, so exact-key cross-source parity is testable.
    for year, decades in ((2041, (2031, 2041)), (2051, (2041, 2051))):
        sources = [source_decade(decade) for decade in decades]
        pr_paths, tas_paths = [item[0] for item in sources], [item[1] for item in sources]
        check_pair(pr_paths, tas_paths)
        tile = OUT / str(year) / "lat100_110"
        tile.mkdir(parents=True, exist_ok=True)
        for label, builder in (("season", "build_crop_year_features.py"),
                               ("stages", "build_crop_stage_features.py")):
            output = tile / f"{label}.parquet"
            resource = tile / f"{label}.resource.json"
            log = tile / f"{label}.log"
            if output.exists() or resource.exists() or log.exists():
                require(output.exists() and resource.exists() and log.exists()
                        and json.loads(resource.read_text())["status"] == "completed",
                        f"{year} {label}: partial output needs review")
            else:
                command = [sys.executable, str(ROOT / "scripts" / builder),
                           "--precip", *map(str, pr_paths),
                           "--temperature", *map(str, tas_paths),
                           "--calendar", str(CALENDAR), "--crop", "mai",
                           "--irrigation", "noirr", "--year-start", str(year),
                           "--year-end", str(year), "--lat-start", "100",
                           "--lat-stop", "110", "--wet-day-mm", "1",
                           "--out", str(output)]
                result = run(command, resource, log, max_mib=512,
                             min_free_gib=130, max_log_mib=2, interval=0.2,
                             write_paths=[output], max_new_disk_mib=64)
                require(result["status"] == "completed",
                        f"{year} {label}: bounded worker {result['status']}")
        with (xr.open_dataset(CALENDAR, engine="h5netcdf") as calendar,
              xr.open_dataset(pr_paths[0], engine="h5netcdf") as pr):
            validation = validate_tile(tile, 100, 110, calendar, pr.lat.values, year)
        season_overlap = compare_bounded(tile, year, "season")
        stage_overlap = compare_bounded(tile, year, "stages")
        results.append({
            "harvest_year": year,
            "source_decades": list(decades),
            "source_receipts": [item[2] for item in sources],
            "tile_validation": validation,
            "bounded_overlap_season_rows": season_overlap,
            "bounded_overlap_stage_rows": stage_overlap,
            "season_sha256": digest(tile / "season.parquet"),
            "stages_sha256": digest(tile / "stages.parquet"),
        })
        print(f"validated cross-decade global tile {year}: "
              f"{season_overlap} bounded season, {stage_overlap} stage rows", flush=True)
    receipt = OUT / "boundary_parity_receipt.json"
    payload = {
        "schema": "gfdl_ssp126_global_contiguous_boundary_pilot_v1",
        "status": "passed_two_boundary_source_feature_parity_only_not_response_damage_or_scc",
        "one_tile_only": True,
        "source_daily_span": [2031, 2060],
        "results": results,
    }
    if receipt.exists():
        require(json.loads(receipt.read_text()) == payload,
                "prior boundary pilot receipt changed")
    else:
        receipt.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print("GFDL contiguous global boundary pilot passed; no response/damage/SCC claim", flush=True)


if __name__ == "__main__":
    main()
