#!/usr/bin/env python3
"""Acquire one exact, provenance-pinned nClimGrid-Daily monthly smoke file.

This is a bounded file-integrity and schema gate. It supports only an object
present in the explicitly supplied reviewed provenance record and emits no
county exposure. New months need their own tracked object identities; the
mutable NCEI URL is never trusted without an exact byte and HTTP metadata pin.
"""
from __future__ import annotations

import argparse
import calendar
import hashlib
import json
import re
import tomllib
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import numpy as np
import pandas as pd
import xarray as xr


BASE_URL = "https://www.ncei.noaa.gov/data/nclimgrid-daily/access/grids"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PROVENANCE_RECORD = PROJECT_ROOT / "data/provenance/nclimgrid_daily_198101.toml"
MAX_BYTES = 100 * 1024 * 1024
EXPECTED_FIELDS = {
    "tmax": ("air_temperature", "degree_Celsius"),
    "tmin": ("air_temperature", "degree_Celsius"),
    "tavg": ("air_temperature", "degree_Celsius"),
    "prcp": ("precipitation_amount", "millimeter"),
}
EXPECTED_TITLE = "nClimGrid-Daily, Gridded Fields"
EXPECTED_VERSION = "v1-0-0 20220829"
EXPECTED_SHAPE = {"lat": 596, "lon": 1385}


def object_name(year: int, month: int) -> str:
    if not 1951 <= year <= 2100:
        raise ValueError("year is outside the plausible nClimGrid-Daily coverage")
    if not 1 <= month <= 12:
        raise ValueError("month must be within 1..12")
    return f"ncdd-{year:04d}{month:02d}-grd-scaled.nc"


def source_url(year: int, month: int) -> str:
    return f"{BASE_URL}/{year:04d}/{object_name(year, month)}"


def head_identity(url: str, opener: Callable[..., Any] = urlopen) -> dict[str, str]:
    request = Request(url, method="HEAD", headers={"User-Agent": "GIVE-precipitation-SCC/1.0"})
    try:
        with opener(request, timeout=90) as response:
            headers = response.headers
            length = headers.get("Content-Length")
            if not length:
                raise RuntimeError("nClimGrid response omitted Content-Length")
            return {
                "url": url,
                "content_length": length,
                "etag": headers.get("ETag", ""),
                "last_modified": headers.get("Last-Modified", ""),
                "content_type": headers.get("Content-Type", ""),
            }
    except HTTPError as error:
        raise RuntimeError(f"nClimGrid metadata request failed with HTTP {error.code}") from None
    except URLError as error:
        raise RuntimeError("nClimGrid metadata request failed due to network/transport error") from error


