#!/usr/bin/env python3
"""Acquire and fail-closed validate NOAA's exact dated county PDSI snapshot."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import tomllib
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PROVENANCE = PROJECT_ROOT / "data/provenance/nclimdiv_county_pdsi_20260806.toml"
BULK_NAME = "climdiv-pdsicy-v1.0.0-20260806"


def sha512_file(path: Path) -> str:
    digest = hashlib.sha512()
    with path.open("rb") as stream:
        while block := stream.read(8 * 1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def load_pins(path: Path) -> tuple[dict[str, object], list[dict[str, object]]]:
    try:
        record = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise RuntimeError(f"Cannot read reviewed nClimDiv provenance: {path}") from error
    files = record.get("files")
    if not isinstance(files, list) or len(files) != 3:
        raise RuntimeError("nClimDiv provenance must pin exactly the bulk file and two READMEs")
    names: set[str] = set()
    for item in files:
        if not isinstance(item, dict):
            raise RuntimeError("nClimDiv file pin is not a table")
        required = {"name", "url", "local_ignored_path", "size_bytes", "sha512", "last_modified", "etag"}
        if missing := required - set(item):
            raise RuntimeError(f"nClimDiv file pin lacks {sorted(missing)}")
        name = item["name"]
        if not isinstance(name, str) or not name or name in names:
            raise RuntimeError("nClimDiv file pins have a blank or duplicate name")
        names.add(name)
        if not isinstance(item["size_bytes"], int) or item["size_bytes"] <= 0:
            raise RuntimeError(f"nClimDiv file {name} has invalid size")
        if not isinstance(item["sha512"], str) or not re.fullmatch(r"[0-9a-f]{128}", item["sha512"]):
            raise RuntimeError(f"nClimDiv file {name} has invalid SHA-512")
        local = Path(str(item["local_ignored_path"]))
        if local.is_absolute() or local.name != name:
            raise RuntimeError(f"nClimDiv file {name} has an unsafe or inconsistent local path")
    if names != {BULK_NAME, "county-readme.txt", "drought-readme.txt"}:
        raise RuntimeError("nClimDiv provenance file identities changed")
    return record, files


def head_identity(url: str, opener: Callable[..., Any] = urlopen) -> dict[str, str]:
    request = Request(url, method="HEAD", headers={"User-Agent": "GIVE-precipitation-SCC/1.0"})
    try:
        with opener(request, timeout=90) as response:
            return {
                "content_length": response.headers.get("Content-Length", ""),
                "etag": response.headers.get("ETag", ""),
                "last_modified": response.headers.get("Last-Modified", ""),
                "content_type": response.headers.get("Content-Type", ""),
            }
    except HTTPError as error:
        raise RuntimeError(f"nClimDiv metadata request failed with HTTP {error.code}") from None
    except URLError as error:
        raise RuntimeError("nClimDiv metadata request failed due to network/transport error") from error


def validate_remote(identity: dict[str, str], pin: dict[str, object]) -> None:
    expected = {
        "content_length": str(pin["size_bytes"]),
        "etag": str(pin["etag"]),
        "last_modified": str(pin["last_modified"]),
    }
    for field, value in expected.items():
        if identity.get(field, "") != value:
            raise RuntimeError(f"nClimDiv upstream {field} differs from reviewed provenance")


def validate_local(path: Path, pin: dict[str, object]) -> None:
    if not path.is_file():
        raise RuntimeError(f"nClimDiv file is absent: {path}")
    if path.stat().st_size != int(pin["size_bytes"]):
        raise RuntimeError(f"nClimDiv file length differs from reviewed provenance: {path.name}")
    if sha512_file(path) != pin["sha512"]:
        raise RuntimeError(f"nClimDiv file SHA-512 differs from reviewed provenance: {path.name}")


def download(url: str, destination: Path, opener: Callable[..., Any] = urlopen) -> None:
    request = Request(url, headers={"User-Agent": "GIVE-precipitation-SCC/1.0"})
    temporary = destination.with_suffix(destination.suffix + ".partial")
    temporary.unlink(missing_ok=True)
    try:
        with opener(request, timeout=900) as response, temporary.open("wb") as stream:
            while block := response.read(8 * 1024 * 1024):
                stream.write(block)
    except HTTPError as error:
        temporary.unlink(missing_ok=True)
        raise RuntimeError(f"nClimDiv download failed with HTTP {error.code}") from None
    except URLError as error:
        temporary.unlink(missing_ok=True)
        raise RuntimeError("nClimDiv download failed due to network/transport error") from error
    temporary.replace(destination)


def validate_bulk_schema(path: Path, validation: dict[str, object]) -> dict[str, object]:
    expected_records = int(validation["record_count"])
    expected_counties = int(validation["internal_county_key_count"])
    first_year, last_year = int(validation["first_year"]), int(validation["last_year"])
    expected_years = last_year - first_year + 1
    keys: set[tuple[str, int]] = set()
    counties: set[str] = set()
    state_codes: set[str] = set()
    missing_positions: list[tuple[int, int]] = []
    missing_by_county: dict[str, set[tuple[int, int]]] = {}
    records = 0
    with path.open("r", encoding="ascii", newline="") as stream:
        for records, raw in enumerate(stream, start=1):
            if not raw.endswith("\n") or len(raw) != int(validation["record_bytes_including_lf"]):
                raise RuntimeError(f"nClimDiv record {records} differs from the fixed byte width")
            line = raw[:-1]
            if len(line) != int(validation["record_characters_excluding_lf"]):
                raise RuntimeError(f"nClimDiv record {records} differs from the fixed character width")
            state_code, county_code, element = line[:2], line[2:5], line[5:7]
            if not (state_code.isdigit() and county_code.isdigit() and line[7:11].isdigit()):
                raise RuntimeError(f"nClimDiv record {records} has malformed key fields")
            if element != str(validation["element_code"]):
                raise RuntimeError(f"nClimDiv record {records} has an unexpected element code")
            year = int(line[7:11])
            if not first_year <= year <= last_year:
                raise RuntimeError(f"nClimDiv record {records} has a year outside the pinned range")
            internal_county = state_code + county_code
            key = (internal_county, year)
            if key in keys:
                raise RuntimeError("nClimDiv contains duplicate internal-county/year records")
            keys.add(key)
            counties.add(internal_county)
            state_codes.add(state_code)
            for month in range(1, 13):
                field = line[11 + 7 * (month - 1):18 + 7 * (month - 1)]
                try:
                    value = float(field)
                except ValueError as error:
                    raise RuntimeError(f"nClimDiv record {records} has a malformed monthly value") from error
                if value == float(validation["missing_value"]):
                    missing_positions.append((year, month))
                    missing_by_county.setdefault(internal_county, set()).add((year, month))
    if records != expected_records or len(keys) != expected_records:
        raise RuntimeError("nClimDiv record count differs from the pinned snapshot")
    if len(counties) != expected_counties:
        raise RuntimeError("nClimDiv internal county count differs from the pinned snapshot")
    if state_codes != {f"{value:02d}" for value in range(1, 49)}:
        raise RuntimeError("nClimDiv internal state codes are not exactly 01-48")
    if expected_counties * expected_years != expected_records:
        raise RuntimeError("Pinned nClimDiv county/year dimensions do not form a rectangle")
    if len(missing_positions) != int(validation["missing_count"]):
        raise RuntimeError("nClimDiv missing-value count differs from the pinned snapshot")
    if set(missing_positions) != {(last_year, month) for month in range(8, 13)}:
        raise RuntimeError("nClimDiv missing values are not confined to August-December 2026")
    expected_missing = {(last_year, month) for month in range(8, 13)}
    if set(missing_by_county) != counties or any(values != expected_missing for values in missing_by_county.values()):
        raise RuntimeError("nClimDiv does not have exactly the five pinned latest-year missing months per county")
    return {
        "records": records,
        "internal_counties": len(counties),
        "first_year": first_year,
        "last_year": last_year,
        "missing_values": len(missing_positions),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--provenance-record", default=str(DEFAULT_PROVENANCE))
    parser.add_argument("--out-dir", default="data/raw/us_county/nclimdiv_pdsicy")
    args = parser.parse_args()
    provenance_path = Path(args.provenance_record)
    record, pins = load_pins(provenance_path)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_rows: list[dict[str, object]] = []
    for pin in pins:
        identity = head_identity(str(pin["url"]))
        validate_remote(identity, pin)
        destination = out_dir / str(pin["name"])
        if destination.exists():
            status = "existing"
        else:
            download(str(pin["url"]), destination)
            status = "downloaded"
        validate_local(destination, pin)
        manifest_rows.append({
            "source": "NOAA nClimDiv county PDSI",
            "name": pin["name"],
            "url": pin["url"],
            "retrieved_utc": datetime.now(UTC).isoformat(),
            "status": status,
            "bytes": destination.stat().st_size,
            "sha512": sha512_file(destination),
            "upstream_identity": identity,
            "role": record["approved_use"],
            "scc_authorized": False,
        })
    bulk_pin = next(item for item in pins if item["name"] == BULK_NAME)
    validation = bulk_pin.get("validation")
    if not isinstance(validation, dict):
        raise RuntimeError("nClimDiv bulk provenance lacks decoded validation expectations")
    summary = validate_bulk_schema(out_dir / BULK_NAME, validation)
    with (out_dir / "MANIFEST.jsonl").open("a", encoding="utf-8") as stream:
        for row in manifest_rows:
            stream.write(json.dumps(row, sort_keys=True) + "\n")
    print(f"valid NOAA county PDSI snapshot: {summary}")


if __name__ == "__main__":
    main()
