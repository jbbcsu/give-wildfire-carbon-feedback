#!/usr/bin/env python3
"""Inventory nClimGrid-Daily monthly HTTP identities without downloading data.

The production catalog is deliberately fixed to January 1981--December 2019.
Only HEAD requests are issued.  A partial run is checkpointed separately and
is promoted to the requested CSV only after all 468 canonical objects have
complete identities.  Resuming first rechecks every recorded identity and
fails rather than accepting upstream drift.

This inventory is an acquisition planning gate, not file provenance.  Every
downloaded object still requires byte-length, SHA-512, NetCDF schema, and time
coverage validation before scientific use.
"""
from __future__ import annotations

import argparse
import csv
import json
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Callable, Iterable, Mapping, Sequence
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


BASE_URL = "https://www.ncei.noaa.gov/data/nclimgrid-daily/access/grids"
START_YEAR = 1981
END_YEAR = 2019
EXPECTED_OBJECT_COUNT = (END_YEAR - START_YEAR + 1) * 12
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = (
    PROJECT_ROOT
    / "data/provenance/nclimgrid_daily_1981_2019_http_inventory.csv"
)
USER_AGENT = "GIVE-precipitation-SCC-nClimGrid-inventory/1.0"
EXPECTED_CONTENT_TYPE = "application/x-netcdf"
CSV_FIELDS = (
    "year",
    "month",
    "name",
    "canonical_url",
    "content_length",
    "etag",
    "last_modified",
    "content_type",
)


@dataclass(frozen=True, slots=True)
class ExpectedObject:
    year: int
    month: int
    name: str
    canonical_url: str

    @property
    def key(self) -> tuple[int, int]:
        return (self.year, self.month)


@dataclass(frozen=True, slots=True)
class InventoryRow:
    year: int
    month: int
    name: str
    canonical_url: str
    content_length: int
    etag: str
    last_modified: str
    content_type: str

    @property
    def key(self) -> tuple[int, int]:
        return (self.year, self.month)

    def as_csv_row(self) -> dict[str, object]:
        return {field: getattr(self, field) for field in CSV_FIELDS}


def object_name(year: int, month: int) -> str:
    if not START_YEAR <= year <= END_YEAR:
        raise ValueError(f"year must be within {START_YEAR}..{END_YEAR}")
    if not 1 <= month <= 12:
        raise ValueError("month must be within 1..12")
    return f"ncdd-{year:04d}{month:02d}-grd-scaled.nc"


def canonical_url(year: int, month: int) -> str:
    return f"{BASE_URL}/{year:04d}/{object_name(year, month)}"


def expected_objects() -> tuple[ExpectedObject, ...]:
    objects = tuple(
        ExpectedObject(year, month, object_name(year, month), canonical_url(year, month))
        for year in range(START_YEAR, END_YEAR + 1)
        for month in range(1, 13)
    )
    if len(objects) != EXPECTED_OBJECT_COUNT:
        raise RuntimeError("internal nClimGrid object-range construction failed")
    return objects


def _required_header(headers: Mapping[str, str], name: str) -> str:
    value = headers.get(name)
    if value is None or not str(value).strip():
        raise RuntimeError(f"nClimGrid HEAD response omitted required {name}")
    return str(value).strip()


def _parse_positive_decimal(value: str, label: str) -> int:
    if not value.isascii() or not value.isdecimal():
        raise RuntimeError(f"{label} must be an unsigned decimal integer")
    parsed = int(value)
    if parsed <= 0 or str(parsed) != value:
        raise RuntimeError(f"{label} must be a canonical positive decimal integer")
    return parsed


def _validate_last_modified(value: str) -> None:
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError, OverflowError) as error:
        raise RuntimeError("Last-Modified is not a valid HTTP date") from error
    if parsed.tzinfo is None:
        raise RuntimeError("Last-Modified HTTP date lacks a timezone")


