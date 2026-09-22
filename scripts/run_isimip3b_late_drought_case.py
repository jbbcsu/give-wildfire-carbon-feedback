#!/usr/bin/env python3
"""Acquire, build, validate, and evict one late-century extrema pair."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

from run_bounded_job import run


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT/"data/raw/isimip3b"
MANIFEST = ROOT/"data/provenance/isimip3b_five_esm_late_drought_extrema_20260921.json"
OUTPUT_ROOT = ROOT/"data/interim/five_esm_late_drought_20260921"
MIN_FREE = 130*2**30
DOWNLOAD_HEADROOM = 1*2**30


def digest(path: Path, algorithm: str = "sha512") -> str:
    value = hashlib.new(algorithm)
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8*1024*1024), b""):
            value.update(block)
    return value.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def acquire(record: dict) -> Path:
    path = RAW/record["esm"]/record["scenario"]/record["variable"]/record["file_name"]
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        require(path.stat().st_size == record["bytes"] and digest(path) == record["sha512"], "resident extrema identity differs")
        return path
    partial = path.with_suffix(path.suffix+".part")
    needed = max(0, int(record["bytes"])-(partial.stat().st_size if partial.exists() else 0))
    require(shutil.disk_usage(ROOT).free >= MIN_FREE+needed+DOWNLOAD_HEADROOM, "insufficient free disk for one bounded download")
    print(f"downloading {record['esm']} {record['scenario']} {record['variable']} ({record['bytes']} bytes)", flush=True)
    completed = subprocess.run(["curl", "-L", "--fail", "--retry", "50", "--retry-all-errors", "--retry-delay", "10",
                                "--connect-timeout", "30", "--speed-limit", "1024", "--speed-time", "120",
                                "--continue-at", "-", "--silent", "--show-error", "--output", str(partial), record["file_url"]], check=False)
    require(completed.returncode == 0, f"curl failed with code {completed.returncode}")
    require(partial.stat().st_size == record["bytes"] and digest(partial) == record["sha512"], "downloaded extrema identity differs")
    partial.replace(path)
    print(f"verified {record['variable']} {path.name}", flush=True)
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--esm", required=True)
    parser.add_argument("--scenario", choices=("ssp126", "ssp370", "ssp585"), required=True)
    args = parser.parse_args()
    manifest = json.loads(MANIFEST.read_text())
    records = [item for item in manifest["objects"] if item["esm"] == args.esm and item["scenario"] == args.scenario]
    require(len(records) == 2 and {item["variable"] for item in records} == {"tasmin", "tasmax"}, "exact frozen extrema pair required")
    slug = f"{args.esm}_{args.scenario}"
    out_dir = OUTPUT_ROOT/slug
    validation = out_dir/"validation.json"
    eviction = ROOT/f"data/provenance/{slug}_late_drought_extrema_eviction_20260921.json"
    climate_completed = eviction.exists()
    if climate_completed:
        receipt = json.loads(eviction.read_text())
        require(receipt["status"] == "two_verified_reproducible_raw_files_deleted" and validation.exists(), "completed-case receipt differs")
        build = json.loads((ROOT/f"data/interim/{slug}_late_drought_builder_20260921.resource.json").read_text())
        checked = json.loads((ROOT/f"data/interim/{slug}_late_drought_validation_20260921.resource.json").read_text())
    else:
        require(not out_dir.exists(), "preserved partial derived case requires review")
        for record in sorted(records, key=lambda item: item["variable"]):
            acquire(record)
        build_receipt = ROOT/f"data/interim/{slug}_late_drought_builder_20260921.resource.json"
        build_log = ROOT/f"data/interim/{slug}_late_drought_builder_20260921.log"
        require(not build_receipt.exists() and not build_log.exists(), "preserved builder attempt requires review")
        build = run([sys.executable, str(ROOT/"scripts/build_isimip3b_late_drought_pair.py"), "--esm", args.esm,
                     "--scenario", args.scenario, "--raw-root", str(RAW), "--out-dir", str(out_dir)],
                    build_receipt, build_log, max_mib=512, min_free_gib=130, max_log_mib=2,
                    write_paths=[out_dir], max_new_disk_mib=128)
        require(build["status"] == "completed", f"bounded builder failed: {build['status']}")
        validation_receipt = ROOT/f"data/interim/{slug}_late_drought_validation_20260921.resource.json"
        validation_log = ROOT/f"data/interim/{slug}_late_drought_validation_20260921.log"
        require(not validation_receipt.exists() and not validation_log.exists(), "preserved validator attempt requires review")
        checked = run([sys.executable, str(ROOT/"scripts/validate_isimip3b_late_drought_pair.py"),
                       "--pair-dir", str(out_dir), "--output", str(validation)],
                      validation_receipt, validation_log, max_mib=512, min_free_gib=130, max_log_mib=2)
        require(checked["status"] == "completed" and json.loads(validation.read_text())["status"] == "passed", "independent validation failed")
        completed = subprocess.run([sys.executable, str(ROOT/"scripts/evict_validated_late_drought_extrema_pair.py"),
                                    "--pair-dir", str(out_dir), "--validation", str(validation), "--receipt", str(eviction)],
                                   check=False, capture_output=True, text=True)
        require(completed.returncode == 0, f"verified extrema eviction failed: {completed.stderr[-1000:]}")
        require(all(not (RAW/item["esm"]/item["scenario"]/item["variable"]/item["file_name"]).exists() for item in records), "raw extrema pair remains")
    crop_summary = out_dir/"crop_window_summary.json"
    crop_validation = out_dir/"crop_window_validation.json"
    if not crop_summary.exists():
        crop_receipt = ROOT/f"data/interim/{slug}_late_drought_crop_windows_20260921.resource.json"
        crop_log = ROOT/f"data/interim/{slug}_late_drought_crop_windows_20260921.log"
        require(not crop_receipt.exists() and not crop_log.exists(), "preserved crop-summary attempt requires review")
        crop_job = run([sys.executable, str(ROOT/"scripts/summarize_isimip3b_late_drought_crop_windows.py"),
                        "--pair-dir", str(out_dir), "--output", str(crop_summary)], crop_receipt, crop_log,
                       max_mib=512, min_free_gib=130, max_log_mib=2)
        require(crop_job["status"] == "completed", "bounded crop-window summary failed")
    if not crop_validation.exists():
        audit_receipt = ROOT/f"data/interim/{slug}_late_drought_crop_window_validation_20260921.resource.json"
        audit_log = ROOT/f"data/interim/{slug}_late_drought_crop_window_validation_20260921.log"
        require(not audit_receipt.exists() and not audit_log.exists(), "preserved crop-validation attempt requires review")
        audit_job = run([sys.executable, str(ROOT/"scripts/validate_isimip3b_late_drought_crop_windows.py"),
                         "--summary", str(crop_summary), "--output", str(crop_validation)],
                        audit_receipt, audit_log, max_mib=512, min_free_gib=130, max_log_mib=2)
        require(audit_job["status"] == "completed", "bounded crop-window validation failed")
    require(json.loads(crop_validation.read_text())["status"] == "passed", "crop-window validation not passed")
    print(json.dumps({"status": "case_and_crop_windows_completed_validated_raw_evicted", "esm": args.esm,
                      "scenario": args.scenario, "builder_peak_rss_bytes": build["sampled_peak_group_rss_bytes"],
                      "validator_peak_rss_bytes": checked["sampled_peak_group_rss_bytes"],
                      "derived": json.loads((out_dir/"result.json").read_text())["output"],
                      "crop_window_summary_sha256": digest(crop_summary, "sha256"),
                      "eviction_receipt": str(eviction.relative_to(ROOT))}))


if __name__ == "__main__":
    main()
