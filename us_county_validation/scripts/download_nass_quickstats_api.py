#!/usr/bin/env python3
"""Bounded USDA NASS Quick Stats API fallback for county crop yields.

This fallback uses the official Quick Stats count and data endpoints. It first
runs the exact filtered count request, refuses a request above the API's 50,000
record limit, and stores raw JSON plus a credential-free provenance record.
The API key is read only from the GIVE repository-root .secrets/nass.env file;
it is never printed, written to a manifest, or embedded in a stored URL.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

API_BASE = "https://quickstats.nass.usda.gov/api"
COUNT_ENDPOINT = f"{API_BASE}/get_counts/"
DATA_ENDPOINT = f"{API_BASE}/api_GET/"
MAX_API_RECORDS = 50_000
ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SECRETS = ROOT / ".secrets" / "nass.env"


def read_key(path: Path) -> str:
    if not path.is_file():
        raise FileNotFoundError(
            f"NASS key file is absent: {path}. Create it locally with NASS_API_KEY=...; do not commit it."
        )
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" not in stripped:
            raise ValueError("NASS key file contains a non-assignment line")
        name, value = stripped.split("=", 1)
        values[name.strip()] = value.strip().strip("'").strip('"')
    key = values.get("NASS_API_KEY") or values.get("QUICKSTATS_API_KEY")
    if not key:
        raise ValueError("NASS key file must define NASS_API_KEY or QUICKSTATS_API_KEY")
    return key


def query_parameters(args: argparse.Namespace) -> dict[str, str]:
    if args.year_min != args.year_max:
        raise ValueError("Quick Stats API acquisition is intentionally limited to one year per request")
    parameters = {
        "source_desc": args.source,
        "sector_desc": "CROPS",
        "commodity_desc": args.commodity.upper(),
        "statisticcat_desc": "YIELD",
        "agg_level_desc": "COUNTY",
        "freq_desc": "ANNUAL",
        "reference_period_desc": "YEAR",
        "year": str(args.year_min),
        "format": "JSON",
    }
    if not args.series_discovery:
        if not args.unit:
            raise ValueError("--unit is required unless --series-discovery is used")
        if not args.util_practice:
            raise ValueError("--util-practice is required unless --series-discovery is used")
        parameters.update({
            "domain_desc": "TOTAL",
            "prodn_practice_desc": args.prodn_practice,
            "util_practice_desc": args.util_practice,
            "unit_desc": args.unit,
        })
    return parameters


def request_json(
    endpoint: str,
    parameters: dict[str, str],
    key: str,
    opener: Callable[..., Any] = urlopen,
) -> dict[str, Any]:
    request_parameters = {**parameters, "key": key}
    request = Request(
        f"{endpoint}?{urlencode(request_parameters)}",
        headers={"Accept": "application/json", "User-Agent": "GIVE-precipitation-SCC/1.0"},
    )
    try:
        with opener(request, timeout=90) as response:
            payload = response.read()
    except HTTPError as error:
        raise RuntimeError(f"NASS API request failed with HTTP {error.code}") from None
    except URLError as error:
        raise RuntimeError("NASS API request failed due to network/transport error") from error
    try:
        decoded = json.loads(payload)
    except json.JSONDecodeError as error:
        raise RuntimeError("NASS API returned invalid JSON") from error
    if not isinstance(decoded, dict):
        raise RuntimeError("NASS API response must be a JSON object")
    if "error" in decoded:
        raise RuntimeError("NASS API reported an error; inspect credentials and official filter values")
    return decoded


def count_records(parameters: dict[str, str], key: str, opener: Callable[..., Any] = urlopen) -> int:
    response = request_json(COUNT_ENDPOINT, parameters, key, opener)
    try:
        count = int(str(response["count"]))
    except (KeyError, TypeError, ValueError) as error:
        raise RuntimeError("NASS count response lacks an integer count") from error
    if count < 0:
        raise RuntimeError("NASS count response is negative")
    return count


def safe_stem(args: argparse.Namespace) -> str:
    parts = [args.commodity]
    if args.series_discovery:
        parts.append("series_discovery")
    else:
        parts.extend([args.util_practice, args.prodn_practice])
    normalized = re.sub(r"[^a-z0-9]+", "_", "_".join(parts).lower()).strip("_")
    return f"quickstats_{normalized}_county_yield_{args.year_min}"


def write_result(
    response: dict[str, Any], parameters: dict[str, str], count: int, out_dir: Path, stem: str
) -> tuple[Path, Path]:
    data = response.get("data")
    if not isinstance(data, list):
        raise RuntimeError("NASS data response lacks a list-valued data field")
    if len(data) != count:
        raise RuntimeError(f"NASS data row count {len(data)} differs from preflight count {count}")
    if len(data) > MAX_API_RECORDS:
        raise RuntimeError("NASS data response exceeds the hard 50,000-record cap")
    response_fields = (
        "source_desc", "sector_desc", "commodity_desc", "statisticcat_desc",
        "agg_level_desc", "freq_desc", "reference_period_desc", "domain_desc",
        "prodn_practice_desc", "util_practice_desc", "unit_desc", "year",
    )
    for field in response_fields:
        expected = parameters.get(field)
        if expected is None:
            continue
        mismatches = [index for index, row in enumerate(data) if str(row.get(field)) != expected]
        if mismatches:
            raise RuntimeError(
                f"NASS response violated requested {field}={expected!r} at row {mismatches[0]}"
            )
    out_dir.mkdir(parents=True, exist_ok=True)
    raw_path = out_dir / f"{stem}.json"
    manifest_path = out_dir / "MANIFEST.jsonl"
    raw_bytes = json.dumps(response, indent=2, sort_keys=True).encode("utf-8") + b"\n"
    raw_path.write_bytes(raw_bytes)
    record = {
        "source": "USDA NASS Quick Stats API",
        "official_count_endpoint": COUNT_ENDPOINT,
        "official_data_endpoint": DATA_ENDPOINT,
        "query_parameters_excluding_key": dict(sorted(parameters.items())),
        "preflight_count": count,
        "retrieved_utc": datetime.now(UTC).isoformat(),
        "raw_file": str(raw_path),
        "raw_bytes": len(raw_bytes),
        "raw_sha512": hashlib.sha512(raw_bytes).hexdigest(),
        "license": "USDA public data; preserve disclosure/suppression flags and source attribution",
        "role": "US county crop-yield validation outcome; not an SCC input",
    }
    with manifest_path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, sort_keys=True) + "\n")
    return raw_path, manifest_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--commodity", required=True, help="e.g. CORN; one crop per request")
    parser.add_argument("--unit", help="explicit NASS yield unit, e.g. BU / ACRE")
    parser.add_argument(
        "--prodn-practice", default="ALL PRODUCTION PRACTICES",
        help="exact NASS prodn_practice_desc value",
    )
    parser.add_argument("--util-practice", help="exact NASS util_practice_desc value")
    parser.add_argument("--year-min", type=int, required=True)
    parser.add_argument("--year-max", type=int, required=True)
    parser.add_argument("--source", default="SURVEY", help="explicit NASS source_desc filter")
    parser.add_argument("--secrets-file", default=str(DEFAULT_SECRETS))
    parser.add_argument("--out-dir", default="data/raw/us_county/nass_api")
    parser.add_argument(
        "--count-only", action="store_true",
        help="authenticate and print only the credential-free preflight count",
    )
    parser.add_argument(
        "--series-discovery", action="store_true",
        help="bounded raw metadata discovery before locking unit/practice filters",
    )
    args = parser.parse_args()
    if args.year_min > args.year_max:
        raise ValueError("--year-min cannot exceed --year-max")
    key = read_key(Path(args.secrets_file))
    parameters = query_parameters(args)
    count = count_records(parameters, key)
    print(f"preflight count: {count}")
    if count > MAX_API_RECORDS:
        raise RuntimeError(
            f"Refusing data request: preflight count {count} exceeds {MAX_API_RECORDS} records"
        )
    if args.count_only:
        return
    if count == 0:
        raise RuntimeError("Refusing empty data request: revise the documented NASS filters")
    response = request_json(DATA_ENDPOINT, parameters, key)
    raw_path, _ = write_result(
        response, parameters, count, Path(args.out_dir),
        safe_stem(args),
    )
    print(f"stored {count} raw county-yield records at {raw_path}")


if __name__ == "__main__":
    main()
