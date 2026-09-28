#!/usr/bin/env python3
"""Acquire exact NASS sorghum/cotton county yield records with checkpoints."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DOWNLOADER = ROOT / "us_county_validation/scripts/download_nass_quickstats_api.py"
PROTOCOL = ROOT / "US_SORGHUM_COTTON_DIRECT_PRACTICE_ACQUISITION_PROTOCOL_20260928.md"
YEARS = tuple(range(1981, 2019))
PRACTICES = ("IRRIGATED", "NON-IRRIGATED")
CROPS = {
    "sorghum_grain": {"commodity_desc": "SORGHUM", "class_desc": "ALL CLASSES", "util_practice_desc": "GRAIN", "unit_desc": "BU / ACRE"},
    "cotton_upland": {"commodity_desc": "COTTON", "class_desc": "UPLAND", "util_practice_desc": "ALL UTILIZATION PRACTICES", "unit_desc": "LB / ACRE"},
}


def digest(path: Path, algorithm: str = "sha256") -> str:
    value = hashlib.new(algorithm)
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 << 20), b""):
            value.update(block)
    return value.hexdigest()


def load_downloader():
    spec = importlib.util.spec_from_file_location("nass_value_downloader", DOWNLOADER)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load credential-safe NASS downloader")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def query(crop: str, practice: str, year: int) -> dict[str, str]:
    return {
        "source_desc": "SURVEY", "sector_desc": "CROPS", **CROPS[crop],
        "statisticcat_desc": "YIELD", "agg_level_desc": "COUNTY",
        "freq_desc": "ANNUAL", "reference_period_desc": "YEAR",
        "domain_desc": "TOTAL", "prodn_practice_desc": practice,
        "year": str(year), "format": "JSON",
    }


def safe_name(crop: str, practice: str, year: int) -> str:
    return f"quickstats_{crop}_{practice.lower().replace('-', '_')}_{year}.json"


def validate_rows(rows: list[dict[str, Any]], parameters: dict[str, str]) -> None:
    for field in (
        "source_desc", "sector_desc", "commodity_desc", "class_desc",
        "statisticcat_desc", "agg_level_desc", "freq_desc",
        "reference_period_desc", "domain_desc", "prodn_practice_desc",
        "util_practice_desc", "unit_desc", "year",
    ):
        expected = parameters[field]
        bad = next((i for i, row in enumerate(rows) if str(row.get(field)) != expected), None)
        if bad is not None:
            raise ValueError(f"response {field} differs at row {bad}")


def request_with_retry(base: Any, endpoint: str, parameters: dict[str, str], key: str) -> dict[str, Any]:
    last: Exception | None = None
    def bounded_opener(request: Any, timeout: float = 90):
        return base.urlopen(request, timeout=min(timeout, 20))

    for delay in (0, 2, 8):
        if delay:
            time.sleep(delay)
        try:
            return base.request_json(endpoint, parameters, key, opener=bounded_opener)
        except (RuntimeError, TimeoutError, OSError) as error:
            last = error
    raise RuntimeError("NASS request failed after bounded retries") from last


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--secrets", type=Path, default=ROOT / ".secrets/nass.env")
    parser.add_argument("--raw-dir", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--throttle-seconds", type=float, default=0.5)
    args = parser.parse_args()
    if args.receipt.exists():
        raise ValueError("fresh receipt required")
    if not args.raw_dir.resolve().is_relative_to((ROOT / "data/raw").resolve()):
        raise ValueError("raw directory must remain under ignored data/raw")
    base = load_downloader()
    key = base.read_key(args.secrets)
    args.raw_dir.mkdir(parents=True, exist_ok=True)
    records = []
    for crop in CROPS:
        for practice in PRACTICES:
            for year in YEARS:
                parameters = query(crop, practice, year)
                path = args.raw_dir / safe_name(crop, practice, year)
                if path.exists():
                    payload = json.loads(path.read_text(encoding="utf-8"))
                    rows = payload.get("data")
                    if not isinstance(rows, list):
                        raise ValueError(f"cached data invalid: {path}")
                    validate_rows(rows, parameters)
                    count = len(rows)
                    source = "validated_checkpoint"
                else:
                    count_payload = request_with_retry(base, base.COUNT_ENDPOINT, parameters, key)
                    count = int(str(count_payload["count"]))
                    if count < 0 or count > base.MAX_API_RECORDS:
                        raise ValueError("NASS count outside bounded range")
                    if count:
                        payload = request_with_retry(base, base.DATA_ENDPOINT, parameters, key)
                        rows = payload.get("data")
                        if not isinstance(rows, list) or len(rows) != count:
                            raise ValueError("NASS row count differs from preflight")
                        validate_rows(rows, parameters)
                    else:
                        payload, rows = {"data": []}, []
                    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
                    source = "live_official_api"
                    time.sleep(args.throttle_seconds)
                records.append({
                    "crop": crop, "practice": practice, "year": year,
                    "count": count, "raw_path": str(path), "bytes": path.stat().st_size,
                    "sha512": digest(path, "sha512"), "source": source,
                    "query_parameters_excluding_key": parameters,
                })
    receipt = {
        "schema": "nass_sorghum_cotton_direct_practice_acquisition/v1",
        "created_at_utc": datetime.now(UTC).isoformat(),
        "status": "acquired_exact_nass_records_no_modeling",
        "protocol": {"path": str(PROTOCOL.relative_to(ROOT)), "sha256": digest(PROTOCOL)},
        "record_count": len(records), "records": records,
        "total_api_rows": sum(row["count"] for row in records),
        "credential_stored": False, "yield_model_run": False,
        "response_damage_or_scc_authorized": False,
        "implementation": {"path": str(Path(__file__).resolve().relative_to(ROOT)), "sha256": digest(Path(__file__).resolve())},
    }
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": receipt["status"], "record_count": len(records), "total_api_rows": receipt["total_api_rows"]}, indent=2))


if __name__ == "__main__":
    main()
