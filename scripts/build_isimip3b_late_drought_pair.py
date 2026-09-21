#!/usr/bin/env python3
"""Build one five-ESM late-century SPEI pair under bounded memory.

The script reads one day from each global source at a time, retains only the
frozen crop-support cells, and applies the observational 1982--2011 GLO
parameters without refitting.  It is exposure engineering only.
"""
from __future__ import annotations

import argparse
import csv
from contextlib import ExitStack
import hashlib
import json
from pathlib import Path
import time

import h5py
import numpy as np
import pandas as pd
import xarray as xr

import build_spei_grid_chunk as engine
from spei_construction_primitives import hargreaves_samani_et0_mm_day
from spei_monthly_engine import _strict_rolling_sum


ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "data/provenance/isimip3b_later_century_plan.csv"
EXTREMA = ROOT / "data/provenance/isimip3b_five_esm_late_drought_extrema_20260921.json"
FITS = ROOT / "data/interim/spei_sparse_candidate_indices_20260908/all_blocks.json"
PROTOCOL = ROOT / "FIVE_ESM_LATE_DROUGHT_STREAMING_PROTOCOL_20260921.md"
SCALES = (1, 3, 6)
EXPECTED_DATES = pd.date_range("2091-01-01", "2100-12-31", freq="D")
EXPECTED_MONTHS = pd.date_range("2091-01-01", "2100-12-01", freq="MS")
ORDER_TOLERANCE_K = 0.00005


