#!/usr/bin/env python3
"""Acquire the fixed 1981--2019 nClimGrid-Daily HTTP inventory safely.

The complete tracked HTTP inventory is the only acquisition scope.  Each
monthly response is written to ``<name>.part`` and is promoted to its final
name only after, in order, byte-length, SHA-512, and nClimGrid NetCDF schema
and calendar validation.  The local manifest is updated atomically only after
that promotion.  Resume is deliberately at the monthly-object boundary: an
interrupted ``.part`` is never trusted or range-resumed and is restarted.

This utility acquires raw historical weather.  It does not build county
features, estimate a climate--yield relationship, calculate damages, or
authorize an SCC input.
"""
from __future__ import annotations

import argparse
import calendar
import json
import os
import re
import sys
import tempfile
import time
import tomllib
from datetime import UTC, datetime
from http.client import IncompleteRead, RemoteDisconnected
from pathlib import Path
from typing import Any, Callable, Mapping
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import download_nclimgrid_smoke as smoke  # noqa: E402
import inventory_nclimgrid_daily_http as inventory  # noqa: E402


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INVENTORY = (
    PROJECT_ROOT / "data/provenance/nclimgrid_daily_1981_2019_http_inventory.csv"
)
DEFAULT_OUT_DIR = PROJECT_ROOT / "data/raw/us_county/nclimgrid_daily"
DEFAULT_LICENSE_RECORD = PROJECT_ROOT / "data/provenance/nclimgrid_daily_198101.toml"
REVIEWED_INVENTORY_SHA512 = (
    "4617d02b923705f15b32ddcad8a2211d2ae3fc25dea29f807ba886618b19255b3"
    "d9210806a0edfc55e1c0338ab52001ed3f067e8aa55ea88a70c9f9cd88dd6ae"
)
REVIEWED_PRODUCT_RECORD_SHA512 = (
    "ef0142d68bc699ffb5a67423d844febabc68084abf1daa3ecd5693276b97814b47"
    "f92f8d1c997a7337b08435160ce3c7916582fef0284c574c996b5372134df8"
)
MANIFEST_NAME = "BULK_ACQUISITION_MANIFEST.jsonl"
MANIFEST_SCHEMA = "nclimgrid_daily_bulk_acquisition_manifest_v1"
SCOPE_START = "1981-01"
SCOPE_END = "2019-12"
USER_AGENT = "GIVE-precipitation-SCC-nClimGrid-bulk/1.0"
DOWNLOAD_CHUNK_BYTES = 8 * 1024 * 1024
SHA512_PATTERN = re.compile(r"[0-9a-f]{128}")
FILE_STATUSES = {"downloaded_and_validated", "adopted_existing_and_validated"}

MANIFEST_FIELDS = {
    "schema_version",
    "scope_start",
    "scope_end",
    "year",
    "month",
    "name",
    "canonical_url",
    "inventory_name",
    "inventory_sha512",
    "reviewed_product_record_name",
    "reviewed_product_record_sha512",
    "upstream_identity",
    "local_filename",
    "size_bytes",
    "local_sha512",
    "file_status",
    "retrieved_utc",
    "validated_utc",
    "source",
    "source_documentation",
    "dataset_doi",
    "product_version",
    "license",
    "scientific_limitations",
    "netcdf_validation",
    "scientific_role",
    "relationship_estimated",
    "damage_estimated",
    "scc_authorized",
}
UPSTREAM_FIELDS = {
    "content_length",
    "etag",
    "last_modified",
    "content_type",
}
LICENSE_FIELDS = {"status", "spdx_identifier", "url", "embedded_statement"}
NETCDF_VALIDATION_FIELDS = {
    "data_variables",
    "time_coordinate",
    "daily_time_steps",
    "start_date",
    "end_date",
    "dimensions",
    "title",
    "product_version",
    "embedded_license",
    "day_label_semantics",
}


