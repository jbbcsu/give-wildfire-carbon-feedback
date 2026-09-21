#!/usr/bin/env python3
"""Sequential, resumable, guarded NOAA county-average feature partitions."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from run_bounded_job import run

BASE = ROOT / "data/interim/us_county/noaa_county_average_crop_year_features_20260916"
JOBS = BASE / "job_receipts"
BUILDER = ROOT / "scripts/build_us_county_average_crop_year_features.py"
PROTOCOL = ROOT / "US_COUNTY_AVERAGE_CROP_YEAR_FEATURE_PROTOCOL_20260916.md"
CALENDAR_DIR = ROOT / "data/interim/us_county/nass_calendar_1981_2025_20260916"
CALENDAR = CALENDAR_DIR / "nass_usual_date_calendars_1981_2025.csv"
SOURCE_SUMMARY = ROOT / "data/interim/nclimgrid_county_averages_full_20260916/acquisition_summary.json"


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(2**20), b""):
            digest.update(block)
    return digest.hexdigest()


def verify(year: int, directory: Path) -> dict:
    receipt_path = directory / "result.json"
    feature_path = directory / "features.parquet"
    receipt = json.loads(receipt_path.read_text())
    if (receipt["status"] != "county_average_crop_year_features_built" or
        receipt["year"] != year or receipt["code_sha256"] != sha(BUILDER) or
        receipt["protocol_sha256"] != sha(PROTOCOL) or
        receipt["source_summary_sha256"] != sha(SOURCE_SUMMARY) or
        receipt["calendar_sha256"] != sha(CALENDAR) or
        receipt["features_sha256"] != sha(feature_path) or
        receipt["audit"]["input_counties"] != 3107 or
        receipt["audit"]["output_rows"] <= 0 or
        receipt["nass_outcomes_read"] is not False or
        receipt["response_or_scc_estimated"] is not False):
        raise ValueError(f"NOAA feature partition failed identity/integrity checks: {year}")
    return {"year": year, "result_sha256": sha(receipt_path),
            "features_sha256": sha(feature_path),
            "rows": receipt["audit"]["output_rows"],
            "counties": receipt["audit"]["output_counties"],
            "output_bytes": feature_path.stat().st_size}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-new-years", type=int, required=True)
    args = parser.parse_args()
    if not 0 <= args.max_new_years <= 45:
        raise ValueError("max new feature-year count outside 0..45")
    source = json.loads(SOURCE_SUMMARY.read_text())
    calendar = json.loads((CALENDAR_DIR / "result.json").read_text())
    if (source["status"] != "complete" or source["completed_batches"] != 90 or
        source["source_objects"] != 2700 or
        calendar["status"] != "nass_calendar_1981_2025_overlap_validated" or
        calendar["calendar_sha256"] != sha(CALENDAR)):
        raise ValueError("source/calendar prerequisites incomplete")
    JOBS.mkdir(parents=True, exist_ok=True)
    order = list(range(2020, 2026)) + list(range(1981, 2020))
    completed: list[dict] = []
    new = 0
    for year in order:
        directory = BASE / str(year)
        if directory.exists():
            completed.append(verify(year, directory))
            print(f"{year}: existing features verified", flush=True)
            continue
        if new >= args.max_new_years:
            break
        receipt_path = JOBS / f"{year}.json"
        log_path = JOBS / f"{year}.log"
        if receipt_path.exists() or log_path.exists():
            raise ValueError("unresolved prior feature-year job evidence")
        command = [str(ROOT / ".venv/bin/python"), "-B", str(BUILDER),
                   "--year", str(year), "--out-dir", str(directory)]
        bounded = run(command, receipt_path, log_path, max_mib=512,
                      min_free_gib=130, max_log_mib=1, write_paths=[directory],
                      max_new_disk_mib=64)
        print(f"{year}: {bounded['status']} in {bounded['wall_seconds']:.1f}s; "
              f"peak RSS {bounded['sampled_peak_group_rss_bytes']/2**20:.1f}MiB", flush=True)
        if bounded["status"] != "completed":
            raise RuntimeError(f"feature-year build failed: {log_path}")
        completed.append(verify(year, directory))
        new += 1
    summary = {"status": "complete" if len(completed) == 45 else "partial",
               "completed_years": len(completed), "new_years_this_run": new,
               "total_rows": sum(item["rows"] for item in completed),
               "total_output_bytes": sum(item["output_bytes"] for item in completed),
               "years": completed, "source_summary_sha256": sha(SOURCE_SUMMARY),
               "calendar_sha256": sha(CALENDAR), "protocol_sha256": sha(PROTOCOL),
               "code_sha256": sha(Path(__file__)),
               "nass_outcomes_read": False, "response_or_scc_estimated": False}
    if len(completed) == 45:
        target = BASE / "feature_summary.json"
        if target.exists():
            raise ValueError("refusing to overwrite complete feature summary")
        target.write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n")
    print(json.dumps({key: summary[key] for key in
                      ("status", "completed_years", "new_years_this_run", "total_rows")}))


if __name__ == "__main__":
    main()