def digest(path: Path, algorithm: str = "sha256") -> str:
    value = hashlib.new(algorithm)
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def normal_ppf(probability: np.ndarray) -> np.ndarray:
    """Vectorized Acklam inverse-normal approximation (absolute error <2e-8)."""
    p = np.asarray(probability, dtype=np.float64)
    if ((p <= 0) | (p >= 1)).any():
        raise ValueError("normal probabilities must lie strictly inside (0,1)")
    a = (-3.969683028665376e1, 2.209460984245205e2, -2.759285104469687e2,
         1.383577518672690e2, -3.066479806614716e1, 2.506628277459239)
    b = (-5.447609879822406e1, 1.615858368580409e2, -1.556989798598866e2,
         6.680131188771972e1, -1.328068155288572e1)
    c = (-7.784894002430293e-3, -3.223964580411365e-1, -2.400758277161838,
         -2.549732539343734, 4.374664141464968, 2.938163982698783)
    d = (7.784695709041462e-3, 3.224671290700398e-1, 2.445134137142996,
         3.754408661907416)
    low = 0.02425
    out = np.empty(p.shape, dtype=np.float64)
    lower = p < low
    upper = p > 1 - low
    middle = ~(lower | upper)
    if lower.any():
        q = np.sqrt(-2 * np.log(p[lower]))
        out[lower] = (((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    if upper.any():
        q = np.sqrt(-2 * np.log1p(-p[upper]))
        out[upper] = -(((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    if middle.any():
        q = p[middle] - 0.5
        r = q*q
        out[middle] = (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5])*q / (((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1)
    return out


def standardize_vectorized(values: np.ndarray, xi: np.ndarray, alpha: np.ndarray,
                           kappa: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Apply independent GLO parameters across columns without Python loops."""
    x = np.asarray(values, dtype=np.float64)
    xi, alpha, kappa = (np.asarray(v, dtype=np.float64) for v in (xi, alpha, kappa))
    if x.ndim != 2 or any(v.shape != (x.shape[1],) for v in (xi, alpha, kappa)):
        raise ValueError("GLO input shapes differ")
    if not ((alpha > 0).all() and (np.abs(kappa) < 1).all()):
        raise ValueError("invalid frozen GLO parameters")
    z = (x - xi[None, :]) / alpha[None, :]
    transformed = np.full(z.shape, np.nan, dtype=np.float64)
    small = np.abs(kappa) <= 1e-6
    transformed[:, small] = z[:, small]
    regular = ~small
    if regular.any():
        kk = kappa[regular][None, :]
        support = 1 - kk * z[:, regular]
        valid = np.isfinite(z[:, regular])
        inside = valid & (support > 0)
        part = np.full(support.shape, np.nan, dtype=np.float64)
        part[inside] = -np.log(support[inside]) / np.broadcast_to(kk, support.shape)[inside]
        outside = valid & ~inside
        outside_high = outside & (np.broadcast_to(kk, support.shape) > 0)
        part[outside_high] = np.inf
        part[outside & ~outside_high] = -np.inf
        transformed[:, regular] = part
    probability = np.empty(transformed.shape, dtype=np.float64)
    nonnegative = transformed >= 0
    probability[nonnegative] = 1 / (1 + np.exp(-transformed[nonnegative]))
    exp_value = np.exp(transformed[~nonnegative])
    probability[~nonnegative] = exp_value / (1 + exp_value)
    probability = np.clip(probability, 0, 1)
    finite = np.isfinite(probability)
    clip = np.full(probability.shape, -9, dtype=np.int8)
    clip[finite] = 0
    clip[finite & (probability < 1e-12)] = -1
    clip[finite & (probability > 1 - 1e-12)] = 1
    clipped = np.clip(probability, 1e-12, 1 - 1e-12)
    return normal_ppf(clipped), clip


def source_record(esm: str, scenario: str, variable: str) -> dict[str, object]:
    with PLAN.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    matches = [r for r in rows if (r["esm_id"], r["scenario"], r["variable"], r["start_year"], r["end_year"])
               == (esm, scenario, variable, "2091", "2100")]
    if len(matches) != 1:
        raise ValueError(f"one registered {variable} source required")
    row = matches[0]
    return {"variable": variable, "file_name": row["file_name"], "bytes": int(row["size_bytes"]),
            "sha512": row["sha512"], "file_url": row["file_url"]}


def extrema_record(esm: str, scenario: str, variable: str) -> dict[str, object]:
    manifest = json.loads(EXTREMA.read_text())
    matches = [r for r in manifest["objects"] if (r["esm"], r["scenario"], r["variable"])
               == (esm, scenario, variable)]
    if len(matches) != 1:
        raise ValueError(f"one frozen {variable} source required")
    return matches[0]


def locate(root: Path, record: dict[str, object]) -> Path:
    matches = list(root.rglob(str(record["file_name"])))
    if len(matches) != 1:
        raise ValueError(f"one resident source required: {record['file_name']}")
    path = matches[0]
    if path.stat().st_size != record["bytes"] or digest(path, "sha512") != record["sha512"]:
        raise ValueError(f"source byte count or SHA-512 differs: {path.name}")
    return path


def load_support() -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, list[dict]]:
    manifest = json.loads(FITS.read_text())
    if manifest.get("status") != "all_candidate_blocks_individually_validated":
        raise ValueError("frozen fit-block validation is not passed")
    latitudes, longitudes, rows, cols, blocks = [], [], [], [], []
    expected_start = 0
    for record in manifest["records"]:
        if int(record["cell_start"]) != expected_start:
            raise ValueError("fit blocks are not contiguous")
        raw = Path(record["output"]["path"])
        path = raw if raw.is_absolute() else ROOT / raw
        if digest(path) != record["output"]["sha256"]:
            raise ValueError("frozen fit block SHA-256 differs")
        with xr.open_dataset(path, engine="h5netcdf", cache=False) as dataset:
            lat = np.asarray(dataset.latitude.values, dtype=np.float64)
            lon = np.asarray(dataset.longitude.values, dtype=np.float64)
            ii = np.asarray(dataset.native_lat_index.values, dtype=np.int64)
            jj = np.asarray(dataset.native_lon_index.values, dtype=np.int64)
            if len(lat) != int(record["cell_count"]) or not np.all(dataset.fit_status_code.values == 0):
                raise ValueError("fit block dimensions/status changed")
            if not np.array_equal(lat, 89.75 - 0.5*ii) or not np.array_equal(lon, -179.75 + 0.5*jj):
                raise ValueError("fit block native-grid binding changed")
        blocks.append({"path": path, "start": expected_start, "count": len(lat)})
        latitudes.append(lat); longitudes.append(lon); rows.append(ii); cols.append(jj)
        expected_start += len(lat)
    arrays = tuple(np.concatenate(items) for items in (latitudes, longitudes, rows, cols))
    if len(arrays[0]) != 31_208 or len(set(zip(arrays[2], arrays[3]))) != 31_208:
        raise ValueError("exact 31,208-cell frozen support required")
    return (*arrays, blocks)


def validate_dataset(dataset: xr.Dataset, variable: str) -> pd.DatetimeIndex:
    if variable not in dataset or dataset[variable].dims != ("time", "lat", "lon"):
        raise ValueError(f"{variable} schema changed")
    expected_units = "kg m-2 s-1" if variable == "pr" else "K"
    if dataset[variable].attrs.get("units") != expected_units:
        raise ValueError(f"{variable} units changed")
    if not np.array_equal(dataset.lat.values, 89.75 - 0.5*np.arange(360)) or not np.array_equal(dataset.lon.values, -179.75 + 0.5*np.arange(720)):
        raise ValueError(f"{variable} grid changed")
    dates = pd.DatetimeIndex(dataset.time.values).normalize()
    if not dates.equals(EXPECTED_DATES):
        raise ValueError(f"{variable} chronology changed")
    return dates


def stream_monthly(paths: dict[str, Path], latitudes: np.ndarray, rows: np.ndarray,
                   cols: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict]:
    n = len(latitudes)
    precipitation = np.zeros((120, n), dtype=np.float64)
    et0 = np.zeros((120, n), dtype=np.float64)
    counts = np.zeros((120, n), dtype=np.int16)
    audit = {"support_missing_triplets": 0, "global_temperature_order_violations": 0,
             "minimum_global_tas_minus_tasmin_k": None, "minimum_global_tasmax_minus_tas_k": None}
    flat = rows*720 + cols
    with ExitStack() as stack:
        datasets = {v: stack.enter_context(xr.open_dataset(paths[v], engine="h5netcdf", decode_times=True,
                                                            mask_and_scale=True, cache=False)) for v in paths}
        dates = {v: validate_dataset(datasets[v], v) for v in paths}
        if any(not dates[v].equals(dates["pr"]) for v in paths):
            raise ValueError("source chronologies differ")
        for position, day in enumerate(EXPECTED_DATES):
            fields = {v: np.asarray(datasets[v][v].isel(time=position).values, dtype=np.float64) for v in paths}
            order = np.isfinite(fields["tasmin"]) & np.isfinite(fields["tas"]) & np.isfinite(fields["tasmax"])
            low_delta = fields["tas"][order] - fields["tasmin"][order]
            high_delta = fields["tasmax"][order] - fields["tas"][order]
            audit["global_temperature_order_violations"] += int(np.count_nonzero(low_delta < -ORDER_TOLERANCE_K) + np.count_nonzero(high_delta < -ORDER_TOLERANCE_K))
            for key, values in (("minimum_global_tas_minus_tasmin_k", low_delta), ("minimum_global_tasmax_minus_tas_k", high_delta)):
                current = float(np.min(values)) if values.size else None
                audit[key] = current if audit[key] is None else min(audit[key], current)
            p = fields["pr"].reshape(-1)[flat] * 86400.0
            lo = fields["tasmin"].reshape(-1)[flat] - 273.15
            hi = fields["tasmax"].reshape(-1)[flat] - 273.15
            complete = np.isfinite(p) & np.isfinite(lo) & np.isfinite(hi)
            if (p[complete] < -1e-10).any() or (hi[complete] < lo[complete] - ORDER_TOLERANCE_K).any():
                raise ValueError("crop-support physical range check failed")
            audit["support_missing_triplets"] += int(np.count_nonzero(~complete))
            month = (day.year - 2091)*12 + day.month - 1
            safe_lo, safe_hi = np.where(complete, lo, 0), np.where(complete, hi, 0)
            daily_et0 = hargreaves_samani_et0_mm_day(safe_lo, safe_hi, latitudes, day.dayofyear)
            precipitation[month] += np.where(complete, np.maximum(p, 0), 0)
            et0[month] += np.where(complete, daily_et0, 0)
            counts[month] += complete
    expected = EXPECTED_MONTHS.days_in_month.to_numpy(dtype=np.int16)[:, None]
    complete_month = counts == expected
    precipitation[~complete_month] = np.nan
    et0[~complete_month] = np.nan
    audit["incomplete_cell_months"] = int(np.count_nonzero(~complete_month))
    return precipitation, et0, counts, audit


def create_output(path: Path, esm: str, scenario: str, lat: np.ndarray, lon: np.ndarray,
                  rows: np.ndarray, cols: np.ndarray) -> h5py.File:
    handle = h5py.File(path, "w")
    handle.attrs.update({"schema": "isimip3b_late_drought_pair_v1", "esm": esm, "scenario": scenario,
                         "scientific_role": "exposure_only_not_yield_damage_or_scc",
                         "calibration": "observational 1982-2011 frozen; no future refit"})
    handle.create_dataset("scale", data=np.asarray(SCALES, dtype=np.int16))
    handle.create_dataset("month", data=EXPECTED_MONTHS.values.astype("datetime64[ns]").astype(np.int64))
    handle.create_dataset("latitude", data=lat); handle.create_dataset("longitude", data=lon)
    handle.create_dataset("native_lat_index", data=rows); handle.create_dataset("native_lon_index", data=cols)
    chunks = (1, 12, min(512, len(lat)))
    handle.create_dataset("spei", shape=(3, 120, len(lat)), dtype="f4", chunks=chunks,
                          compression="gzip", compression_opts=4, fillvalue=np.nan)
    handle.create_dataset("cdf_clip_code", shape=(3, 120, len(lat)), dtype="i1", chunks=chunks,
                          compression="gzip", compression_opts=4, fillvalue=-9)
    return handle


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--esm", required=True)
    parser.add_argument("--scenario", choices=("ssp126", "ssp370", "ssp585"), required=True)
    parser.add_argument("--raw-root", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    out_dir = args.out_dir if args.out_dir.is_absolute() else ROOT / args.out_dir
    if out_dir.exists():
        raise ValueError("fresh output directory required")
    records = {v: source_record(args.esm, args.scenario, v) for v in ("pr", "tas")}
    records.update({v: extrema_record(args.esm, args.scenario, v) for v in ("tasmin", "tasmax")})
    paths = {v: locate(args.raw_root, records[v]) for v in records}
    lat, lon, rows, cols, blocks = load_support()
    started = time.perf_counter()
    precipitation, et0, counts, daily_audit = stream_monthly(paths, lat, rows, cols)
    out_dir.mkdir(parents=True)
    partial = out_dir / "late_drought_pair.h5.partial"
    finite = np.zeros(3, dtype=np.int64); total = np.zeros(3); below1 = np.zeros(3, dtype=np.int64)
    below15 = np.zeros(3, dtype=np.int64); lower = np.zeros(3, dtype=np.int64); upper = np.zeros(3, dtype=np.int64)
    with create_output(partial, args.esm, args.scenario, lat, lon, rows, cols) as output:
        for block in blocks:
            start, stop = block["start"], block["start"] + block["count"]
            balance = precipitation[:, start:stop] - et0[:, start:stop]
            with xr.open_dataset(block["path"], engine="h5netcdf", cache=False) as fit:
                xi = np.asarray(fit.glo_location_xi_mm.values); alpha = np.asarray(fit.glo_scale_alpha_mm.values)
                kappa = np.asarray(fit.glo_shape_kappa.values)
            for scale_index, scale in enumerate(SCALES):
                accumulated = _strict_rolling_sum(balance, scale)
                block_spei = np.full(accumulated.shape, np.nan); block_clip = np.full(accumulated.shape, -9, dtype=np.int8)
                for month_number in range(1, 13):
                    positions = np.flatnonzero(EXPECTED_MONTHS.month == month_number)
                    values, clips = standardize_vectorized(accumulated[positions], xi[scale_index, month_number-1],
                                                           alpha[scale_index, month_number-1], kappa[scale_index, month_number-1])
                    block_spei[positions] = values; block_clip[positions] = clips
                stored_spei = block_spei.astype(np.float32)
                output["spei"][scale_index, :, start:stop] = stored_spei
                output["cdf_clip_code"][scale_index, :, start:stop] = block_clip
                ok = np.isfinite(stored_spei); finite[scale_index] += int(ok.sum()); total[scale_index] += float(stored_spei[ok].astype(np.float64).sum())
                below1[scale_index] += int(np.count_nonzero(stored_spei[ok] <= -1)); below15[scale_index] += int(np.count_nonzero(stored_spei[ok] <= -1.5))
                lower[scale_index] += int(np.count_nonzero(block_clip == -1)); upper[scale_index] += int(np.count_nonzero(block_clip == 1))
    output_path = out_dir / "late_drought_pair.h5"
    partial.replace(output_path)
    summaries = [{"scale_months": scale, "finite_cell_months": int(finite[i]),
                  "mean_spei": float(total[i]/finite[i]), "fraction_le_minus_1": float(below1[i]/finite[i]),
                  "fraction_le_minus_1_5": float(below15[i]/finite[i]), "lower_tail_clips": int(lower[i]),
                  "upper_tail_clips": int(upper[i])} for i, scale in enumerate(SCALES)]
    result = {"schema": "isimip3b_late_drought_pair_result_v1", "status": "completed_pending_independent_validation",
              "role": "exposure_only_not_yield_response_damage_or_scc", "esm": args.esm, "scenario": args.scenario,
              "period": "2091-2100", "crop_window_years_reserved": list(range(2092, 2100)),
              "support_cells": len(lat), "months": 120, "scales": list(SCALES), "daily_audit": daily_audit,
              "summaries": summaries, "sources": [{"variable": v, "path": str(paths[v].relative_to(ROOT)),
              "bytes": records[v]["bytes"], "sha512": records[v]["sha512"]} for v in sorted(records)],
              "fit_manifest": {"path": str(FITS.relative_to(ROOT)), "sha256": digest(FITS), "blocks": len(blocks)},
              "protocol": {"path": str(PROTOCOL.relative_to(ROOT)), "sha256": digest(PROTOCOL)},
              "output": {"path": str(output_path.relative_to(ROOT)), "bytes": output_path.stat().st_size,
                         "sha256": digest(output_path)}, "wall_seconds": time.perf_counter()-started,
              "implementation": {"path": str(Path(__file__).resolve().relative_to(ROOT)), "sha256": digest(Path(__file__).resolve())},
              "gates": {"future_drought_exposure": False, "yield_response": False, "damage": False, "scc": False}}
    engine.write_json_atomic(out_dir / "result.json", result)
    print(json.dumps({"status": result["status"], "output": result["output"], "summaries": summaries}))


if __name__ == "__main__":
    main()
