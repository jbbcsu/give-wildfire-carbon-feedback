#!/usr/bin/env python3
"""Build one fail-closed, resumable, spatially bounded SPEI grid chunk.

This engineering runner reads either the local nClimGrid-Daily archive or the
local ISIMIP3a GSWP3-W5E5 archive.  It validates exact source identities,
checkpoints daily-to-monthly aggregation by source block, fits native-cell
calendar-month GLO parameters only on 1982--2011, freezes those parameters for
application, and writes a NetCDF plus source/contract/output receipts.

It deliberately cannot fit crop outcomes or run an unchunked full grid.
"""
from __future__ import annotations

import argparse
import calendar
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import resource
import sys
import time
import tomllib
from typing import Any, Iterable, Mapping

import numpy as np
import pandas as pd
import xarray as xr
import h5netcdf
import h5py

from spei_construction_primitives import hargreaves_samani_et0_mm_day
from spei_distribution import CDF_CLIP_EPSILON, FIT_STATUS_LABELS
from spei_monthly_engine import LOCKED_SCALES, MonthlySpeiResult, construct_monthly_spei
from validate_spei_competitor_contract import FALSE_GATES, load_contract, validate_contract


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONTRACT = PROJECT_ROOT / "config/spei_competitor_v1.toml"
DEFAULT_OUTPUT_ROOT = PROJECT_ROOT / "outputs/spei_competitor_v1/chunks"
US_CONTENT_RECEIPT = (
    PROJECT_ROOT / "data/provenance/nclimgrid_daily_1981_2019_content_receipt.json"
)
GLOBAL_PROVENANCE = PROJECT_ROOT / "data/provenance/isimip3a_daily_climate_plan.toml"
ALGORITHM_VERSION = "spei_grid_chunk_v2_environment_bound"
CHECKPOINT_VERSION = "daily_to_monthly_checkpoint_v2_environment_bound"
MAX_CELLS_PER_CHUNK = 64
HASH_WORKERS = 4
PRECIPITATION_TOLERANCE = 1e-10
TEMPERATURE_ORDER_TOLERANCE_C = 1e-7


@dataclass(frozen=True)
class SourceRecord:
    name: str
    path: Path
    size_bytes: int
    sha512: str
    variable: str
    block: str
    start_date: str
    end_date: str

    def public_identity(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "size_bytes": self.size_bytes,
            "sha512": self.sha512,
            "variable": self.variable,
            "block": self.block,
            "start_date": self.start_date,
            "end_date": self.end_date,
        }


@dataclass(frozen=True)
class SourceInventory:
    source: str
    root: Path
    provenance_path: Path
    provenance_sha512: str
    source_id: str
    dataset_doi: str
    license: str
    records: tuple[SourceRecord, ...]
    declared_file_set_sha512: str


@dataclass(frozen=True)
class SpatialSlice:
    lat_start: int
    lat_stop: int
    lon_start: int
    lon_stop: int

    @property
    def lat_count(self) -> int:
        return self.lat_stop - self.lat_start

    @property
    def lon_count(self) -> int:
        return self.lon_stop - self.lon_start

    @property
    def cells(self) -> int:
        return self.lat_count * self.lon_count

    def as_dict(self) -> dict[str, int]:
        return {
            "lat_start": self.lat_start,
            "lat_stop_exclusive": self.lat_stop,
            "lon_start": self.lon_start,
            "lon_stop_exclusive": self.lon_stop,
            "cells": self.cells,
        }


@dataclass(frozen=True)
class MonthlyCheckpoint:
    months: pd.DatetimeIndex
    precipitation_mm: np.ndarray
    et0_mm: np.ndarray
    daily_complete_count: np.ndarray
    calendar_day_count: np.ndarray
    latitude: np.ndarray
    longitude: np.ndarray
    audit: dict[str, Any]


def canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def sha512_bytes(value: bytes) -> str:
    return hashlib.sha512(value).hexdigest()


