#!/usr/bin/env python3
"""Acquire one bounded, provenance-recorded gridMET daily smoke input.

This intentionally supports one calendar year and one weather variable per
invocation. It is a climate-file integrity smoke test, not county exposure
construction: no county centroid or unweighted county weather is emitted.
Official gridMET full-CONUS NetCDF files are hosted by the Northwest Knowledge
Network; raw files stay under the project-gitignored data/raw directory.
"""
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

import xarray as xr
import numpy as np
import pandas as pd

BASE_URL = "https://www.northwestknowledge.net/metdata/data"
ALLOWED_VARIABLES = {"pr", "tmmn", "tmmx"}
EXPECTED_FIELDS = {
    "pr": ("precipitation_amount", "mm"),
    "tmmn": ("air_temperature", "K"),
    "tmmx": ("air_temperature", "K"),
}
MAX_BYTES = 100 * 1024 * 1024
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PROVENANCE_RECORD = PROJECT_ROOT / "data/provenance/gridmet_pr_2018.toml"


def source_url(variable: str, year: int) -> str:
    if variable not in ALLOWED_VARIABLES:
        raise ValueError(f"variable must be one of {sorted(ALLOWED_VARIABLES)}")
    if not 1979 <= year <= 2100:
        raise ValueError("year must be within gridMET's plausible coverage")
    return f"{BASE_URL}/{variable}_{year}.nc"


def head_identity(url: str, opener: Callable[..., Any] = urlopen) -> dict[str, str]:
    request = Request(url, method="HEAD", headers={"User-Agent": "GIVE-precipitation-SCC/1.0"})
    try:
        with opener(request, timeout=90) as response:
            headers = response.headers
            length = headers.get("Content-Length")
            if not length:
                raise RuntimeError("gridMET response omitted Content-Length")
            return {
                "url": url,
                "content_length": length,
                "etag": headers.get("ETag", ""),
                "last_modified": headers.get("Last-Modified", ""),
                "content_type": headers.get("Content-Type", ""),
            }
    except HTTPError as error:
        raise RuntimeError(f"gridMET metadata request failed with HTTP {error.code}") from None
    except URLError as error:
        raise RuntimeError("gridMET metadata request failed due to network/transport error") from error


def sha512_file(path: Path) -> str:
    digest = hashlib.sha512()
    with path.open("rb") as stream:
        while block := stream.read(8 * 1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def load_pinned_record(path: Path, variable: str, year: int) -> dict[str, object]:
    """Load one reviewed gridMET object identity and fail on scope drift."""
    try:
        record = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise RuntimeError(f"Cannot read reviewed gridMET provenance record: {path}") from error
    obj = record.get("object")
    license_record = record.get("license")
    stability = record.get("stability")
    if not isinstance(obj, dict) or not isinstance(license_record, dict):
        raise RuntimeError("gridMET provenance record lacks object/license tables")
    if obj.get("variable") != variable or obj.get("year") != year:
        raise RuntimeError("gridMET request differs from reviewed provenance object")
    expected_url = source_url(variable, year)
    if obj.get("source_url") != expected_url:
        raise RuntimeError("gridMET provenance source URL differs from the canonical request URL")
    sha512 = obj.get("local_sha512")
    size_bytes = obj.get("size_bytes")
    local_path = obj.get("local_ignored_path")
    if not isinstance(sha512, str) or not re.fullmatch(r"[0-9a-f]{128}", sha512):
        raise RuntimeError("gridMET provenance lacks a valid lowercase SHA-512")
    if not isinstance(size_bytes, int) or size_bytes <= 0:
        raise RuntimeError("gridMET provenance lacks a positive byte length")
    if not isinstance(local_path, str) or Path(local_path).name != f"gridmet_{variable}_{year}.nc":
        raise RuntimeError("gridMET provenance local filename differs from requested object")
    upstream = obj.get("upstream_identity")
    if not isinstance(upstream, dict):
        raise RuntimeError("gridMET provenance lacks upstream HTTP identity")
    if upstream.get("content_length") != size_bytes:
        raise RuntimeError("gridMET provenance byte lengths disagree")
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
    """Reject a mutable upstream URL if its recorded HTTP identity changed."""
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
                f"gridMET upstream {field} differs from reviewed provenance identity"
            )


def validate_pinned_file(path: Path, pin: dict[str, object]) -> None:
    """Verify byte length and content digest before decoding an existing/downloaded file."""
    if path.stat().st_size != int(pin["size_bytes"]):
        raise RuntimeError("gridMET file length differs from reviewed provenance identity")
    if sha512_file(path) != pin["sha512"]:
        raise RuntimeError("gridMET file SHA-512 differs from reviewed provenance identity")


