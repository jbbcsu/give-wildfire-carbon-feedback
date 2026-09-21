#!/usr/bin/env python3
"""Independently validate one bounded late-century SPEI pair."""
from __future__ import annotations

import argparse
from contextlib import ExitStack
import hashlib
import json
from pathlib import Path

import h5py
import numpy as np
import pandas as pd
import xarray as xr

from spei_construction_primitives import hargreaves_samani_et0_mm_day
from spei_distribution import GloParameters, standardize_glo
from spei_monthly_engine import _strict_rolling_sum


ROOT = Path(__file__).resolve().parents[1]
FITS = ROOT / "data/interim/spei_sparse_candidate_indices_20260908/all_blocks.json"
MONTHS = pd.date_range("2091-01-01", "2100-12-01", freq="MS")
DATES = pd.date_range("2091-01-01", "2100-12-31", freq="D")
SCALES = (1, 3, 6)


def digest(path: Path, algorithm: str = "sha256") -> str:
    value = hashlib.new(algorithm)
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def reference_samples(sources: dict[str, Path], indices: np.ndarray, latitudes: np.ndarray,
                      rows: np.ndarray, cols: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    n = len(indices)
    precipitation = np.zeros((120, n)); et0 = np.zeros((120, n)); counts = np.zeros((120, n), dtype=np.int16)
    flat = rows*720 + cols
    with ExitStack() as stack:
        datasets = {v: stack.enter_context(xr.open_dataset(sources[v], engine="h5netcdf", decode_times=True,
                                                            mask_and_scale=True, cache=False)) for v in ("pr", "tasmin", "tasmax")}
        for variable, dataset in datasets.items():
            require(variable in dataset and dataset[variable].dims == ("time", "lat", "lon"), "source schema changed")
            require(pd.DatetimeIndex(dataset.time.values).normalize().equals(DATES), "source chronology changed")
        for position, day in enumerate(DATES):
            p = np.asarray(datasets["pr"].pr.isel(time=position).values, dtype=np.float64).reshape(-1)[flat]*86400
            lo = np.asarray(datasets["tasmin"].tasmin.isel(time=position).values, dtype=np.float64).reshape(-1)[flat]-273.15
            hi = np.asarray(datasets["tasmax"].tasmax.isel(time=position).values, dtype=np.float64).reshape(-1)[flat]-273.15
            complete = np.isfinite(p) & np.isfinite(lo) & np.isfinite(hi)
            month = (day.year-2091)*12+day.month-1
            precipitation[month] += np.where(complete, np.maximum(p, 0), 0)
            et0[month] += np.where(complete, hargreaves_samani_et0_mm_day(np.where(complete, lo, 0),
                                                                          np.where(complete, hi, 0),
                                                                          latitudes, day.dayofyear), 0)
            counts[month] += complete
    expected = MONTHS.days_in_month.to_numpy(dtype=np.int16)[:, None]
    precipitation[counts != expected] = np.nan; et0[counts != expected] = np.nan
    return precipitation, et0


def frozen_parameters(indices: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    manifest = json.loads(FITS.read_text())
    result = [np.empty((3, 12, len(indices))) for _ in range(3)]
    filled = np.zeros(len(indices), dtype=bool)
    for record in manifest["records"]:
        start, stop = int(record["cell_start"]), int(record["cell_start"])+int(record["cell_count"])
        selected = np.flatnonzero((indices >= start) & (indices < stop))
        if not len(selected):
            continue
        raw = Path(record["output"]["path"]); path = raw if raw.is_absolute() else ROOT/raw
        require(digest(path) == record["output"]["sha256"], "fit block hash changed")
        local = indices[selected]-start
        with xr.open_dataset(path, engine="h5netcdf", cache=False) as dataset:
            for destination, name in zip(result, ("glo_location_xi_mm", "glo_scale_alpha_mm", "glo_shape_kappa")):
                destination[:, :, selected] = np.asarray(dataset[name].values)[:, :, local]
        filled[selected] = True
    require(filled.all(), "not all validation samples map to frozen parameters")
    return tuple(result)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pair-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    pair_dir = args.pair_dir if args.pair_dir.is_absolute() else ROOT/args.pair_dir
    output = args.output if args.output.is_absolute() else ROOT/args.output
    require(not output.exists(), "fresh validation output required")
    result_path = pair_dir/"result.json"; result = json.loads(result_path.read_text())
    source_paths = {item["variable"]: ROOT/item["path"] for item in result["sources"]}
    checks = 0
    for item in result["sources"]:
        path = ROOT/item["path"]
        require(path.stat().st_size == item["bytes"] and digest(path, "sha512") == item["sha512"], "source identity changed")
        checks += 2
    cube = ROOT/result["output"]["path"]
    require(cube.stat().st_size == result["output"]["bytes"] and digest(cube) == result["output"]["sha256"], "output identity changed")
    checks += 2
    with h5py.File(cube, "r") as handle:
        require(handle["spei"].shape == (3, 120, 31_208) and handle["cdf_clip_code"].shape == (3, 120, 31_208), "output dimensions changed")
        require(tuple(handle["scale"][:]) == SCALES and np.array_equal(handle["month"][:], MONTHS.values.astype("datetime64[ns]").astype(np.int64)), "output axes changed")
        lat = handle["latitude"][:]; rows = handle["native_lat_index"][:]; cols = handle["native_lon_index"][:]
        require(np.array_equal(lat, 89.75-.5*rows), "output native-grid binding changed")
        indices = np.unique(np.linspace(0, len(lat)-1, 24, dtype=np.int64))
        stored_spei = handle["spei"][:, :, indices]
        stored_clips = handle["cdf_clip_code"][:, :, indices]
        finite = np.zeros(3, dtype=np.int64); sums = np.zeros(3); below1 = np.zeros(3, dtype=np.int64)
        below15 = np.zeros(3, dtype=np.int64); lower = np.zeros(3, dtype=np.int64); upper = np.zeros(3, dtype=np.int64)
        for start in range(0, 31_208, 512):
            stop = min(start+512, 31_208)
            values = handle["spei"][:, :, start:stop].astype(np.float64); clips = handle["cdf_clip_code"][:, :, start:stop]
            ok = np.isfinite(values)
            finite += ok.sum(axis=(1,2)); sums += np.where(ok, values, 0).sum(axis=(1,2))
            below1 += ((values <= -1) & ok).sum(axis=(1,2)); below15 += ((values <= -1.5) & ok).sum(axis=(1,2))
            lower += (clips == -1).sum(axis=(1,2)); upper += (clips == 1).sum(axis=(1,2))
    precipitation, et0 = reference_samples(source_paths, indices, lat[indices], rows[indices], cols[indices])
    xi, alpha, kappa = frozen_parameters(indices)
    balance = precipitation-et0
    max_abs = 0.0; sample_checks = 0
    for scale_index, scale in enumerate(SCALES):
        accumulated = _strict_rolling_sum(balance, scale)
        for month_number in range(1, 13):
            positions = np.flatnonzero(MONTHS.month == month_number)
            for sample in range(len(indices)):
                parameters = GloParameters(float(xi[scale_index, month_number-1, sample]),
                                           float(alpha[scale_index, month_number-1, sample]),
                                           float(kappa[scale_index, month_number-1, sample]), 30, 0, 0, 0, 0, 0, 0)
                reference = standardize_glo(accumulated[positions, sample], parameters)
                difference = np.abs(stored_spei[scale_index, positions, sample].astype(np.float64)-reference.spei)
                max_abs = max(max_abs, float(np.nanmax(difference)))
                require(np.allclose(stored_spei[scale_index, positions, sample], reference.spei, rtol=0, atol=8e-6, equal_nan=True), "sample SPEI differs")
                require(np.array_equal(stored_clips[scale_index, positions, sample], reference.clip_code), "sample clip codes differ")
                sample_checks += 2*len(positions)
    for index, summary in enumerate(result["summaries"]):
        require(int(finite[index]) == summary["finite_cell_months"], "summary finite count differs")
        require(abs(sums[index]/finite[index]-summary["mean_spei"]) <= 2e-7, "summary mean differs beyond float32 tolerance")
        require(int(below1[index]) == round(summary["fraction_le_minus_1"]*finite[index]), "summary <=-1 count differs")
        require(int(below15[index]) == round(summary["fraction_le_minus_1_5"]*finite[index]), "summary <=-1.5 count differs")
        require(int(lower[index]) == summary["lower_tail_clips"] and int(upper[index]) == summary["upper_tail_clips"], "summary clip counts differ")
        checks += 5
    validation = {"schema": "isimip3b_late_drought_pair_validation_v1", "status": "passed",
                  "role": "independent_exposure_validation_not_yield_damage_or_scc", "pair_result_sha256": digest(result_path),
                  "output_sha256": result["output"]["sha256"], "fixed_sample_cells": len(indices),
                  "sample_cell_month_scale_checks": sample_checks, "maximum_spei_absolute_error": max_abs,
                  "structural_and_summary_checks": checks,
                  "implementation": {"path": str(Path(__file__).resolve().relative_to(ROOT)), "sha256": digest(Path(__file__).resolve())},
                  "gates": {"future_drought_exposure": True, "yield_response": False, "damage": False, "scc": False}}
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix+".partial")
    temporary.write_text(json.dumps(validation, indent=2, sort_keys=True)+"\n"); temporary.replace(output)
    print(json.dumps(validation))


if __name__ == "__main__":
    main()
