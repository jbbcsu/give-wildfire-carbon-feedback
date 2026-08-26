#!/usr/bin/env python3
"""Export a tracked-safe receipt for the ignored national NASS API archive.

The receipt exposes query identities, acquisition times, byte sizes, and
SHA-512 hashes, but no API key or county-level response value.  The complete
ignored manifest and every raw JSON object are revalidated before export.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[1]
DEFAULT_RAW_DIR = PROJECT_ROOT / "data/raw/us_county/nass_api/national_all_practice_1981_2019"
DEFAULT_MANIFEST = DEFAULT_RAW_DIR / "MANIFEST.jsonl"
DEFAULT_RECEIPT = PROJECT_ROOT / "data/provenance/nass_quickstats_national_all_practice_1981_2019_content_receipt.json"

SCHEMA = "nass_quickstats_national_all_practice_content_receipt_v1"
EXPECTED_OBJECTS = 78
EXPECTED_TOTAL_BYTES = 190_394_822
EXPECTED_TOTAL_RECORDS = 146_672
REVIEWED_MANIFEST_SIZE_BYTES = 90_636
REVIEWED_MANIFEST_SHA512 = (
    "dbc3ec766f1dbaa0e8a909a52a54b1144fc46006f4ba0cae396baef1551c3d77"
    "a66e41b562f61d17a6986d0bbafc8a1c9ee12ee185e20007266455474131d0a9"
)
SHA512 = re.compile(r"[0-9a-f]{128}")
MANIFEST_FIELDS = {
    "license", "official_count_endpoint", "official_data_endpoint", "preflight_count",
    "query_parameters_excluding_key", "raw_bytes", "raw_file", "raw_sha512",
    "retrieved_utc", "role", "source",
}
QUERY_FIELDS = {
    "agg_level_desc", "commodity_desc", "domain_desc", "format", "freq_desc",
    "prodn_practice_desc", "reference_period_desc", "sector_desc", "source_desc",
    "statisticcat_desc", "unit_desc", "util_practice_desc", "year",
}
SERIES = {
    "CORN": {"util": "GRAIN", "stem": "corn_grain", "outcome_crop": "corn_grain"},
    "SOYBEANS": {
        "util": "ALL UTILIZATION PRACTICES",
        "stem": "soybeans_all_utilization_practices",
        "outcome_crop": "soybeans",
    },
}
FORBIDDEN_FIELD_NAMES = {"api_key", "key", "access_token", "authorization", "password", "secret"}


def sha512_bytes(payload: bytes) -> str:
    return hashlib.sha512(payload).hexdigest()


def canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def serialize(receipt: Mapping[str, Any]) -> bytes:
    return (json.dumps(receipt, indent=2, sort_keys=True, ensure_ascii=True) + "\n").encode("utf-8")


def _strict_mapping(value: object, fields: set[str], label: str) -> Mapping[str, Any]:
    if not isinstance(value, dict) or set(value) != fields:
        observed = sorted(value) if isinstance(value, dict) else type(value).__name__
        raise RuntimeError(f"{label} fields differ: {observed}")
    return value


def _validate_timestamp(value: object, label: str) -> str:
    if not isinstance(value, str):
        raise RuntimeError(f"{label} must be an ISO timestamp")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as error:
        raise RuntimeError(f"{label} is not a valid ISO timestamp") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None or parsed.utcoffset().total_seconds() != 0:
        raise RuntimeError(f"{label} must have an explicit UTC offset")
    return value


def _expected_query(commodity: str, year: int) -> dict[str, str]:
    return {
        "agg_level_desc": "COUNTY",
        "commodity_desc": commodity,
        "domain_desc": "TOTAL",
        "format": "JSON",
        "freq_desc": "ANNUAL",
        "prodn_practice_desc": "ALL PRODUCTION PRACTICES",
        "reference_period_desc": "YEAR",
        "sector_desc": "CROPS",
        "source_desc": "SURVEY",
        "statisticcat_desc": "YIELD",
        "unit_desc": "BU / ACRE",
        "util_practice_desc": str(SERIES[commodity]["util"]),
        "year": str(year),
    }


def _expected_name(commodity: str, year: int) -> str:
    return (
        f"quickstats_{SERIES[commodity]['stem']}_all_production_practices_"
        f"county_yield_{year}.json"
    )


def _validate_raw_payload(payload: bytes, *, commodity: str, year: int, expected_rows: int) -> None:
    try:
        decoded = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RuntimeError(f"{commodity} {year} raw JSON is invalid") from error
    if not isinstance(decoded, dict) or set(decoded) != {"data"} or not isinstance(decoded["data"], list):
        raise RuntimeError(f"{commodity} {year} raw payload lacks one data array")
    rows = decoded["data"]
    if len(rows) != expected_rows or not rows:
        raise RuntimeError(f"{commodity} {year} raw row count differs from preflight")
    checks = {
        "year": str(year), "commodity_desc": commodity, "unit_desc": "BU / ACRE",
        "prodn_practice_desc": "ALL PRODUCTION PRACTICES",
        "util_practice_desc": str(SERIES[commodity]["util"]), "source_desc": "SURVEY",
        "sector_desc": "CROPS", "statisticcat_desc": "YIELD", "agg_level_desc": "COUNTY",
        "freq_desc": "ANNUAL", "reference_period_desc": "YEAR", "domain_desc": "TOTAL",
        "domaincat_desc": "NOT SPECIFIED",
    }
    required = set(checks) | {"Value", "state_ansi", "county_ansi"}
    for index, row in enumerate(rows):
        if not isinstance(row, dict) or not required.issubset(row):
            raise RuntimeError(f"{commodity} {year} raw row {index} lacks required fields")
        for field, expected in checks.items():
            if str(row[field]).strip().upper() != expected:
                raise RuntimeError(f"{commodity} {year} raw row {index} differs on {field}")


def build_receipt(manifest_path: Path = DEFAULT_MANIFEST, raw_dir: Path = DEFAULT_RAW_DIR) -> dict[str, Any]:
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise RuntimeError("NASS source manifest must be a regular file")
    before = manifest_path.read_bytes()
    if len(before) != REVIEWED_MANIFEST_SIZE_BYTES or sha512_bytes(before) != REVIEWED_MANIFEST_SHA512:
        raise RuntimeError("NASS source manifest differs from the reviewed complete manifest")
    records = []
    for line_number, line in enumerate(before.splitlines(), start=1):
        if not line.strip():
            raise RuntimeError("NASS source manifest contains a blank record")
        try:
            record = json.loads(line)
        except json.JSONDecodeError as error:
            raise RuntimeError(f"NASS manifest line {line_number} is invalid JSON") from error
        record = _strict_mapping(record, MANIFEST_FIELDS, f"NASS manifest line {line_number}")
        if FORBIDDEN_FIELD_NAMES & set(record):
            raise RuntimeError("NASS source manifest contains a credential-like field")
        query = _strict_mapping(record["query_parameters_excluding_key"], QUERY_FIELDS, "NASS query")
        if FORBIDDEN_FIELD_NAMES & set(query):
            raise RuntimeError("NASS query contains a credential-like field")
        commodity = str(query["commodity_desc"])
        if commodity not in SERIES:
            raise RuntimeError("NASS manifest contains an unregistered commodity")
        try:
            year = int(str(query["year"]))
        except ValueError as error:
            raise RuntimeError("NASS manifest year is invalid") from error
        if query != _expected_query(commodity, year):
            raise RuntimeError(f"NASS query differs from the locked {commodity} {year} series")
        name = _expected_name(commodity, year)
        raw_path = Path(str(record["raw_file"]))
        if raw_path.name != name:
            raise RuntimeError(f"NASS raw filename differs from query identity for {commodity} {year}")
        expected_path = raw_dir / name
        if raw_path.is_absolute():
            if raw_path.resolve() != expected_path.resolve():
                raise RuntimeError("NASS manifest raw path points outside the registered directory")
        elif (PROJECT_ROOT / raw_path).resolve() != expected_path.resolve():
            raise RuntimeError("NASS manifest raw path points outside the registered directory")
        if expected_path.is_symlink() or not expected_path.is_file():
            raise RuntimeError(f"NASS raw object is absent: {name}")
        payload = expected_path.read_bytes()
        raw_bytes = record["raw_bytes"]
        preflight = record["preflight_count"]
        digest = record["raw_sha512"]
        if type(raw_bytes) is not int or raw_bytes <= 0 or len(payload) != raw_bytes:
            raise RuntimeError(f"NASS raw byte length differs for {name}")
        if type(preflight) is not int or preflight <= 0:
            raise RuntimeError(f"NASS preflight count is invalid for {name}")
        if not isinstance(digest, str) or SHA512.fullmatch(digest) is None or sha512_bytes(payload) != digest:
            raise RuntimeError(f"NASS raw SHA-512 differs for {name}")
        _validate_timestamp(record["retrieved_utc"], f"{name} retrieval time")
        if record["source"] != "USDA NASS Quick Stats API":
            raise RuntimeError("NASS source label changed")
        if record["license"] != (
            "USDA public data; preserve disclosure/suppression flags and source attribution"
        ):
            raise RuntimeError("NASS source license statement changed")
        if record["role"] != "US county crop-yield validation outcome; not an SCC input":
            raise RuntimeError("NASS scientific role statement changed")
        if record["official_count_endpoint"] != "https://quickstats.nass.usda.gov/api/get_counts/" or record["official_data_endpoint"] != "https://quickstats.nass.usda.gov/api/api_GET/":
            raise RuntimeError("NASS official endpoint changed")
        _validate_raw_payload(payload, commodity=commodity, year=year, expected_rows=preflight)
        records.append(
            {
                "commodity": commodity,
                "outcome_crop": SERIES[commodity]["outcome_crop"],
                "year": year,
                "name": name,
                "raw_bytes": raw_bytes,
                "raw_records": preflight,
                "raw_sha512": digest,
                "retrieved_utc": record["retrieved_utc"],
                "query_parameters_excluding_key": dict(query),
            }
        )
    expected_keys = [(commodity, year) for commodity in ("CORN", "SOYBEANS") for year in range(1981, 2020)]
    observed_keys = [(value["commodity"], value["year"]) for value in records]
    if len(records) != EXPECTED_OBJECTS or observed_keys != expected_keys:
        raise RuntimeError("NASS manifest does not preserve the complete ordered 78-object scope")
    if sum(value["raw_bytes"] for value in records) != EXPECTED_TOTAL_BYTES:
        raise RuntimeError("NASS archive byte total differs from the reviewed scope")
    if sum(value["raw_records"] for value in records) != EXPECTED_TOTAL_RECORDS:
        raise RuntimeError("NASS archive record total differs from the reviewed scope")
    if manifest_path.read_bytes() != before:
        raise RuntimeError("NASS source manifest changed during receipt construction")

    receipt: dict[str, Any] = {
        "schema_version": SCHEMA,
        "dataset": {
            "source": "USDA NASS Quick Stats API",
            "documentation_url": "https://quickstats.nass.usda.gov/api",
            "license": "USDA public data; preserve disclosure/suppression flags and source attribution",
            "scientific_role": "US county historical predictive validation outcome only",
        },
        "scope": {
            "start_year": 1981, "end_year": 2019, "commodities": ["CORN", "SOYBEANS"],
            "object_count": len(records), "raw_bytes": sum(value["raw_bytes"] for value in records),
            "raw_records": sum(value["raw_records"] for value in records),
        },
        "source_manifest": {
            "name": manifest_path.name, "size_bytes": len(before),
            "sha512": sha512_bytes(before), "record_count": len(records),
        },
        "content_validation": {
            "all_object_byte_lengths_validated": True,
            "all_local_sha512_values_recomputed": True,
            "all_raw_json_schemas_and_exact_series_validated": True,
            "all_preflight_record_counts_recomputed_from_payloads": True,
        },
        "object_records_sha512": sha512_bytes(canonical_bytes(records)),
        "objects": records,
        "scientific_use_gates": {
            "relationship_estimated": False, "causal_claim_authorized": False,
            "damage_estimated": False, "scc_authorized": False,
        },
    }
    receipt["receipt_payload_sha512"] = sha512_bytes(canonical_bytes(receipt))
    validate_receipt(receipt)
    return receipt


def validate_receipt(receipt: Mapping[str, Any]) -> None:
    if receipt.get("schema_version") != SCHEMA:
        raise RuntimeError("NASS tracked receipt schema changed")
    objects = receipt.get("objects")
    if not isinstance(objects, list) or len(objects) != EXPECTED_OBJECTS:
        raise RuntimeError("NASS tracked receipt object scope changed")
    if receipt.get("object_records_sha512") != sha512_bytes(canonical_bytes(objects)):
        raise RuntimeError("NASS tracked receipt object envelope changed")
    payload = dict(receipt)
    observed = payload.pop("receipt_payload_sha512", None)
    if observed != sha512_bytes(canonical_bytes(payload)):
        raise RuntimeError("NASS tracked receipt payload envelope changed")
    gates = receipt.get("scientific_use_gates")
    if not isinstance(gates, dict) or any(value is not False for value in gates.values()):
        raise RuntimeError("NASS tracked receipt opens a scientific-use gate")
    serialized = serialize(receipt).decode("utf-8").lower()
    for forbidden in ("api_key", "access_token", "authorization", "password", "/users/"):
        if forbidden in serialized:
            raise RuntimeError("NASS tracked receipt contains a credential or machine path")


def write_atomic(path: Path, receipt: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(serialize(receipt))
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW_DIR)
    parser.add_argument("--out", type=Path, default=DEFAULT_RECEIPT)
    args = parser.parse_args()
    receipt = build_receipt(args.manifest, args.raw_dir)
    write_atomic(args.out, receipt)
    print(
        f"validated and exported {receipt['scope']['object_count']} NASS objects, "
        f"{receipt['scope']['raw_bytes']} bytes, {receipt['scope']['raw_records']} records"
    )


if __name__ == "__main__":
    main()