def head_identity(
    expected: ExpectedObject,
    *,
    opener: Callable[..., object] = urlopen,
    timeout_seconds: float = 90,
) -> InventoryRow:
    """Return one complete identity using HEAD; response content is never read."""
    request = Request(
        expected.canonical_url,
        method="HEAD",
        headers={"User-Agent": USER_AGENT, "Accept-Encoding": "identity"},
    )
    with opener(request, timeout=timeout_seconds) as response:  # type: ignore[attr-defined]
        status = getattr(response, "status", 200)
        if not isinstance(status, int) or not 200 <= status < 300:
            raise RuntimeError(f"nClimGrid HEAD returned unexpected status {status!r}")
        final_url = response.geturl()  # type: ignore[attr-defined]
        if final_url != expected.canonical_url:
            raise RuntimeError(
                "nClimGrid HEAD redirected away from the canonical object URL: "
                f"{final_url!r}"
            )
        headers = response.headers  # type: ignore[attr-defined]
        length_text = _required_header(headers, "Content-Length")
        etag = _required_header(headers, "ETag")
        last_modified = _required_header(headers, "Last-Modified")
        content_type = _required_header(headers, "Content-Type")
    content_length = _parse_positive_decimal(length_text, "Content-Length")
    _validate_last_modified(last_modified)
    if content_type != EXPECTED_CONTENT_TYPE:
        raise RuntimeError(
            "nClimGrid HEAD Content-Type differs from the reviewed NetCDF type: "
            f"{content_type!r}"
        )
    return InventoryRow(
        year=expected.year,
        month=expected.month,
        name=expected.name,
        canonical_url=expected.canonical_url,
        content_length=content_length,
        etag=etag,
        last_modified=last_modified,
        content_type=content_type,
    )


def fetch_with_retries(
    expected: ExpectedObject,
    *,
    opener: Callable[..., object] = urlopen,
    timeout_seconds: float = 90,
    attempts: int = 3,
    sleeper: Callable[[float], None] = time.sleep,
) -> InventoryRow:
    """Retry transport/429/5xx failures; incomplete identities fail immediately."""
    if attempts < 1:
        raise ValueError("attempts must be at least one")
    for attempt in range(1, attempts + 1):
        try:
            return head_identity(
                expected, opener=opener, timeout_seconds=timeout_seconds
            )
        except HTTPError as error:
            retryable = error.code == 429 or 500 <= error.code <= 599
            if not retryable or attempt == attempts:
                raise RuntimeError(
                    f"nClimGrid HEAD failed for {expected.name} with HTTP {error.code}"
                ) from error
        except (URLError, TimeoutError, ConnectionError, OSError) as error:
            if attempt == attempts:
                raise RuntimeError(
                    f"nClimGrid HEAD transport failed for {expected.name}"
                ) from error
        sleeper(min(2.0 ** (attempt - 1), 8.0))
    raise AssertionError("unreachable retry state")


def _row_from_mapping(raw: Mapping[str, str], line_number: int) -> InventoryRow:
    prefix = f"inventory line {line_number}"
    year_text = raw["year"]
    month_text = raw["month"]
    if not year_text.isdecimal() or not month_text.isdecimal():
        raise RuntimeError(f"{prefix} has a nonnumeric year/month")
    year = int(year_text)
    month = int(month_text)
    if str(year) != year_text or str(month) != month_text:
        raise RuntimeError(f"{prefix} has a noncanonical year/month representation")
    try:
        expected_name = object_name(year, month)
    except ValueError as error:
        raise RuntimeError(f"{prefix} is outside the fixed 1981--2019 range") from error
    expected_url = canonical_url(year, month)
    if raw["name"] != expected_name:
        raise RuntimeError(f"{prefix} has a noncanonical nClimGrid object name")
    if raw["canonical_url"] != expected_url:
        raise RuntimeError(f"{prefix} has a noncanonical nClimGrid URL")
    content_length = _parse_positive_decimal(
        raw["content_length"], f"{prefix} content_length"
    )
    for field in ("etag", "last_modified", "content_type"):
        if not raw[field] or raw[field].strip() != raw[field]:
            raise RuntimeError(f"{prefix} has a missing or noncanonical {field}")
    _validate_last_modified(raw["last_modified"])
    if raw["content_type"] != EXPECTED_CONTENT_TYPE:
        raise RuntimeError(f"{prefix} does not identify the reviewed NetCDF content type")
    return InventoryRow(
        year=year,
        month=month,
        name=raw["name"],
        canonical_url=raw["canonical_url"],
        content_length=content_length,
        etag=raw["etag"],
        last_modified=raw["last_modified"],
        content_type=raw["content_type"],
    )


