#!/usr/bin/env python3
"""Run bounded one-year sorghum/cotton county-weather feature jobs sequentially."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKER = ROOT / "scripts/build_sorghum_cotton_county_average_features.py"


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 << 20), b""):
            value.update(block)
    return value.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--calendar", required=True)
    parser.add_argument("--county-inventory", required=True)
    parser.add_argument("--out-root", type=Path, required=True)
    parser.add_argument("--summary-out", type=Path, required=True)
    args = parser.parse_args()
    completed = []
    for year in range(1981, 2019):
        destination = args.out_root / str(year)
        receipt_path, feature_path = destination / "result.json", destination / "features.parquet"
        if destination.exists():
            receipt = json.loads(receipt_path.read_text())
            if receipt["status"] != "sorghum_cotton_county_average_features_built" or receipt["year"] != year or digest(feature_path) != receipt["features_sha256"]:
                raise ValueError(f"existing year {year} fails receipt/hash checks")
        else:
            subprocess.run([
                sys.executable, str(WORKER), "--year", str(year), "--calendar", args.calendar,
                "--county-inventory", args.county_inventory, "--out-dir", str(destination),
            ], cwd=ROOT, check=True)
            receipt = json.loads(receipt_path.read_text())
        completed.append({
            "year": year, "rows": receipt["rows"], "counties": receipt["counties"],
            "features_sha256": receipt["features_sha256"], "receipt_sha256": digest(receipt_path),
        })
    summary = {
        "status": "complete_38_sequential_year_jobs", "years": "1981-2018",
        "completed_years": len(completed), "total_rows": sum(item["rows"] for item in completed),
        "peak_concurrency": 1, "yield_values_read": False,
        "response_estimation_authorized": False, "scc_authorized": False,
        "year_receipts": completed,
    }
    args.summary_out.parent.mkdir(parents=True, exist_ok=True)
    args.summary_out.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps({key: summary[key] for key in ["status", "completed_years", "total_rows", "peak_concurrency"]}, indent=2))


if __name__ == "__main__":
    main()
