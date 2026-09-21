#!/usr/bin/env python3
"""Sequential, source-locked ESM maize weather-feature panels.

The exact registry covers named 2042 anchors and the preregistered 2092--2099
late-century matrix. Cases outside those source-bound combinations fail closed.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import tomllib

import numpy as np
import xarray as xr

from continue_gfdl_2032_maize_global_tiles import (
    digest, locked_source_file, require, validate_tile,
)
from run_bounded_job import run
from run_gfdl_single_year_global_tile_pilot import ROOT, CALENDAR


SOURCES = {
    ("ukesm1-0-ll", "ssp126", 2042):
        ROOT / "data/provenance/isimip3b_later_century_ukesm_ssp126_2041_2050.toml",
    ("ukesm1-0-ll", "ssp370", 2042):
        ROOT / "data/provenance/isimip3b_later_century_ukesm_ssp370_2041_2050.toml",
    ("ukesm1-0-ll", "ssp585", 2042):
        ROOT / "data/provenance/isimip3b_later_century_ukesm_ssp585_2041_2050.toml",
    ("mri-esm2-0", "ssp585", 2042):
        ROOT / "data/provenance/isimip3b_later_century_mri_ssp585_2041_2050.toml",
    ("gfdl-esm4", "ssp126", 2042):
        ROOT / "data/provenance/isimip3b_later_century_gfdl_ssp126_2041_2050.toml",
    ("ukesm1-0-ll", "ssp126", 2092):
        ROOT / "data/provenance/isimip3b_later_century_ukesm_ssp126_2091_2100.toml",
    ("ukesm1-0-ll", "ssp370", 2092):
        ROOT / "data/provenance/isimip3b_later_century_ukesm_ssp370_2091_2100.toml",
    ("ukesm1-0-ll", "ssp585", 2092):
        ROOT / "data/provenance/isimip3b_later_century_ukesm_ssp585_2091_2100.toml",
    ("gfdl-esm4", "ssp126", 2092):
        ROOT / "data/provenance/isimip3b_later_century_gfdl_ssp126_2091_2100.toml",
    ("gfdl-esm4", "ssp370", 2092):
        ROOT / "data/provenance/isimip3b_later_century_gfdl_ssp370_2091_2100.toml",
    ("gfdl-esm4", "ssp585", 2092):
        ROOT / "data/provenance/isimip3b_later_century_gfdl_ssp585_2091_2100.toml",
    ("ipsl-cm6a-lr", "ssp126", 2092):
        ROOT / "data/provenance/isimip3b_later_century_ipsl_ssp126_2091_2100.toml",
    ("ipsl-cm6a-lr", "ssp370", 2092):
        ROOT / "data/provenance/isimip3b_later_century_ipsl_ssp370_2091_2100.toml",
    ("ipsl-cm6a-lr", "ssp585", 2092):
        ROOT / "data/provenance/isimip3b_later_century_ipsl_ssp585_2091_2100.toml",
    ("mpi-esm1-2-hr", "ssp126", 2092):
        ROOT / "data/provenance/isimip3b_later_century_mpi_ssp126_2091_2100.toml",
    ("mpi-esm1-2-hr", "ssp370", 2092):
        ROOT / "data/provenance/isimip3b_later_century_mpi_ssp370_2091_2100.toml",
    ("mpi-esm1-2-hr", "ssp585", 2092):
        ROOT / "data/provenance/isimip3b_later_century_mpi_ssp585_2091_2100.toml",
    ("mri-esm2-0", "ssp126", 2092):
        ROOT / "data/provenance/isimip3b_later_century_mri_ssp126_2091_2100.toml",
    ("mri-esm2-0", "ssp370", 2092):
        ROOT / "data/provenance/isimip3b_later_century_mri_ssp370_2091_2100.toml",
    ("mri-esm2-0", "ssp585", 2092):
        ROOT / "data/provenance/isimip3b_later_century_mri_ssp585_2091_2100.toml",
}
MEMBERS = {
    "gfdl-esm4": "r1i1p1f1", "ipsl-cm6a-lr": "r1i1p1f1",
    "mpi-esm1-2-hr": "r1i1p1f1", "mri-esm2-0": "r1i1p1f1",
    "ukesm1-0-ll": "r1i1p1f2",
}


def destination(esm: str, scenario: str, year: int) -> Path:
    return ROOT / f"data/interim/isimip3b_global_{esm}_{scenario}_{year}_mai_noirr_full_20260917"


def source_context(esm: str, scenario: str, year: int) -> tuple[dict, Path, Path, Path]:
    key = (esm, scenario, year)
    # Registered 2093--2099 continuations reuse exact scenario-specific
    # pinned decade sources, with one-year panels for bounded validation.
    if key not in SOURCES and ((esm == "ukesm1-0-ll" and scenario in {"ssp126", "ssp370", "ssp585"})
                               or (esm == "gfdl-esm4" and scenario == "ssp126")
                               or (esm == "mri-esm2-0" and scenario == "ssp585")) and 2043 <= year <= 2049:
        receipt_path = SOURCES[(esm, scenario, 2042)]
    elif key not in SOURCES and (esm in MEMBERS
                                and scenario in {"ssp126", "ssp370", "ssp585"}) \
            and 2093 <= year <= 2099:
        receipt_path = SOURCES[(esm, scenario, 2092)]
    elif key in SOURCES:
        receipt_path = SOURCES[key]
    else:
        raise ValueError(f"source not registered for full-grid processing: {key}")
    receipt = tomllib.loads(receipt_path.read_text(encoding="utf-8"))
    start_year, end_year = (2041, 2050) if 2042 <= year <= 2049 else (2091, 2100)
    require((receipt["esm"].lower(), receipt["scenario"], receipt["member"],
             receipt["dataset_version"], receipt["period_start_year"],
             receipt["period_end_year"])
            == (esm, scenario, MEMBERS[esm], "20210512", start_year, end_year),
            "registered source identity changed")
    raw_root = ROOT / "data/raw/isimip3b" / esm / scenario
    pr = locked_source_file(receipt, "precipitation", "pr", raw_root)
    tas = locked_source_file(receipt, "paired_temperature", "tas", raw_root)
    return receipt, receipt_path, pr, tas


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--esm", default="ukesm1-0-ll")
    parser.add_argument("--scenario", default="ssp126")
    parser.add_argument("--year", type=int, default=2092)
    args = parser.parse_args()
    esm, scenario, year = args.esm, args.scenario, args.year
    receipt, receipt_path, pr, tas = source_context(esm, scenario, year)
    out_root = destination(esm, scenario, year)
    out_root.mkdir(parents=True, exist_ok=True)
    with (xr.open_dataset(CALENDAR, engine="h5netcdf") as calendar,
          xr.open_dataset(pr, engine="h5netcdf") as pr_ds,
          xr.open_dataset(tas, engine="h5netcdf") as tas_ds):
        latitudes = pr_ds.lat.values.copy()
        require(len(latitudes) == 360 and len(pr_ds.lon) == 720
                and np.array_equal(calendar.lat.values, latitudes)
                and np.array_equal(calendar.lon.values, pr_ds.lon.values)
                and np.array_equal(pr_ds.lat.values, tas_ds.lat.values)
                and np.array_equal(pr_ds.lon.values, tas_ds.lon.values),
                "source/calendar coordinate mismatch")
        steps = receipt["precipitation"].get("daily_steps", receipt.get("decoded_content_contract", {}).get("daily_steps"))
        require(steps is not None and len(pr_ds.time) == len(tas_ds.time) == steps
                and np.array_equal(pr_ds.time.values, tas_ds.time.values)
                and int(pr_ds.time.dt.year.values[0]) == receipt["period_start_year"]
                and int(pr_ds.time.dt.year.values[-1]) == receipt["period_end_year"]
                and pr_ds.pr.attrs.get("units") == "kg m-2 s-1"
                and tas_ds.tas.attrs.get("units") == "K",
                "paired source chronology or units changed")
        records = []
        for start in range(0, 360, 10):
            stop = start + 10
            tile = out_root / f"lat{start:03d}_{stop:03d}"
            tile.mkdir(parents=True, exist_ok=True)
            validation = tile / "validation.json"
            if validation.exists():
                old = json.loads(validation.read_text())
                current = validate_tile(tile, start, stop, calendar, latitudes, year)
                require(old == current, f"previous tile changed: {tile}")
                records.append(current)
                print(f"reused {start:03d}-{stop:03d}: {current['season_rows']} rows", flush=True)
                continue
            for label, builder in (("season", "build_crop_year_features.py"),
                                   ("stages", "build_crop_stage_features.py")):
                output = tile / f"{label}.parquet"
                worker_receipt = tile / f"{label}.resource.json"
                log = tile / f"{label}.log"
                require(not output.exists() and not worker_receipt.exists() and not log.exists(),
                        f"partial tile requires review before rerun: {tile}")
                command = [str(ROOT / ".venv/bin/python"), str(ROOT / "scripts" / builder),
                           "--precip", str(pr), "--temperature", str(tas),
                           "--calendar", str(CALENDAR), "--crop", "mai", "--irrigation", "noirr",
                           "--year-start", str(year), "--year-end", str(year),
                           "--lat-start", str(start), "--lat-stop", str(stop),
                           "--wet-day-mm", "1", "--out", str(output)]
                result = run(command, worker_receipt, log, max_mib=512,
                             min_free_gib=130, max_log_mib=2, interval=0.2,
                             write_paths=[output], max_new_disk_mib=64)
                require(result["status"] == "completed", f"worker failed: {label} {tile}: {result['status']}")
            record = validate_tile(tile, start, stop, calendar, latitudes, year)
            validation.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
            records.append(record)
            print(f"completed {start:03d}-{stop:03d}: {record['season_rows']} rows; "
                  f"peak {record['peak_sampled_rss_bytes']} bytes", flush=True)
    require(len(records) == 36 and sum(r["lat_stop"] - r["lat_start"] for r in records) == 360,
            "global latitude partition incomplete")
    result = {
        "schema": "isimip3b_global_mai_noirr_source_only_tiles_v1",
        "status": "complete_engineering_pending_independent_validation_not_response_damage_or_scc",
        "esm": esm, "member": receipt["member"], "scenario": scenario, "harvest_year": year,
        "source_receipt_path": str(receipt_path.relative_to(ROOT)),
        "source_receipt_sha256": digest(receipt_path),
        "precip_sha512": receipt["precipitation"]["sha512"],
        "temperature_sha512": receipt["paired_temperature"]["sha512"],
        "season_rows": sum(r["season_rows"] for r in records),
        "stage_rows": sum(r["stage_rows"] for r in records),
        "peak_sampled_worker_rss_bytes": max(r["peak_sampled_rss_bytes"] for r in records),
        "tiles": records,
    }
    manifest = out_root / "global_manifest.json"
    if manifest.exists():
        require(json.loads(manifest.read_text()) == result, "previous global manifest changed")
    else:
        manifest.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(f"global source-only tiles complete: {result['season_rows']} season rows", flush=True)


if __name__ == "__main__":
    main()
