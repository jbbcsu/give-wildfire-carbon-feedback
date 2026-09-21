#!/usr/bin/env python3
"""Acquire fixed 2020–2025 NASS all-practice county-yield snapshot, key safe."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "us_county_validation/scripts"))
import download_nass_quickstats_api as nass

PROTOCOL = ROOT / "US_2020_2025_NASS_HOLDOUT_PROTOCOL_20260916.md"
PROTOCOL_SHA = "f0b1384babe36d141dc349f767b03045a1c0a0fd94d2b58cbac47edd02389a71"
SERIES = {"CORN": "GRAIN", "SOYBEANS": "ALL UTILIZATION PRACTICES"}


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(2**20), b""):
            digest.update(block)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    out = args.out_dir.resolve()
    if out.exists() or not out.is_relative_to(ROOT / "data/interim") or out == ROOT / "data/interim":
        raise ValueError("fresh ignored interim output required")
    if sha(PROTOCOL) != PROTOCOL_SHA:
        raise ValueError("pre-acquisition protocol changed")
    key = nass.read_key(nass.DEFAULT_SECRETS)
    out.mkdir(parents=True)
    rows = []
    for commodity, utilization in SERIES.items():
        for year in range(2020, 2026):
            arguments = argparse.Namespace(commodity=commodity, unit="BU / ACRE",
                                           util_practice=utilization,
                                           prodn_practice="ALL PRODUCTION PRACTICES",
                                           year_min=year, year_max=year,
                                           source="SURVEY", series_discovery=False)
            parameters = nass.query_parameters(arguments)
            count = nass.count_records(parameters, key)
            if not 0 < count <= nass.MAX_API_RECORDS:
                raise ValueError(f"{commodity}/{year}: invalid or excessive official count {count}")
            response = nass.request_json(nass.DATA_ENDPOINT, parameters, key)
            stem = nass.safe_stem(arguments)
            if (out / f"{stem}.json").exists():
                raise ValueError("refusing to overwrite an outcome snapshot")
            raw, _ = nass.write_result(response, parameters, count, out, stem)
            rows.append({"commodity": commodity, "year": year, "preflight_rows": count,
                         "raw_path": str(raw.relative_to(ROOT)), "raw_sha256": sha(raw)})
            print(f"{commodity}/{year}: {count} rows; snapshot saved", flush=True)
    summary = {"status": "raw_outcomes_acquired_no_values_analyzed",
               "protocol_sha256": sha(PROTOCOL), "credential_written": False,
               "filters": "official SURVEY county annual all-production-practices yield; corn GRAIN, soy ALL UTILIZATION PRACTICES",
               "snapshots": rows, "code_sha256": sha(Path(__file__))}
    (out / "snapshot_summary.json").write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"status": summary["status"], "objects": len(rows),
                      "rows": sum(item["preflight_rows"] for item in rows)}))


if __name__ == "__main__":
    main()
