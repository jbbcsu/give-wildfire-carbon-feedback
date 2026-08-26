#!/usr/bin/env python3
"""Export and validate the tracked-safe nClimGrid-Daily content receipt.

The bulk acquisition manifest and NetCDF objects remain under ``data/raw``
and are intentionally ignored by git.  This module validates the complete
manifest against the reviewed 468-row HTTP inventory and product record, then
projects only publication-safe content identity into deterministic JSON.  It
does not contact NOAA, construct weather features, fit a relationship,
calculate damages, or authorize SCC use.
"""
from __future__ import annotations

import argparse
import calendar
import hashlib
import json
import os
import tempfile
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable, Mapping


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[1]

import acquire_nclimgrid_daily_bulk as acquisition  # noqa: E402
import inventory_nclimgrid_daily_http as inventory  # noqa: E402


DEFAULT_INVENTORY = acquisition.DEFAULT_INVENTORY
DEFAULT_REVIEWED_PRODUCT = acquisition.DEFAULT_LICENSE_RECORD
DEFAULT_RAW_DIR = acquisition.DEFAULT_OUT_DIR
DEFAULT_MANIFEST = DEFAULT_RAW_DIR / acquisition.MANIFEST_NAME
DEFAULT_RECEIPT = (
    PROJECT_ROOT
    / "data/provenance/nclimgrid_daily_1981_2019_content_receipt.json"
)

RECEIPT_SCHEMA = "nclimgrid_daily_content_receipt_v1"
EXPECTED_TOTAL_BYTES = 27_857_685_556
REVIEWED_COMPLETE_MANIFEST_SIZE_BYTES = 1_403_481
REVIEWED_COMPLETE_MANIFEST_SHA512 = (
    "3e46415d4bba94362a46c6db536c756e2cc55f73624eee977b67fef63955d03d"
    "eae832b35c553a8e1bcb1f758e020eb5020fa8e087979e0372f3e47c7d17ac5f"
)
REVIEWED_OBJECT_RECORDS_SHA512 = (
    "9234b635a39b94312accafa344c884a450824b9b72d5d730724f798601ae8e514"
    "45e9c600dbe946f9e58366e4bc3c3b5b2161a97c5844ccfb9887734d8154893"
)
SHA512_PATTERN = acquisition.SHA512_PATTERN

TOP_LEVEL_FIELDS = {
    "schema_version",
    "dataset",
    "scope",
    "frozen_inputs",
    "source_manifest",
    "acquisition_validation",
    "content_validation",
    "netcdf_schema",
    "object_records_sha512",
    "objects",
    "scientific_use_gates",
    "receipt_payload_sha512",
}
DATASET_FIELDS = {
    "source",
    "documentation_url",
    "dataset_doi",
    "product_version",
    "license",
    "scientific_role",
}
SCOPE_FIELDS = {"start_month", "end_month", "object_count", "content_length_bytes"}
FROZEN_INPUT_FIELDS = {"http_inventory", "reviewed_product_record"}
PIN_FIELDS = {"name", "sha512"}
SOURCE_MANIFEST_FIELDS = {
    "name",
    "schema_version",
    "sha512",
    "size_bytes",
    "record_count",
}
ACQUISITION_VALIDATION_FIELDS = {
    "downloaded_and_validated_objects",
    "adopted_existing_and_validated_objects",
    "earliest_retrieved_utc",
    "latest_retrieved_utc",
    "earliest_validated_utc",
    "latest_validated_utc",
}
CONTENT_VALIDATION_FIELDS = {
    "applies_to_all_objects",
    "exact_byte_length_validated",
    "local_sha512_computed",
    "netcdf_schema_validated",
    "exact_daily_calendar_validated",
}
NETCDF_SCHEMA_FIELDS = {
    "data_variables",
    "variables",
    "time_coordinate",
    "spatial_dimensions",
    "coordinate_checks",
    "title",
    "product_version",
    "embedded_license",
    "day_label_semantics",
}
OBJECT_FIELDS = {
    "period",
    "name",
    "canonical_url",
    "http_identity",
    "local_sha512",
    "calendar",
}
HTTP_IDENTITY_FIELDS = {
    "content_length",
    "etag",
    "last_modified",
    "content_type",
}
CALENDAR_FIELDS = {"daily_time_steps", "start_date", "end_date"}
SCIENTIFIC_USE_GATE_FIELDS = {
    "relationship_estimated",
    "causal_claim_authorized",
    "damage_estimated",
    "scc_authorized",
}


