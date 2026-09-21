#!/usr/bin/env python3
"""Acquire one fixed six-month NOAA county-average weather batch safely."""
import argparse
import calendar
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
import sys
from urllib.request import HTTPRedirectHandler, Request, build_opener

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "us_county_validation/scripts"))
from audit_nclimgrid_county_average_sample import load_area_average, load_crosswalk

PROTOCOL = ROOT / "US_NCLIMGRID_COUNTY_AVERAGE_FULL_ACQUISITION_20260916.md"
PROTOCOL_SHA = "362a680df48eb0e16a76492d813441e14e32222c238218b97fe97c5a1d2b803f"
PILOT = ROOT / "data/interim/nclimgrid_county_average_terminal_pilot_20260916_v2/result.json"
PILOT_SHA = "a256aa61657f1fa7a1f445ee3f62fa595167dbe25dc2d5183e5fa1c58ba627e2"
CROSSWALK = ROOT / "data/raw/us_county/nclimgrid_county_averages/us-state-codes_ncei-to-fips.csv"
VARIABLES = ("PRCP", "TAVG", "TMIN", "TMAX")


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None


OPENER = build_opener(NoRedirect)


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(2**20), b""):
            digest.update(block)
    return digest.hexdigest()


def http_identity(response, url):
    if response.status != 200 or response.geturl() != url:
        raise ValueError("NOAA status or final URL differs")
    headers = response.headers
    if headers.get("Content-Encoding") not in (None, "identity"):
        raise ValueError("NOAA unexpected content encoding")
    result = {"content_length": headers.get("Content-Length"),
              "etag": headers.get("ETag"),
              "last_modified": headers.get("Last-Modified"),
              "content_type": headers.get("Content-Type")}
    if any(not value for value in result.values()):
        raise ValueError("NOAA required identity header absent")
    result["content_length"] = int(result["content_length"])
    return result


def fetch(url, path, max_bytes):
    if not url.startswith("https://www.ncei.noaa.gov/data/nclimgrid-daily/access/averages/"):
        raise ValueError("NOAA source host/path changed")
    headers = {"User-Agent": "GIVE-precipitation-SCC-county-averages/1.0",
               "Accept-Encoding": "identity"}
    with OPENER.open(Request(url, headers=headers, method="HEAD"), timeout=25) as response:
        expected = http_identity(response, url)
    if not 0 < expected["content_length"] <= max_bytes:
        raise ValueError("NOAA object outside per-file byte cap")
    with OPENER.open(Request(url, headers=headers, method="GET"), timeout=60) as response:
        observed = http_identity(response, url)
        if observed != expected:
            raise ValueError("NOAA HEAD/GET identity changed")
        body = response.read(max_bytes + 1)
    if len(body) != expected["content_length"]:
        raise ValueError("NOAA object truncated or exceeds cap")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(body)
    return {"url": url, "path": str(path.relative_to(ROOT)),
            "sha256": sha(path), "http": expected,
            "retrieved_utc": datetime.now(UTC).isoformat()}


def reference_counties(state_map):
    if sha(PILOT) != PILOT_SHA:
        raise ValueError("validated NOAA pilot receipt changed")
    pilot = json.loads(PILOT.read_text())
    if pilot["status"] != "pilot_validated" or sha(CROSSWALK) != pilot["crosswalk_sha256"]:
        raise ValueError("pilot/crosswalk validation invalid")
    source = pilot["months"]["198101"]["files"]["PRCP"]
    path = ROOT / source["path"]
    if sha(path) != source["sha256"]:
        raise ValueError("pilot reference source changed")
    loaded = load_area_average(path, "PRCP", state_map)
    return set(loaded["records"])


def check_month(year, month, out, state_map, reference):
    label = f"{year}{month:02d}"
    url_root = f"https://www.ncei.noaa.gov/data/nclimgrid-daily/access/averages/{year}"
    sources = {}
    loaded = {}
    for variable in VARIABLES:
        name = f"{variable.lower()}-{label}-cty-scaled.csv"
        path = out / label / name
        sources[variable] = fetch(f"{url_root}/{name}", path, 2 * 2**20)
        loaded[variable] = load_area_average(path, variable, state_map)
        if loaded[variable]["year_month"] != (year, month):
            raise ValueError("NOAA CSV month differs")
        if set(loaded[variable]["records"]) != reference:
            raise ValueError("NOAA county support differs from fixed pilot")
    version_name = f"ncdd-{label}-version.txt"
    version_path = out / label / version_name
    version = fetch(f"{url_root}/{version_name}", version_path, 16 * 2**10)
    text = version_path.read_text(encoding="utf-8").strip()
    end_day = calendar.monthrange(year, month)[1]
    expected_line = (f"nClimGrid-Daily v1-0-0 complete for {year}-{month:02d}-01 "
                     f"through {year}-{month:02d}-{end_day:02d}")
    if not text.startswith(expected_line):
        raise ValueError("NOAA month version not complete/matched")
    min_precip = float("inf")
    max_midpoint = 0.0
    max_order = 0.0
    for county in reference:
        p = loaded["PRCP"]["records"][county]["values"]
        avg = loaded["TAVG"]["records"][county]["values"]
        lo = loaded["TMIN"]["records"][county]["values"]
        hi = loaded["TMAX"]["records"][county]["values"]
        min_precip = min(min_precip, float(np.min(p)))
        max_midpoint = max(max_midpoint, float(np.max(np.abs(avg - (lo + hi) / 2))))
        max_order = max(max_order, float(np.max(np.maximum(lo - avg, avg - hi))))
    if min_precip < 0 or max_midpoint > 0.020 or max_order > 0.011:
        raise ValueError("NOAA month physical/rounding check failed")
    return {"county_rows": len(reference), "real_days": end_day,
            "minimum_daily_precipitation_mm": min_precip,
            "maximum_temperature_midpoint_discrepancy_c": max_midpoint,
            "maximum_temperature_order_violation_c": max_order,
            "sources": sources, "version": {**version, "text": text}}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--half", type=int, choices=(1, 2), required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    out = args.out_dir.resolve()
    if not 1981 <= args.year <= 2025 or out.exists() or not out.is_relative_to(ROOT / "data/interim") or out == ROOT / "data/interim":
        raise ValueError("fixed year/fresh ignored output required")
    protocol_hash = sha(PROTOCOL)
    if protocol_hash != PROTOCOL_SHA:
        raise ValueError("full-acquisition protocol changed after registration")
    state_map = load_crosswalk(CROSSWALK)
    reference = reference_counties(state_map)
    if len(reference) != 3107:
        raise ValueError("pilot reference county count changed")
    months = range(1, 7) if args.half == 1 else range(7, 13)
    result = {"status": "complete_county_average_weather_batch",
              "year": args.year, "half": args.half,
              "protocol_sha256": protocol_hash, "pilot_sha256": PILOT_SHA,
              "crosswalk_sha256": sha(CROSSWALK), "source_product": "NOAA nClimGrid-Daily v1.0.0 county scaled area averages",
              "months": {}, "weather_exposure_built": False,
              "nass_outcomes_read": False, "response_or_scc_estimated": False}
    out.mkdir(parents=True)
    for month in months:
        result["months"][f"{args.year}{month:02d}"] = check_month(args.year, month, out, state_map, reference)
        print(f"{args.year}-{month:02d}: four CSVs/version validated", flush=True)
    result["code_sha256"] = sha(Path(__file__))
    (out / "result.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"status": result["status"], "year": args.year, "half": args.half,
                      "months": len(result["months"])}))


if __name__ == "__main__":
    main()
