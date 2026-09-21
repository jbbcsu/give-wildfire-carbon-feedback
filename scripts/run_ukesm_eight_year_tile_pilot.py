#!/usr/bin/env python3
"""Source-locked 2092--2099 UKESM maize tile under strict resource caps."""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
import xarray as xr

from audit_gfdl_2032_2039_maize_crossyear import digest, require
from continue_isimip3b_global_maize_tiles import source_context
from run_bounded_job import run
from run_gfdl_single_year_global_tile_pilot import ROOT, CALENDAR


OUT = ROOT / "data/interim/ukesm_ssp126_2092_2099_mai_noirr_lat100_110_pilot_20260917"


def main() -> None:
    source, receipt_path, pr, tas = source_context("ukesm1-0-ll", "ssp126", 2092)
    with (xr.open_dataset(CALENDAR, engine="h5netcdf") as cal,
          xr.open_dataset(pr, engine="h5netcdf") as p,
          xr.open_dataset(tas, engine="h5netcdf") as t):
        require(np.array_equal(cal.lat.values, p.lat.values)
                and np.array_equal(cal.lon.values, p.lon.values)
                and np.array_equal(p.lat.values, t.lat.values)
                and np.array_equal(p.lon.values, t.lon.values)
                and np.array_equal(p.time.values, t.time.values)
                and len(p.time) == len(t.time) == source["precipitation"]["daily_steps"]
                and p.pr.attrs.get("units") == "kg m-2 s-1"
                and t.tas.attrs.get("units") == "K",
                "source/calendar and paired daily metadata mismatch")
    OUT.mkdir(parents=True, exist_ok=True)
    paths = {}
    peaks = {}
    for label, builder in (("season", "build_crop_year_features.py"),
                           ("stages", "build_crop_stage_features.py")):
        output = OUT / f"{label}.parquet"
        receipt = OUT / f"{label}.resource.json"
        log = OUT / f"{label}.log"
        require(not output.exists() and not receipt.exists() and not log.exists(),
                f"pilot partial output requires review: {label}")
        command = [str(ROOT / ".venv/bin/python"), str(ROOT / "scripts" / builder),
                   "--precip", str(pr), "--temperature", str(tas),
                   "--calendar", str(CALENDAR), "--crop", "mai", "--irrigation", "noirr",
                   "--year-start", "2092", "--year-end", "2099",
                   "--lat-start", "100", "--lat-stop", "110",
                   "--wet-day-mm", "1", "--out", str(output)]
        result = run(command, receipt, log, max_mib=512, min_free_gib=130,
                     max_log_mib=2, interval=0.2, write_paths=[output],
                     max_new_disk_mib=64)
        require(result["status"] == "completed", f"pilot worker failed: {label} {result['status']}")
        paths[label] = output
        peaks[label] = result["sampled_peak_group_rss_bytes"]
    manifest = {
        "schema": "ukesm_ssp126_2092_2099_mai_noirr_lat100_110_pilot_v1",
        "status": "engineering_pending_independent_validation_not_response_damage_or_scc",
        "source_receipt_sha256": digest(receipt_path),
        "source_precip_sha512": source["precipitation"]["sha512"],
        "source_temperature_sha512": source["paired_temperature"]["sha512"],
        "harvest_years": list(range(2092, 2100)),
        "latitude_start": 100, "latitude_stop": 110,
        "season_rows": len(pd.read_parquet(paths["season"])),
        "stage_rows": len(pd.read_parquet(paths["stages"])),
        "season_sha256": digest(paths["season"]),
        "stages_sha256": digest(paths["stages"]),
        "peak_sampled_worker_rss_bytes": max(peaks.values()),
    }
    target = OUT / "pilot_manifest.json"
    require(not target.exists(), "pilot manifest already exists")
    target.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": manifest["status"], "season_rows": manifest["season_rows"],
                      "stage_rows": manifest["stage_rows"], "peak_rss": manifest["peak_sampled_worker_rss_bytes"]}, sort_keys=True))


if __name__ == "__main__":
    main()
