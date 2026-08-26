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
    args = parser.parse_args()
    url = source_url(args.variable, args.year)
    identity = head_identity(url)
    expected_bytes = int(identity["content_length"])
    if expected_bytes > MAX_BYTES:
        raise RuntimeError(
            f"Refusing {expected_bytes} byte gridMET file; smoke cap is {MAX_BYTES} bytes"
        )
    out_dir = Path(args.out_dir)
    destination = out_dir / f"gridmet_{args.variable}_{args.year}.nc"
    if destination.exists():
        if destination.stat().st_size != expected_bytes:
            raise RuntimeError("Existing gridMET smoke file length differs from pinned identity")
        status = "existing"
    else:
        out_dir.mkdir(parents=True, exist_ok=True)
        download(url, destination)
        if destination.stat().st_size != expected_bytes:
            destination.unlink(missing_ok=True)
            raise RuntimeError("Downloaded gridMET file length differs from pinned identity")
        status = "downloaded"
    details = validate_netcdf(destination, args.variable, args.year)
    record = {
        "source": "gridMET daily surface meteorological data",
        "source_url": url,
        "source_documentation": "https://climatetoolbox.org/data/past-weather-data",
        "license": "Verify current gridMET/Northwest Knowledge Network terms before redistribution",
        "role": "US county validation weather-file smoke only; not county exposure or SCC input",
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
