#!/usr/bin/env python3
"""Run a fixed, outcome-blind LOCA2 point pilot under a remote-byte guard."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import tomllib
from pathlib import Path
from typing import Any

import numpy as np
import s3fs
import xarray as xr


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def normalize_longitude(longitude: float, grid: np.ndarray) -> float:
    if float(np.nanmin(grid)) >= 0.0 and longitude < 0.0:
        return longitude % 360.0
    return longitude


def maximum_run(mask: np.ndarray) -> int:
    best = current = 0
    for value in mask.astype(bool):
        current = current + 1 if value else 0
        best = max(best, current)
    return best


def summarize(pr: np.ndarray, tasmin: np.ndarray, tasmax: np.ndarray) -> dict[str, float | int]:
    require(pr.ndim == tasmin.ndim == tasmax.ndim == 1, "pilot arrays must be one dimensional")
    require(len(pr) == len(tasmin) == len(tasmax) and len(pr) > 0, "pilot arrays differ or are empty")
    require(np.isfinite(pr).all() and np.isfinite(tasmin).all() and np.isfinite(tasmax).all(), "pilot arrays contain nonfinite values")
    require((pr >= 0).all(), "negative precipitation in pilot")
    require((tasmax >= tasmin).all(), "tasmax below tasmin in pilot")
    rolling5 = np.convolve(pr, np.ones(5), mode="valid") if len(pr) >= 5 else np.array([np.nan])
    return {
        "days": int(len(pr)),
        "precipitation_total_mm": float(pr.sum()),
        "wet_days_ge_1mm": int((pr >= 1.0).sum()),
        "maximum_consecutive_dry_days_lt_1mm": maximum_run(pr < 1.0),
        "rx1day_mm": float(pr.max()),
        "rx5day_mm": float(np.nanmax(rolling5)),
        "mean_tasmin_c": float(tasmin.mean()),
        "mean_tasmax_c": float(tasmax.mean()),
        "maximum_tasmax_c": float(tasmax.max()),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    config = tomllib.loads(args.config.read_text())
    root = Path(__file__).resolve().parents[2]
    daily_path = root / config["outputs"]["daily_csv"]
    receipt_path = root / config["outputs"]["receipt"]
    require(not daily_path.exists(), "fresh daily output required")
    require(not receipt_path.exists(), "fresh receipt required")
    require(config["selection"]["outcome_data_read"] is False, "pilot must remain outcome blind")

    fs = s3fs.S3FileSystem(
        anon=True,
        client_kwargs={"endpoint_url": config["source"]["endpoint_url"]},
    )
    store = config["source"]["store"]
    ds = xr.open_zarr(fs.get_mapper(store), consolidated=True, chunks=None)
    for variable in config["source"]["variables"]:
        require(variable in ds, f"missing variable: {variable}")
    require(ds["pr"].attrs.get("LOCA2_version") == config["source"]["precipitation_version"], "precipitation version differs")

    mask = (
        (ds.source_id.values == config["source"]["source_id"])
        & (ds.experiment_id.values == config["source"]["experiment_id"])
        & (ds.variant_label.values == config["source"]["variant_label"])
    )
    matches = np.flatnonzero(mask)
    require(len(matches) == 1, "pilot ensemble identity is not unique")
    ensemble_index = int(matches[0])
    target_lon = normalize_longitude(float(config["selection"]["longitude"]), ds.lon.values)
    lat_index = int(np.argmin(np.abs(ds.lat.values - float(config["selection"]["latitude"]))))
    lon_index = int(np.argmin(np.abs(ds.lon.values - target_lon)))
    start = np.datetime64(config["selection"]["start_date"])
    end = np.datetime64(config["selection"]["end_date"])
    time_indices = np.flatnonzero((ds.time.values >= start) & (ds.time.values <= end))
    require(len(time_indices) > 0, "pilot time window has no observations")

    chunk_shape = ds["pr"].encoding["chunks"]
    time_chunks = sorted({int(index // chunk_shape[1]) for index in time_indices})
    require(len(time_chunks) == 1, "pilot must use one remote time chunk")
    lat_chunk = lat_index // chunk_shape[2]
    lon_chunk = lon_index // chunk_shape[3]
    chunk_records = []
    for variable in config["source"]["variables"]:
        variable_chunks = ds[variable].encoding["chunks"]
        require(tuple(variable_chunks) == tuple(chunk_shape), "pilot variables use different chunk shapes")
        key = f"{variable}/{ensemble_index}.{time_chunks[0]}.{lat_chunk}.{lon_chunk}"
        info = fs.info(f"{store}/{key}")
        chunk_records.append({"variable": variable, "key": key, "compressed_bytes": int(info["size"])})
    remote_bytes = sum(item["compressed_bytes"] for item in chunk_records)
    maximum_bytes = int(config["resources"]["maximum_remote_chunk_mib"]) * 1024**2
    require(remote_bytes <= maximum_bytes, "pilot remote chunks exceed byte guard")

    point = ds[list(config["source"]["variables"])].isel(
        ensemble=ensemble_index,
        lat=lat_index,
        lon=lon_index,
    ).sel(time=slice(str(start), str(end))).load()
    pr = point.pr.values.astype(float)
    tasmin = point.tasmin.values.astype(float)
    tasmax = point.tasmax.values.astype(float)
    metrics = summarize(pr, tasmin, tasmax)

    daily_path.parent.mkdir(parents=True, exist_ok=True)
    with daily_path.open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["date", "pr_mm", "tasmin_c", "tasmax_c"])
        for date, p, tmin, tmax in zip(point.time.values, pr, tasmin, tasmax, strict=True):
            writer.writerow([str(np.datetime_as_string(date, unit="D")), f"{p:.8g}", f"{tmin:.8g}", f"{tmax:.8g}"])

    receipt = {
        "schema": "loca2_us_bounded_daily_point_pilot/v1",
        "status": "pass",
        "role": "access_engineering_only_not_county_average_or_crop_season",
        "config": {"path": str(args.config), "sha256": sha256(args.config)},
        "source": {
            "store": store,
            "endpoint_url": config["source"]["endpoint_url"],
            "LOCA2_precipitation_version": ds["pr"].attrs["LOCA2_version"],
            "source_id": str(ds.source_id.values[ensemble_index]),
            "experiment_id": str(ds.experiment_id.values[ensemble_index]),
            "variant_label": str(ds.variant_label.values[ensemble_index]),
            "ensemble_index": ensemble_index,
            "remote_chunks": chunk_records,
            "remote_chunk_bytes_upper_bound": remote_bytes,
            "remote_chunk_mib_upper_bound": remote_bytes / 1024**2,
        },
        "selection": {
            **config["selection"],
            "selected_latitude": float(ds.lat.values[lat_index]),
            "selected_longitude_native": float(ds.lon.values[lon_index]),
            "selected_longitude_degrees_east": float(ds.lon.values[lon_index]),
            "lat_index": lat_index,
            "lon_index": lon_index,
        },
        "metrics": metrics,
        "daily_output": {"path": str(daily_path.relative_to(root)), "sha256": sha256(daily_path), "bytes": daily_path.stat().st_size},
        "claim_gates": {
            "access_engineering": True,
            "county_average": False,
            "crop_season_feature": False,
            "historical_validation": False,
            "outcome_response": False,
            "causal_damage": False,
            "SCC": False,
        },
    }
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": "pass", "remote_chunk_mib": receipt["source"]["remote_chunk_mib_upper_bound"], "metrics": metrics}, indent=2))


if __name__ == "__main__":
    main()
