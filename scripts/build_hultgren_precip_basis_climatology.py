#!/usr/bin/env python3
"""Build rainfed/irrigated maize precipitation-basis climatologies."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

ROOT = Path(__file__).resolve().parents[1]

import sys
sys.path.insert(0, str(ROOT / "scripts"))

from build_hultgren_grid_weather_basis import crop_month_keys, load_support

EXPECTED = {
    "gswp3-w5e5_obsclim_pr_global_daily_1981_1990.nc": "c2b0688e59196088a1eaeac6fdc25b0bf1419f78c8662e9c21038c63b58aa6c40df5f22cc723d0ad9e24104a081bd215b9760f9003f0fc557b947341dc2d03f2",
    "gswp3-w5e5_obsclim_pr_global_daily_1991_2000.nc": "48daa05dbac176127e34e70fb6149e39f259695928276f4c968d01d60f4e1e0a0a6f1978734a0425f9fcd1012370dd6f8c3f356ff4798d265f4349a5d5d660c6",
    "gswp3-w5e5_obsclim_pr_global_daily_2001_2010.nc": "5208a595e7f7ed16d88588651313ee4415bb50a96f5592e50d1902a86943fdd1d3f7913ca2149d5f6a0eee5eef3c9198e85ebb112fccf12116011b1db466c8c4",
}
FEATURES = [f"prcp_poly_{power}_bin{phase}" for power in (1, 2) for phase in (1, 2, 3)]


def digest(path: Path, algorithm: str = "sha256") -> str:
    value = hashlib.new(algorithm)
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def phase_basis(monthly_rain: np.ndarray) -> np.ndarray:
    require(monthly_rain.ndim == 1 and 4 <= len(monthly_rain) <= 10, "crop-season rain shape differs")
    require(np.isfinite(monthly_rain).all() and np.all(monthly_rain >= 0.0), "invalid crop-season rain")
    slices = (slice(0, 1), slice(1, 4), slice(4, None))
    linear = [float(monthly_rain[selected].sum()) for selected in slices]
    squared = [float(np.square(monthly_rain[selected]).sum()) for selected in slices]
    return np.asarray([*linear, *squared], dtype=np.float64)


def stream_monthly(paths: list[Path], support: pd.DataFrame) -> tuple[pd.DatetimeIndex, np.ndarray, dict[str, int]]:
    months = pd.date_range("1981-01-01", "2010-12-01", freq="MS")
    rain = np.zeros((len(months), len(support)), dtype=np.float64)
    counts = np.zeros((len(months), len(support)), dtype=np.int16)
    flat = support.native_lat_index.to_numpy(dtype=np.int64) * 720 + support.native_lon_index.to_numpy(dtype=np.int64)
    daily_steps = 0
    missing_pairs = 0
    for path in sorted(paths):
        with xr.open_dataset(path, engine="h5netcdf", decode_times=True, cache=False) as dataset:
            require(dataset.pr.dims == ("time", "lat", "lon") and dataset.pr.attrs.get("units") == "kg m-2 s-1", "precipitation schema differs")
            require(np.array_equal(dataset.lat.values, 89.75 - 0.5 * np.arange(360)), "latitude grid differs")
            require(np.array_equal(dataset.lon.values, -179.75 + 0.5 * np.arange(720)), "longitude grid differs")
            dates = pd.DatetimeIndex(dataset.time.values).normalize()
            expected = pd.date_range(dates[0], dates[-1], freq="D")
            require(dates.equals(expected), "daily chronology differs")
            for position, day in enumerate(dates):
                daily = np.asarray(dataset.pr.isel(time=position).values, dtype=np.float64).reshape(-1)[flat] * 86_400.0
                complete = np.isfinite(daily)
                missing_pairs += int(np.count_nonzero(~complete))
                require(not np.any(daily[complete] < -1e-10), "negative precipitation")
                month_index = (int(day.year) - 1981) * 12 + int(day.month) - 1
                rain[month_index, complete] += np.maximum(daily[complete], 0.0)
                counts[month_index, complete] += 1
            daily_steps += len(dates)
    expected_counts = months.days_in_month.to_numpy(dtype=np.int16)[:, None]
    require(np.array_equal(counts, np.broadcast_to(expected_counts, counts.shape)), "incomplete support cell-month")
    return months, rain, {"daily_steps": daily_steps, "missing_daily_cell_pairs": missing_pairs}


def summarize_regime(
    regime: str, support: pd.DataFrame, union_lookup: dict[tuple[int, int], int],
    months: pd.DatetimeIndex, rain: np.ndarray,
) -> pd.DataFrame:
    month_lookup = {(int(value.year), int(value.month)): index for index, value in enumerate(months)}
    records = []
    for row in support.itertuples(index=False):
        union_index = union_lookup[(int(row.native_lat_index), int(row.native_lon_index))]
        yearly = []
        for harvest_year in range(1982, 2011):
            keys = crop_month_keys(harvest_year, int(row.plant_month), int(row.harvest_month))
            indices = [month_lookup[key] for key in keys]
            yearly.append(phase_basis(rain[indices, union_index]))
        matrix = np.stack(yearly)
        values = {
            "regime": regime,
            "native_lat_index": int(row.native_lat_index),
            "native_lon_index": int(row.native_lon_index),
            "latitude": float(row.latitude),
            "longitude": float(row.longitude),
            "plant_month": int(row.plant_month),
            "harvest_month": int(row.harvest_month),
            "season_months": int(row.season_months),
            "mirca_area_ha": float(row.mirca_area_ha),
            "complete_harvest_years": int(matrix.shape[0]),
        }
        values.update({feature: float(matrix[:, index].mean()) for index, feature in enumerate(FEATURES)})
        records.append(values)
    output = pd.DataFrame(records)
    require(len(output) == len(support) and np.isfinite(output[FEATURES].to_numpy()).all(), f"{regime} basis invalid")
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pr", action="append", type=Path, required=True)
    parser.add_argument("--rainfed-calendar", type=Path, required=True)
    parser.add_argument("--rainfed-area", type=Path, required=True)
    parser.add_argument("--irrigated-calendar", type=Path, required=True)
    parser.add_argument("--irrigated-area", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists() and not args.receipt.exists(), "fresh outputs required")
    require(len(args.pr) == 3 and {path.name for path in args.pr} == set(EXPECTED), "three frozen precipitation decades required")
    for path in args.pr:
        require(digest(path, "sha512") == EXPECTED[path.name], f"precipitation source hash differs: {path.name}")

    rainfed, rainfed_audit = load_support(args.rainfed_calendar, args.rainfed_area)
    irrigated, irrigated_audit = load_support(args.irrigated_calendar, args.irrigated_area)
    union = pd.concat([rainfed[["native_lat_index", "native_lon_index"]], irrigated[["native_lat_index", "native_lon_index"]]])
    union = union.drop_duplicates().sort_values(["native_lat_index", "native_lon_index"]).reset_index(drop=True)
    months, rain, stream_audit = stream_monthly(args.pr, union)
    lookup = {(int(row.native_lat_index), int(row.native_lon_index)): index for index, row in union.iterrows()}
    output = pd.concat([
        summarize_regime("rainfed", rainfed, lookup, months, rain),
        summarize_regime("irrigated", irrigated, lookup, months, rain),
    ], ignore_index=True)
    require(not output.duplicated(["regime", "native_lat_index", "native_lon_index"]).any(), "duplicate regime-cell output")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    output.to_parquet(args.output, index=False)
    require(args.output.stat().st_size < 64 * 2**20, "output exceeds 64 MiB owned-output budget")

    result = {
        "schema": "hultgren_precip_basis_climatology/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "complete_historical_precipitation_basis_not_response_damage_or_scc",
        "source_period": [1981, 2010],
        "harvest_years": [1982, 2010],
        "sources": [{"path": str(path), "bytes": path.stat().st_size, "sha512": digest(path, "sha512")} for path in sorted(args.pr)],
        "support_sources": {
            "rainfed_calendar": {"path": str(args.rainfed_calendar), "sha256": digest(args.rainfed_calendar)},
            "rainfed_area": {"path": str(args.rainfed_area), "sha256": digest(args.rainfed_area)},
            "irrigated_calendar": {"path": str(args.irrigated_calendar), "sha256": digest(args.irrigated_calendar)},
            "irrigated_area": {"path": str(args.irrigated_area), "sha256": digest(args.irrigated_area)},
        },
        "support": {
            "union_cells": int(len(union)), "rainfed_cells": int(len(rainfed)), "irrigated_cells": int(len(irrigated)),
            "output_rows": int(len(output)), "rainfed": rainfed_audit, "irrigated": irrigated_audit, **stream_audit,
        },
        "definition": "mean across 29 complete 1982-2010 crop harvest years of three phase precipitation totals and sums of squared monthly precipitation",
        "features": FEATURES,
        "output": {"path": str(args.output), "bytes": args.output.stat().st_size, "sha256": digest(args.output)},
        "limitations": [
            "GSWP3-W5E5 and GGCMI/MIRCA are alternative transport products, not the authors' GMFD/SAGE administrative inputs.",
            "This is a fixed historical precipitation basis; it contains no marginal pulse and holds within-season shares fixed in the quantity benchmark.",
            "No crop response, damage, or SCC gate is opened.",
        ],
        "claim_gates": {"precipitation_basis_input": True, "response": False, "damage_or_scc": False},
        "implementation": {"path": str(Path(__file__).resolve().relative_to(ROOT)), "sha256": digest(Path(__file__).resolve())},
    }
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "support": result["support"], "output": result["output"]}, indent=2))


if __name__ == "__main__":
    main()
