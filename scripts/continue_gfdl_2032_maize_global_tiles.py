#!/usr/bin/env python3
"""Sequential, resumable, bounded full-grid climate-feature engineering."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tomllib
import argparse

import numpy as np
import pandas as pd
import xarray as xr

from run_bounded_job import run
from run_gfdl_single_year_global_tile_pilot import ROOT, SOURCE_RECEIPT, RAW_ROOT, CALENDAR


def digest(path: Path, algorithm: str = "sha256") -> str:
    result = hashlib.new(algorithm)
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def receipt_for_year(year: int) -> Path:
    if 2032 <= year <= 2039:
        return SOURCE_RECEIPT
    if 2042 <= year <= 2049:
        return ROOT / "data/provenance/isimip3b_later_century_gfdl_ssp126_2041_2050.toml"
    if 2092 <= year <= 2099:
        return ROOT / "data/provenance/isimip3b_later_century_gfdl_ssp126_2091_2100.toml"
    raise ValueError("harvest year outside registered daily source windows")


def locked_source_file(receipt: dict, section: str, variable: str,
                       raw_root: Path = RAW_ROOT) -> Path:
    record = receipt[section]
    path = raw_root / variable / record["file_name"]
    require(path.is_file() and path.stat().st_size == record["bytes"],
            f"daily source size/path changed: {path}")
    require(digest(path, "sha512") == record["sha512"], f"daily source SHA-512 changed: {path}")
    audit = ROOT / record["content_audit"]
    require(audit.is_file(), f"daily source content audit absent: {audit}")
    # The 2031--2040 receipt also pins the audit bytes. Later registered
    # receipts do not contain a content-audit digest, so require the audit's
    # decoded identity/content fields to agree with the source receipt.
    if "content_audit_sha256" in record:
        require(digest(audit) == record["content_audit_sha256"],
                f"daily source content-audit digest changed: {audit}")
    content = json.loads(audit.read_text())
    declared = receipt.get("decoded_content_contract", {})
    def contract_value(name: str) -> object:
        if name in record:
            return record[name]
        if name == "units":
            key = "precipitation_units" if variable == "pr" else "temperature_units"
            if key in declared:
                return declared[key]
        elif name in declared:
            return declared[name]
        # Some older MRI receipts omit these keys, but pin the decoded
        # audit's exact bytes. Accept its recorded value only after that
        # SHA-256 check, then enforce units/calendar/period independently.
        require("content_audit_sha256" in record and content.get(name) is not None,
                f"source receipt and pinned audit missing declared {name}: {path}")
        return content[name]
    require(content.get("result") == "passed" and content.get("file_name") == record["file_name"]
            and content.get("sha512") == record["sha512"]
            and content.get("bytes") == record["bytes"]
            and content.get("variable") == variable
            and content.get("units") == contract_value("units")
            and content.get("calendar") == contract_value("calendar")
            and content.get("start_time") == contract_value("start_time")
            and content.get("end_time") == contract_value("end_time")
            and content.get("dimensions", {}).get("time") == contract_value("daily_steps"),
            f"daily source decoded content audit disagrees: {audit}")
    expected_units = "kg m-2 s-1" if variable == "pr" else "K"
    require(content["units"] == expected_units and content["calendar"] == "proleptic_gregorian"
            and content["start_time"].split("T")[0] == f"{receipt['period_start_year']}-01-01"
            and content["end_time"].split("T")[0] == f"{receipt['period_end_year']}-12-31"
            and content["start_time"].split("T")[1] in {"00:00:00", "12:00:00"}
            and content["end_time"].split("T")[1] == content["start_time"].split("T")[1],
            f"daily source pinned audit physical units/calendar/period failed: {audit}")
    return path


def validate_tile(tile: Path, start: int, stop: int, calendar: xr.Dataset, latitudes: np.ndarray, year: int = 2032) -> dict:
    season_path = tile / "season.parquet"
    stage_path = tile / "stages.parquet"
    season = pd.read_parquet(season_path)
    stages = pd.read_parquet(stage_path)
    key = ["harvest_year", "lat", "lon", "crop", "irrigation"]
    stage_key = key + ["stage_id"]
    require(not season.duplicated(key).any(), f"duplicate season key in {tile}")
    require(not stages.duplicated(stage_key).any(), f"duplicate stage key in {tile}")
    require(len(stages) == 3 * len(season), f"three-stage support mismatch in {tile}")
    cal = calendar.isel(lat=slice(start, stop))
    valid = (np.isfinite(cal.planting_day.values) & np.isfinite(cal.maturity_day.values)
             & (cal.planting_day.values >= 1) & (cal.maturity_day.values >= 1))
    require(len(season) == int(valid.sum()), f"valid calendar-cell count mismatch in {tile}")
    require(set(season.harvest_year) <= {year} and set(season.crop) <= {"mai"}
            and set(season.irrigation) <= {"noirr"}, f"identity mismatch in {tile}")
    require(set(season.lat) <= set(float(x) for x in latitudes[start:stop]),
            f"latitude outside tile in {tile}")
    require(set(stages.stage_id) <= {1, 2, 3}, f"unknown stage in {tile}")
    if len(season):
        aggregate = stages.groupby(key, sort=False).agg(
            stage_days=("stage_days", "sum"), rain_stage=("precip_mm", "sum"),
            wet_stage=("wet_days_n", "sum"), rx1_stage=("rx1day_mm", "max"),
        )
        joint = season.set_index(key).join(aggregate, validate="one_to_one")
        require(not joint[["stage_days", "rain_stage", "wet_stage", "rx1_stage"]].isna().any(axis=None),
                f"stage join incomplete in {tile}")
        require(np.array_equal(joint.season_days.to_numpy(), joint.stage_days.to_numpy()),
                f"stage-day reconciliation failed in {tile}")
        require(np.array_equal(joint.wet_days_n.to_numpy(), joint.wet_stage.to_numpy()),
                f"wet-day reconciliation failed in {tile}")
        require(float(np.max(np.abs(joint.precip_mm - joint.rain_stage))) <= 1e-8,
                f"rain reconciliation failed in {tile}")
        require(float(np.max(np.abs(joint.rx1day_mm - joint.rx1_stage))) <= 1e-8,
                f"Rx1day reconciliation failed in {tile}")
    peak = 0
    for label in ("season", "stages"):
        receipt = json.loads((tile / f"{label}.resource.json").read_text())
        require(receipt["status"] == "completed" and receipt["sampled_peak_group_rss_bytes"] <= 512 * 2**20,
                f"{label} worker memory/status failed in {tile}")
        require(receipt["sampled_peak_new_disk_bytes"] <= 64 * 2**20,
                f"{label} owned-output failed in {tile}")
        peak = max(peak, int(receipt["sampled_peak_group_rss_bytes"]))
    return {
        "lat_start": start, "lat_stop": stop, "season_rows": len(season),
        "stage_rows": len(stages), "season_sha256": digest(season_path),
        "stages_sha256": digest(stage_path), "peak_sampled_rss_bytes": peak,
        "status": "passed_engineering_only",
    }


def run_year(year: int = 2032) -> None:
    out_root = ROOT / f"data/interim/gfdl_ssp126_global_{year}_maize_full_20260917"
    receipt = tomllib.loads(receipt_for_year(year).read_text(encoding="utf-8"))
    require(receipt.get("esm") == "GFDL-ESM4" and receipt.get("member") == "r1i1p1f1"
            and receipt.get("scenario") == "ssp126" and receipt.get("dataset_version") == "20210512",
            "source identity changed")
    require(receipt["period_start_year"] + 1 <= year <= receipt["period_end_year"] - 1,
            "crop year outside exact source decade")
    pr = locked_source_file(receipt, "precipitation", "pr")
    tas = locked_source_file(receipt, "paired_temperature", "tas")
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
                "global calendar/source coordinate mismatch")
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
            tile_receipt = tile / "validation.json"
            if tile_receipt.exists():
                old = json.loads(tile_receipt.read_text())
                new = validate_tile(tile, start, stop, calendar, latitudes, year)
                require(old == new, f"completed tile changed: {tile}")
                records.append(new)
                print(f"reused {start:03d}-{stop:03d}: {new['season_rows']} rows", flush=True)
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
                result = run(command, worker_receipt, log, max_mib=512, min_free_gib=130,
                             max_log_mib=2, interval=0.2, write_paths=[output], max_new_disk_mib=64)
                require(result["status"] == "completed", f"{label} failed in {tile}: {result['status']}")
            record = validate_tile(tile, start, stop, calendar, latitudes, year)
            tile_receipt.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
            records.append(record)
            print(f"completed {start:03d}-{stop:03d}: {record['season_rows']} rows; peak {record['peak_sampled_rss_bytes']} bytes", flush=True)
    require(len(records) == 36 and sum(x["lat_stop"] - x["lat_start"] for x in records) == 360,
            "full latitude partition incomplete")
    manifest = out_root / "global_manifest.json"
    result = {
        "schema": f"gfdl_ssp126_{year}_maize_global_tile_engineering_v1",
        "status": "complete_engineering_pending_independent_global_validation_not_damage_or_scc",
        "season_rows": sum(x["season_rows"] for x in records),
        "stage_rows": sum(x["stage_rows"] for x in records),
        "peak_sampled_worker_rss_bytes": max(x["peak_sampled_rss_bytes"] for x in records),
        "tiles": records,
    }
    if manifest.exists():
        require(json.loads(manifest.read_text()) == result, "existing global manifest changed")
    else:
        manifest.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(f"global engineering tiles complete: {result['season_rows']} season rows", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--year", type=int, default=2032)
    args = parser.parse_args()
    run_year(args.year)


if __name__ == "__main__":
    main()