def load_inventory(path: Path, *, require_complete: bool) -> dict[tuple[int, int], InventoryRow]:
    try:
        with path.open("r", encoding="utf-8", newline="") as stream:
            reader = csv.DictReader(stream)
            if tuple(reader.fieldnames or ()) != CSV_FIELDS:
                raise RuntimeError(
                    f"inventory schema differs from the required fields: {CSV_FIELDS}"
                )
            rows: dict[tuple[int, int], InventoryRow] = {}
            observed_order: list[tuple[int, int]] = []
            for line_number, raw in enumerate(reader, start=2):
                if None in raw or any(raw[field] is None for field in CSV_FIELDS):
                    raise RuntimeError(f"inventory line {line_number} is malformed")
                row = _row_from_mapping(raw, line_number)  # type: ignore[arg-type]
                if row.key in rows:
                    raise RuntimeError(
                        f"inventory contains duplicate year/month {row.year}-{row.month:02d}"
                    )
                rows[row.key] = row
                observed_order.append(row.key)
    except OSError as error:
        raise RuntimeError(f"cannot read nClimGrid inventory: {path}") from error
    if observed_order != sorted(observed_order):
        raise RuntimeError("inventory rows are not in canonical chronological order")
    expected_keys = {item.key for item in expected_objects()}
    unexpected = set(rows).difference(expected_keys)
    if unexpected:
        raise RuntimeError(f"inventory contains unexpected objects: {sorted(unexpected)}")
    if require_complete and set(rows) != expected_keys:
        missing = len(expected_keys.difference(rows))
        raise RuntimeError(f"final inventory is incomplete; {missing} objects are missing")
    return rows


def write_inventory_atomic(path: Path, rows: Mapping[tuple[int, int], InventoryRow]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    try:
        with temporary.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=CSV_FIELDS, lineterminator="\n")
            writer.writeheader()
            for key in sorted(rows):
                writer.writerow(rows[key].as_csv_row())
        temporary.replace(path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def partial_path(output: Path) -> Path:
    return output.with_name(output.name + ".partial")


def _chunks(items: Sequence[ExpectedObject], size: int) -> Iterable[Sequence[ExpectedObject]]:
    for start in range(0, len(items), size):
        yield items[start : start + size]


def _fetch_many(
    objects: Sequence[ExpectedObject],
    fetcher: Callable[[ExpectedObject], InventoryRow],
    workers: int,
) -> list[InventoryRow]:
    if workers == 1:
        return [fetcher(item) for item in objects]
    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="nclimgrid-head") as pool:
        return list(pool.map(fetcher, objects))


def _assert_same_identity(pinned: InventoryRow, observed: InventoryRow) -> None:
    changed = [
        field
        for field in CSV_FIELDS
        if getattr(pinned, field) != getattr(observed, field)
    ]
    if changed:
        raise RuntimeError(
            f"upstream identity drift for {pinned.name}; changed fields: {', '.join(changed)}"
        )


