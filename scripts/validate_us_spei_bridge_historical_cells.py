#!/usr/bin/env python3
"""Independently validate the exact 11-cell historical SPEI extension."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import xarray as xr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from spei_construction_primitives import hargreaves_samani_et0_mm_day  # noqa: E402
from spei_monthly_engine import construct_monthly_spei  # noqa: E402

ARRAYS = {
    "precipitation_mm": "precipitation_mm", "et0_hargreaves_mm": "et0_mm",
    "water_balance_mm": "water_balance_mm", "accumulated_water_balance_mm": "accumulated_balance_mm",
    "glo_cdf_probability": "cdf_probability", "spei": "spei", "cdf_clip_code": "cdf_clip_code",
    "glo_location_xi_mm": "location_xi_mm", "glo_scale_alpha_mm": "scale_alpha_mm",
    "glo_shape_kappa": "shape_kappa", "calibration_finite_count": "calibration_finite_count",
    "fit_status_code": "fit_status_code",
}
SENTINELS = ("1981-01", "1999-07", "2011-10", "2019-12")


def digest(path: Path, algorithm: str = "sha256") -> str:
    value = hashlib.new(algorithm)
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def check(condition: bool, label: str, checks: list[str]) -> None:
    if not condition:
        raise ValueError(label)
    checks.append(label)


def raw_month(record_by_name: dict[str, dict], period: str, cells: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    year, month = (int(item) for item in period.split("-"))
    block = next(value["block"] for value in record_by_name.values()
                 if value["start_date"] <= f"{year}-01-01" <= value["end_date"])
    records = {value["variable"]: value for value in record_by_name.values() if value["block"] == block}
    ii = xr.DataArray(cells.native_lat_index.to_numpy(dtype=np.int64), dims="cell")
    jj = xr.DataArray(cells.native_lon_index.to_numpy(dtype=np.int64), dims="cell")
    arrays, dates = {}, None
    for variable in ("pr", "tasmin", "tasmax"):
        record = records[variable]
        path = ROOT / "data/raw/isimip3a_gswp3_w5e5_v1_3" / record["name"]
        check_size = path.stat().st_size == record["size_bytes"]
        if not check_size:
            raise ValueError(f"raw source size changed: {record['name']}")
        with xr.open_dataset(path, engine="h5netcdf", decode_times=True, mask_and_scale=True, cache=False) as dataset:
            source_dates = pd.DatetimeIndex(dataset.time.values).normalize()
            selected = np.flatnonzero((source_dates.year == year) & (source_dates.month == month))
            if dates is None:
                dates = source_dates[selected]
            elif not source_dates[selected].equals(dates):
                raise ValueError("sentinel chronology differs")
            arrays[variable] = np.asarray(dataset[variable].isel(time=selected, lat=ii, lon=jj).values,
                                          dtype=np.float64)
    complete = np.isfinite(arrays["pr"]) & np.isfinite(arrays["tasmin"]) & np.isfinite(arrays["tasmax"])
    if not complete.all():
        raise ValueError("sentinel raw triplet incomplete")
    precipitation = np.sum(np.maximum(arrays["pr"]*86400.0, 0), axis=0)
    day_of_year = dates.dayofyear.to_numpy(dtype=np.int16)[:, None]
    et0 = hargreaves_samani_et0_mm_day(arrays["tasmin"]-273.15, arrays["tasmax"]-273.15,
                                       cells.latitude.to_numpy(dtype=np.float64)[None, :], day_of_year).sum(axis=0)
    return precipitation, et0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--resource", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.result = args.result if args.result.is_absolute() else ROOT / args.result
    args.resource = args.resource if args.resource.is_absolute() else ROOT / args.resource
    args.output = args.output if args.output.is_absolute() else ROOT / args.output
    if args.output.exists():
        raise ValueError("fresh validation output required")
    result = json.loads(args.result.read_text())
    resource = json.loads(args.resource.read_text())
    checks: list[str] = []
    check(result["schema"] == "us_spei_bridge_historical_cells_result_v1", "result schema", checks)
    check(result["status"] == "completed_pending_independent_validation", "result status", checks)
    check(result["cells"] == 11 and result["months"] == 468 and result["fits"] == 396, "result dimensions", checks)
    check(not any(result["gates"].values()), "all result gates closed", checks)
    check(resource["status"] == "completed" and resource["returncode"] == 0, "bounded run completed", checks)
    check(resource["sampled_peak_group_rss_bytes"] <= 512*2**20, "memory gate", checks)
    output = ROOT / result["output"]["path"]
    check(output.stat().st_size == result["output"]["bytes"] and digest(output) == result["output"]["sha256"],
          "output identity", checks)
    implementation = ROOT / result["implementation"]["path"]
    check(digest(implementation) == result["implementation"]["sha256"], "implementation identity", checks)
    cells_path = ROOT / result["cell_inventory"]["path"]
    check(digest(cells_path) == result["cell_inventory"]["sha256"], "cell inventory identity", checks)
    cells = pd.read_csv(cells_path)
    record_by_name = {record["name"]: record for block in result["source_blocks"] for record in block["objects"]}
    check(len(record_by_name) == 16, "sixteen historical source bindings", checks)
    check(result["source_validation"]["all_sha512_recomputed"] and result["source_validation"]["all_sha512_equal_declared"],
          "full historical source verification", checks)
    with xr.open_dataset(output, engine="h5netcdf", cache=False) as dataset:
        check(dict(dataset.sizes) == {"month": 468, "cell": 11, "scale": 3, "calendar_month": 12},
              "output dimensions", checks)
        months = pd.DatetimeIndex(dataset.month.values)
        check(months.equals(pd.date_range("1981-01-01", "2019-12-01", freq="MS")), "monthly chronology", checks)
        check(np.array_equal(dataset.native_lat_index.values, cells.native_lat_index.values)
              and np.array_equal(dataset.native_lon_index.values, cells.native_lon_index.values), "native cell order", checks)
        recomputed = construct_monthly_spei(months, dataset.precipitation_mm.values,
                                            dataset.et0_hargreaves_mm.values)
        maximum_difference = 0.0
        for stored_name, attribute in ARRAYS.items():
            observed = np.asarray(dataset[stored_name].values)
            expected = np.asarray(getattr(recomputed, attribute))
            check(observed.shape == expected.shape and np.array_equal(np.isfinite(observed), np.isfinite(expected)),
                  f"{stored_name} shape and missingness", checks)
            finite = np.isfinite(expected)
            difference = float(np.max(np.abs(observed[finite].astype(np.float64)-expected[finite].astype(np.float64)), initial=0))
            tolerance = 0.0 if np.issubdtype(expected.dtype, np.integer) else 1e-12
            check(difference <= tolerance, f"{stored_name} independent reconstruction", checks)
            maximum_difference = max(maximum_difference, difference)
        sentinel_checks = []
        for period in SENTINELS:
            precipitation, et0 = raw_month(record_by_name, period, cells)
            position = int(np.flatnonzero(months.strftime("%Y-%m") == period)[0])
            p_error = float(np.max(np.abs(precipitation-dataset.precipitation_mm.values[position])))
            et_error = float(np.max(np.abs(et0-dataset.et0_hargreaves_mm.values[position])))
            check(p_error <= 1e-10 and et_error <= 1e-10, f"raw sentinel {period}", checks)
            sentinel_checks.append({"period": period, "maximum_precipitation_absolute_difference": p_error,
                                    "maximum_et0_absolute_difference": et_error})
    validation = {
        "schema": "us_spei_bridge_historical_cells_validation_v1", "status": "passed",
        "checks": len(checks), "cells": 11, "months": 468, "fits": 396,
        "maximum_reconstruction_absolute_difference": maximum_difference,
        "raw_month_sentinels": sentinel_checks,
        "result": {"path": str(args.result.relative_to(ROOT)), "sha256": digest(args.result)},
        "resource": {"path": str(args.resource.relative_to(ROOT)), "sha256": digest(args.resource),
                     "sampled_peak_group_rss_bytes": resource["sampled_peak_group_rss_bytes"]},
        "gates": {name: False for name in result["gates"]},
    }
    args.output.write_text(json.dumps(validation, indent=2, sort_keys=True) + "\n")
    print(json.dumps(validation, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
