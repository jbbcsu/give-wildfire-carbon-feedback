#!/usr/bin/env python3
"""Bounded NOAA county-average weather identity/schema pilot; no outcomes."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
from urllib.request import HTTPRedirectHandler, Request, build_opener

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "us_county_validation/scripts"))
from audit_nclimgrid_county_average_sample import load_area_average, load_crosswalk

PROTOCOL = ROOT / "US_NCLIMGRID_COUNTY_AVERAGE_EXTENSION_PILOT_20260916.md"
PROTOCOL_SHA = "0b54bc42873daa8e7155b3be1cc6b8b88435f038fd98e9f6193ce399590a5d44"
CROSSWALK = ROOT / "data/raw/us_county/nclimgrid_county_averages/us-state-codes_ncei-to-fips.csv"
MONTHS = ((1981, 1), (2024, 2), (2025, 7))
VARIABLES = ("PRCP", "TAVG", "TMIN", "TMAX")


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None


OPENER = build_opener(NoRedirect)


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(2**20), b""):
            digest.update(block)
    return digest.hexdigest()


def identity(response, url):
    if response.status != 200 or response.geturl() != url:
        raise ValueError("NOAA response status/final URL differs")
    headers = response.headers
    required = {"content_length": headers.get("Content-Length"),
                "etag": headers.get("ETag"),
                "last_modified": headers.get("Last-Modified"),
                "content_type": headers.get("Content-Type")}
    if any(not value for value in required.values()):
        raise ValueError("NOAA response missing identity header")
    required["content_length"] = int(required["content_length"])
    return required


def fetch(url, path, max_bytes):
    headers = {"User-Agent": "GIVE-precipitation-SCC-county-average-pilot/1.0",
               "Accept-Encoding": "identity"}
    with OPENER.open(Request(url, headers=headers, method="HEAD"), timeout=25) as response:
        expected = identity(response, url)
    if not 0 < expected["content_length"] <= max_bytes:
        raise ValueError("NOAA object exceeds pilot byte cap")
    with OPENER.open(Request(url, headers=headers, method="GET"), timeout=60) as response:
        observed = identity(response, url)
        if observed != expected:
            raise ValueError("NOAA HEAD/GET identity changed")
        body = response.read(max_bytes + 1)
    if len(body) != expected["content_length"]:
        raise ValueError("NOAA object truncated or exceeds byte cap")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(body)
    return {"url": url, "path": str(path.relative_to(ROOT)),
            "sha256": sha(path), "http": expected}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    out = args.out_dir.resolve()
    if out.exists() or not out.is_relative_to(ROOT / "data/interim") or out == ROOT / "data/interim":
        raise ValueError("fresh ignored output required")
    protocol_hash = sha(PROTOCOL)
    if protocol_hash != PROTOCOL_SHA:
        raise ValueError("pilot design changed after registration")
    crosswalk_hash = sha(CROSSWALK)
    state_map = load_crosswalk(CROSSWALK)
    result = {"status": "pilot_validated", "protocol_sha256": protocol_hash,
              "crosswalk_sha256": crosswalk_hash, "months": {},
              "yield_outcome_read": False, "response_or_scc_estimated": False}
    out.mkdir(parents=True)
    for year, month in MONTHS:
        label = f"{year}{month:02d}"
        root = f"https://www.ncei.noaa.gov/data/nclimgrid-daily/access/averages/{year}"
        files = {}
        loads = {}
        for variable in VARIABLES:
            name = f"{variable.lower()}-{label}-cty-scaled.csv"
            url = f"{root}/{name}"
            path = out / label / name
            files[variable] = fetch(url, path, 2 * 2**20)
            loads[variable] = load_area_average(path, variable, state_map)
            if loads[variable]["year_month"] != (year, month):
                raise ValueError("NOAA county CSV month mismatch")
        version_name = f"ncdd-{label}-version.txt"
        version_path = out / label / version_name
        version_file = fetch(f"{root}/{version_name}", version_path, 16 * 2**10)
        support = {key: set(value["records"]) for key, value in loads.items()}
        if any(keys != support["PRCP"] for keys in support.values()):
            raise ValueError("NOAA variable county sets differ")
        max_midpoint = 0.0
        max_order = 0.0
        min_precip = float("inf")
        for county in sorted(support["PRCP"]):
            p = loads["PRCP"]["records"][county]["values"]
            avg = loads["TAVG"]["records"][county]["values"]
            lo = loads["TMIN"]["records"][county]["values"]
            hi = loads["TMAX"]["records"][county]["values"]
            min_precip = min(min_precip, float(np.min(p)))
            max_midpoint = max(max_midpoint, float(np.max(np.abs(avg - (lo + hi) / 2))))
            max_order = max(max_order, float(np.max(np.maximum(lo - avg, avg - hi))))
        if min_precip < 0 or max_midpoint > 0.020 or max_order > 0.011:
            raise ValueError("NOAA physical/rounding check failed")
        result["months"][label] = {"county_rows": len(support["PRCP"]),
                                   "real_days": len(next(iter(loads["PRCP"]["records"].values()))["values"]),
                                   "max_temperature_midpoint_error_c": max_midpoint,
                                   "max_temperature_order_violation_c": max_order,
                                   "minimum_daily_precipitation_mm": min_precip,
                                   "files": files, "version": {**version_file,
                                                                 "text": version_path.read_text().strip()}}
        print(f"{label}: {len(support['PRCP'])} county rows, identity/schema passed", flush=True)
    result["code_sha256"] = sha(Path(__file__))
    (out / "result.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"status": result["status"], "months": list(result["months"])}))


if __name__ == "__main__":
    main()