def _strict_fields(value: object, expected: set[str], label: str) -> Mapping[str, Any]:
    if not isinstance(value, dict) or set(value) != expected:
        observed = sorted(value) if isinstance(value, dict) else type(value).__name__
        raise RuntimeError(f"{label} fields differ; observed {observed}")
    return value


def _require_int(value: object, label: str, *, positive: bool = False) -> int:
    if type(value) is not int:
        raise RuntimeError(f"{label} must be an integer")
    if positive and value <= 0:
        raise RuntimeError(f"{label} must be positive")
    return value


def _require_sha512(value: object, label: str) -> str:
    if not isinstance(value, str) or SHA512_PATTERN.fullmatch(value) is None:
        raise RuntimeError(f"{label} must be a lowercase SHA-512")
    return value


def _sha512_bytes(payload: bytes) -> str:
    return hashlib.sha512(payload).hexdigest()


def _canonical_json_bytes(value: object) -> bytes:
    """Canonical bytes used by the receipt's internal hash envelopes."""
    return json.dumps(
        value, ensure_ascii=True, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def serialize_receipt(receipt: Mapping[str, Any]) -> bytes:
    """Return the sole accepted tracked serialization."""
    return (
        json.dumps(receipt, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def _timestamp(value: object, label: str) -> datetime:
    if not isinstance(value, str):
        raise RuntimeError(f"{label} must be an ISO-8601 UTC timestamp")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as error:
        raise RuntimeError(f"{label} is not a valid ISO-8601 timestamp") from error
    if (
        parsed.tzinfo is None
        or parsed.utcoffset() is None
        or parsed.utcoffset().total_seconds() != 0
    ):
        raise RuntimeError(f"{label} must have an explicit UTC offset")
    return parsed.astimezone(UTC)


def _timestamp_bounds(
    records: Mapping[tuple[int, int], Mapping[str, Any]], field: str
) -> tuple[str | None, str | None]:
    values = [
        _timestamp(record[field], f"{record['name']} {field}")
        for record in records.values()
        if record[field] is not None
    ]
    if not values:
        return None, None
    return min(values).isoformat(), max(values).isoformat()


def _expected_netcdf_schema() -> dict[str, object]:
    shape = acquisition.smoke.EXPECTED_SHAPE
    return {
        "data_variables": sorted(acquisition.smoke.EXPECTED_FIELDS),
        "variables": {
            name: {
                "standard_name": standard_name,
                "units": units,
                "dimensions": ["time", "lat", "lon"],
                "required_comment_phrase": (
                    "24-hour period ending in the early morning"
                ),
            }
            for name, (standard_name, units) in sorted(
                acquisition.smoke.EXPECTED_FIELDS.items()
            )
        },
        "time_coordinate": "time",
        "spatial_dimensions": {"lat": shape["lat"], "lon": shape["lon"]},
        "coordinate_checks": {
            "latitude": {
                "name": "lat",
                "finite": True,
                "unique": True,
                "strictly_increasing": True,
            },
            "longitude": {
                "name": "lon",
                "finite": True,
                "unique": True,
                "strictly_increasing": True,
            },
        },
        "title": acquisition.smoke.EXPECTED_TITLE,
        "product_version": acquisition.smoke.EXPECTED_VERSION,
        "embedded_license": "no restrictions",
        "day_label_semantics": (
            "24-hour period ending early morning of specified date"
        ),
    }


def _expected_calendar(year: int, month: int) -> dict[str, object]:
    days = calendar.monthrange(year, month)[1]
    return {
        "daily_time_steps": days,
        "start_date": f"{year:04d}-{month:02d}-01",
        "end_date": f"{year:04d}-{month:02d}-{days:02d}",
    }


def _load_validated_source(
    *,
    manifest_path: Path,
    inventory_path: Path,
    reviewed_product_path: Path,
) -> tuple[
    dict[tuple[int, int], inventory.InventoryRow],
    dict[tuple[int, int], dict[str, object]],
    dict[str, object],
    bytes,
    str,
]:
    """Load the complete ignored manifest under all frozen provenance gates."""
    if manifest_path.name != acquisition.MANIFEST_NAME:
        raise RuntimeError("source manifest must retain its canonical basename")
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise RuntimeError("source manifest must be a regular non-symbolic-link file")
    if inventory_path.name != DEFAULT_INVENTORY.name:
        raise RuntimeError("HTTP inventory must retain its canonical basename")
    if reviewed_product_path.name != DEFAULT_REVIEWED_PRODUCT.name:
        raise RuntimeError("reviewed product record must retain its canonical basename")

    rows = inventory.load_inventory(inventory_path, require_complete=True)
    if len(rows) != inventory.EXPECTED_OBJECT_COUNT:
        raise RuntimeError("HTTP inventory is not the exact 468-object scope")
    inventory_digest = acquisition.smoke.sha512_file(inventory_path)
    if inventory_digest != acquisition.REVIEWED_INVENTORY_SHA512:
        raise RuntimeError("HTTP inventory differs from its reviewed SHA-512")
    if sum(row.content_length for row in rows.values()) != EXPECTED_TOTAL_BYTES:
        raise RuntimeError("HTTP inventory byte total differs from the reviewed scope")
    product = acquisition.load_reviewed_product_record(reviewed_product_path)

    try:
        before = manifest_path.read_bytes()
    except OSError as error:
        raise RuntimeError("cannot read the bulk acquisition manifest") from error
    records = acquisition.load_acquisition_manifest(
        manifest_path,
        rows=rows,
        inventory_name=inventory_path.name,
        inventory_sha512=inventory_digest,
        product=product,
    )
    try:
        after = manifest_path.read_bytes()
    except OSError as error:
        raise RuntimeError("cannot reread the bulk acquisition manifest") from error
    if before != after:
        raise RuntimeError("bulk acquisition manifest changed while being validated")
    if len(after) != REVIEWED_COMPLETE_MANIFEST_SIZE_BYTES:
        raise RuntimeError("bulk acquisition manifest differs from its reviewed byte size")
    if _sha512_bytes(after) != REVIEWED_COMPLETE_MANIFEST_SHA512:
        raise RuntimeError("bulk acquisition manifest differs from its reviewed SHA-512")
    if list(records) != list(rows):
        missing = [
            f"{year:04d}-{month:02d}"
            for year, month in rows
            if (year, month) not in records
        ]
        extra = [
            f"{year:04d}-{month:02d}"
            for year, month in records
            if (year, month) not in rows
        ]
        raise RuntimeError(
            "bulk acquisition manifest is not the complete 468-object scope; "
            f"missing={missing[:3]}, extra={extra[:3]}"
        )
    if sum(int(record["size_bytes"]) for record in records.values()) != EXPECTED_TOTAL_BYTES:
        raise RuntimeError("bulk acquisition manifest byte total differs from the inventory")
    return rows, records, product, after, inventory_digest


def _project_object(
    row: inventory.InventoryRow, record: Mapping[str, object]
) -> dict[str, object]:
    validation = record["netcdf_validation"]
    if not isinstance(validation, dict):
        raise RuntimeError(f"manifest validation for {row.name} is not an object")
    expected_schema = _expected_netcdf_schema()
    manifest_schema_fields = {
        "data_variables",
        "time_coordinate",
        "spatial_dimensions",
        "title",
        "product_version",
        "embedded_license",
        "day_label_semantics",
    }
    observed_schema = {
        "data_variables": validation["data_variables"],
        "time_coordinate": validation["time_coordinate"],
        "spatial_dimensions": {
            "lat": validation["dimensions"]["lat"],  # type: ignore[index]
            "lon": validation["dimensions"]["lon"],  # type: ignore[index]
        },
        "title": validation["title"],
        "product_version": validation["product_version"],
        "embedded_license": validation["embedded_license"],
        "day_label_semantics": validation["day_label_semantics"],
    }
    if observed_schema != {
        field: expected_schema[field] for field in manifest_schema_fields
    }:
        raise RuntimeError(f"manifest schema projection changed for {row.name}")
    expected_calendar = _expected_calendar(row.year, row.month)
    observed_calendar = {
        "daily_time_steps": validation["daily_time_steps"],
        "start_date": validation["start_date"],
        "end_date": validation["end_date"],
    }
    if observed_calendar != expected_calendar:
        raise RuntimeError(f"manifest calendar projection changed for {row.name}")
    return {
        "period": f"{row.year:04d}-{row.month:02d}",
        "name": row.name,
        "canonical_url": row.canonical_url,
        "http_identity": {
            "content_length": row.content_length,
            "etag": row.etag,
            "last_modified": row.last_modified,
            "content_type": row.content_type,
        },
        "local_sha512": record["local_sha512"],
        "calendar": expected_calendar,
    }


def build_receipt(
    *,
    manifest_path: Path = DEFAULT_MANIFEST,
    inventory_path: Path = DEFAULT_INVENTORY,
    reviewed_product_path: Path = DEFAULT_REVIEWED_PRODUCT,
) -> dict[str, Any]:
    """Build a deterministic receipt without reading a raw NetCDF body."""
    rows, records, product, manifest_bytes, inventory_digest = _load_validated_source(
        manifest_path=manifest_path,
        inventory_path=inventory_path,
        reviewed_product_path=reviewed_product_path,
    )
    objects = [_project_object(rows[key], records[key]) for key in rows]
    status_counts = Counter(str(record["file_status"]) for record in records.values())
    earliest_retrieved, latest_retrieved = _timestamp_bounds(records, "retrieved_utc")
    earliest_validated, latest_validated = _timestamp_bounds(records, "validated_utc")
    payload: dict[str, Any] = {
        "schema_version": RECEIPT_SCHEMA,
        "dataset": {
            "source": product["source"],
            "documentation_url": product["landing_page_url"],
            "dataset_doi": product["dataset_doi"],
            "product_version": acquisition.smoke.EXPECTED_VERSION,
            "license": product["license"],
            "scientific_role": "raw_historical_weather_content_identity_only",
        },
        "scope": {
            "start_month": acquisition.SCOPE_START,
            "end_month": acquisition.SCOPE_END,
            "object_count": len(objects),
            "content_length_bytes": sum(
                row.content_length for row in rows.values()
            ),
        },
        "frozen_inputs": {
            "http_inventory": {
                "name": inventory_path.name,
                "sha512": inventory_digest,
            },
            "reviewed_product_record": {
                "name": reviewed_product_path.name,
                "sha512": product["sha512"],
            },
        },
        "source_manifest": {
            "name": acquisition.MANIFEST_NAME,
            "schema_version": acquisition.MANIFEST_SCHEMA,
            "sha512": _sha512_bytes(manifest_bytes),
            "size_bytes": len(manifest_bytes),
            "record_count": len(records),
        },
        "acquisition_validation": {
            "downloaded_and_validated_objects": status_counts[
                "downloaded_and_validated"
            ],
            "adopted_existing_and_validated_objects": status_counts[
                "adopted_existing_and_validated"
            ],
            "earliest_retrieved_utc": earliest_retrieved,
            "latest_retrieved_utc": latest_retrieved,
            "earliest_validated_utc": earliest_validated,
            "latest_validated_utc": latest_validated,
        },
        "content_validation": {
            "applies_to_all_objects": True,
            "exact_byte_length_validated": True,
            "local_sha512_computed": True,
            "netcdf_schema_validated": True,
            "exact_daily_calendar_validated": True,
        },
        "netcdf_schema": _expected_netcdf_schema(),
        "object_records_sha512": _sha512_bytes(_canonical_json_bytes(objects)),
        "objects": objects,
        "scientific_use_gates": {
            "relationship_estimated": False,
            "causal_claim_authorized": False,
            "damage_estimated": False,
            "scc_authorized": False,
        },
    }
    payload["receipt_payload_sha512"] = _sha512_bytes(_canonical_json_bytes(payload))
    validate_receipt(payload, rows=rows, product=product)
    return payload


def validate_receipt(
    receipt: object,
    *,
    rows: Mapping[tuple[int, int], inventory.InventoryRow],
    product: Mapping[str, object],
) -> dict[str, Any]:
    """Validate receipt semantics and both internal SHA-512 envelopes."""
    parsed = dict(_strict_fields(receipt, TOP_LEVEL_FIELDS, "content receipt"))
    if parsed["schema_version"] != RECEIPT_SCHEMA:
        raise RuntimeError("content receipt schema version changed")

    dataset = dict(_strict_fields(parsed["dataset"], DATASET_FIELDS, "dataset"))
    expected_dataset = {
        "source": product["source"],
        "documentation_url": product["landing_page_url"],
        "dataset_doi": product["dataset_doi"],
        "product_version": acquisition.smoke.EXPECTED_VERSION,
        "license": product["license"],
        "scientific_role": "raw_historical_weather_content_identity_only",
    }
    if dataset != expected_dataset:
        raise RuntimeError("content receipt dataset provenance changed")

    scope = dict(_strict_fields(parsed["scope"], SCOPE_FIELDS, "scope"))
    expected_scope = {
        "start_month": acquisition.SCOPE_START,
        "end_month": acquisition.SCOPE_END,
        "object_count": inventory.EXPECTED_OBJECT_COUNT,
        "content_length_bytes": EXPECTED_TOTAL_BYTES,
    }
    if scope != expected_scope:
        raise RuntimeError("content receipt scope differs from the reviewed scope")

    frozen = dict(
        _strict_fields(parsed["frozen_inputs"], FROZEN_INPUT_FIELDS, "frozen_inputs")
    )
    inventory_pin = dict(
        _strict_fields(frozen["http_inventory"], PIN_FIELDS, "HTTP inventory pin")
    )
    product_pin = dict(
        _strict_fields(
            frozen["reviewed_product_record"], PIN_FIELDS, "product record pin"
        )
    )
    if inventory_pin != {
        "name": DEFAULT_INVENTORY.name,
        "sha512": acquisition.REVIEWED_INVENTORY_SHA512,
    }:
        raise RuntimeError("content receipt HTTP inventory pin changed")
    if product_pin != {
        "name": DEFAULT_REVIEWED_PRODUCT.name,
        "sha512": acquisition.REVIEWED_PRODUCT_RECORD_SHA512,
    }:
        raise RuntimeError("content receipt reviewed-product pin changed")

    source_manifest = dict(
        _strict_fields(
            parsed["source_manifest"], SOURCE_MANIFEST_FIELDS, "source_manifest"
        )
    )
    if (
        source_manifest["name"] != acquisition.MANIFEST_NAME
        or source_manifest["schema_version"] != acquisition.MANIFEST_SCHEMA
    ):
        raise RuntimeError("content receipt source-manifest identity changed")
    _require_sha512(source_manifest["sha512"], "source_manifest sha512")
    if source_manifest["sha512"] != REVIEWED_COMPLETE_MANIFEST_SHA512:
        raise RuntimeError("content receipt source-manifest SHA-512 changed")
    if _require_int(
        source_manifest["size_bytes"], "source_manifest size_bytes", positive=True
    ) != REVIEWED_COMPLETE_MANIFEST_SIZE_BYTES:
        raise RuntimeError("content receipt source-manifest byte size changed")
    if (
        _require_int(
            source_manifest["record_count"], "source_manifest record_count"
        )
        != inventory.EXPECTED_OBJECT_COUNT
    ):
        raise RuntimeError("content receipt source manifest is incomplete")

    acquisition_validation = dict(
        _strict_fields(
            parsed["acquisition_validation"],
            ACQUISITION_VALIDATION_FIELDS,
            "acquisition_validation",
        )
    )
    downloaded = _require_int(
        acquisition_validation["downloaded_and_validated_objects"],
        "downloaded object count",
    )
    adopted = _require_int(
        acquisition_validation["adopted_existing_and_validated_objects"],
        "adopted object count",
    )
    if downloaded < 0 or adopted < 0 or downloaded + adopted != inventory.EXPECTED_OBJECT_COUNT:
        raise RuntimeError("content receipt acquisition-status counts are incomplete")
    timestamp_fields = (
        "earliest_retrieved_utc",
        "latest_retrieved_utc",
        "earliest_validated_utc",
        "latest_validated_utc",
    )
    for field in timestamp_fields:
        value = acquisition_validation[field]
        if value is not None:
            _timestamp(value, f"acquisition_validation {field}")
    if (acquisition_validation["earliest_retrieved_utc"] is None) != (
        acquisition_validation["latest_retrieved_utc"] is None
    ):
        raise RuntimeError("content receipt retrieval timestamp bounds are inconsistent")
    if downloaded == 0 and acquisition_validation["earliest_retrieved_utc"] is not None:
        raise RuntimeError("content receipt invents retrieval times without downloads")
    if downloaded > 0 and acquisition_validation["earliest_retrieved_utc"] is None:
        raise RuntimeError("content receipt omits retrieval times for downloaded objects")
    if acquisition_validation["earliest_validated_utc"] is None:
        raise RuntimeError("content receipt omits validation timestamp bounds")
    for first, last in (
        ("earliest_retrieved_utc", "latest_retrieved_utc"),
        ("earliest_validated_utc", "latest_validated_utc"),
    ):
        if acquisition_validation[first] is not None and _timestamp(
            acquisition_validation[first], first
        ) > _timestamp(acquisition_validation[last], last):
            raise RuntimeError(f"content receipt has inverted {first}/{last}")

    content_validation = dict(
        _strict_fields(
            parsed["content_validation"], CONTENT_VALIDATION_FIELDS, "content_validation"
        )
    )
    if any(value is not True for value in content_validation.values()):
        raise RuntimeError("content receipt understates or corrupts content validation")
    schema = dict(
        _strict_fields(parsed["netcdf_schema"], NETCDF_SCHEMA_FIELDS, "netcdf_schema")
    )
    if schema != _expected_netcdf_schema():
        raise RuntimeError("content receipt NetCDF schema changed")

    objects = parsed["objects"]
    if not isinstance(objects, list) or len(objects) != inventory.EXPECTED_OBJECT_COUNT:
        raise RuntimeError("content receipt objects are incomplete")
    if len(rows) != inventory.EXPECTED_OBJECT_COUNT or list(rows) != sorted(rows):
        raise RuntimeError("validator received an invalid HTTP inventory")
    for index, (key, row) in enumerate(rows.items()):
        label = f"content receipt object {index + 1}"
        obj = dict(_strict_fields(objects[index], OBJECT_FIELDS, label))
        identity = dict(
            _strict_fields(obj["http_identity"], HTTP_IDENTITY_FIELDS, f"{label} HTTP identity")
        )
        object_calendar = dict(
            _strict_fields(obj["calendar"], CALENDAR_FIELDS, f"{label} calendar")
        )
        expected = {
            "period": f"{key[0]:04d}-{key[1]:02d}",
            "name": row.name,
            "canonical_url": row.canonical_url,
            "http_identity": {
                "content_length": row.content_length,
                "etag": row.etag,
                "last_modified": row.last_modified,
                "content_type": row.content_type,
            },
            "calendar": _expected_calendar(*key),
        }
        for field, value in expected.items():
            if field == "http_identity":
                observed = identity
            elif field == "calendar":
                observed = object_calendar
            else:
                observed = obj[field]
            if observed != value:
                raise RuntimeError(
                    f"{label} {field} differs from the frozen inventory/calendar"
                )
        _require_sha512(obj["local_sha512"], f"{label} local_sha512")
        if Path(str(obj["name"])).name != obj["name"]:
            raise RuntimeError(f"{label} leaks a non-basename local path")

    object_records_digest = _sha512_bytes(_canonical_json_bytes(objects))
    if _require_sha512(
        parsed["object_records_sha512"], "object_records_sha512"
    ) != object_records_digest:
        raise RuntimeError("content receipt object-record hash envelope changed")
    if object_records_digest != REVIEWED_OBJECT_RECORDS_SHA512:
        raise RuntimeError("content receipt differs from the reviewed object identities")

    gates = dict(
        _strict_fields(
            parsed["scientific_use_gates"],
            SCIENTIFIC_USE_GATE_FIELDS,
            "scientific_use_gates",
        )
    )
    if any(value is not False for value in gates.values()):
        raise RuntimeError("content receipt unexpectedly opens a scientific-use gate")

    expected_payload_digest = parsed.pop("receipt_payload_sha512")
    if _require_sha512(expected_payload_digest, "receipt_payload_sha512") != _sha512_bytes(
        _canonical_json_bytes(parsed)
    ):
        raise RuntimeError("content receipt payload hash envelope changed")
    parsed["receipt_payload_sha512"] = expected_payload_digest
    return parsed


def load_receipt(
    path: Path,
    *,
    rows: Mapping[tuple[int, int], inventory.InventoryRow],
    product: Mapping[str, object],
) -> dict[str, Any]:
    try:
        payload = path.read_bytes()
        parsed = json.loads(payload.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RuntimeError(f"cannot read content receipt {path.name}") from error
    validated = validate_receipt(parsed, rows=rows, product=product)
    if payload != serialize_receipt(validated):
        raise RuntimeError("content receipt is not in canonical deterministic serialization")
    return validated


def check_receipt_against_manifest(
    receipt_path: Path,
    *,
    manifest_path: Path = DEFAULT_MANIFEST,
    inventory_path: Path = DEFAULT_INVENTORY,
    reviewed_product_path: Path = DEFAULT_REVIEWED_PRODUCT,
) -> dict[str, Any]:
    """Fail unless one canonical receipt is the exact source-manifest projection."""
    expected = build_receipt(
        manifest_path=manifest_path,
        inventory_path=inventory_path,
        reviewed_product_path=reviewed_product_path,
    )
    rows, _, product, manifest_bytes, _ = _load_validated_source(
        manifest_path=manifest_path,
        inventory_path=inventory_path,
        reviewed_product_path=reviewed_product_path,
    )
    if expected["source_manifest"]["sha512"] != _sha512_bytes(manifest_bytes):
        raise RuntimeError("bulk acquisition manifest changed during receipt checking")
    observed = load_receipt(receipt_path, rows=rows, product=product)
    if observed != expected:
        raise RuntimeError(
            "tracked content receipt differs from the complete ignored manifest"
        )
    return observed


def verify_local_files(
    *,
    raw_dir: Path,
    rows: Mapping[tuple[int, int], inventory.InventoryRow],
    records: Mapping[tuple[int, int], Mapping[str, object]],
    local_validator: Callable[
        ..., tuple[str, dict[str, object]]
    ] = acquisition.validate_local_payload,
) -> dict[str, int]:
    """Offline full-body revalidation; never performs a network request."""
    if raw_dir.is_symlink() or not raw_dir.is_dir():
        raise RuntimeError("raw nClimGrid directory must be a regular directory")
    parts = sorted(path.name for path in raw_dir.glob("*.part"))
    if parts:
        raise RuntimeError(f"raw nClimGrid directory contains unresolved partials: {parts[:3]}")
    expected_names = {row.name for row in rows.values()}
    observed_names = {path.name for path in raw_dir.glob("*.nc") if path.is_file()}
    if observed_names != expected_names:
        raise RuntimeError(
            "raw nClimGrid files differ from the complete inventory; "
            f"missing={sorted(expected_names - observed_names)[:3]}, "
            f"extra={sorted(observed_names - expected_names)[:3]}"
        )
    total = 0
    for key, row in rows.items():
        path = raw_dir / row.name
        if path.is_symlink() or not path.is_file():
            raise RuntimeError(f"raw nClimGrid object is not a regular file: {row.name}")
        digest, details = local_validator(
            path, row, expected_sha512=str(records[key]["local_sha512"])
        )
        if digest != records[key]["local_sha512"]:
            raise RuntimeError(f"raw nClimGrid SHA-512 changed: {row.name}")
        if details != records[key]["netcdf_validation"]:
            raise RuntimeError(f"raw nClimGrid schema/calendar changed: {row.name}")
        total += row.content_length
    if total != EXPECTED_TOTAL_BYTES:
        raise RuntimeError("revalidated raw nClimGrid byte total changed")
    return {"validated_objects": len(rows), "validated_bytes": total}


def write_receipt_atomic(path: Path, receipt: Mapping[str, Any]) -> None:
    payload = serialize_receipt(receipt)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as stream:
            temporary = Path(stream.name)
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(path)
    except BaseException:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
        raise


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Offline export/check of the deterministic tracked nClimGrid-Daily "
            "content receipt; no network requests are made."
        )
    )
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--inventory", type=Path, default=DEFAULT_INVENTORY)
    parser.add_argument(
        "--reviewed-product", type=Path, default=DEFAULT_REVIEWED_PRODUCT
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_RECEIPT)
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail unless the existing receipt exactly matches the validated manifest",
    )
    parser.add_argument(
        "--verify-local-files",
        action="store_true",
        help=(
            "also reread, SHA-512, and NetCDF/schema/calendar validate all 468 "
            "local objects; still performs no network requests"
        ),
    )
    args = parser.parse_args()

    expected = build_receipt(
        manifest_path=args.manifest,
        inventory_path=args.inventory,
        reviewed_product_path=args.reviewed_product,
    )
    rows, records, product, _, _ = _load_validated_source(
        manifest_path=args.manifest,
        inventory_path=args.inventory,
        reviewed_product_path=args.reviewed_product,
    )
    local_validation = None
    if args.verify_local_files:
        local_validation = verify_local_files(
            raw_dir=args.manifest.parent,
            rows=rows,
            records=records,
        )

    if args.check:
        observed = check_receipt_against_manifest(
            args.output,
            manifest_path=args.manifest,
            inventory_path=args.inventory,
            reviewed_product_path=args.reviewed_product,
        )
        mode = "checked"
    else:
        write_receipt_atomic(args.output, expected)
        observed = load_receipt(args.output, rows=rows, product=product)
        if observed != expected:
            raise RuntimeError("durable content receipt differs after atomic write")
        mode = "written"

    result: dict[str, object] = {
        "mode": mode,
        "receipt_name": args.output.name,
        "receipt_sha512": acquisition.smoke.sha512_file(args.output),
        "source_manifest_sha512": expected["source_manifest"]["sha512"],
        "object_records_sha512": expected["object_records_sha512"],
        "objects": expected["scope"]["object_count"],
        "content_length_bytes": expected["scope"]["content_length_bytes"],
        "scientific_use_gates": expected["scientific_use_gates"],
    }
    if local_validation is not None:
        result["offline_local_revalidation"] = local_validation
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
