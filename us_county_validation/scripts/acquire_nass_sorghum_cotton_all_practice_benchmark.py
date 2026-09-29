#!/usr/bin/env python3
"""Acquire count-gated all-practice NASS yields for the frozen benchmark audit."""
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
PROTOCOL = ROOT / "US_SORGHUM_COTTON_ALL_PRACTICE_BENCHMARK_PROTOCOL_20260928.md"
YEARS = tuple(range(1981, 2019))
CROPS = {
    "sorghum_grain": {
        "commodity_desc": "SORGHUM", "class_desc": "ALL CLASSES",
        "util_practice_desc": "GRAIN", "unit_desc": "BU / ACRE",
    },
    "cotton_upland": {
        "commodity_desc": "COTTON", "class_desc": "UPLAND",
        "util_practice_desc": "ALL UTILIZATION PRACTICES",
        "unit_desc": "LB / ACRE",
    },
}


def digest(path: Path, algorithm: str = "sha256") -> str:
    value = hashlib.new(algorithm)
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 << 20), b""):
            value.update(block)
    return value.hexdigest()


def load_downloader():
    spec = importlib.util.spec_from_file_location("nass_all_practice_benchmark", DOWNLOADER)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load credential-safe NASS downloader")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def query(crop: str, year: int) -> dict[str, str]:
    if crop not in CROPS or year not in YEARS:
        raise ValueError("unsupported benchmark query")
    return {
        "source_desc": "SURVEY", "sector_desc": "CROPS", **CROPS[crop],
        "statisticcat_desc": "YIELD", "agg_level_desc": "COUNTY",
        "freq_desc": "ANNUAL", "reference_period_desc": "YEAR",
        "domain_desc": "TOTAL", "prodn_practice_desc": "ALL PRODUCTION PRACTICES",
        "year": str(year), "format": "JSON",
    }


def validate_rows(rows: list[dict[str, Any]], parameters: dict[str, str]) -> None:
    fields = (
        "source_desc", "sector_desc", "commodity_desc", "class_desc",
        "statisticcat_desc", "agg_level_desc", "freq_desc",
        "reference_period_desc", "domain_desc", "prodn_practice_desc",
        "util_practice_desc", "unit_desc", "year",
    )
    for field in fields:
        expected = parameters[field]
        bad = next(
            (index for index, row in enumerate(rows) if str(row.get(field)) != expected),
            None,
        )
        if bad is not None:
            raise ValueError(f"benchmark response {field} differs at row {bad}")


def request_with_retry(
    base: Any, endpoint: str, parameters: dict[str, str], key: str, label: str,
) -> dict[str, Any]:
    last: Exception | None = None

    def bounded_opener(request: Any, timeout: float = 90):
        return base.urlopen(request, timeout=min(timeout, 30))

    for delay in (0, 3, 12, 30):
        if delay:
            time.sleep(delay)
        try:
            return base.request_json(
                endpoint, parameters, key, opener=bounded_opener,
            )
        except (RuntimeError, TimeoutError, OSError) as error:
            last = error
    raise RuntimeError(f"NASS request failed after bounded retries for {label}") from last


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--secrets", type=Path, default=ROOT / ".secrets/nass.env")
    parser.add_argument("--raw-dir", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--throttle-seconds", type=float, default=0.75)
    args = parser.parse_args()
    raw_dir = args.raw_dir.resolve()
    receipt_path = args.receipt.resolve()
    if receipt_path.exists():
        raise ValueError("fresh acquisition receipt required")
    if not raw_dir.is_relative_to((ROOT / "data/raw").resolve()):
        raise ValueError("raw benchmark responses must remain under ignored data/raw")
    base = load_downloader()
    key = base.read_key(args.secrets)
    raw_dir.mkdir(parents=True, exist_ok=True)
    records = []
    for crop in CROPS:
        for year in YEARS:
            parameters = query(crop, year)
            label = f"{crop}|{year}"
            path = raw_dir / f"quickstats_{crop}_all_production_practices_{year}.json"
            if path.exists():
                payload = json.loads(path.read_text(encoding="utf-8"))
                rows = payload.get("data")
                if not isinstance(rows, list):
                    raise ValueError(f"cached benchmark response invalid: {path}")
                validate_rows(rows, parameters)
                count = len(rows)
                source = "validated_checkpoint"
            else:
                count_payload = request_with_retry(
                    base, base.COUNT_ENDPOINT, parameters, key, label,
                )
                try:
                    count = int(str(count_payload["count"]))
                except (KeyError, TypeError, ValueError) as error:
                    raise RuntimeError(f"invalid count response for {label}") from error
                if count < 0 or count > base.MAX_API_RECORDS:
                    raise ValueError(f"bounded record count failed for {label}")
                if count:
                    payload = request_with_retry(
                        base, base.DATA_ENDPOINT, parameters, key, label,
                    )
                    rows = payload.get("data")
                    if not isinstance(rows, list) or len(rows) != count:
                        raise ValueError(f"benchmark row count differs for {label}")
                    validate_rows(rows, parameters)
                else:
                    payload = {"data": []}
                path.write_text(
                    json.dumps(payload, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8",
                )
                source = "live_official_api"
                time.sleep(args.throttle_seconds)
            records.append({
                "crop": crop, "year": year, "count": count,
                "raw_path": str(path.relative_to(ROOT)),
                "bytes": path.stat().st_size, "sha512": digest(path, "sha512"),
                "source": source,
                "query_parameters_excluding_key": parameters,
            })
    receipt = {
        "schema": "nass_sorghum_cotton_all_practice_acquisition_v1",
        "created_at_utc": datetime.now(UTC).isoformat(),
        "status": "acquired_exact_all_practice_benchmark_no_modeling",
        "protocol": {
            "path": str(PROTOCOL.relative_to(ROOT)), "sha256": digest(PROTOCOL),
        },
        "implementation": {
            "path": str(Path(__file__).resolve().relative_to(ROOT)),
            "sha256": digest(Path(__file__).resolve()),
        },
        "record_count": len(records), "records": records,
        "total_api_rows": sum(row["count"] for row in records),
        "credential_stored": False, "weather_read": False,
        "moisture_family_used": False, "yield_model_run": False,
        "causal_damage_or_scc_authorized": False,
    }
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8",
    )
    print(json.dumps({
        "status": receipt["status"], "record_count": len(records),
        "total_api_rows": receipt["total_api_rows"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