def run_inventory(
    output: Path,
    *,
    fetcher: Callable[[ExpectedObject], InventoryRow],
    workers: int = 4,
    batch_size: int = 12,
    max_new: int | None = None,
) -> dict[str, object]:
    """Validate/resume an inventory and return an auditable size summary."""
    if not 1 <= workers <= 8:
        raise ValueError("workers must be within 1..8")
    if batch_size < 1:
        raise ValueError("batch_size must be positive")
    if max_new is not None and max_new < 0:
        raise ValueError("max_new cannot be negative")
    checkpoint = partial_path(output)
    if output.exists() and checkpoint.exists():
        raise RuntimeError("both final and partial inventories exist; refusing ambiguity")

    objects = expected_objects()
    by_key = {item.key: item for item in objects}
    if output.exists():
        rows = load_inventory(output, require_complete=True)
        source_path = output
    elif checkpoint.exists():
        rows = load_inventory(checkpoint, require_complete=False)
        source_path = checkpoint
    else:
        rows = {}
        source_path = None

    # Recheck all recorded identities before adding anything.  No drift is
    # overwritten or silently normalized.
    existing_objects = [by_key[key] for key in sorted(rows)]
    for batch in _chunks(existing_objects, batch_size):
        for observed in _fetch_many(batch, fetcher, workers):
            _assert_same_identity(rows[observed.key], observed)

    if output.exists():
        total_bytes = sum(row.content_length for row in rows.values())
        return {
            "complete": True,
            "expected_objects": len(objects),
            "recorded_objects": len(rows),
            "new_objects": 0,
            "total_content_length_bytes": total_bytes,
            "total_content_length_gib": total_bytes / (1024**3),
            "inventory": str(output),
            "existing_inventory_reverified": True,
            "note": (
                "HTTP identity only; acquired files still require local byte-length, "
                "SHA-512, NetCDF schema, and exact time-coverage validation"
            ),
        }

    missing = [item for item in objects if item.key not in rows]
    selected = missing if max_new is None else missing[:max_new]
    new_count = 0
    for batch in _chunks(selected, batch_size):
        observed_rows = _fetch_many(batch, fetcher, workers)
        for observed in observed_rows:
            if observed.key in rows:
                raise RuntimeError(f"internal duplicate result for {observed.name}")
            expected = by_key.get(observed.key)
            if expected is None:
                raise RuntimeError(f"fetcher returned unexpected object {observed.name}")
            if (
                observed.name != expected.name
                or observed.canonical_url != expected.canonical_url
            ):
                raise RuntimeError("fetcher returned a noncanonical object identity")
            rows[observed.key] = observed
            new_count += 1
        write_inventory_atomic(checkpoint, rows)

    complete = len(rows) == len(objects)
    if complete:
        # Reload with the complete gate before atomic promotion.
        load_inventory(checkpoint, require_complete=True)
        checkpoint.replace(output)
        source_path = output
    elif rows:
        source_path = checkpoint

    total_bytes = sum(row.content_length for row in rows.values())
    return {
        "complete": complete,
        "expected_objects": len(objects),
        "recorded_objects": len(rows),
        "new_objects": new_count,
        "total_content_length_bytes": total_bytes,
        "total_content_length_gib": total_bytes / (1024**3),
        "inventory": str(source_path) if source_path else None,
        "existing_inventory_reverified": bool(existing_objects),
        "note": (
            "HTTP identity only; acquired files still require local byte-length, "
            "SHA-512, NetCDF schema, and exact time-coverage validation"
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "HEAD-only nClimGrid-Daily inventory for all 468 months in 1981--2019; "
            "this command never downloads a NetCDF response body"
        )
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--batch-size", type=int, default=12)
    parser.add_argument("--timeout-seconds", type=float, default=90)
    parser.add_argument("--attempts", type=int, default=3)
    parser.add_argument(
        "--max-new",
        type=int,
        help=(
            "bounded metadata run: add at most this many missing HEAD identities; "
            "the CSV remains .partial until all 468 objects are present"
        ),
    )
    args = parser.parse_args()
    if args.timeout_seconds <= 0:
        parser.error("--timeout-seconds must be positive")
    if args.attempts < 1:
        parser.error("--attempts must be at least one")

    def fetch(item: ExpectedObject) -> InventoryRow:
        return fetch_with_retries(
            item,
            timeout_seconds=args.timeout_seconds,
            attempts=args.attempts,
        )

    result = run_inventory(
        args.output,
        fetcher=fetch,
        workers=args.workers,
        batch_size=args.batch_size,
        max_new=args.max_new,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