def sha512_file(path: Path) -> str:
    digest = hashlib.sha512()
    with path.open("rb") as stream:
        while block := stream.read(8 * 1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def load_pinned_record(path: Path, year: int, month: int) -> dict[str, object]:
    try:
        record = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise RuntimeError(f"Cannot read reviewed nClimGrid provenance record: {path}") from error
    single_object = record.get("object")
    listed_objects = record.get("files", [])
    license_record = record.get("license")
    stability = record.get("stability")
    objects: list[dict[str, object]] = []
    if isinstance(single_object, dict):
        objects.append(single_object)
    if isinstance(listed_objects, list):
        objects.extend(item for item in listed_objects if isinstance(item, dict))
    if not objects or not isinstance(license_record, dict):
        raise RuntimeError("nClimGrid provenance record lacks object/license tables")
    matches = [obj for obj in objects if obj.get("year") == year and obj.get("month") == month]
    if len(matches) != 1:
        raise RuntimeError("nClimGrid request differs from reviewed provenance object")
    obj = matches[0]
    expected_url = source_url(year, month)
    if obj.get("source_url") != expected_url:
        raise RuntimeError("nClimGrid provenance URL differs from canonical request URL")
    sha512 = obj.get("local_sha512")
    size_bytes = obj.get("size_bytes")
    local_path = obj.get("local_ignored_path")
    if not isinstance(sha512, str) or not re.fullmatch(r"[0-9a-f]{128}", sha512):
        raise RuntimeError("nClimGrid provenance lacks a valid lowercase SHA-512")
    if not isinstance(size_bytes, int) or size_bytes <= 0:
        raise RuntimeError("nClimGrid provenance lacks a positive byte length")
    if not isinstance(local_path, str) or Path(local_path).name != object_name(year, month):
        raise RuntimeError("nClimGrid provenance local filename differs from requested object")
    upstream = obj.get("upstream_identity")
    if not isinstance(upstream, dict):
        raise RuntimeError("nClimGrid provenance lacks upstream HTTP identity")
    if upstream.get("content_length") != size_bytes:
        raise RuntimeError("nClimGrid provenance byte lengths disagree")
    return {
        "record": record,
        "sha512": sha512,
        "size_bytes": size_bytes,
        "local_ignored_path": local_path,
        "source_url": expected_url,
        "upstream_identity": upstream,
        "license": license_record,
        "stability": stability if isinstance(stability, dict) else {},
    }


def validate_pinned_remote(identity: dict[str, str], pin: dict[str, object]) -> None:
    upstream = pin["upstream_identity"]
    assert isinstance(upstream, dict)
    expected = {
        "url": str(pin["source_url"]),
        "content_length": str(pin["size_bytes"]),
        "etag": str(upstream.get("etag", "")),
        "last_modified": str(upstream.get("last_modified", "")),
        "content_type": str(upstream.get("content_type", "")),
    }
    for field, value in expected.items():
        if identity.get(field, "") != value:
            raise RuntimeError(
                f"nClimGrid upstream {field} differs from reviewed provenance identity"
            )


def validate_pinned_file(path: Path, pin: dict[str, object]) -> None:
    if path.stat().st_size != int(pin["size_bytes"]):
        raise RuntimeError("nClimGrid file length differs from reviewed provenance identity")
    if sha512_file(path) != pin["sha512"]:
        raise RuntimeError("nClimGrid file SHA-512 differs from reviewed provenance identity")


def validate_netcdf(path: Path, year: int, month: int) -> dict[str, object]:
    with xr.open_dataset(path, engine="h5netcdf") as dataset:
        if set(dataset.data_vars) != set(EXPECTED_FIELDS):
            raise RuntimeError(
                f"nClimGrid variables changed: {sorted(dataset.data_vars)}"
            )
        expected_days = calendar.monthrange(year, month)[1]
        if dict(dataset.sizes) != {"time": expected_days, **EXPECTED_SHAPE}:
            raise RuntimeError(f"nClimGrid dimensions changed: {dict(dataset.sizes)}")
        if dataset.attrs.get("title") != EXPECTED_TITLE:
            raise RuntimeError("nClimGrid title differs from the reviewed product")
        if dataset.attrs.get("product_version") != EXPECTED_VERSION:
            raise RuntimeError("nClimGrid product_version differs from the reviewed product")
        if dataset.attrs.get("license") != "no restrictions":
            raise RuntimeError("nClimGrid embedded license statement changed")
        for name, (standard_name, units) in EXPECTED_FIELDS.items():
            field = dataset[name]
            if field.dims != ("time", "lat", "lon"):
                raise RuntimeError(f"nClimGrid {name} dimensions changed: {field.dims}")
            if field.attrs.get("standard_name") != standard_name:
                raise RuntimeError(f"nClimGrid {name} standard_name changed")
            if field.attrs.get("units") != units:
                raise RuntimeError(f"nClimGrid {name} units changed from {units}")
            comment = str(field.attrs.get("comment", "")).lower()
            if "24-hour period ending in the early morning" not in comment:
                raise RuntimeError(f"nClimGrid {name} day-label semantics are missing")
        dates = pd.DatetimeIndex(dataset.time.values)
        end = pd.Timestamp(year, month, expected_days)
        expected_dates = pd.date_range(pd.Timestamp(year, month, 1), end, freq="D")
        if not dates.equals(expected_dates):
            raise RuntimeError("nClimGrid chronology is not the exact requested calendar month")
        latitude = dataset.lat.values.astype(float)
        longitude = dataset.lon.values.astype(float)
        if not np.isfinite(latitude).all() or not np.isfinite(longitude).all():
            raise RuntimeError("nClimGrid coordinates must be finite")
        if len(np.unique(latitude)) != len(latitude) or len(np.unique(longitude)) != len(longitude):
            raise RuntimeError("nClimGrid coordinates must be unique")
        if not ((np.diff(latitude) > 0).all() and (np.diff(longitude) > 0).all()):
            raise RuntimeError("nClimGrid latitude/longitude orientation changed")
        return {
            "data_variables": sorted(EXPECTED_FIELDS),
            "time_coordinate": "time",
            "daily_time_steps": len(dates),
            "start_date": dates[0].date().isoformat(),
            "end_date": dates[-1].date().isoformat(),
            "dimensions": {str(name): int(size) for name, size in dataset.sizes.items()},
            "title": dataset.attrs["title"],
            "product_version": dataset.attrs["product_version"],
            "embedded_license": dataset.attrs["license"],
            "day_label_semantics": "24-hour period ending early morning of specified date",
        }


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
        raise RuntimeError(f"nClimGrid download failed with HTTP {error.code}") from None
    except URLError as error:
        temporary.unlink(missing_ok=True)
        raise RuntimeError("nClimGrid download failed due to network/transport error") from error
    temporary.replace(destination)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", required=True, type=int)
    parser.add_argument("--month", required=True, type=int)
    parser.add_argument("--out-dir", default="data/raw/us_county/nclimgrid_daily")
    parser.add_argument(
        "--provenance-record",
        default=str(DEFAULT_PROVENANCE_RECORD),
        help="reviewed tracked provenance record defining the only accepted object identity",
    )
    args = parser.parse_args()
    url = source_url(args.year, args.month)
    provenance_path = Path(args.provenance_record)
    pin = load_pinned_record(provenance_path, args.year, args.month)
    identity = head_identity(url)
    validate_pinned_remote(identity, pin)
    expected_bytes = int(pin["size_bytes"])
    if expected_bytes > MAX_BYTES:
        raise RuntimeError(
            f"Refusing {expected_bytes} byte nClimGrid file; smoke cap is {MAX_BYTES} bytes"
        )
    out_dir = Path(args.out_dir)
    destination = out_dir / object_name(args.year, args.month)
    if destination.exists():
        validate_pinned_file(destination, pin)
        status = "existing"
    else:
        out_dir.mkdir(parents=True, exist_ok=True)
        download(url, destination)
        try:
            validate_pinned_file(destination, pin)
        except RuntimeError:
            destination.unlink(missing_ok=True)
            raise
        status = "downloaded"
    details = validate_netcdf(destination, args.year, args.month)
    license_record = pin["license"]
    stability = pin["stability"]
    assert isinstance(license_record, dict) and isinstance(stability, dict)
    try:
        displayed_provenance = str(provenance_path.resolve().relative_to(PROJECT_ROOT))
    except ValueError:
        displayed_provenance = provenance_path.name
    record = {
        "source": "NOAA NCEI nClimGrid-Daily v1.0.0",
        "source_url": url,
        "source_documentation": pin["record"]["landing_page_url"],
        "provenance_record": displayed_provenance,
        "license": license_record["status"],
        "license_spdx_identifier": license_record["spdx_identifier"],
        "license_url": license_record["url"],
        "role": pin["record"]["approved_use"],
        "scientific_limitations": stability.get("scientific_limitations", []),
        "retrieved_utc": datetime.now(UTC).isoformat(),
        "status": status,
        "file": str(destination),
        "bytes": destination.stat().st_size,
        "sha512": sha512_file(destination),
        "upstream_identity": identity,
        "netcdf_validation": details,
    }
    with (out_dir / "MANIFEST.jsonl").open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, sort_keys=True) + "\n")
    print(
        f"{status}: {destination.name} ({record['bytes']} bytes; "
        f"{details['daily_time_steps']} daily steps)"
    )


if __name__ == "__main__":
    main()
