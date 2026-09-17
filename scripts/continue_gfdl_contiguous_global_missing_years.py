#!/usr/bin/env python3
"""Build only missing global GFDL SSP126 2032--2059 maize source years.

This is a serial, fail-closed source pipeline, not a GMT/crop response.
See GLOBAL_CONTIGUOUS_GFDL_RIMEX_SOURCE_PILOT_PROTOCOL_20260917.md.
"""
from __future__ import annotations

from contextlib import ExitStack
import json
import sys

import numpy as np
import xarray as xr

from climate_inputs import daily_series_coordinates
from continue_gfdl_2032_maize_global_tiles import digest, require, validate_tile
from pilot_gfdl_contiguous_global_boundary import (
    OUT, ROOT, CALENDAR, compare_bounded, source_decade,
)
from run_bounded_job import run


YEAR_SOURCES = {
    2040: (2031,), 2041: (2031, 2041), 2050: (2041,),
    2051: (2041, 2051),
    **{year: (2051,) for year in range(2052, 2060)},
}


def check_sources(year: int, pr_paths, tas_paths, decades) -> None:
    with ExitStack() as stack:
        pr_time, pr_lat, pr_lon = daily_series_coordinates(
            stack, [str(path) for path in pr_paths], "pr")
        tas_time, tas_lat, tas_lon = daily_series_coordinates(
            stack, [str(path) for path in tas_paths], "tas")
    require(np.array_equal(pr_time, tas_time)
            and np.array_equal(pr_lat, tas_lat)
            and np.array_equal(pr_lon, tas_lon)
            and len(pr_lat) == 360 and len(pr_lon) == 720,
            f"{year}: paired time/grid mismatch")
    require(str(pr_time[0])[:10] == f"{decades[0]}-01-01"
            and str(pr_time[-1])[:10] == f"{decades[-1] + 9}-12-31"
            and np.all(np.diff(pr_time) == np.timedelta64(1, "D"))
            and int(str(pr_time[0])[:4]) <= year - 1
            and int(str(pr_time[-1])[:4]) >= year,
            f"{year}: source chronology/support mismatch")


def complete_year(year: int, decades: tuple[int, ...]) -> None:
    sources = [source_decade(decade) for decade in decades]
    pr_paths = [item[0] for item in sources]
    tas_paths = [item[1] for item in sources]
    check_sources(year, pr_paths, tas_paths, decades)
    out_root = OUT / str(year)
    out_root.mkdir(parents=True, exist_ok=True)
    with (xr.open_dataset(CALENDAR, engine="h5netcdf") as calendar,
          xr.open_dataset(pr_paths[0], engine="h5netcdf") as pr):
        latitudes = pr.lat.values.copy()
        require(np.array_equal(calendar.lat.values, latitudes)
                and np.array_equal(calendar.lon.values, pr.lon.values),
                f"{year}: calendar/source grid mismatch")
        records = []
        for start in range(0, 360, 10):
            stop = start + 10
            tile = out_root / f"lat{start:03d}_{stop:03d}"
            tile.mkdir(parents=True, exist_ok=True)
            validation_path = tile / "validation.json"
            if validation_path.exists():
                old = json.loads(validation_path.read_text())
                new = validate_tile(tile, start, stop, calendar, latitudes, year)
                require(old == new, f"{year}: completed tile changed {start}")
                records.append(new)
                continue
            for label, builder in (("season", "build_crop_year_features.py"),
                                   ("stages", "build_crop_stage_features.py")):
                output = tile / f"{label}.parquet"
                resource = tile / f"{label}.resource.json"
                log = tile / f"{label}.log"
                if output.exists() or resource.exists() or log.exists():
                    require(output.exists() and resource.exists() and log.exists()
                            and json.loads(resource.read_text())["status"] == "completed",
                            f"{year} {start} {label}: partial tile needs review")
                else:
                    command = [sys.executable, str(ROOT / "scripts" / builder),
                               "--precip", *map(str, pr_paths),
                               "--temperature", *map(str, tas_paths),
                               "--calendar", str(CALENDAR), "--crop", "mai",
                               "--irrigation", "noirr", "--year-start", str(year),
                               "--year-end", str(year), "--lat-start", str(start),
                               "--lat-stop", str(stop), "--wet-day-mm", "1",
                               "--out", str(output)]
                    result = run(command, resource, log, max_mib=512,
                                 min_free_gib=130, max_log_mib=2, interval=0.2,
                                 write_paths=[output], max_new_disk_mib=64)
                    require(result["status"] == "completed",
                            f"{year} {start} {label}: {result['status']}")
            record = validate_tile(tile, start, stop, calendar, latitudes, year)
            validation_path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
            records.append(record)
            print(f"completed GFDL contiguous {year} latitude {start:03d}-{stop:03d}; "
                  f"peak {record['peak_sampled_rss_bytes']} bytes", flush=True)
    require(len(records) == 36
            and sum(record["season_rows"] for record in records) == 67420
            and sum(record["stage_rows"] for record in records) == 202260,
            f"{year}: global calendar support failed")
    overlap_tile = out_root / "lat100_110"
    overlap_season = compare_bounded(overlap_tile, year, "season")
    overlap_stage = compare_bounded(overlap_tile, year, "stages")
    require((overlap_season, overlap_stage) == (686, 2058),
            f"{year}: bounded overlapping row support changed")
    manifest = {
        "schema": "gfdl_ssp126_global_contiguous_source_year_v1",
        "status": "passed_source_feature_year_only_not_response_damage_or_scc",
        "esm": "gfdl-esm4", "member": "r1i1p1f1", "scenario": "ssp126",
        "crop": "mai", "irrigation": "noirr", "harvest_year": year,
        "source_decades": list(decades),
        "source_receipts": [item[2] for item in sources],
        "calendar_sha256": digest(CALENDAR),
        "season_rows": 67420, "stage_rows": 202260,
        "bounded_overlap_season_rows": overlap_season,
        "bounded_overlap_stage_rows": overlap_stage,
        "peak_sampled_worker_rss_bytes": max(record["peak_sampled_rss_bytes"] for record in records),
        "tiles": records,
    }
    manifest_path = out_root / "global_manifest.json"
    if manifest_path.exists():
        require(json.loads(manifest_path.read_text()) == manifest,
                f"{year}: previous global manifest changed")
    else:
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(f"validated GFDL contiguous global year {year}: 67420 seasons", flush=True)


def main() -> None:
    pilot = OUT / "boundary_parity_receipt.json"
    require(pilot.is_file()
            and json.loads(pilot.read_text())["status"]
                == "passed_two_boundary_source_feature_parity_only_not_response_damage_or_scc",
            "boundary parity pilot must pass first")
    for year, decades in YEAR_SOURCES.items():
        complete_year(year, decades)
    print("GFDL missing contiguous full-grid years complete; independent 28-year audit pending", flush=True)


if __name__ == "__main__":
    main()
