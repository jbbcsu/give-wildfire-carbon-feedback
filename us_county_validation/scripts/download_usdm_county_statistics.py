#!/usr/bin/env python3
"""Download documented county-week U.S. Drought Monitor area-share statistics.

The official REST endpoint accepts one state and at most one year per request.
This script intentionally requires explicit states and years, writes raw CSVs
under the gitignored US validation raw-data tree, and records URL, check time,
retrieval time (for downloads), bytes, and SHA-512. It does not interpret
USDM categories as a projected climate variable.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import subprocess
import tempfile
from datetime import UTC, datetime
from io import StringIO
from pathlib import Path
from urllib.parse import urlencode


API = "https://usdmdataservices.unl.edu/api/CountyStatistics/GetDroughtSeverityStatisticsByAreaPercent"
REQUIRED_COLUMNS = {
    "MapDate",
    "FIPS",
    "County",
    "State",
    "None",
    "D0",
    "D1",
    "D2",
    "D3",
    "D4",
    "ValidStart",
    "ValidEnd",
    "StatisticFormatID",
}


def build_url(state: str, year: int) -> str:
    query = urlencode({
        "aoi": state.upper(),
        "startdate": f"1/1/{year}",
        "enddate": f"12/31/{year}",
        "statisticsType": "2",
    })
    return f"{API}?{query}"


def validate_payload(payload: bytes, state: str, year: int) -> dict[str, object]:
    """Validate that a response is the requested county-area-percent extract."""
    if not payload:
        raise RuntimeError(f"empty USDM response for {state} {year}")
    try:
        text = payload.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise RuntimeError(f"USDM response is not UTF-8 CSV for {state} {year}") from error
    reader = csv.DictReader(StringIO(text))
    if reader.fieldnames is None:
        raise RuntimeError(f"USDM response is missing a CSV header for {state} {year}")
    if missing := REQUIRED_COLUMNS - set(reader.fieldnames):
        raise RuntimeError(
            f"USDM response missing columns {sorted(missing)} for {state} {year}"
        )

    rows = list(reader)
    if not rows:
        raise RuntimeError(f"USDM response has no data rows for {state} {year}")
    keys: set[tuple[str, str]] = set()
    map_dates: list[datetime] = []
    expected_state = state.upper()
    requested_start = datetime(year, 1, 1)
    requested_end = datetime(year, 12, 31)
    for row_number, row in enumerate(rows, start=2):
        if None in row or any(row.get(column) is None for column in REQUIRED_COLUMNS):
            raise RuntimeError(f"USDM response row {row_number} is not a rectangular CSV row")
        row_state = row["State"].strip().upper()
        if row_state != expected_state:
            raise RuntimeError(
                f"USDM response row {row_number} has state {row_state!r}, "
                f"expected {expected_state}"
            )
        if row["StatisticFormatID"].strip() != "2":
            raise RuntimeError(
                f"USDM response row {row_number} is not area-percent statistic format 2"
            )
        fips = row["FIPS"].strip()
        if len(fips) != 5 or not fips.isdigit():
            raise RuntimeError(
                f"USDM response row {row_number} has invalid five-digit county FIPS {fips!r}"
            )
        try:
            map_date = datetime.strptime(row["MapDate"].strip(), "%Y%m%d")
        except ValueError as error:
            raise RuntimeError(
                f"USDM response row {row_number} has invalid MapDate {row['MapDate']!r}"
            ) from error
        try:
            valid_start = datetime.strptime(row["ValidStart"].strip(), "%Y-%m-%d")
            valid_end = datetime.strptime(row["ValidEnd"].strip(), "%Y-%m-%d")
        except ValueError as error:
            raise RuntimeError(
                f"USDM response row {row_number} has invalid validity dates"
            ) from error
        if valid_end < valid_start or not valid_start <= map_date <= valid_end:
            raise RuntimeError(
                f"USDM response row {row_number} has inconsistent map/validity dates"
            )
        # A calendar-year query legitimately includes the preceding Tuesday's
        # map when its validity interval covers January 1.
        if valid_end < requested_start or valid_start > requested_end:
            raise RuntimeError(
                f"USDM response row {row_number} does not overlap requested year {year}"
            )
        key = (fips, map_date.strftime("%Y%m%d"))
        if key in keys:
            raise RuntimeError(
                f"USDM response has duplicate county-week key {fips} {key[1]}"
            )
        keys.add(key)
        map_dates.append(map_date)
    return {
        "rows": len(rows),
        "counties": len({fips for fips, _ in keys}),
        "map_date_min": min(map_dates).date().isoformat(),
        "map_date_max": max(map_dates).date().isoformat(),
    }


def pinned_identity(
    manifest: Path, state: str, year: int, target: Path
) -> tuple[int, str] | None:
    """Return one previously recorded identity, rejecting conflicting history."""
    if not manifest.exists():
        return None
    identities: set[tuple[int, str]] = set()
    lines = manifest.read_text(encoding="utf-8").splitlines()
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as error:
            raise RuntimeError(f"Malformed USDM manifest line {line_number}") from error
        if (
            str(record.get("state", "")).upper() == state
            and record.get("year") == year
            and Path(str(record.get("file", ""))).name == target.name
        ):
            try:
                identity = (int(record["bytes"]), str(record["sha512"]).lower())
            except (KeyError, TypeError, ValueError) as error:
                raise RuntimeError(
                    f"Incomplete identity on USDM manifest line {line_number}"
                ) from error
            if len(identity[1]) != 128 or any(
                character not in "0123456789abcdef" for character in identity[1]
            ):
                raise RuntimeError(f"Invalid SHA-512 on USDM manifest line {line_number}")
            identities.add(identity)
    if len(identities) > 1:
        raise RuntimeError(
            f"Conflicting pinned identities for {target.name}; inspect the manifest and raw file"
        )
    return next(iter(identities), None)


def atomic_write(target: Path, payload: bytes) -> None:
    """Write one validated response without exposing a partial target file."""
    with tempfile.NamedTemporaryFile(
        dir=target.parent, prefix=f".{target.name}.", delete=False
    ) as stream:
        temporary = Path(stream.name)
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    try:
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--state",
        action="append",
        required=True,
        help="two-letter state code; repeatable",
    )
    parser.add_argument("--year-min", type=int, required=True)
    parser.add_argument("--year-max", type=int, required=True)
    parser.add_argument("--out-dir", default="data/raw/us_county/usdm")
    parser.add_argument("--timeout-seconds", type=int, default=60)
    args = parser.parse_args()
    if args.year_min > args.year_max:
        raise ValueError("--year-min must not exceed --year-max")
    states = sorted({state.strip().upper() for state in args.state})
    if any(len(state) != 2 or not state.isalpha() for state in states):
        raise ValueError("each --state must be a two-letter alphabetic code")

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = out_dir / "MANIFEST.jsonl"
    with manifest.open("a", encoding="utf-8") as manifest_stream:
        for state in states:
            for year in range(args.year_min, args.year_max + 1):
                target = out_dir / f"usdm_county_area_pct_{state}_{year}.csv"
                url = build_url(state, year)
                expected_identity = pinned_identity(manifest, state, year, target)
                if target.exists() and target.stat().st_size > 0:
                    payload = target.read_bytes()
                    status = "existing_validated"
                else:
                    # macOS's system curl uses the trusted system certificate
                    # store; the bundled Python runtime may not. Do not use
                    # curl's insecure (-k) mode.
                    response = subprocess.run(
                        ["curl", "--fail", "--location", "--silent", "--show-error",
                         "--max-time", str(args.timeout_seconds), url],
                        check=True,
                        capture_output=True,
                    )
                    payload = response.stdout
                    status = "downloaded"
                validation = validate_payload(payload, state, year)
                identity = (len(payload), hashlib.sha512(payload).hexdigest())
                if expected_identity is not None and identity != expected_identity:
                    raise RuntimeError(
                        f"USDM identity mismatch for {target.name}: expected "
                        f"{expected_identity[0]} bytes / {expected_identity[1]}, got "
                        f"{identity[0]} bytes / {identity[1]}"
                    )
                if status == "downloaded":
                    atomic_write(target, payload)
                checked_utc = datetime.now(UTC).isoformat()
                record = {
                    "source": "U.S. Drought Monitor county severity statistics REST service",
                    "url": url,
                    "state": state,
                    "year": year,
                    "checked_utc": checked_utc,
                    "retrieved_utc": checked_utc if status == "downloaded" else None,
                    "status": status,
                    "bytes": identity[0],
                    "sha512": identity[1],
                    "file": str(target),
                    **validation,
                }
                manifest_stream.write(json.dumps(record, sort_keys=True) + "\n")
                print(f"{status}: {target.name} ({len(payload)} bytes)")


if __name__ == "__main__":
    main()