def sha512_file(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError(f"expected a regular non-symbolic-link file: {path}")
    before = path.stat()
    digest = hashlib.sha512()
    with path.open("rb") as stream:
        while chunk := stream.read(8 * 1024 * 1024):
            digest.update(chunk)
    after = path.stat()
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise RuntimeError(f"file changed while being hashed: {path}")
    return digest.hexdigest()


def coordinate_sha512(values: np.ndarray) -> str:
    array = np.ascontiguousarray(np.asarray(values, dtype="<f8"))
    return sha512_bytes(array.tobytes())


def signature(value: object) -> str:
    return sha512_bytes(canonical_json_bytes(value))


def numerical_environment_identity() -> dict[str, str]:
    """Return every runtime identity that can affect parsing or numerics."""
    return {
        "python_implementation": platform.python_implementation(),
        "python_version": platform.python_version(),
        "python_cache_tag": str(sys.implementation.cache_tag),
        "platform_system": platform.system(),
        "platform_release": platform.release(),
        "platform_machine": platform.machine(),
        "byteorder": sys.byteorder,
        "numpy": np.__version__,
        "pandas": pd.__version__,
        "xarray": xr.__version__,
        "h5py": h5py.__version__,
        "hdf5": h5py.version.hdf5_version,
        "h5netcdf": h5netcdf.__version__,
    }


def with_hash_envelope(payload: Mapping[str, Any]) -> dict[str, Any]:
    result = dict(payload)
    if "receipt_payload_sha512" in result:
        raise ValueError("receipt payload already contains its hash envelope")
    result["receipt_payload_sha512"] = signature(result)
    return result


def validate_hash_envelope(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise RuntimeError(f"{label} is not a JSON object")
    result = dict(value)
    observed = result.pop("receipt_payload_sha512", None)
    if not isinstance(observed, str) or observed != signature(result):
        raise RuntimeError(f"{label} hash envelope is invalid")
    result["receipt_payload_sha512"] = observed
    return result


def read_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RuntimeError(f"cannot read {label}: {path}") from error
    if not isinstance(value, dict):
        raise RuntimeError(f"{label} must be a JSON object")
    return value


def write_json_atomic(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = (
        json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True, allow_nan=False)
        + "\n"
    ).encode("utf-8")
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    if temporary.exists():
        raise RuntimeError(f"refusing to overwrite unresolved temporary file: {temporary}")
    try:
        with temporary.open("xb") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except BaseException:
        if temporary.exists():
            temporary.unlink()
        raise


def ensure_deterministic_receipt(path: Path, payload: Mapping[str, Any]) -> dict[str, Any]:
    expected = with_hash_envelope(payload)
    if path.exists():
        observed = validate_hash_envelope(read_json(path, path.name), path.name)
        if observed != expected:
            raise RuntimeError(f"existing {path.name} differs; quarantine the stale run directory")
    else:
        write_json_atomic(path, expected)
    return expected


def _require_lower_sha512(value: object, label: str) -> str:
    if not isinstance(value, str) or len(value) != 128:
        raise RuntimeError(f"{label} is not a SHA-512")
    if any(character not in "0123456789abcdef" for character in value):
        raise RuntimeError(f"{label} is not a lowercase SHA-512")
    return value


def _load_us_inventory(contract: Mapping[str, Any]) -> SourceInventory:
    provenance = read_json(US_CONTENT_RECEIPT, "nClimGrid content receipt")
    if provenance.get("schema_version") != "nclimgrid_daily_content_receipt_v1":
        raise RuntimeError("unexpected nClimGrid content-receipt schema")
    payload = dict(provenance)
    observed_payload_hash = payload.pop("receipt_payload_sha512", None)
    if observed_payload_hash != signature(payload):
        raise RuntimeError("nClimGrid content-receipt hash envelope changed")
    objects = provenance.get("objects")
    if not isinstance(objects, list) or len(objects) != 468:
        raise RuntimeError("nClimGrid content receipt must contain exactly 468 objects")
    if provenance.get("object_records_sha512") != signature(objects):
        raise RuntimeError("nClimGrid object-record hash envelope changed")
    scope = provenance.get("scope")
    if not isinstance(scope, dict) or scope != {
        "start_month": "1981-01",
        "end_month": "2019-12",
        "object_count": 468,
        "content_length_bytes": 27_857_685_556,
    }:
        raise RuntimeError("nClimGrid content-receipt scope changed")
    gates = provenance.get("scientific_use_gates")
    if not isinstance(gates, dict) or any(value is not False for value in gates.values()):
        raise RuntimeError("nClimGrid source receipt unexpectedly opens a use gate")

    panel = contract["us_county"]
    root = PROJECT_ROOT / str(panel["weather_root"])
    records: list[SourceRecord] = []
    expected_periods = list(pd.period_range("1981-01", "2019-12", freq="M").astype(str))
    for expected_period, item in zip(expected_periods, objects, strict=True):
        if not isinstance(item, dict) or item.get("period") != expected_period:
            raise RuntimeError(f"nClimGrid object sequence changed at {expected_period}")
        year, month = (int(value) for value in expected_period.split("-"))
        expected_name = f"ncdd-{year:04d}{month:02d}-grd-scaled.nc"
        if item.get("name") != expected_name:
            raise RuntimeError(f"unexpected nClimGrid filename for {expected_period}")
        identity = item.get("http_identity")
        source_calendar = item.get("calendar")
        if not isinstance(identity, dict) or not isinstance(source_calendar, dict):
            raise RuntimeError(f"incomplete nClimGrid identity for {expected_name}")
        expected_days = calendar.monthrange(year, month)[1]
        expected_calendar = {
            "daily_time_steps": expected_days,
            "start_date": f"{year:04d}-{month:02d}-01",
            "end_date": f"{year:04d}-{month:02d}-{expected_days:02d}",
        }
        if source_calendar != expected_calendar:
            raise RuntimeError(f"nClimGrid calendar identity changed for {expected_name}")
        records.append(
            SourceRecord(
                name=expected_name,
                path=root / expected_name,
                size_bytes=int(identity["content_length"]),
                sha512=_require_lower_sha512(item.get("local_sha512"), expected_name),
                variable="prcp,tavg,tmax,tmin",
                block=f"{year:04d}",
                start_date=expected_calendar["start_date"],
                end_date=expected_calendar["end_date"],
            )
        )
    dataset = provenance.get("dataset")
    if not isinstance(dataset, dict):
        raise RuntimeError("nClimGrid dataset provenance missing")
    return SourceInventory(
        source="nclimgrid",
        root=root,
        provenance_path=US_CONTENT_RECEIPT,
        provenance_sha512=sha512_file(US_CONTENT_RECEIPT),
        source_id=str(panel["weather_source_id"]),
        dataset_doi=str(dataset["dataset_doi"]),
        license=str(dataset["license"]["status"]),
        records=tuple(records),
        declared_file_set_sha512=signature([record.public_identity() for record in records]),
    )


def _load_global_inventory(contract: Mapping[str, Any]) -> SourceInventory:
    try:
        provenance = tomllib.loads(GLOBAL_PROVENANCE.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise RuntimeError("cannot read ISIMIP3a provenance") from error
    if (
        provenance.get("schema_version") != 2
        or provenance.get("input_id") != "daily_climate"
        or provenance.get("variables") != ["pr", "tas", "tasmax", "tasmin"]
        or provenance.get("license") != "CC0-1.0"
    ):
        raise RuntimeError("ISIMIP3a provenance identity changed")
    files = provenance.get("files")
    if not isinstance(files, list) or len(files) != 16:
        raise RuntimeError("ISIMIP3a provenance must contain exactly 16 source files")
    panel = contract["global"]
    root = PROJECT_ROOT / str(panel["weather_root"])
    blocks = ((1981, 1990), (1991, 2000), (2001, 2010), (2011, 2019))
    expected_pairs = [(variable, block) for variable in ("pr", "tas", "tasmax", "tasmin") for block in blocks]
    records: list[SourceRecord] = []
    for item, (variable, (start_year, end_year)) in zip(files, expected_pairs, strict=True):
        if not isinstance(item, dict):
            raise RuntimeError("ISIMIP3a file record is not a table")
        expected_name = (
            f"gswp3-w5e5_obsclim_{variable}_global_daily_"
            f"{start_year:04d}_{end_year:04d}.nc"
        )
        if (
            item.get("name") != expected_name
            or item.get("variable") != variable
            or item.get("years") != f"{start_year:04d}-{end_year:04d}"
        ):
            raise RuntimeError(f"ISIMIP3a file identity changed for {expected_name}")
        records.append(
            SourceRecord(
                name=expected_name,
                path=root / expected_name,
                size_bytes=int(item["size_bytes"]),
                sha512=_require_lower_sha512(item.get("sha512"), expected_name),
                variable=variable,
                block=f"{start_year:04d}_{end_year:04d}",
                start_date=f"{start_year:04d}-01-01",
                end_date=f"{end_year:04d}-12-31",
            )
        )
    checksum_path = root / "SHA512SUMS"
    checksum_rows: dict[str, str] = {}
    for line in checksum_path.read_text(encoding="utf-8").splitlines():
        parts = line.split(maxsplit=1)
        if len(parts) != 2:
            raise RuntimeError("malformed local ISIMIP3a SHA512SUMS")
        checksum_rows[Path(parts[1].strip()).name] = parts[0]
    expected_checksums = {record.name: record.sha512 for record in records}
    if checksum_rows != expected_checksums:
        raise RuntimeError("local ISIMIP3a SHA512SUMS differs from frozen provenance")
    return SourceInventory(
        source="isimip",
        root=root,
        provenance_path=GLOBAL_PROVENANCE,
        provenance_sha512=sha512_file(GLOBAL_PROVENANCE),
        source_id=str(panel["weather_source_id"]),
        dataset_doi=str(provenance["source_doi"]),
        license=str(provenance["license"]),
        records=tuple(records),
        declared_file_set_sha512=signature([record.public_identity() for record in records]),
    )


def load_source_inventory(source: str, contract: Mapping[str, Any]) -> SourceInventory:
    if source == "nclimgrid":
        return _load_us_inventory(contract)
    if source == "isimip":
        return _load_global_inventory(contract)
    raise ValueError(f"unknown source: {source}")


def verify_source_files(inventory: SourceInventory) -> dict[str, Any]:
    if inventory.root.is_symlink() or not inventory.root.is_dir():
        raise RuntimeError(f"source root must be a regular directory: {inventory.root}")
    expected_names = {record.name for record in inventory.records}
    observed_names = {path.name for path in inventory.root.glob("*.nc") if path.is_file()}
    if observed_names != expected_names:
        raise RuntimeError(
            "source NetCDF file set differs: "
            f"missing={sorted(expected_names - observed_names)[:3]}, "
            f"extra={sorted(observed_names - expected_names)[:3]}"
        )
    partials = sorted(path.name for path in inventory.root.glob("*.part"))
    if partials:
        raise RuntimeError(f"source root contains unresolved partial files: {partials[:3]}")
    for record in inventory.records:
        if record.path.is_symlink() or not record.path.is_file():
            raise RuntimeError(f"source object is not a regular file: {record.name}")
        if record.path.stat().st_size != record.size_bytes:
            raise RuntimeError(f"source byte length changed: {record.name}")
    print(f"validating SHA-512 for {len(inventory.records)} {inventory.source} source objects", flush=True)
    with ThreadPoolExecutor(max_workers=min(HASH_WORKERS, len(inventory.records))) as executor:
        observed_hashes = list(executor.map(lambda item: sha512_file(item.path), inventory.records))
    for record, observed in zip(inventory.records, observed_hashes, strict=True):
        if observed != record.sha512:
            raise RuntimeError(f"source SHA-512 changed: {record.name}")
    actual = [
        {
            "name": record.name,
            "size_bytes": record.path.stat().st_size,
            "sha512": observed,
            "variable": record.variable,
            "block": record.block,
            "start_date": record.start_date,
            "end_date": record.end_date,
        }
        for record, observed in zip(inventory.records, observed_hashes, strict=True)
    ]
    actual_signature = signature(actual)
    if actual_signature != inventory.declared_file_set_sha512:
        raise RuntimeError("actual source file-set signature differs from declared identities")
    return {
        "objects": len(actual),
        "bytes": int(sum(item["size_bytes"] for item in actual)),
        "all_sha512_recomputed": True,
        "all_sha512_equal_declared": True,
        "actual_file_set_sha512": actual_signature,
    }


def _finite_minimum(values: np.ndarray) -> float | None:
    finite = values[np.isfinite(values)]
    return None if finite.size == 0 else float(np.min(finite))


def _finite_maximum(values: np.ndarray) -> float | None:
    finite = values[np.isfinite(values)]
    return None if finite.size == 0 else float(np.max(finite))


def _require_daily_dates(dates: object, expected_start: str, expected_end: str) -> pd.DatetimeIndex:
    index = pd.DatetimeIndex(dates)
    expected = pd.date_range(expected_start, expected_end, freq="D")
    if index.tz is not None or index.hasnans or not index.is_normalized:
        raise RuntimeError("source daily dates must be normalized, finite, and timezone-naive")
    if not index.equals(expected):
        raise RuntimeError(
            f"source daily chronology differs from {expected_start} through {expected_end}"
        )
    return index


def aggregate_daily_to_monthly(
    dates: object,
    precipitation_mm_day: object,
    tmin_c: object,
    tmax_c: object,
    latitude: object,
) -> MonthlyCheckpoint:
    """Validate one complete daily block and aggregate without imputation."""
    index = pd.DatetimeIndex(dates)
    if index.empty:
        raise RuntimeError("daily source block is empty")
    index = _require_daily_dates(index, str(index[0].date()), str(index[-1].date()))
    if index[0].day != 1 or index[-1].day != index[-1].days_in_month:
        raise RuntimeError("daily source block must begin and end on complete months")
    try:
        precipitation = np.asarray(precipitation_mm_day, dtype=np.float64)
        minimum = np.asarray(tmin_c, dtype=np.float64)
        maximum = np.asarray(tmax_c, dtype=np.float64)
        lat = np.asarray(latitude, dtype=np.float64)
    except (TypeError, ValueError) as error:
        raise RuntimeError("daily source arrays must be numeric") from error
    if precipitation.shape != minimum.shape or precipitation.shape != maximum.shape:
        raise RuntimeError("daily precipitation/Tmin/Tmax shapes differ")
    if precipitation.ndim != 3 or precipitation.shape[0] != len(index):
        raise RuntimeError("daily arrays must have dimensions time, lat, lon")
    if lat.ndim != 1 or lat.size != precipitation.shape[1] or not np.isfinite(lat).all():
        raise RuntimeError("latitude coordinate does not match the daily source block")
    if np.isinf(precipitation).any() or np.isinf(minimum).any() or np.isinf(maximum).any():
        raise RuntimeError("daily source arrays contain infinities")
    finite_precipitation = np.isfinite(precipitation)
    finite_minimum = np.isfinite(minimum)
    finite_maximum = np.isfinite(maximum)
    if (precipitation[finite_precipitation] < -PRECIPITATION_TOLERANCE).any():
        raise RuntimeError("daily precipitation contains negative finite values")
    precipitation = np.where(
        finite_precipitation,
        np.maximum(precipitation, 0.0),
        np.nan,
    )
    paired_temperature = finite_minimum & finite_maximum
    if (
        maximum[paired_temperature]
        < minimum[paired_temperature] - TEMPERATURE_ORDER_TOLERANCE_C
    ).any():
        raise RuntimeError("daily Tmax is lower than Tmin beyond float tolerance")
    complete = finite_precipitation & finite_minimum & finite_maximum
    safe_minimum = np.where(complete, minimum, 0.0)
    safe_maximum = np.where(complete, maximum, 0.0)
    day_of_year = index.dayofyear.to_numpy(dtype=np.int16)[:, None, None]
    latitude_grid = lat[None, :, None]
    et0 = hargreaves_samani_et0_mm_day(
        safe_minimum,
        safe_maximum,
        latitude_grid,
        day_of_year,
    )
    et0 = np.where(complete, et0, np.nan)

    periods = index.to_period("M")
    unique_periods = periods.unique().sort_values()
    expected_periods = pd.period_range(periods[0], periods[-1], freq="M")
    if not unique_periods.equals(expected_periods):
        raise RuntimeError("daily block has a missing calendar month")
    spatial_shape = precipitation.shape[1:]
    monthly_precipitation = np.full((len(unique_periods), *spatial_shape), np.nan)
    monthly_et0 = np.full_like(monthly_precipitation, np.nan)
    daily_complete_count = np.zeros((len(unique_periods), *spatial_shape), dtype=np.int16)
    calendar_day_count = np.zeros(len(unique_periods), dtype=np.int16)
    for month_index, period in enumerate(unique_periods):
        positions = periods == period
        expected_days = period.days_in_month
        if int(np.count_nonzero(positions)) != expected_days:
            raise RuntimeError(f"daily block has an incomplete source calendar for {period}")
        counts = np.count_nonzero(complete[positions], axis=0)
        valid_month = counts == expected_days
        precipitation_sum = np.sum(np.where(complete[positions], precipitation[positions], 0.0), axis=0)
        et0_sum = np.sum(np.where(complete[positions], et0[positions], 0.0), axis=0)
        monthly_precipitation[month_index] = np.where(valid_month, precipitation_sum, np.nan)
        monthly_et0[month_index] = np.where(valid_month, et0_sum, np.nan)
        daily_complete_count[month_index] = counts
        calendar_day_count[month_index] = expected_days

    audit = {
        "daily_steps": int(len(index)),
        "daily_grid_values": int(precipitation.size),
        "precipitation_missing": int(np.count_nonzero(~finite_precipitation)),
        "tmin_missing": int(np.count_nonzero(~finite_minimum)),
        "tmax_missing": int(np.count_nonzero(~finite_maximum)),
        "complete_triplet_missing": int(np.count_nonzero(~complete)),
        "monthly_grid_values": int(monthly_precipitation.size),
        "monthly_incomplete": int(np.count_nonzero(~np.isfinite(monthly_precipitation))),
        "negative_precipitation_failures": 0,
        "temperature_order_failures": 0,
        "imputed_values": 0,
        "precipitation_mm_day_min": _finite_minimum(precipitation),
        "precipitation_mm_day_max": _finite_maximum(precipitation),
        "tmin_c_min": _finite_minimum(minimum),
        "tmin_c_max": _finite_maximum(minimum),
        "tmax_c_min": _finite_minimum(maximum),
        "tmax_c_max": _finite_maximum(maximum),
        "et0_mm_day_min": _finite_minimum(et0),
        "et0_mm_day_max": _finite_maximum(et0),
    }
    return MonthlyCheckpoint(
        months=unique_periods.to_timestamp(),
        precipitation_mm=monthly_precipitation,
        et0_mm=monthly_et0,
        daily_complete_count=daily_complete_count,
        calendar_day_count=calendar_day_count,
        latitude=lat,
        longitude=np.empty(0, dtype=np.float64),
        audit=audit,
    )


def _validate_spatial_coordinates(
    latitude: np.ndarray,
    longitude: np.ndarray,
    *,
    expected_shape: tuple[int, int],
    latitude_direction: str,
) -> None:
    if latitude.shape != (expected_shape[0],) or longitude.shape != (expected_shape[1],):
        raise RuntimeError("source spatial coordinate lengths changed")
    if not np.isfinite(latitude).all() or not np.isfinite(longitude).all():
        raise RuntimeError("source spatial coordinates must be finite")
    if len(np.unique(latitude)) != len(latitude) or len(np.unique(longitude)) != len(longitude):
        raise RuntimeError("source spatial coordinates must be unique")
    latitude_difference = np.diff(latitude)
    if latitude_direction == "increasing" and not (latitude_difference > 0.0).all():
        raise RuntimeError("source latitude must be strictly increasing")
    if latitude_direction == "decreasing" and not (latitude_difference < 0.0).all():
        raise RuntimeError("source latitude must be strictly decreasing")
    if not (np.diff(longitude) > 0.0).all():
        raise RuntimeError("source longitude must be strictly increasing")


def _validate_nclimgrid_schema(ds: xr.Dataset, record: SourceRecord) -> None:
    if dict(ds.sizes) != {
        "time": calendar.monthrange(int(record.start_date[:4]), int(record.start_date[5:7]))[1],
        "lat": 596,
        "lon": 1385,
    }:
        raise RuntimeError(f"nClimGrid dimensions changed: {record.name}")
    if set(ds.data_vars) != {"prcp", "tavg", "tmax", "tmin"}:
        raise RuntimeError(f"nClimGrid variables changed: {record.name}")
    if ds.attrs.get("title") != "nClimGrid-Daily, Gridded Fields":
        raise RuntimeError(f"nClimGrid title changed: {record.name}")
    if ds.attrs.get("product_version") != "v1-0-0 20220829":
        raise RuntimeError(f"nClimGrid product version changed: {record.name}")
    expected = {
        "prcp": ("precipitation_amount", "millimeter"),
        "tavg": ("air_temperature", "degree_Celsius"),
        "tmax": ("air_temperature", "degree_Celsius"),
        "tmin": ("air_temperature", "degree_Celsius"),
    }
    for variable, (standard_name, units) in expected.items():
        data = ds[variable]
        if (
            data.dims != ("time", "lat", "lon")
            or data.attrs.get("standard_name") != standard_name
            or data.attrs.get("units") != units
            or "24-hour period ending in the early morning" not in str(data.attrs.get("comment", ""))
        ):
            raise RuntimeError(f"nClimGrid schema changed for {variable}: {record.name}")
    if "24-hour period ending in the early morning" not in str(ds.time.attrs.get("comment", "")):
        raise RuntimeError(f"nClimGrid day-label semantics changed: {record.name}")


def process_nclimgrid_year(
    records: Iterable[SourceRecord],
    spatial: SpatialSlice,
) -> MonthlyCheckpoint:
    year_records = list(records)
    if len(year_records) != 12 or len({record.block for record in year_records}) != 1:
        raise RuntimeError("nClimGrid checkpoint block must contain exactly one year")
    monthly_parts: list[MonthlyCheckpoint] = []
    full_latitude: np.ndarray | None = None
    full_longitude: np.ndarray | None = None
    selected_latitude: np.ndarray | None = None
    selected_longitude: np.ndarray | None = None
    for record in year_records:
        with xr.open_dataset(
            record.path,
            engine="h5netcdf",
            decode_times=True,
            mask_and_scale=True,
            cache=False,
        ) as ds:
            _validate_nclimgrid_schema(ds, record)
            dates = _require_daily_dates(ds.time.values, record.start_date, record.end_date)
            latitude = np.asarray(ds.lat.values, dtype=np.float64)
            longitude = np.asarray(ds.lon.values, dtype=np.float64)
            _validate_spatial_coordinates(
                latitude,
                longitude,
                expected_shape=(596, 1385),
                latitude_direction="increasing",
            )
            if full_latitude is None:
                full_latitude, full_longitude = latitude, longitude
            elif not np.array_equal(latitude, full_latitude) or not np.array_equal(longitude, full_longitude):
                raise RuntimeError(f"nClimGrid coordinates changed: {record.name}")
            selected_latitude = latitude[spatial.lat_start : spatial.lat_stop]
            selected_longitude = longitude[spatial.lon_start : spatial.lon_stop]
            selection = {
                "lat": slice(spatial.lat_start, spatial.lat_stop),
                "lon": slice(spatial.lon_start, spatial.lon_stop),
            }
            precipitation = np.asarray(ds.prcp.isel(**selection).values, dtype=np.float64)
            tmin = np.asarray(ds.tmin.isel(**selection).values, dtype=np.float64)
            tmax = np.asarray(ds.tmax.isel(**selection).values, dtype=np.float64)
        part = aggregate_daily_to_monthly(
            dates,
            precipitation,
            tmin,
            tmax,
            selected_latitude,
        )
        monthly_parts.append(
            MonthlyCheckpoint(
                months=part.months,
                precipitation_mm=part.precipitation_mm,
                et0_mm=part.et0_mm,
                daily_complete_count=part.daily_complete_count,
                calendar_day_count=part.calendar_day_count,
                latitude=selected_latitude,
                longitude=selected_longitude,
                audit={**part.audit, "files_schema_validated": 1, "unused_mean_metadata_validated": 1},
            )
        )
    return combine_monthly_checkpoints(monthly_parts)


GLOBAL_STANDARD_NAMES = {
    "pr": "precipitation_flux",
    "tas": "air_temperature",
    "tasmax": "air_temperature",
    "tasmin": "air_temperature",
}
GLOBAL_UNITS = {"pr": "kg m-2 s-1", "tas": "K", "tasmax": "K", "tasmin": "K"}


def _validate_isimip_schema(ds: xr.Dataset, record: SourceRecord) -> None:
    expected_days = len(pd.date_range(record.start_date, record.end_date, freq="D"))
    if dict(ds.sizes) != {"lon": 720, "lat": 360, "time": expected_days}:
        raise RuntimeError(f"ISIMIP dimensions changed: {record.name}")
    if set(ds.data_vars) != {record.variable}:
        raise RuntimeError(f"ISIMIP variable set changed: {record.name}")
    data = ds[record.variable]
    if (
        data.dims != ("time", "lat", "lon")
        or data.attrs.get("standard_name") != GLOBAL_STANDARD_NAMES[record.variable]
        or data.attrs.get("units") != GLOBAL_UNITS[record.variable]
    ):
        raise RuntimeError(f"ISIMIP variable schema changed: {record.name}")
    calendar_name = ds.time.encoding.get("calendar")
    if calendar_name != "proleptic_gregorian":
        raise RuntimeError(f"ISIMIP calendar changed: {record.name}")


def process_isimip_block(
    records: Iterable[SourceRecord],
    spatial: SpatialSlice,
    *,
    target_year: int,
) -> MonthlyCheckpoint:
    block_records = list(records)
    if len(block_records) != 4 or len({record.block for record in block_records}) != 1:
        raise RuntimeError("ISIMIP checkpoint block must contain four aligned variables")
    by_variable = {record.variable: record for record in block_records}
    if set(by_variable) != {"pr", "tas", "tasmax", "tasmin"}:
        raise RuntimeError("ISIMIP block lacks the four locked variables")
    full_latitude: np.ndarray | None = None
    full_longitude: np.ndarray | None = None
    common_dates: pd.DatetimeIndex | None = None
    selected_latitude: np.ndarray | None = None
    selected_longitude: np.ndarray | None = None
    values: dict[str, np.ndarray] = {}
    for variable in ("pr", "tas", "tasmax", "tasmin"):
        record = by_variable[variable]
        with xr.open_dataset(
            record.path,
            engine="h5netcdf",
            decode_times=True,
            mask_and_scale=True,
            cache=False,
        ) as ds:
            _validate_isimip_schema(ds, record)
            source_dates = _require_daily_dates(ds.time.values, record.start_date, record.end_date)
            positions = np.flatnonzero(source_dates.year == target_year)
            expected_year_dates = pd.date_range(
                f"{target_year:04d}-01-01", f"{target_year:04d}-12-31", freq="D"
            )
            if positions.size != len(expected_year_dates) or not source_dates[positions].equals(
                expected_year_dates
            ):
                raise RuntimeError(f"ISIMIP file does not contain complete target year {target_year}")
            time_slice = slice(int(positions[0]), int(positions[-1]) + 1)
            dates = source_dates[time_slice]
            latitude = np.asarray(ds.lat.values, dtype=np.float64)
            longitude = np.asarray(ds.lon.values, dtype=np.float64)
            _validate_spatial_coordinates(
                latitude,
                longitude,
                expected_shape=(360, 720),
                latitude_direction="decreasing",
            )
            expected_latitude = 89.75 - 0.5 * np.arange(360)
            expected_longitude = -179.75 + 0.5 * np.arange(720)
            if not np.array_equal(latitude, expected_latitude) or not np.array_equal(
                longitude, expected_longitude
            ):
                raise RuntimeError(f"ISIMIP 0.5-degree grid coordinates changed: {record.name}")
            if full_latitude is None:
                full_latitude, full_longitude, common_dates = latitude, longitude, dates
            elif (
                not np.array_equal(latitude, full_latitude)
                or not np.array_equal(longitude, full_longitude)
                or not dates.equals(common_dates)
            ):
                raise RuntimeError(f"ISIMIP variable coordinates/times differ: {record.name}")
            selected_latitude = latitude[spatial.lat_start : spatial.lat_stop]
            selected_longitude = longitude[spatial.lon_start : spatial.lon_stop]
            # tas is required and metadata-validated but intentionally not read:
            # Hargreaves Tmean is exactly (tasmin + tasmax) / 2.
            if variable != "tas":
                values[variable] = np.asarray(
                    ds[variable]
                    .isel(
                        time=time_slice,
                        lat=slice(spatial.lat_start, spatial.lat_stop),
                        lon=slice(spatial.lon_start, spatial.lon_stop),
                    )
                    .values,
                    dtype=np.float64,
                )
    assert common_dates is not None and selected_latitude is not None and selected_longitude is not None
    precipitation = values["pr"] * 86_400.0
    tmin = values["tasmin"] - 273.15
    tmax = values["tasmax"] - 273.15
    part = aggregate_daily_to_monthly(
        common_dates,
        precipitation,
        tmin,
        tmax,
        selected_latitude,
    )
    return MonthlyCheckpoint(
        months=part.months,
        precipitation_mm=part.precipitation_mm,
        et0_mm=part.et0_mm,
        daily_complete_count=part.daily_complete_count,
        calendar_day_count=part.calendar_day_count,
        latitude=selected_latitude,
        longitude=selected_longitude,
        audit={**part.audit, "files_schema_validated": 4, "unused_mean_metadata_validated": 1},
    )


AUDIT_SUM_FIELDS = (
    "daily_steps",
    "daily_grid_values",
    "precipitation_missing",
    "tmin_missing",
    "tmax_missing",
    "complete_triplet_missing",
    "monthly_grid_values",
    "monthly_incomplete",
    "negative_precipitation_failures",
    "temperature_order_failures",
    "imputed_values",
    "files_schema_validated",
    "unused_mean_metadata_validated",
)
AUDIT_MIN_FIELDS = (
    "precipitation_mm_day_min",
    "tmin_c_min",
    "tmax_c_min",
    "et0_mm_day_min",
)
AUDIT_MAX_FIELDS = (
    "precipitation_mm_day_max",
    "tmin_c_max",
    "tmax_c_max",
    "et0_mm_day_max",
)


def combine_audits(audits: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    items = list(audits)
    if not items:
        raise RuntimeError("cannot combine an empty audit collection")
    result: dict[str, Any] = {
        field: int(sum(int(item.get(field, 0)) for item in items))
        for field in AUDIT_SUM_FIELDS
    }
    for field in AUDIT_MIN_FIELDS:
        values = [float(item[field]) for item in items if item.get(field) is not None]
        result[field] = None if not values else min(values)
    for field in AUDIT_MAX_FIELDS:
        values = [float(item[field]) for item in items if item.get(field) is not None]
        result[field] = None if not values else max(values)
    return result


def combine_monthly_checkpoints(parts: Iterable[MonthlyCheckpoint]) -> MonthlyCheckpoint:
    checkpoints = list(parts)
    if not checkpoints:
        raise RuntimeError("no monthly checkpoints were supplied")
    latitude = checkpoints[0].latitude
    longitude = checkpoints[0].longitude
    for checkpoint in checkpoints[1:]:
        if not np.array_equal(checkpoint.latitude, latitude) or not np.array_equal(
            checkpoint.longitude, longitude
        ):
            raise RuntimeError("checkpoint spatial coordinates differ")
    months = pd.DatetimeIndex(np.concatenate([part.months.values for part in checkpoints]))
    expected = pd.date_range(months[0], months[-1], freq="MS")
    if not months.equals(expected):
        raise RuntimeError("checkpoint months are not consecutive and unique")
    return MonthlyCheckpoint(
        months=months,
        precipitation_mm=np.concatenate([part.precipitation_mm for part in checkpoints]),
        et0_mm=np.concatenate([part.et0_mm for part in checkpoints]),
        daily_complete_count=np.concatenate([part.daily_complete_count for part in checkpoints]),
        calendar_day_count=np.concatenate([part.calendar_day_count for part in checkpoints]),
        latitude=latitude,
        longitude=longitude,
        audit=combine_audits(part.audit for part in checkpoints),
    )


def write_npz_atomic(path: Path, arrays: Mapping[str, np.ndarray]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    if temporary.exists():
        raise RuntimeError(f"refusing to overwrite unresolved temporary file: {temporary}")
    try:
        with temporary.open("xb") as stream:
            np.savez_compressed(stream, **arrays)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except BaseException:
        if temporary.exists():
            temporary.unlink()
        raise


def checkpoint_payload(
    checkpoint: MonthlyCheckpoint,
    *,
    source: str,
    block: str,
    block_signature: str,
    npz_path: Path,
    npz_sha512: str,
    input_records: Iterable[SourceRecord],
) -> dict[str, Any]:
    records = list(input_records)
    environment = numerical_environment_identity()
    return {
        "schema_version": CHECKPOINT_VERSION,
        "source": source,
        "block": block,
        "block_signature_sha512": block_signature,
        "numerical_environment": environment,
        "numerical_environment_sha512": signature(environment),
        "checkpoint_file": npz_path.name,
        "checkpoint_sha512": npz_sha512,
        "input_file_set_sha512": signature([record.public_identity() for record in records]),
        "input_files": [record.name for record in records],
        "months": int(len(checkpoint.months)),
        "start_month": checkpoint.months[0].strftime("%Y-%m"),
        "end_month": checkpoint.months[-1].strftime("%Y-%m"),
        "shape": list(checkpoint.precipitation_mm.shape),
        "latitude_sha512": coordinate_sha512(checkpoint.latitude),
        "longitude_sha512": coordinate_sha512(checkpoint.longitude),
        "daily_audit": checkpoint.audit,
        "outcomes_read": 0,
        "imputation_allowed": False,
        "scientific_use_gates": {gate: False for gate in FALSE_GATES},
    }


def save_checkpoint(
    checkpoint_dir: Path,
    checkpoint: MonthlyCheckpoint,
    *,
    source: str,
    block: str,
    block_signature: str,
    records: Iterable[SourceRecord],
) -> tuple[MonthlyCheckpoint, dict[str, Any]]:
    npz_path = checkpoint_dir / f"monthly_{block}.npz"
    receipt_path = checkpoint_dir / f"monthly_{block}.receipt.json"
    if npz_path.exists() or receipt_path.exists():
        raise RuntimeError(f"refusing to overwrite incomplete checkpoint pair for {block}")
    write_npz_atomic(
        npz_path,
        {
            "months": checkpoint.months.values.astype("datetime64[D]"),
            "precipitation_mm": checkpoint.precipitation_mm,
            "et0_mm": checkpoint.et0_mm,
            "daily_complete_count": checkpoint.daily_complete_count,
            "calendar_day_count": checkpoint.calendar_day_count,
            "latitude": checkpoint.latitude,
            "longitude": checkpoint.longitude,
        },
    )
    npz_digest = sha512_file(npz_path)
    payload = checkpoint_payload(
        checkpoint,
        source=source,
        block=block,
        block_signature=block_signature,
        npz_path=npz_path,
        npz_sha512=npz_digest,
        input_records=records,
    )
    receipt = with_hash_envelope(payload)
    write_json_atomic(receipt_path, receipt)
    return checkpoint, receipt


def load_checkpoint(
    checkpoint_dir: Path,
    *,
    source: str,
    block: str,
    block_signature: str,
) -> tuple[MonthlyCheckpoint, dict[str, Any]] | None:
    npz_path = checkpoint_dir / f"monthly_{block}.npz"
    receipt_path = checkpoint_dir / f"monthly_{block}.receipt.json"
    if not npz_path.exists() and not receipt_path.exists():
        return None
    if not npz_path.is_file() or not receipt_path.is_file():
        raise RuntimeError(f"incomplete checkpoint pair for {block}")
    receipt = validate_hash_envelope(read_json(receipt_path, receipt_path.name), receipt_path.name)
    if (
        receipt.get("schema_version") != CHECKPOINT_VERSION
        or receipt.get("source") != source
        or receipt.get("block") != block
        or receipt.get("block_signature_sha512") != block_signature
        or receipt.get("checkpoint_file") != npz_path.name
    ):
        raise RuntimeError(f"stale or incompatible checkpoint receipt for {block}")
    current_environment = numerical_environment_identity()
    if (
        receipt.get("numerical_environment") != current_environment
        or receipt.get("numerical_environment_sha512") != signature(current_environment)
    ):
        raise RuntimeError(f"checkpoint numerical environment changed for {block}")
    if (
        receipt.get("outcomes_read") != 0
        or receipt.get("imputation_allowed") is not False
        or receipt.get("scientific_use_gates") != {gate: False for gate in FALSE_GATES}
    ):
        raise RuntimeError(f"checkpoint safety gates changed for {block}")
    if sha512_file(npz_path) != receipt.get("checkpoint_sha512"):
        raise RuntimeError(f"checkpoint content hash changed for {block}")
    try:
        with np.load(npz_path, allow_pickle=False) as archive:
            expected_keys = {
                "months",
                "precipitation_mm",
                "et0_mm",
                "daily_complete_count",
                "calendar_day_count",
                "latitude",
                "longitude",
            }
            if set(archive.files) != expected_keys:
                raise RuntimeError(f"checkpoint arrays changed for {block}")
            checkpoint = MonthlyCheckpoint(
                months=pd.DatetimeIndex(archive["months"]),
                precipitation_mm=np.asarray(archive["precipitation_mm"], dtype=np.float64),
                et0_mm=np.asarray(archive["et0_mm"], dtype=np.float64),
                daily_complete_count=np.asarray(archive["daily_complete_count"], dtype=np.int16),
                calendar_day_count=np.asarray(archive["calendar_day_count"], dtype=np.int16),
                latitude=np.asarray(archive["latitude"], dtype=np.float64),
                longitude=np.asarray(archive["longitude"], dtype=np.float64),
                audit=dict(receipt["daily_audit"]),
            )
    except (OSError, ValueError) as error:
        raise RuntimeError(f"cannot read checkpoint arrays for {block}") from error
    if (
        list(checkpoint.precipitation_mm.shape) != receipt.get("shape")
        or checkpoint.et0_mm.shape != checkpoint.precipitation_mm.shape
        or checkpoint.daily_complete_count.shape != checkpoint.precipitation_mm.shape
        or checkpoint.calendar_day_count.shape != (len(checkpoint.months),)
        or coordinate_sha512(checkpoint.latitude) != receipt.get("latitude_sha512")
        or coordinate_sha512(checkpoint.longitude) != receipt.get("longitude_sha512")
        or checkpoint.months[0].strftime("%Y-%m") != receipt.get("start_month")
        or checkpoint.months[-1].strftime("%Y-%m") != receipt.get("end_month")
    ):
        raise RuntimeError(f"checkpoint structure differs from receipt for {block}")
    if np.isinf(checkpoint.precipitation_mm).any() or np.isinf(checkpoint.et0_mm).any():
        raise RuntimeError(f"checkpoint contains infinities for {block}")
    return checkpoint, receipt


def grouped_source_records(inventory: SourceInventory) -> list[tuple[str, list[SourceRecord]]]:
    if inventory.source == "nclimgrid":
        result: list[tuple[str, list[SourceRecord]]] = []
        for year in range(1981, 2020):
            block = f"{year:04d}"
            records = [record for record in inventory.records if record.block == block]
            if len(records) != 12:
                raise RuntimeError(f"nClimGrid source block is incomplete: {block}")
            result.append((block, records))
        return result
    result = []
    for year in range(1981, 2020):
        block = f"{year:04d}"
        source_block = (
            "1981_1990"
            if year <= 1990
            else "1991_2000"
            if year <= 2000
            else "2001_2010"
            if year <= 2010
            else "2011_2019"
        )
        records = [record for record in inventory.records if record.block == source_block]
        if len(records) != 4:
            raise RuntimeError(f"ISIMIP source block is incomplete: {source_block}")
        result.append((block, records))
    return result


def build_or_resume_checkpoints(
    inventory: SourceInventory,
    spatial: SpatialSlice,
    checkpoint_dir: Path,
    run_signature: str,
) -> tuple[MonthlyCheckpoint, list[dict[str, Any]]]:
    parts: list[MonthlyCheckpoint] = []
    receipts: list[dict[str, Any]] = []
    for block, records in grouped_source_records(inventory):
        block_signature = signature(
            {
                "run_signature_sha512": run_signature,
                "block": block,
                "input_records": [record.public_identity() for record in records],
                "checkpoint_version": CHECKPOINT_VERSION,
            }
        )
        loaded = load_checkpoint(
            checkpoint_dir,
            source=inventory.source,
            block=block,
            block_signature=block_signature,
        )
        if loaded is not None:
            checkpoint, receipt = loaded
            print(f"resumed validated checkpoint {inventory.source} {block}", flush=True)
        else:
            print(f"building checkpoint {inventory.source} {block}", flush=True)
            checkpoint = (
                process_nclimgrid_year(records, spatial)
                if inventory.source == "nclimgrid"
                else process_isimip_block(records, spatial, target_year=int(block))
            )
            checkpoint, receipt = save_checkpoint(
                checkpoint_dir,
                checkpoint,
                source=inventory.source,
                block=block,
                block_signature=block_signature,
                records=records,
            )
        parts.append(checkpoint)
        receipts.append(receipt)
    combined = combine_monthly_checkpoints(parts)
    expected_months = pd.date_range("1981-01-01", "2019-12-01", freq="MS")
    if not combined.months.equals(expected_months):
        raise RuntimeError("combined checkpoints do not span exactly 1981-01 through 2019-12")
    if combined.precipitation_mm.shape[1:] != (spatial.lat_count, spatial.lon_count):
        raise RuntimeError("combined checkpoint shape differs from requested spatial slice")
    return combined, receipts


def code_identities(contract_path: Path) -> dict[str, str]:
    paths = (
        Path(__file__).resolve(),
        PROJECT_ROOT / "scripts/spei_construction_primitives.py",
        PROJECT_ROOT / "scripts/spei_distribution.py",
        PROJECT_ROOT / "scripts/spei_monthly_engine.py",
        PROJECT_ROOT / "scripts/validate_spei_competitor_contract.py",
        contract_path,
    )
    return {str(path.relative_to(PROJECT_ROOT)): sha512_file(path) for path in paths}


def contract_receipt_payload(
    contract: Mapping[str, Any],
    contract_path: Path,
    code_hashes: Mapping[str, str],
    source: str,
    spatial: SpatialSlice,
    run_signature: str,
    numerical_environment: Mapping[str, str],
) -> dict[str, Any]:
    method = contract["method"]
    calibration = contract["calibration"]
    return {
        "schema_version": "spei_contract_receipt_v1",
        "contract_id": contract["contract_id"],
        "contract_path": str(contract_path.relative_to(PROJECT_ROOT)),
        "contract_sha512": code_hashes[str(contract_path.relative_to(PROJECT_ROOT))],
        "algorithm_version": ALGORITHM_VERSION,
        "code_sha512": dict(sorted(code_hashes.items())),
        "source": source,
        "spatial_slice": spatial.as_dict(),
        "run_signature_sha512": run_signature,
        "numerical_environment": dict(sorted(numerical_environment.items())),
        "numerical_environment_sha512": signature(numerical_environment),
        "locked_method": {
            "pet_method": method["pet_method"],
            "tmean_definition": method["tmean_definition"],
            "scales": method["accumulation_scales_months"],
            "accumulation_kernel": method["accumulation_kernel"],
            "distribution": method["distribution"],
            "fit_method": method["fit_method"],
            "cdf_probability_clip_epsilon": method["cdf_probability_clip_epsilon"],
            "calibration_start_year": calibration["start_year"],
            "calibration_end_year": calibration["end_year"],
            "calibration_observations_per_calendar_month": calibration[
                "minimum_years_per_calendar_month"
            ],
            "terminal_holdout_start_year": calibration["terminal_holdout_start_year"],
        },
        "authorization_gates": {gate: False for gate in FALSE_GATES},
        "outcomes_read": 0,
        "full_grid_run": False,
    }


def source_receipt_payload(
    inventory: SourceInventory,
    source_validation: Mapping[str, Any],
    spatial: SpatialSlice,
    run_signature: str,
    monthly: MonthlyCheckpoint,
    checkpoint_receipts: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    receipts = list(checkpoint_receipts)
    expected_days = len(pd.date_range("1981-01-01", "2019-12-31", freq="D"))
    if monthly.audit["daily_steps"] != expected_days:
        raise RuntimeError("daily audit does not cover exactly 14,244 source dates")
    return {
        "schema_version": "spei_source_receipt_v1",
        "source": inventory.source,
        "source_id": inventory.source_id,
        "dataset_doi": inventory.dataset_doi,
        "license": inventory.license,
        "source_root": str(inventory.root.relative_to(PROJECT_ROOT)),
        "provenance_path": str(inventory.provenance_path.relative_to(PROJECT_ROOT)),
        "provenance_sha512": inventory.provenance_sha512,
        "declared_file_set_sha512": inventory.declared_file_set_sha512,
        "source_validation": dict(source_validation),
        "spatial_slice": spatial.as_dict(),
        "latitude": [float(value) for value in monthly.latitude],
        "longitude": [float(value) for value in monthly.longitude],
        "latitude_sha512": coordinate_sha512(monthly.latitude),
        "longitude_sha512": coordinate_sha512(monthly.longitude),
        "run_signature_sha512": run_signature,
        "daily_start": "1981-01-01",
        "daily_end": "2019-12-31",
        "daily_steps_expected": expected_days,
        "monthly_start": "1981-01",
        "monthly_end": "2019-12",
        "monthly_steps_expected": 468,
        "daily_validation_audit": monthly.audit,
        "checkpoint_count": len(receipts),
        "checkpoint_receipts_sha512": signature(receipts),
        "checkpoint_content_sha512": [str(receipt["checkpoint_sha512"]) for receipt in receipts],
        "unit_conversions": (
            {
                "precipitation": "already millimeter per source day",
                "temperature": "already degree_Celsius",
            }
            if inventory.source == "nclimgrid"
            else {
                "precipitation": "kg m-2 s-1 multiplied by exactly 86400 to mm per source day",
                "temperature": "K minus exactly 273.15 to degree_Celsius",
            }
        ),
        "tmean_rule": "arithmetic mean of source Tmin and Tmax; source mean metadata validated but values not used",
        "missing_rule": "a monthly cell is finite only when P, Tmin, and Tmax are finite on every source day",
        "imputed_values": 0,
        "outcomes_read": 0,
        "scientific_role": "bounded_engineering_source_validation_only",
        "scientific_use_gates": {gate: False for gate in FALSE_GATES},
    }


def support_audit(
    source: str,
    monthly: MonthlyCheckpoint,
    result: MonthlySpeiResult,
) -> dict[str, Any]:
    if result.spei.ndim != 4:
        raise RuntimeError("pipeline result must have scale, month, lat, lon dimensions")
    analysis_end = 2019 if source == "nclimgrid" else 2016
    analysis = (result.months.year >= 1982) & (result.months.year <= analysis_end)
    calibration = (result.months.year >= 1982) & (result.months.year <= 2011)
    terminal = (result.months.year >= 2012) & (result.months.year <= analysis_end)
    source_complete = np.isfinite(result.precipitation_mm) & np.isfinite(result.et0_mm)
    complete_cells = np.all(source_complete, axis=0)
    any_complete_cells = np.any(source_complete, axis=0)
    fit_valid = result.fit_status_code == 0
    output: dict[str, Any] = {
        "requested_cells": int(source_complete.shape[1] * source_complete.shape[2]),
        "cells_with_any_complete_month": int(np.count_nonzero(any_complete_cells)),
        "cells_with_all_468_complete_months": int(np.count_nonzero(complete_cells)),
        "complete_month_cell_values": int(np.count_nonzero(source_complete)),
        "incomplete_month_cell_values": int(np.count_nonzero(~source_complete)),
        "analysis_start_year": 1982,
        "analysis_end_year": analysis_end,
        "calibration_months": int(np.count_nonzero(calibration)),
        "terminal_months": int(np.count_nonzero(terminal)),
        "valid_fit_rows": int(np.count_nonzero(fit_valid)),
        "invalid_fit_rows": int(np.count_nonzero(~fit_valid)),
        "cells_with_all_36_valid_fits": int(np.count_nonzero(np.all(fit_valid, axis=(0, 1)))),
        "by_scale": {},
    }
    for scale_index, scale in enumerate(LOCKED_SCALES):
        finite = np.isfinite(result.spei[scale_index])
        output["by_scale"][str(scale)] = {
            "finite_all_month_cell_values": int(np.count_nonzero(finite)),
            "missing_all_month_cell_values": int(np.count_nonzero(~finite)),
            "finite_calibration_month_cell_values": int(np.count_nonzero(finite[calibration])),
            "finite_terminal_month_cell_values": int(np.count_nonzero(finite[terminal])),
            "finite_analysis_month_cell_values": int(np.count_nonzero(finite[analysis])),
            "cells_complete_for_every_analysis_month": int(np.count_nonzero(np.all(finite[analysis], axis=0))),
            "lower_cdf_clips": int(np.count_nonzero(result.cdf_clip_code[scale_index] == -1)),
            "upper_cdf_clips": int(np.count_nonzero(result.cdf_clip_code[scale_index] == 1)),
            "exact_zero_cdf": int(np.count_nonzero(result.cdf_probability[scale_index] == 0.0)),
            "exact_one_cdf": int(np.count_nonzero(result.cdf_probability[scale_index] == 1.0)),
        }
    if output["cells_with_any_complete_month"] == 0:
        raise RuntimeError("bounded chunk has no supported source cell; choose a land/support tile")
    if output["cells_with_all_36_valid_fits"] == 0:
        raise RuntimeError("bounded chunk has no cell with all 36 valid frozen SPEI fits")
    return output


def result_dataset(
    source: str,
    inventory: SourceInventory,
    spatial: SpatialSlice,
    run_signature: str,
    contract_sha512: str,
    source_receipt_sha512: str,
    monthly: MonthlyCheckpoint,
    result: MonthlySpeiResult,
) -> xr.Dataset:
    coordinates = {
        "scale": np.asarray(LOCKED_SCALES, dtype=np.int16),
        "month": result.months.values,
        "calendar_month": np.arange(1, 13, dtype=np.int8),
        "lat": monthly.latitude,
        "lon": monthly.longitude,
    }
    dataset = xr.Dataset(
        data_vars={
            "calendar_day_count": (("month",), monthly.calendar_day_count),
            "daily_complete_count": (
                ("month", "lat", "lon"),
                monthly.daily_complete_count,
            ),
            "precipitation_mm": (("month", "lat", "lon"), result.precipitation_mm),
            "et0_hargreaves_mm": (("month", "lat", "lon"), result.et0_mm),
            "water_balance_mm": (("month", "lat", "lon"), result.water_balance_mm),
            "accumulated_water_balance_mm": (
                ("scale", "month", "lat", "lon"),
                result.accumulated_balance_mm,
            ),
            "glo_cdf_probability": (
                ("scale", "month", "lat", "lon"),
                result.cdf_probability,
            ),
            "spei": (("scale", "month", "lat", "lon"), result.spei),
            "cdf_clip_code": (
                ("scale", "month", "lat", "lon"),
                result.cdf_clip_code,
            ),
            "glo_location_xi_mm": (
                ("scale", "calendar_month", "lat", "lon"),
                result.location_xi_mm,
            ),
            "glo_scale_alpha_mm": (
                ("scale", "calendar_month", "lat", "lon"),
                result.scale_alpha_mm,
            ),
            "glo_shape_kappa": (
                ("scale", "calendar_month", "lat", "lon"),
                result.shape_kappa,
            ),
            "calibration_finite_count": (
                ("scale", "calendar_month", "lat", "lon"),
                result.calibration_finite_count,
            ),
            "fit_status_code": (
                ("scale", "calendar_month", "lat", "lon"),
                result.fit_status_code,
            ),
        },
        coords=coordinates,
        attrs={
            "title": "Bounded native-grid SPEI construction diagnostic",
            "schema_version": "spei_grid_chunk_output_v1",
            "algorithm_version": ALGORITHM_VERSION,
            "source": source,
            "source_id": inventory.source_id,
            "dataset_doi": inventory.dataset_doi,
            "source_license": inventory.license,
            "run_signature_sha512": run_signature,
            "contract_sha512": contract_sha512,
            "source_receipt_sha512": source_receipt_sha512,
            "calibration": "1982-2011 inclusive; 30 observations per calendar month",
            "distribution": "Hosking generalized logistic (SPEI log-Logistic), unbiased PWM",
            "pet": "daily Hargreaves-Samani with FAO-56 extraterrestrial radiation",
            "tmean": "(Tmin + Tmax) / 2; source tavg/tas not used",
            "probability_clip": f"[{CDF_CLIP_EPSILON}, {1.0 - CDF_CLIP_EPSILON}] with observation-level audit",
            "fit_status_codes": json.dumps(FIT_STATUS_LABELS, sort_keys=True),
            "cdf_clip_codes": json.dumps({-9: "missing", -1: "lower", 0: "none", 1: "upper"}, sort_keys=True),
            "scientific_role": "bounded engineering diagnostic only; no crop outcome fit",
            "full_grid_run": "false",
            **{f"gate_{gate}": "false" for gate in FALSE_GATES},
        },
    )
    dataset["lat"].attrs.update(standard_name="latitude", units="degrees_north")
    dataset["lon"].attrs.update(standard_name="longitude", units="degrees_east")
    dataset["month"].attrs.update(long_name="calendar month start")
    dataset["scale"].attrs.update(long_name="right-aligned accumulation scale", units="months")
    dataset["precipitation_mm"].attrs["units"] = "mm month-1"
    dataset["et0_hargreaves_mm"].attrs["units"] = "mm month-1"
    dataset["water_balance_mm"].attrs["units"] = "mm month-1"
    dataset["accumulated_water_balance_mm"].attrs["units"] = "mm"
    dataset["spei"].attrs["units"] = "1"
    dataset["glo_cdf_probability"].attrs["units"] = "1"
    return dataset


def write_netcdf_atomic(path: Path, dataset: xr.Dataset) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    if temporary.exists():
        raise RuntimeError(f"refusing to overwrite unresolved temporary file: {temporary}")
    floating = [name for name, variable in dataset.data_vars.items() if variable.dtype.kind == "f"]
    encoding: dict[str, dict[str, Any]] = {
        name: {"zlib": True, "complevel": 4, "shuffle": True} for name in dataset.data_vars
    }
    for name in floating:
        encoding[name]["_FillValue"] = np.nan
    encoding["month"] = {
        "units": "days since 1981-01-01 00:00:00",
        "calendar": "proleptic_gregorian",
    }
    try:
        dataset.to_netcdf(
            temporary,
            engine="h5netcdf",
            mode="w",
            format="NETCDF4",
            encoding=encoding,
        )
        with temporary.open("rb") as stream:
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except BaseException:
        if temporary.exists():
            temporary.unlink()
        raise


def validate_output_netcdf(
    path: Path,
    *,
    source: str,
    run_signature: str,
    spatial: SpatialSlice,
) -> None:
    with xr.open_dataset(path, engine="h5netcdf", cache=False) as dataset:
        expected_sizes = {
            "scale": 3,
            "month": 468,
            "calendar_month": 12,
            "lat": spatial.lat_count,
            "lon": spatial.lon_count,
        }
        if dict(dataset.sizes) != expected_sizes:
            raise RuntimeError("durable SPEI NetCDF dimensions differ")
        if (
            dataset.attrs.get("schema_version") != "spei_grid_chunk_output_v1"
            or dataset.attrs.get("source") != source
            or dataset.attrs.get("run_signature_sha512") != run_signature
            or dataset.attrs.get("full_grid_run") != "false"
        ):
            raise RuntimeError("durable SPEI NetCDF identity differs")
        for gate in FALSE_GATES:
            if dataset.attrs.get(f"gate_{gate}") != "false":
                raise RuntimeError(f"durable SPEI NetCDF unexpectedly opens {gate}")
        if not pd.DatetimeIndex(dataset.month.values).equals(
            pd.date_range("1981-01-01", "2019-12-01", freq="MS")
        ):
            raise RuntimeError("durable SPEI NetCDF monthly chronology differs")
        if dataset.scale.values.tolist() != [1, 3, 6]:
            raise RuntimeError("durable SPEI NetCDF scale coordinate differs")
        for name, variable in dataset.data_vars.items():
            if variable.dtype.kind == "f" and np.isinf(variable.values).any():
                raise RuntimeError(f"durable SPEI NetCDF contains infinities in {name}")
        for name in ("precipitation_mm", "et0_hargreaves_mm"):
            values = dataset[name].values
            if (values[np.isfinite(values)] < 0.0).any():
                raise RuntimeError(f"durable SPEI NetCDF contains negative values in {name}")
        probability = dataset.glo_cdf_probability.values
        finite_probability = probability[np.isfinite(probability)]
        if ((finite_probability < 0.0) | (finite_probability > 1.0)).any():
            raise RuntimeError("durable SPEI NetCDF has a CDF outside [0, 1]")
        clip_code = dataset.cdf_clip_code.values
        finite_spei = np.isfinite(dataset.spei.values)
        if not np.array_equal(clip_code != -9, finite_spei):
            raise RuntimeError("durable SPEI NetCDF SPEI/clip missingness differs")
        if not np.array_equal(np.isfinite(probability), finite_spei):
            raise RuntimeError("durable SPEI NetCDF SPEI/CDF missingness differs")
        calendar_days = dataset.calendar_day_count.values[:, None, None]
        complete_days = dataset.daily_complete_count.values
        if (complete_days < 0).any() or (complete_days > calendar_days).any():
            raise RuntimeError("durable SPEI NetCDF daily completeness counts are invalid")
        if not np.allclose(
            dataset.water_balance_mm.values,
            dataset.precipitation_mm.values - dataset.et0_hargreaves_mm.values,
            rtol=0.0,
            atol=0.0,
            equal_nan=True,
        ):
            raise RuntimeError("durable SPEI NetCDF water balance identity differs")
        if not np.allclose(
            dataset.accumulated_water_balance_mm.sel(scale=1).values,
            dataset.water_balance_mm.values,
            rtol=0.0,
            atol=0.0,
            equal_nan=True,
        ):
            raise RuntimeError("durable SPEI NetCDF one-month accumulation differs")
        if not set(np.unique(dataset.fit_status_code.values)).issubset(FIT_STATUS_LABELS):
            raise RuntimeError("durable SPEI NetCDF has an unknown fit status")
        if not set(np.unique(dataset.cdf_clip_code.values)).issubset({-9, -1, 0, 1}):
            raise RuntimeError("durable SPEI NetCDF has an unknown CDF clip code")


def relative_or_absolute(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def peak_rss_bytes() -> int:
    maximum = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    return maximum if sys.platform == "darwin" else maximum * 1024


def cpu_seconds() -> tuple[float, float]:
    usage = resource.getrusage(resource.RUSAGE_SELF)
    return float(usage.ru_utime), float(usage.ru_stime)


def verify_completed_run(
    run_dir: Path,
    *,
    source: str,
    run_signature: str,
    spatial: SpatialSlice,
    contract_receipt_path: Path,
    source_file_set_sha512: str,
) -> dict[str, Any] | None:
    output_path = run_dir / "spei_monthly.nc"
    output_receipt_path = run_dir / "output_receipt.json"
    source_receipt_path = run_dir / "source_receipt.json"
    if not output_receipt_path.exists():
        if output_path.exists():
            raise RuntimeError("SPEI output exists without its completion receipt")
        return None
    if not output_path.is_file() or not source_receipt_path.is_file():
        raise RuntimeError("completion receipt exists without source receipt or NetCDF")
    output_receipt = validate_hash_envelope(
        read_json(output_receipt_path, output_receipt_path.name), output_receipt_path.name
    )
    source_receipt = validate_hash_envelope(
        read_json(source_receipt_path, source_receipt_path.name), source_receipt_path.name
    )
    if (
        output_receipt.get("status") != "complete"
        or output_receipt.get("source") != source
        or output_receipt.get("run_signature_sha512") != run_signature
        or source_receipt.get("run_signature_sha512") != run_signature
        or source_receipt.get("declared_file_set_sha512") != source_file_set_sha512
    ):
        raise RuntimeError("existing completed run identity differs")
    if source_receipt.get("scientific_use_gates") != {gate: False for gate in FALSE_GATES}:
        raise RuntimeError("existing source receipt unexpectedly opens a scientific-use gate")
    if output_receipt.get("authorization_gates") != {gate: False for gate in FALSE_GATES}:
        raise RuntimeError("existing output receipt unexpectedly opens an authorization gate")
    if output_receipt.get("output", {}).get("sha512") != sha512_file(output_path):
        raise RuntimeError("existing SPEI output hash differs from completion receipt")
    if output_receipt.get("output", {}).get("size_bytes") != output_path.stat().st_size:
        raise RuntimeError("existing SPEI output byte length differs from completion receipt")
    if output_receipt.get("contract_receipt_sha512") != sha512_file(contract_receipt_path):
        raise RuntimeError("existing contract receipt hash differs from completion receipt")
    if output_receipt.get("source_receipt_sha512") != sha512_file(source_receipt_path):
        raise RuntimeError("existing source receipt hash differs from completion receipt")
    validate_output_netcdf(
        output_path,
        source=source,
        run_signature=run_signature,
        spatial=spatial,
    )
    return output_receipt


def parse_spatial_slice(args: argparse.Namespace, source: str) -> SpatialSlice:
    lat_size, lon_size = (596, 1385) if source == "nclimgrid" else (360, 720)
    values = (args.lat_start, args.lat_count, args.lon_start, args.lon_count)
    if any(type(value) is not int for value in values):
        raise ValueError("spatial slice arguments must be integers")
    if args.lat_start < 0 or args.lon_start < 0 or args.lat_count <= 0 or args.lon_count <= 0:
        raise ValueError("spatial slice starts must be nonnegative and counts positive")
    spatial = SpatialSlice(
        lat_start=args.lat_start,
        lat_stop=args.lat_start + args.lat_count,
        lon_start=args.lon_start,
        lon_stop=args.lon_start + args.lon_count,
    )
    if spatial.lat_stop > lat_size or spatial.lon_stop > lon_size:
        raise ValueError(f"spatial slice exceeds {source} grid {lat_size}x{lon_size}")
    if spatial.cells > MAX_CELLS_PER_CHUNK:
        raise ValueError(
            f"one invocation may contain at most {MAX_CELLS_PER_CHUNK} cells; "
            "use separate spatial chunks"
        )
    if spatial.cells >= lat_size * lon_size:
        raise ValueError("an unchunked full-grid run is forbidden")
    return spatial


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Construct one verified, bounded native-grid SPEI chunk; no outcomes are read."
    )
    parser.add_argument("--source", choices=("nclimgrid", "isimip"), required=True)
    parser.add_argument("--lat-start", type=int, required=True)
    parser.add_argument("--lat-count", type=int, required=True)
    parser.add_argument("--lon-start", type=int, required=True)
    parser.add_argument("--lon-count", type=int, required=True)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    args = parser.parse_args()

    started_utc = datetime.now(UTC)
    wall_start = time.perf_counter()
    user_start, system_start = cpu_seconds()
    spatial = parse_spatial_slice(args, args.source)
    contract_path = args.contract.resolve()
    try:
        contract_relative = contract_path.relative_to(PROJECT_ROOT)
    except ValueError as error:
        raise ValueError("contract must remain inside the project") from error
    if contract_relative != Path("config/spei_competitor_v1.toml"):
        raise ValueError("bounded construction requires the canonical SPEI competitor contract")
    contract = load_contract(contract_path)
    validate_contract(contract, require_local_inputs=True)
    if any(contract.get(gate) is not False for gate in FALSE_GATES):
        raise RuntimeError("every SPEI authorization gate must remain exactly false")

    inventory = load_source_inventory(args.source, contract)
    source_validation = verify_source_files(inventory)
    hashes = code_identities(contract_path)
    numerical_environment = numerical_environment_identity()
    run_components = {
        "algorithm_version": ALGORITHM_VERSION,
        "checkpoint_version": CHECKPOINT_VERSION,
        "source": args.source,
        "source_id": inventory.source_id,
        "source_file_set_sha512": inventory.declared_file_set_sha512,
        "source_provenance_sha512": inventory.provenance_sha512,
        "spatial_slice": spatial.as_dict(),
        "code_sha512": dict(sorted(hashes.items())),
        "numerical_environment": numerical_environment,
        "numerical_environment_sha512": signature(numerical_environment),
        "cdf_clip_epsilon": CDF_CLIP_EPSILON,
        "calibration": "1982-2011",
        "scales": list(LOCKED_SCALES),
        "outcomes_read": 0,
    }
    run_signature = signature(run_components)
    chunk_id = (
        f"{args.source}_lat{spatial.lat_start:04d}-{spatial.lat_stop:04d}_"
        f"lon{spatial.lon_start:04d}-{spatial.lon_stop:04d}"
    )
    output_root = args.output_root.resolve()
    if args.output_root.exists() and args.output_root.is_symlink():
        raise RuntimeError("output root must not be a symbolic link")
    run_dir = output_root / chunk_id
    if run_dir.exists() and run_dir.is_symlink():
        raise RuntimeError("run directory must not be a symbolic link")
    run_dir.mkdir(parents=True, exist_ok=True)
    contract_receipt_path = run_dir / "contract_receipt.json"
    contract_receipt = ensure_deterministic_receipt(
        contract_receipt_path,
        contract_receipt_payload(
            contract,
            contract_path,
            hashes,
            args.source,
            spatial,
            run_signature,
            numerical_environment,
        ),
    )
    completed = verify_completed_run(
        run_dir,
        source=args.source,
        run_signature=run_signature,
        spatial=spatial,
        contract_receipt_path=contract_receipt_path,
        source_file_set_sha512=inventory.declared_file_set_sha512,
    )
    if completed is not None:
        print(
            json.dumps(
                {
                    "status": "resumed_complete",
                    "chunk_id": chunk_id,
                    "output": completed["output"],
                    "original_runtime": completed["runtime"],
                    "support": completed["support"],
                    "source_hashes_revalidated": True,
                    "authorization_gates": completed["authorization_gates"],
                },
                indent=2,
                sort_keys=True,
            )
        )
        return

    checkpoint_dir = run_dir / "checkpoints"
    monthly, checkpoint_receipts = build_or_resume_checkpoints(
        inventory,
        spatial,
        checkpoint_dir,
        run_signature,
    )
    source_receipt_path = run_dir / "source_receipt.json"
    source_receipt = ensure_deterministic_receipt(
        source_receipt_path,
        source_receipt_payload(
            inventory,
            source_validation,
            spatial,
            run_signature,
            monthly,
            checkpoint_receipts,
        ),
    )
    source_receipt_sha512 = sha512_file(source_receipt_path)

    print(f"fitting frozen 1982-2011 calendar-month GLO parameters for {chunk_id}", flush=True)
    result = construct_monthly_spei(
        monthly.months,
        monthly.precipitation_mm,
        monthly.et0_mm,
    )
    support = support_audit(args.source, monthly, result)
    output_path = run_dir / "spei_monthly.nc"
    if output_path.exists():
        raise RuntimeError("refusing to overwrite SPEI NetCDF without a valid completion receipt")
    contract_sha512 = hashes[str(contract_relative)]
    dataset = result_dataset(
        args.source,
        inventory,
        spatial,
        run_signature,
        contract_sha512,
        source_receipt_sha512,
        monthly,
        result,
    )
    write_netcdf_atomic(output_path, dataset)
    dataset.close()
    validate_output_netcdf(
        output_path,
        source=args.source,
        run_signature=run_signature,
        spatial=spatial,
    )

    user_end, system_end = cpu_seconds()
    finished_utc = datetime.now(UTC)
    runtime = {
        "started_utc": started_utc.isoformat(),
        "finished_utc": finished_utc.isoformat(),
        "wall_seconds": time.perf_counter() - wall_start,
        "cpu_user_seconds": user_end - user_start,
        "cpu_system_seconds": system_end - system_start,
        "peak_rss_bytes": peak_rss_bytes(),
    }
    output_details = {
        "path": relative_or_absolute(output_path),
        "size_bytes": output_path.stat().st_size,
        "sha512": sha512_file(output_path),
        "schema_version": "spei_grid_chunk_output_v1",
        "months": 468,
        "start_month": "1981-01",
        "end_month": "2019-12",
        "scales": list(LOCKED_SCALES),
        "spatial_cells": spatial.cells,
    }
    output_receipt_payload = {
        "schema_version": "spei_output_receipt_v1",
        "status": "complete",
        "generated_utc": finished_utc.isoformat(),
        "source": args.source,
        "source_id": inventory.source_id,
        "chunk_id": chunk_id,
        "spatial_slice": spatial.as_dict(),
        "run_signature_sha512": run_signature,
        "run_components": run_components,
        "contract_receipt_sha512": sha512_file(contract_receipt_path),
        "source_receipt_sha512": source_receipt_sha512,
        "output": output_details,
        "runtime": runtime,
        "support": support,
        "daily_source_audit": monthly.audit,
        "construction_audit": result.audit,
        "environment": numerical_environment,
        "environment_sha512": signature(numerical_environment),
        "checkpoint_count": len(checkpoint_receipts),
        "checkpoint_receipts_sha512": signature(checkpoint_receipts),
        "full_grid_run": False,
        "outcome_rows_read": 0,
        "crop_outcome_fit_performed": False,
        "imputed_values": 0,
        "scientific_role": "bounded engineering construction diagnostic only",
        "authorization_gates": {gate: False for gate in FALSE_GATES},
    }
    output_receipt_path = run_dir / "output_receipt.json"
    output_receipt = with_hash_envelope(output_receipt_payload)
    write_json_atomic(output_receipt_path, output_receipt)
    verified = verify_completed_run(
        run_dir,
        source=args.source,
        run_signature=run_signature,
        spatial=spatial,
        contract_receipt_path=contract_receipt_path,
        source_file_set_sha512=inventory.declared_file_set_sha512,
    )
    if verified != output_receipt:
        raise RuntimeError("durable output receipt differs after final verification")
    print(
        json.dumps(
            {
                "status": "complete",
                "chunk_id": chunk_id,
                "output": output_details,
                "runtime": runtime,
                "support": support,
                "authorization_gates": output_receipt["authorization_gates"],
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
