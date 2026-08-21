#!/usr/bin/env python3
"""Download documented county-week U.S. Drought Monitor area-share statistics.

The official REST endpoint accepts one state and at most one year per request.
This script intentionally requires explicit states and years, writes raw CSVs
under the gitignored US validation raw-data tree, and records URL, retrieval
time, bytes, and SHA-512 for every response. It does not interpret USDM
categories as a projected climate variable.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlencode


API = "https://usdmdataservices.unl.edu/api/CountyStatistics/GetDroughtSeverityStatisticsByAreaPercent"


def build_url(state: str, year: int) -> str:
    query = urlencode({
        "aoi": state.upper(),
        "startdate": f"1/1/{year}",
        "enddate": f"12/31/{year}",
        "statisticsType": "2",
    })
    return f"{API}?{query}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", action="append", required=True, help="two-letter state code; repeatable")
    parser.add_argument("--year-min", type=int, required=True)
    parser.add_argument("--year-max", type=int, required=True)
    parser.add_argument("--out-dir", default="data/raw/us_county/usdm")
    parser.add_argument("--timeout-seconds", type=int, default=60)
    args = parser.parse_args()
    if args.year_min > args.year_max:
        raise ValueError("--year-min must not exceed --year-max")
    states = sorted({state.strip().upper() for state in args.state})
    if any(len(state) != 2 or not state.isalpha() for state in states):
        raise ValueError("each --state must be a two-letter alphabetic code")

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = out_dir / "MANIFEST.jsonl"
    with manifest.open("a", encoding="utf-8") as manifest_stream:
        for state in states:
            for year in range(args.year_min, args.year_max + 1):
                target = out_dir / f"usdm_county_area_pct_{state}_{year}.csv"
                url = build_url(state, year)
                if target.exists() and target.stat().st_size > 0:
                    payload = target.read_bytes()
                    status = "existing"
                else:
                    # macOS's system curl uses the trusted system certificate
                    # store; the bundled Python runtime may not. Do not use
                    # curl's insecure (-k) mode.
                    response = subprocess.run(
                        ["curl", "--fail", "--location", "--silent", "--show-error",
                         "--max-time", str(args.timeout_seconds), url],
                        check=True,
                        capture_output=True,
                    )
                    payload = response.stdout
                    if not payload:
                        raise RuntimeError(f"empty USDM response for {state} {year}")
                    rows = list(csv.reader(payload.decode("utf-8-sig").splitlines()))
                    if len(rows) < 2:
                        raise RuntimeError(f"USDM response has no data rows for {state} {year}")
                    target.write_bytes(payload)
                    status = "downloaded"
                record = {
                    "source": "U.S. Drought Monitor county severity statistics REST service",
                    "url": url,
                    "state": state,
                    "year": year,
                    "retrieved_utc": datetime.now(UTC).isoformat(),
                    "status": status,
                    "bytes": len(payload),
                    "sha512": hashlib.sha512(payload).hexdigest(),
                    "file": str(target),
                }
                manifest_stream.write(json.dumps(record, sort_keys=True) + "\n")
                print(f"{status}: {target.name} ({len(payload)} bytes)")


if __name__ == "__main__":
    main()
