#!/usr/bin/env python3
"""Sequential, resumable NOAA county-average batches under per-job guards."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from run_bounded_job import run

BASE = ROOT / "data/interim/nclimgrid_county_averages_full_20260916"
JOBS = BASE / "job_receipts"
BATCH_SCRIPT = ROOT / "scripts/acquire_us_nclimgrid_county_averages_batch.py"
PROTOCOL = ROOT / "US_NCLIMGRID_COUNTY_AVERAGE_FULL_ACQUISITION_20260916.md"
PROTOCOL_SHA = "362a680df48eb0e16a76492d813441e14e32222c238218b97fe97c5a1d2b803f"


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(2**20), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_batch(year, half, out):
    path = out / "result.json"
    if not path.is_file():
        raise ValueError(f"existing batch lacks complete result: {out}")
    result = json.loads(path.read_text())
    months = {f"{year}{month:02d}" for month in (range(1, 7) if half == 1 else range(7, 13))}
    if (result["status"] != "complete_county_average_weather_batch" or
        result["year"] != year or result["half"] != half or
        result["protocol_sha256"] != PROTOCOL_SHA or
        result["code_sha256"] != sha(BATCH_SCRIPT) or set(result["months"]) != months):
        raise ValueError(f"batch identity/code/protocol changed: {out}")
    count = 0
    size = 0
    for month in result["months"].values():
        if month["county_rows"] != 3107 or not 28 <= month["real_days"] <= 31:
            raise ValueError("batch county/calendar result changed")
        for source in [*month["sources"].values(), month["version"]]:
            body = ROOT / source["path"]
            if not body.is_relative_to(out) or not body.is_file():
                raise ValueError("batch source path/bytes missing")
            if sha(body) != source["sha256"] or body.stat().st_size != source["http"]["content_length"]:
                raise ValueError("batch source content changed")
            count += 1
            size += body.stat().st_size
    if count != 30:
        raise ValueError("six-month batch does not have 30 source objects")
    return {"year": year, "half": half, "result_sha256": sha(path),
            "source_objects": count, "source_bytes": size}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-new-batches", type=int, required=True)
    args = parser.parse_args()
    if not 0 <= args.max_new_batches <= 90 or sha(PROTOCOL) != PROTOCOL_SHA:
        raise ValueError("batch cap or protocol identity invalid")
    JOBS.mkdir(parents=True, exist_ok=True)
    # Recent outcome years first; all 90 half-years are still mandatory.
    order = [(year, half) for year in range(2020, 2026) for half in (1, 2)] + [
        (year, half) for year in range(1981, 2020) for half in (1, 2)]
    new = 0
    completed = []
    for year, half in order:
        out = BASE / f"{year}_h{half}"
        if out.exists():
            completed.append(verify_batch(year, half, out))
            print(f"{year}_h{half}: existing complete batch verified", flush=True)
            continue
        if new >= args.max_new_batches:
            break
        receipt = JOBS / f"{year}_h{half}.json"
        log = JOBS / f"{year}_h{half}.log"
        if receipt.exists() or log.exists():
            raise ValueError("unresolved existing batch job evidence")
        command = [str(ROOT / ".venv/bin/python"), "-B", str(BATCH_SCRIPT),
                   "--year", str(year), "--half", str(half), "--out-dir", str(out)]
        result = run(command, receipt, log, max_mib=512, min_free_gib=130,
                     max_log_mib=1, write_paths=[out], max_new_disk_mib=64)
        print(f"{year}_h{half}: {result['status']} in {result['wall_seconds']:.1f}s; "
              f"peak RSS {result['sampled_peak_group_rss_bytes']/2**20:.1f}MiB", flush=True)
        if result["status"] != "completed":
            raise RuntimeError(f"bounded batch failed; inspect {log}")
        completed.append(verify_batch(year, half, out))
        new += 1
    summary = {"status": "complete" if len(completed) == 90 else "partial",
               "completed_batches": len(completed), "new_batches_this_run": new,
               "source_objects": sum(item["source_objects"] for item in completed),
               "source_bytes": sum(item["source_bytes"] for item in completed),
               "batches": completed, "protocol_sha256": PROTOCOL_SHA,
               "batch_code_sha256": sha(BATCH_SCRIPT),
               "nass_outcomes_read": False, "response_or_scc_estimated": False,
               "code_sha256": sha(Path(__file__))}
    if len(completed) == 90:
        target = BASE / "acquisition_summary.json"
        if target.exists():
            raise ValueError("refusing to overwrite full acquisition summary")
        target.write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n")
    print(json.dumps({key: summary[key] for key in ("status", "completed_batches", "new_batches_this_run",
                                                    "source_objects", "source_bytes")}))


if __name__ == "__main__":
    main()