def validate_netcdf(path: Path, variable: str, year: int) -> dict[str, object]:
    with xr.open_dataset(path, engine="h5netcdf") as dataset:
        expected_field, expected_units = EXPECTED_FIELDS[variable]
        if set(dataset.data_vars) != {expected_field}:
            raise RuntimeError(
                f"gridMET data variables differ from {variable}: {sorted(dataset.data_vars)}"
            )
        time_name = next((name for name in ("day", "time") if name in dataset.coords or name in dataset.dims), None)
        if time_name is None:
            raise RuntimeError("gridMET file has no recognized daily time coordinate")
        time_count = int(dataset.sizes[time_name])
        expected_days = 366 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 365
        if time_count != expected_days:
            raise RuntimeError(f"gridMET file has {time_count} time steps; expected {expected_days}")
        if not ({"lat", "lon"} <= set(dataset.coords) or {"lat", "lon"} <= set(dataset.dims)):
            raise RuntimeError("gridMET file lacks latitude/longitude coordinates")
        field = dataset[expected_field]
        if field.dims != (time_name, "lat", "lon"):
            raise RuntimeError(f"gridMET variable has unexpected dimensions {field.dims}")
        if field.attrs.get("units") != expected_units:
            raise RuntimeError(f"gridMET {variable} units differ from {expected_units}")
        dates = pd.DatetimeIndex(dataset[time_name].values)
        expected_dates = pd.date_range(f"{year}-01-01", f"{year}-12-31", freq="D")
        if not dates.equals(expected_dates):
            raise RuntimeError("gridMET time coordinate is not the exact requested daily year")
        latitude = dataset["lat"].values.astype(float)
        longitude = dataset["lon"].values.astype(float)
        if not np.isfinite(latitude).all() or not np.isfinite(longitude).all():
            raise RuntimeError("gridMET coordinates must be finite")
        if len(np.unique(latitude)) != len(latitude) or len(np.unique(longitude)) != len(longitude):
            raise RuntimeError("gridMET coordinates must be unique")
        if not ((np.diff(latitude) < 0).all() and (np.diff(longitude) > 0).all()):
            raise RuntimeError("gridMET latitude/longitude orientation changed")
        return {
            "data_variable": expected_field,
            "units": expected_units,
            "time_coordinate": time_name,
            "daily_time_steps": time_count,
            "start_date": dates[0].date().isoformat(),
            "end_date": dates[-1].date().isoformat(),
            "dimensions": {str(name): int(size) for name, size in dataset.sizes.items()},
            "requested_short_name": variable,
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
        raise RuntimeError(f"gridMET download failed with HTTP {error.code}") from None
    except URLError as error:
        temporary.unlink(missing_ok=True)
        raise RuntimeError("gridMET download failed due to network/transport error") from error
    temporary.replace(destination)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--variable", required=True, choices=sorted(ALLOWED_VARIABLES))
    parser.add_argument("--year", required=True, type=int)
    parser.add_argument("--out-dir", default="data/raw/us_county/gridmet")
    parser.add_argument(
        "--provenance-record",
        default=str(DEFAULT_PROVENANCE_RECORD),
        help="reviewed tracked provenance record defining the only accepted object identity",
    )
    args = parser.parse_args()
    url = source_url(args.variable, args.year)
    provenance_path = Path(args.provenance_record)
    pin = load_pinned_record(provenance_path, args.variable, args.year)
    identity = head_identity(url)
    validate_pinned_remote(identity, pin)
    expected_bytes = int(pin["size_bytes"])
    if expected_bytes > MAX_BYTES:
        raise RuntimeError(
            f"Refusing {expected_bytes} byte gridMET file; smoke cap is {MAX_BYTES} bytes"
        )
    out_dir = Path(args.out_dir)
    destination = out_dir / f"gridmet_{args.variable}_{args.year}.nc"
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
    details = validate_netcdf(destination, args.variable, args.year)
    license_record = pin["license"]
    stability = pin["stability"]
    assert isinstance(license_record, dict) and isinstance(stability, dict)
    try:
        displayed_provenance = str(provenance_path.resolve().relative_to(PROJECT_ROOT))
    except ValueError:
        displayed_provenance = provenance_path.name
    record = {
        "source": "gridMET daily surface meteorological data",
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
    print(f"{status}: {destination.name} ({record['bytes']} bytes; {details['daily_time_steps']} daily steps)")


if __name__ == "__main__":
    main()
