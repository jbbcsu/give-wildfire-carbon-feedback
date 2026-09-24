#!/usr/bin/env python3
"""Build a bounded 1981--2010 annual-precipitation baseline on maize cells."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

ROOT = Path(__file__).resolve().parents[1]
KEYS = ["native_lat_index", "native_lon_index"]
EXPECTED = {
    "gswp3-w5e5_obsclim_pr_global_daily_1981_1990.nc": "c2b0688e59196088a1eaeac6fdc25b0bf1419f78c8662e9c21038c63b58aa6c40df5f22cc723d0ad9e24104a081bd215b9760f9003f0fc557b947341dc2d03f2",
    "gswp3-w5e5_obsclim_pr_global_daily_1991_2000.nc": "48daa05dbac176127e34e70fb6149e39f259695928276f4c968d01d60f4e1e0a0a6f1978734a0425f9fcd1012370dd6f8c3f356ff4798d265f4349a5d5d660c6",
    "gswp3-w5e5_obsclim_pr_global_daily_2001_2010.nc": "5208a595e7f7ed16d88588651313ee4415bb50a96f5592e50d1902a86943fdd1d3f7913ca2149d5f6a0eee5eef3c9198e85ebb112fccf12116011b1db466c8c4",
}


def digest(path: Path, algorithm: str = "sha256") -> str:
    value = hashlib.new(algorithm)
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def summarize_annual(annual: np.ndarray) -> dict[str, np.ndarray]:
    require(annual.ndim == 2 and annual.shape[0] >= 2, "annual matrix differs")
    require(np.isfinite(annual).all() and np.all(annual >= 0.0), "invalid annual precipitation")
    return {
        "annual_precip_mean_mm": annual.mean(axis=0),
        "annual_precip_sd_mm": annual.std(axis=0, ddof=1),
        "annual_precip_min_mm": annual.min(axis=0),
        "annual_precip_max_mm": annual.max(axis=0),
    }


def read_decade(path: Path, flat: np.ndarray) -> tuple[list[int], list[np.ndarray], int]:
    years: list[int] = []
    totals: list[np.ndarray] = []
    missing_pairs = 0
    with xr.open_dataset(path, engine="h5netcdf", decode_times=True, cache=False) as dataset:
        require("pr" in dataset and dataset.pr.dims == ("time", "lat", "lon"), "precipitation schema changed")
        require(dataset.pr.attrs.get("units") == "kg m-2 s-1", "precipitation units changed")
        require(np.array_equal(dataset.lat.values, 89.75 - 0.5 * np.arange(360)), "latitude grid changed")
        require(np.array_equal(dataset.lon.values, -179.75 + 0.5 * np.arange(720)), "longitude grid changed")
        dates = pd.DatetimeIndex(dataset.time.values).normalize()
        require(dates.is_monotonic_increasing and not dates.duplicated().any(), "daily chronology invalid")
        expected_dates = pd.date_range(dates[0], dates[-1], freq="D")
        require(dates.equals(expected_dates) and dates[0].month == dates[0].day == 1 and dates[-1].month == 12 and dates[-1].day == 31, "decade is not complete daily years")
        current_year = int(dates[0].year)
        total = np.zeros(len(flat), dtype=np.float64)
        count = np.zeros(len(flat), dtype=np.int16)
        for position, day in enumerate(dates):
            if int(day.year) != current_year:
                expected_days = 366 if pd.Timestamp(current_year, 12, 31).dayofyear == 366 else 365
                require(np.all(count == expected_days), f"incomplete crop-cell year {current_year}")
                years.append(current_year); totals.append(total)
                current_year = int(day.year)
                total = np.zeros(len(flat), dtype=np.float64)
                count = np.zeros(len(flat), dtype=np.int16)
            daily = np.asarray(dataset.pr.isel(time=position).values, dtype=np.float64).reshape(-1)[flat] * 86_400.0
            complete = np.isfinite(daily)
            missing_pairs += int(np.count_nonzero(~complete))
            require(not np.any(daily[complete] < -1e-10), "negative precipitation on crop support")
            total[complete] += np.maximum(daily[complete], 0.0)
            count[complete] += 1
        expected_days = 366 if pd.Timestamp(current_year, 12, 31).dayofyear == 366 else 365
        require(np.all(count == expected_days), f"incomplete crop-cell year {current_year}")
        years.append(current_year); totals.append(total)
    return years, totals, missing_pairs


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pr", action="append", type=Path, required=True)
    parser.add_argument("--weights", type=Path, required=True)
    parser.add_argument("--weights-receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists() and not args.receipt.exists(), "fresh outputs required")
    require(len(args.pr) == 3 and {path.name for path in args.pr} == set(EXPECTED), "three frozen precipitation decades required")
    for path in args.pr:
        require(digest(path, "sha512") == EXPECTED[path.name], f"precipitation source hash differs: {path.name}")

    weight_receipt = json.loads(args.weights_receipt.read_text(encoding="utf-8"))
    require(weight_receipt["schema"] == "hultgren_country_cell_maize_value_weights_common_price/v1", "weight receipt schema differs")
    require(weight_receipt["output"]["sha256"] == digest(args.weights), "weight file hash differs")
    weights = pd.read_parquet(args.weights, columns=KEYS).drop_duplicates().sort_values(KEYS).reset_index(drop=True)
    require(not weights.empty and not weights.duplicated(KEYS).any(), "cell support invalid")
    lat_index = weights.native_lat_index.to_numpy(dtype=np.int64)
    lon_index = weights.native_lon_index.to_numpy(dtype=np.int64)
    require(np.all((0 <= lat_index) & (lat_index < 360)) and np.all((0 <= lon_index) & (lon_index < 720)), "cell index outside climate grid")
    flat = lat_index * 720 + lon_index

    years: list[int] = []
    totals: list[np.ndarray] = []
    missing_pairs = 0
    for path in sorted(args.pr):
        decade_years, decade_totals, decade_missing = read_decade(path, flat)
        years.extend(decade_years); totals.extend(decade_totals); missing_pairs += decade_missing
    require(years == list(range(1981, 2011)), "source years do not form 1981-2010")
    annual = np.stack(totals)
    summary = summarize_annual(annual)
    output = weights.copy()
    output["latitude"] = 89.75 - 0.5 * lat_index
    output["longitude"] = -179.75 + 0.5 * lon_index
    output["complete_years"] = annual.shape[0]
    for name, values in summary.items():
        output[name] = values
    args.output.parent.mkdir(parents=True, exist_ok=True)
    output.to_parquet(args.output, index=False)
    require(args.output.stat().st_size < 64 * 2**20, "output exceeds 64 MiB owned-output budget")

    result = {
        "schema": "hultgren_cell_annual_precip_climatology/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "validated_cell_annual_precipitation_baseline_not_response_damage_or_scc",
        "period": [1981, 2010],
        "definition": "arithmetic mean of 30 complete calendar-year precipitation totals at each represented maize cell",
        "sources": [{"path": str(path), "bytes": path.stat().st_size, "sha512": digest(path, "sha512")} for path in sorted(args.pr)],
        "weights": {"path": str(args.weights), "sha256": digest(args.weights), "receipt": str(args.weights_receipt), "receipt_sha256": digest(args.weights_receipt)},
        "support": {
            "unique_cells": int(len(output)), "years": len(years),
            "daily_steps": int(sum(366 if pd.Timestamp(year, 12, 31).dayofyear == 366 else 365 for year in years)),
            "missing_daily_cell_pairs": missing_pairs,
            "minimum_mean_annual_precip_mm": float(output.annual_precip_mean_mm.min()),
            "maximum_mean_annual_precip_mm": float(output.annual_precip_mean_mm.max()),
            "zero_mean_annual_precip_cells": int(output.annual_precip_mean_mm.eq(0.0).sum()),
        },
        "output": {"path": str(args.output), "bytes": args.output.stat().st_size, "sha256": digest(args.output)},
        "limitations": [
            "This is a GSWP3-W5E5 crop-cell climatology, not the source PEEPS country mask or the authors' GMFD product.",
            "Zero-rainfall cells are retained and counted but must be excluded from proportional scaling with explicit production/value accounting.",
            "It supplies a positive annual baseline for a uniform-absolute-change quantity benchmark only.",
            "It does not represent marginal precipitation, yield response, damage, or SCC.",
        ],
        "claim_gates": {"annual_baseline_input": True, "response": False, "damage_or_scc": False},
        "implementation": {"path": str(Path(__file__).resolve().relative_to(ROOT)), "sha256": digest(Path(__file__).resolve())},
    }
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "support": result["support"], "output": result["output"]}, indent=2))


if __name__ == "__main__":
    main()