class RetryableDownloadError(RuntimeError):
    """A bounded retry may restart this monthly GET safely from byte zero."""


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _iso_utc(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return value.astimezone(UTC).isoformat()


def _validate_utc_timestamp(value: object, label: str) -> None:
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


def _strict_fields(value: object, expected: set[str], label: str) -> Mapping[str, Any]:
    if not isinstance(value, dict) or set(value) != expected:
        observed = sorted(value) if isinstance(value, dict) else type(value).__name__
        raise RuntimeError(f"{label} fields differ; observed {observed}")
    return value


def load_reviewed_product_record(path: Path) -> dict[str, object]:
    """Load the already-reviewed product/license assertions used by the smoke."""
    try:
        payload = path.read_bytes()
        record = tomllib.loads(payload.decode("utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as error:
        raise RuntimeError(f"cannot read reviewed nClimGrid product record: {path}") from error
    digest = smoke.sha512_file(path)
    if digest != REVIEWED_PRODUCT_RECORD_SHA512:
        raise RuntimeError("nClimGrid product/license record differs from its reviewed SHA-512")
    license_record = record.get("license")
    stability = record.get("stability")
    if not isinstance(license_record, dict) or not isinstance(stability, dict):
        raise RuntimeError("reviewed nClimGrid record lacks license/stability tables")
    required_license = {
        "status": "U.S. federal government data with no restrictions stated in the reviewed NetCDF",
        "spdx_identifier": "NOASSERTION",
        "url": "https://www.ncei.noaa.gov/products/land-based-station/nclimgrid-daily",
        "embedded_statement": "no restrictions",
    }
    observed_license = {key: license_record.get(key) for key in required_license}
    if observed_license != required_license:
        raise RuntimeError("reviewed nClimGrid license assertions changed")
    limitations = stability.get("scientific_limitations")
    if (
        not isinstance(limitations, list)
        or not limitations
        or not all(isinstance(value, str) and value.strip() for value in limitations)
    ):
        raise RuntimeError("reviewed nClimGrid limitations are missing")
    required_top = {
        "source": "NOAA NCEI nClimGrid-Daily v1.0.0",
        "landing_page_url": required_license["url"],
        "dataset_doi": "https://doi.org/10.25921/c4gt-r169",
        "version": "v1-0-0 20220829 as embedded in the reviewed NetCDF",
    }
    for key, expected in required_top.items():
        if record.get(key) != expected:
            raise RuntimeError(f"reviewed nClimGrid product field {key} changed")
    return {
        **required_top,
        "license": required_license,
        "scientific_limitations": limitations,
        "sha512": digest,
        "name": path.name,
    }


def assert_current_identity(
    pinned: inventory.InventoryRow, observed: inventory.InventoryRow
) -> None:
    changed = [
        field
        for field in inventory.CSV_FIELDS
        if getattr(pinned, field) != getattr(observed, field)
    ]
    if changed:
        raise RuntimeError(
            f"upstream identity drift for {pinned.name}; changed fields: {', '.join(changed)}"
        )


def _header(headers: Mapping[str, str], name: str) -> str:
    value = headers.get(name)
    if value is None or not str(value).strip():
        raise RuntimeError(f"nClimGrid GET response omitted required {name}")
    return str(value).strip()


def download_to_part(
    row: inventory.InventoryRow,
    part_path: Path,
    *,
    opener: Callable[..., object] = urlopen,
    timeout_seconds: float = 900,
) -> None:
    """Download one exact object to a new .part, rejecting response drift."""
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive")
    if part_path.name != row.name + ".part":
        raise RuntimeError("partial path does not match the canonical object name")
    # A prior partial response has no trusted remote checksum.  Restarting the
    # one monthly object is safer than byte-range resumption.
    part_path.unlink(missing_ok=True)
    request = Request(
        row.canonical_url,
        method="GET",
        headers={"User-Agent": USER_AGENT, "Accept-Encoding": "identity"},
    )
    try:
        with opener(request, timeout=timeout_seconds) as response:  # type: ignore[attr-defined]
            status = getattr(response, "status", 200)
            if status != 200:
                if isinstance(status, int) and (status == 429 or 500 <= status <= 599):
                    raise RetryableDownloadError(
                        f"nClimGrid GET returned retryable status {status}"
                    )
                raise RuntimeError(f"nClimGrid GET returned unexpected status {status!r}")
            if response.geturl() != row.canonical_url:  # type: ignore[attr-defined]
                raise RuntimeError("nClimGrid GET redirected away from the canonical URL")
            headers = response.headers  # type: ignore[attr-defined]
            observed = {
                "content_length": _header(headers, "Content-Length"),
                "etag": _header(headers, "ETag"),
                "last_modified": _header(headers, "Last-Modified"),
                "content_type": _header(headers, "Content-Type"),
            }
            expected = {
                "content_length": str(row.content_length),
                "etag": row.etag,
                "last_modified": row.last_modified,
                "content_type": row.content_type,
            }
            if observed != expected:
                changed = [key for key in expected if observed.get(key) != expected[key]]
                raise RuntimeError(
                    f"nClimGrid GET identity drift for {row.name}: {', '.join(changed)}"
                )
            encoding = str(headers.get("Content-Encoding", "")).strip().lower()
            if encoding not in {"", "identity"}:
                raise RuntimeError("nClimGrid GET unexpectedly used content encoding")
            bytes_written = 0
            with part_path.open("xb") as stream:
                while block := response.read(DOWNLOAD_CHUNK_BYTES):  # type: ignore[attr-defined]
                    bytes_written += len(block)
                    if bytes_written > row.content_length:
                        raise RuntimeError("nClimGrid GET exceeded the pinned byte length")
                    stream.write(block)
                stream.flush()
                os.fsync(stream.fileno())
        if bytes_written != row.content_length:
            raise RetryableDownloadError(
                f"nClimGrid GET length {bytes_written} differs from pin {row.content_length}"
            )
    except HTTPError as error:
        part_path.unlink(missing_ok=True)
        error_type = (
            RetryableDownloadError
            if error.code == 429 or 500 <= error.code <= 599
            else RuntimeError
        )
        raise error_type(
            f"nClimGrid GET failed for {row.name} with HTTP {error.code}"
        ) from error
    except (URLError, TimeoutError, ConnectionError, IncompleteRead, RemoteDisconnected) as error:
        part_path.unlink(missing_ok=True)
        raise RetryableDownloadError(
            f"nClimGrid GET transport failed for {row.name}"
        ) from error
    except OSError as error:
        # Local filesystem failures (including insufficient space) should not
        # be hidden behind repeated network attempts.
        part_path.unlink(missing_ok=True)
        raise RuntimeError(f"local write failed for {row.name}") from error
    except BaseException:
        part_path.unlink(missing_ok=True)
        raise


def download_with_retries(
    row: inventory.InventoryRow,
    part_path: Path,
    *,
    opener: Callable[..., object] = urlopen,
    timeout_seconds: float = 900,
    attempts: int = 3,
    sleeper: Callable[[float], None] = time.sleep,
) -> None:
    """Restart one monthly object from byte zero after bounded transient failures."""
    if attempts < 1:
        raise ValueError("attempts must be at least one")
    for attempt in range(1, attempts + 1):
        try:
            download_to_part(
                row,
                part_path,
                opener=opener,
                timeout_seconds=timeout_seconds,
            )
            return
        except RetryableDownloadError:
            if attempt == attempts:
                raise
            sleeper(min(2.0 ** (attempt - 1), 8.0))
    raise AssertionError("unreachable download retry state")


def validate_netcdf_summary(
    details: object, year: int, month: int, *, label: str
) -> dict[str, object]:
    summary = dict(_strict_fields(details, NETCDF_VALIDATION_FIELDS, label))
    expected_days = calendar.monthrange(year, month)[1]
    expected_start = f"{year:04d}-{month:02d}-01"
    expected_end = f"{year:04d}-{month:02d}-{expected_days:02d}"
    expected = {
        "data_variables": sorted(smoke.EXPECTED_FIELDS),
        "time_coordinate": "time",
        "daily_time_steps": expected_days,
        "start_date": expected_start,
        "end_date": expected_end,
        "dimensions": {"time": expected_days, **smoke.EXPECTED_SHAPE},
        "title": smoke.EXPECTED_TITLE,
        "product_version": smoke.EXPECTED_VERSION,
        "embedded_license": "no restrictions",
        "day_label_semantics": "24-hour period ending early morning of specified date",
    }
    if summary != expected:
        raise RuntimeError(f"{label} does not match the fixed nClimGrid schema/calendar")
    return summary


def validate_local_payload(
    path: Path,
    row: inventory.InventoryRow,
    *,
    netcdf_validator: Callable[[Path, int, int], dict[str, object]] = smoke.validate_netcdf,
    expected_sha512: str | None = None,
) -> tuple[str, dict[str, object]]:
    """Validate in the required order: bytes, SHA-512, then NetCDF/calendar."""
    try:
        size = path.stat().st_size
    except OSError as error:
        raise RuntimeError(f"cannot stat nClimGrid payload: {path}") from error
    if size != row.content_length:
        raise RuntimeError(
            f"local byte length for {row.name} is {size}; expected {row.content_length}"
        )
    digest = smoke.sha512_file(path)
    if expected_sha512 is not None and digest != expected_sha512:
        raise RuntimeError(f"local SHA-512 for {row.name} differs from its manifest")
    try:
        raw_details = netcdf_validator(path, row.year, row.month)
    except Exception as error:
        raise RuntimeError(f"NetCDF validation failed for {row.name}") from error
    details = validate_netcdf_summary(
        raw_details, row.year, row.month, label=f"NetCDF validation for {row.name}"
    )
    return digest, details


def _expected_upstream(row: inventory.InventoryRow) -> dict[str, object]:
    return {
        "content_length": row.content_length,
        "etag": row.etag,
        "last_modified": row.last_modified,
        "content_type": row.content_type,
    }


def _validate_manifest_record(
    record: object,
    *,
    line_number: int,
    rows: Mapping[tuple[int, int], inventory.InventoryRow],
    inventory_name: str,
    inventory_sha512: str,
    product: Mapping[str, object],
) -> dict[str, object]:
    label = f"bulk acquisition manifest line {line_number}"
    parsed = dict(_strict_fields(record, MANIFEST_FIELDS, label))
    if parsed["schema_version"] != MANIFEST_SCHEMA:
        raise RuntimeError(f"{label} has an unsupported schema version")
    if parsed["scope_start"] != SCOPE_START or parsed["scope_end"] != SCOPE_END:
        raise RuntimeError(f"{label} differs from the fixed 1981--2019 scope")
    year, month = parsed["year"], parsed["month"]
    if type(year) is not int or type(month) is not int:
        raise RuntimeError(f"{label} year/month must be integers")
    row = rows.get((year, month))
    if row is None:
        raise RuntimeError(f"{label} is outside the complete HTTP inventory")
    direct_expected = {
        "name": row.name,
        "canonical_url": row.canonical_url,
        "inventory_name": inventory_name,
        "inventory_sha512": inventory_sha512,
        "reviewed_product_record_name": product["name"],
        "reviewed_product_record_sha512": product["sha512"],
        "local_filename": row.name,
        "size_bytes": row.content_length,
        "source": product["source"],
        "source_documentation": product["landing_page_url"],
        "dataset_doi": product["dataset_doi"],
        "product_version": smoke.EXPECTED_VERSION,
        "scientific_limitations": product["scientific_limitations"],
        "scientific_role": "raw_historical_weather_input_only",
        "relationship_estimated": False,
        "damage_estimated": False,
        "scc_authorized": False,
    }
    for field, expected in direct_expected.items():
        if parsed[field] != expected:
            raise RuntimeError(f"{label} field {field} differs from reviewed provenance")
    upstream = dict(
        _strict_fields(
            parsed["upstream_identity"], UPSTREAM_FIELDS, f"{label} upstream_identity"
        )
    )
    if upstream != _expected_upstream(row):
        raise RuntimeError(f"{label} upstream identity differs from the HTTP inventory")
    license_record = dict(_strict_fields(parsed["license"], LICENSE_FIELDS, f"{label} license"))
    if license_record != product["license"]:
        raise RuntimeError(f"{label} license differs from the reviewed product record")
    sha512 = parsed["local_sha512"]
    if not isinstance(sha512, str) or SHA512_PATTERN.fullmatch(sha512) is None:
        raise RuntimeError(f"{label} has an invalid SHA-512")
    status = parsed["file_status"]
    if status not in FILE_STATUSES:
        raise RuntimeError(f"{label} has an invalid file status")
    retrieved = parsed["retrieved_utc"]
    if status == "downloaded_and_validated":
        _validate_utc_timestamp(retrieved, f"{label} retrieved_utc")
    elif retrieved is not None:
        raise RuntimeError(f"{label} must not invent a retrieval time for an adopted file")
    _validate_utc_timestamp(parsed["validated_utc"], f"{label} validated_utc")
    parsed["netcdf_validation"] = validate_netcdf_summary(
        parsed["netcdf_validation"], year, month, label=f"{label} netcdf_validation"
    )
    return parsed


def load_acquisition_manifest(
    path: Path,
    *,
    rows: Mapping[tuple[int, int], inventory.InventoryRow],
    inventory_name: str,
    inventory_sha512: str,
    product: Mapping[str, object],
) -> dict[tuple[int, int], dict[str, object]]:
    if not path.exists():
        return {}
    records: dict[tuple[int, int], dict[str, object]] = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as error:
        raise RuntimeError(f"cannot read bulk acquisition manifest: {path}") from error
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            raise RuntimeError(f"bulk acquisition manifest line {line_number} is blank")
        try:
            raw = json.loads(line)
        except json.JSONDecodeError as error:
            raise RuntimeError(
                f"bulk acquisition manifest line {line_number} is invalid JSON"
            ) from error
        record = _validate_manifest_record(
            raw,
            line_number=line_number,
            rows=rows,
            inventory_name=inventory_name,
            inventory_sha512=inventory_sha512,
            product=product,
        )
        key = (int(record["year"]), int(record["month"]))
        if key in records:
            raise RuntimeError(f"bulk acquisition manifest has duplicate object {key}")
        records[key] = record
    if list(records) != sorted(records):
        raise RuntimeError("bulk acquisition manifest is not in chronological order")
    return records


def write_manifest_atomic(
    path: Path, records: Mapping[tuple[int, int], Mapping[str, object]]
) -> None:
    """Atomically rewrite the unique chronological local manifest."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as stream:
            temporary = Path(stream.name)
            for key in sorted(records):
                stream.write(json.dumps(records[key], sort_keys=True, separators=(",", ":")))
                stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(path)
    except BaseException:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
        raise


def _build_record(
    row: inventory.InventoryRow,
    *,
    inventory_name: str,
    inventory_sha512: str,
    product: Mapping[str, object],
    digest: str,
    details: Mapping[str, object],
    file_status: str,
    event_time: datetime,
) -> dict[str, object]:
    if file_status not in FILE_STATUSES:
        raise ValueError("invalid file_status")
    timestamp = _iso_utc(event_time)
    record: dict[str, object] = {
        "schema_version": MANIFEST_SCHEMA,
        "scope_start": SCOPE_START,
        "scope_end": SCOPE_END,
        "year": row.year,
        "month": row.month,
        "name": row.name,
        "canonical_url": row.canonical_url,
        "inventory_name": inventory_name,
        "inventory_sha512": inventory_sha512,
        "reviewed_product_record_name": product["name"],
        "reviewed_product_record_sha512": product["sha512"],
        "upstream_identity": _expected_upstream(row),
        "local_filename": row.name,
        "size_bytes": row.content_length,
        "local_sha512": digest,
        "file_status": file_status,
        "retrieved_utc": timestamp if file_status == "downloaded_and_validated" else None,
        "validated_utc": timestamp,
        "source": product["source"],
        "source_documentation": product["landing_page_url"],
        "dataset_doi": product["dataset_doi"],
        "product_version": smoke.EXPECTED_VERSION,
        "license": product["license"],
        "scientific_limitations": product["scientific_limitations"],
        "netcdf_validation": dict(details),
        "scientific_role": "raw_historical_weather_input_only",
        "relationship_estimated": False,
        "damage_estimated": False,
        "scc_authorized": False,
    }
    _validate_manifest_record(
        record,
        line_number=1,
        rows={row.key: row},
        inventory_name=inventory_name,
        inventory_sha512=inventory_sha512,
        product=product,
    )
    return record


def storage_plan(rows: Mapping[tuple[int, int], inventory.InventoryRow]) -> dict[str, object]:
    total = sum(row.content_length for row in rows.values())
    maximum = max(row.content_length for row in rows.values())
    return {
        "scope_start": SCOPE_START,
        "scope_end": SCOPE_END,
        "objects": len(rows),
        "content_length_bytes": total,
        "content_length_decimal_gb": total / 1_000_000_000,
        "content_length_gib": total / (1024**3),
        "maximum_single_part_bytes": maximum,
        "peak_note": (
            "Allow filesystem/metadata overhead plus at most one monthly .part file; "
            "the inventory sum is compressed NetCDF transfer size, not derived-feature storage."
        ),
    }


def run_acquisition(
    *,
    inventory_path: Path,
    out_dir: Path,
    reviewed_product_record: Path,
    max_new: int | None,
    head_fetcher: Callable[[inventory.InventoryRow], inventory.InventoryRow],
    downloader: Callable[[inventory.InventoryRow, Path], None],
    netcdf_validator: Callable[[Path, int, int], dict[str, object]] = smoke.validate_netcdf,
    now: Callable[[], datetime] = _utc_now,
) -> dict[str, object]:
    """Validate existing files and acquire at most max_new missing objects."""
    if max_new is not None and max_new < 0:
        raise ValueError("max_new cannot be negative")
    rows = inventory.load_inventory(inventory_path, require_complete=True)
    if len(rows) != inventory.EXPECTED_OBJECT_COUNT:
        raise RuntimeError("nClimGrid inventory is not the exact 468-object scope")
    inventory_sha512 = smoke.sha512_file(inventory_path)
    if inventory_sha512 != REVIEWED_INVENTORY_SHA512:
        raise RuntimeError("complete nClimGrid HTTP inventory differs from its reviewed SHA-512")
    product = load_reviewed_product_record(reviewed_product_record)
    manifest_path = out_dir / MANIFEST_NAME
    if manifest_path.is_symlink():
        raise RuntimeError("bulk acquisition manifest must not be a symbolic link")
    records = load_acquisition_manifest(
        manifest_path,
        rows=rows,
        inventory_name=inventory_path.name,
        inventory_sha512=inventory_sha512,
        product=product,
    )
    out_dir.mkdir(parents=True, exist_ok=True)

    reverified = 0
    adopted = 0
    downloaded = 0
    downloaded_bytes = 0

    # Manifested files are immutable checkpoints.  Any missing or changed file
    # fails rather than being silently replaced.
    for key in sorted(records):
        row = rows[key]
        destination = out_dir / row.name
        part = out_dir / (row.name + ".part")
        if part.exists():
            raise RuntimeError(f"both validated file and .part state exist for {row.name}")
        if destination.is_symlink() or not destination.is_file():
            raise RuntimeError(f"manifested nClimGrid file is missing: {row.name}")
        observed = head_fetcher(row)
        assert_current_identity(row, observed)
        digest, details = validate_local_payload(
            destination,
            row,
            netcdf_validator=netcdf_validator,
            expected_sha512=str(records[key]["local_sha512"]),
        )
        if details != records[key]["netcdf_validation"] or digest != records[key]["local_sha512"]:
            raise RuntimeError(f"manifested validation details changed for {row.name}")
        reverified += 1

    # Safely adopt unmanifested exact files (for example previously validated
    # smoke months).  A retrieval time is deliberately not invented.
    for key in sorted(rows):
        if key in records:
            continue
        row = rows[key]
        destination = out_dir / row.name
        part = out_dir / (row.name + ".part")
        if destination.exists() and part.exists():
            raise RuntimeError(f"both final and .part files exist for {row.name}")
        if not destination.exists():
            continue
        if destination.is_symlink() or not destination.is_file():
            raise RuntimeError(f"nClimGrid destination is not a regular file: {destination}")
        observed = head_fetcher(row)
        assert_current_identity(row, observed)
        digest, details = validate_local_payload(
            destination, row, netcdf_validator=netcdf_validator
        )
        records[key] = _build_record(
            row,
            inventory_name=inventory_path.name,
            inventory_sha512=inventory_sha512,
            product=product,
            digest=digest,
            details=details,
            file_status="adopted_existing_and_validated",
            event_time=now(),
        )
        write_manifest_atomic(manifest_path, records)
        adopted += 1

    missing = [row for key, row in sorted(rows.items()) if key not in records]
    selected = missing if max_new is None else missing[:max_new]
    for row in selected:
        destination = out_dir / row.name
        part = out_dir / (row.name + ".part")
        if destination.exists():
            raise RuntimeError(f"unrecorded final file appeared during acquisition: {row.name}")
        observed = head_fetcher(row)
        assert_current_identity(row, observed)
        try:
            downloader(row, part)
            digest, details = validate_local_payload(
                part, row, netcdf_validator=netcdf_validator
            )
            part.replace(destination)
        except BaseException:
            part.unlink(missing_ok=True)
            raise
        records[row.key] = _build_record(
            row,
            inventory_name=inventory_path.name,
            inventory_sha512=inventory_sha512,
            product=product,
            digest=digest,
            details=details,
            file_status="downloaded_and_validated",
            event_time=now(),
        )
        write_manifest_atomic(manifest_path, records)
        downloaded += 1
        downloaded_bytes += row.content_length

    # Reload the durable manifest after the last atomic update.  This also
    # catches serialization/schema errors before reporting success.
    durable = load_acquisition_manifest(
        manifest_path,
        rows=rows,
        inventory_name=inventory_path.name,
        inventory_sha512=inventory_sha512,
        product=product,
    )
    if durable.keys() != records.keys():
        raise RuntimeError("durable acquisition manifest differs from in-memory state")
    plan = storage_plan(rows)
    return {
        "scope_start": SCOPE_START,
        "scope_end": SCOPE_END,
        "expected_objects": len(rows),
        "validated_objects": len(records),
        "remaining_objects": len(rows) - len(records),
        "complete": len(records) == len(rows),
        "reverified_manifested_objects": reverified,
        "adopted_existing_objects": adopted,
        "new_downloaded_objects": downloaded,
        "new_downloaded_bytes": downloaded_bytes,
        "max_new": max_new,
        "manifest": str(manifest_path),
        "inventory_sha512": inventory_sha512,
        "storage_plan": plan,
        "relationship_estimated": False,
        "damage_estimated": False,
        "scc_authorized": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Acquire the exact 468 monthly nClimGrid-Daily objects for 1981--2019. "
            "Choose a bounded number or explicitly authorize all missing objects."
        )
    )
    scope = parser.add_mutually_exclusive_group(required=True)
    scope.add_argument(
        "--max-new",
        type=int,
        help=(
            "download at most N missing monthly files; N=0 revalidates/adopts only "
            "existing files and performs no GET"
        ),
    )
    scope.add_argument(
        "--all",
        action="store_true",
        help="explicitly acquire every missing object in the fixed 1981--2019 inventory",
    )
    parser.add_argument("--timeout-seconds", type=float, default=900)
    parser.add_argument("--head-timeout-seconds", type=float, default=90)
    parser.add_argument(
        "--attempts",
        type=int,
        default=3,
        help=(
            "attempts per HEAD and per monthly GET (default 3); every GET retry "
            "discards .part and restarts the object from byte zero"
        ),
    )
    args = parser.parse_args()
    if args.max_new is not None and args.max_new < 0:
        parser.error("--max-new cannot be negative")
    if args.timeout_seconds <= 0 or args.head_timeout_seconds <= 0:
        parser.error("timeouts must be positive")
    if args.attempts < 1:
        parser.error("--attempts must be at least one")

    def fetch_current(row: inventory.InventoryRow) -> inventory.InventoryRow:
        expected = inventory.ExpectedObject(
            row.year, row.month, row.name, row.canonical_url
        )
        return inventory.fetch_with_retries(
            expected,
            timeout_seconds=args.head_timeout_seconds,
            attempts=args.attempts,
        )

    def retrieve(row: inventory.InventoryRow, part: Path) -> None:
        download_with_retries(
            row,
            part,
            timeout_seconds=args.timeout_seconds,
            attempts=args.attempts,
        )

    # Print the exact compressed-input footprint before any network GET.  The
    # inventory is loaded again inside run_acquisition under the same gate.
    reviewed_rows = inventory.load_inventory(DEFAULT_INVENTORY, require_complete=True)
    if smoke.sha512_file(DEFAULT_INVENTORY) != REVIEWED_INVENTORY_SHA512:
        raise RuntimeError("complete nClimGrid HTTP inventory differs from its reviewed SHA-512")
    load_reviewed_product_record(DEFAULT_LICENSE_RECORD)
    print(json.dumps({"acquisition_plan": storage_plan(reviewed_rows)}, indent=2, sort_keys=True))
    result = run_acquisition(
        inventory_path=DEFAULT_INVENTORY,
        out_dir=DEFAULT_OUT_DIR,
        reviewed_product_record=DEFAULT_LICENSE_RECORD,
        max_new=None if args.all else args.max_new,
        head_fetcher=fetch_current,
        downloader=retrieve,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
