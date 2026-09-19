#!/usr/bin/env python3
"""Independent allocation, key, summary, and fixed-sample crop-window audit."""

from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
import math
from pathlib import Path
import sys

import h5py
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import xarray as xr


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from spei_crop_window_metrics import window_metrics  # noqa: E402
from build_spei_tile_crop_features import spans  # noqa: E402


KEYS = ["scenario", "crop", "lat", "lon_360", "harvest_year", "window", "scale"]
INPUT_CUBE = ROOT / "data/interim/gfdl_future_spei_boundary_pilot_v2_20260919/gfdl_boundary_spei.nc"


def sha(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def same(left: np.ndarray, right: np.ndarray, tolerance: float = 2e-12) -> tuple[bool, float]:
    finite = np.isfinite(left) & np.isfinite(right)
    if not np.array_equal(np.isnan(left), np.isnan(right)):
        return False, math.inf
    error = 0.0 if not finite.any() else float(np.max(np.abs(left[finite] - right[finite])))
    return error <= tolerance, error


def calendar(crop: str, irrigation: str) -> tuple:
    path = ROOT / f"data/raw/crop_calendars/ggcmi-crop-calendar-phase3_2015soc_{crop}_{irrigation}.nc"
    with h5py.File(path, "r") as handle:
        return (
            {float(value): index for index, value in enumerate(handle["lat"][:])},
            {float(value) % 360: index for index, value in enumerate(handle["lon"][:])},
            handle["planting_day"][:], handle["maturity_day"][:],
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    input_dir = (args.input_dir if args.input_dir.is_absolute() else ROOT / args.input_dir).resolve()
    result_path = input_dir / "result.json"
    result = json.loads(result_path.read_text())
    if result["status"] != "completed_pending_independent_validation":
        raise ValueError("builder status changed")
    records = {item["kind"]: item for item in result["records"]}
    if set(records) != {"regime", "combined"}:
        raise ValueError("output registry changed")
    frames = {}
    for kind, record in records.items():
        path = ROOT / record["path"]
        if path.stat().st_size != record["bytes"] or sha(path) != record["sha256"]:
            raise ValueError(f"{kind} output identity changed")
        frames[kind] = pq.read_table(path).to_pandas()
    regime, combined = frames["regime"], frames["combined"]
    checks = 0
    if len(combined) != 150390 or len(regime) != 163350:
        raise ValueError("row counts changed")
    if combined.duplicated(KEYS).any() or regime.duplicated(KEYS + ["irrigation"]).any():
        raise ValueError("duplicate feature key")
    checks += len(combined) + len(regime)
    if set(combined.status) != {"complete"} or set(regime.status) != {"complete"}:
        raise ValueError("unexpected incomplete status")
    if set(combined.scenario) != {"ssp126", "ssp370", "ssp585"} or set(combined.crop) != {"mai", "soy"}:
        raise ValueError("scenario/crop registry changed")
    if set(combined.harvest_year) != set(range(2015, 2021)) or set(combined.window) != {"season", "stage1", "stage2", "stage3", "preplant90"} or set(combined.scale) != {1, 3, 6}:
        raise ValueError("year/window/scale support changed")
    checks += 5
    grouped = regime.groupby(KEYS, sort=False, observed=True)
    share_sum = grouped.area_share.sum().reindex(pd.MultiIndex.from_frame(combined[KEYS])).to_numpy()
    if not np.allclose(share_sum, 1, rtol=0, atol=1e-12):
        raise ValueError("irrigation shares do not close")
    expected_spei = (regime.area_share * regime.spei_mean).groupby([regime[key] for key in KEYS], sort=False).sum().reindex(pd.MultiIndex.from_frame(combined[KEYS])).to_numpy()
    expected_month_end = (regime.area_share * regime.month_end_spei_mean).groupby([regime[key] for key in KEYS], sort=False).sum().reindex(pd.MultiIndex.from_frame(combined[KEYS])).to_numpy()
    expected_days = (regime.area_share * regime.overlap_days).groupby([regime[key] for key in KEYS], sort=False).sum().reindex(pd.MultiIndex.from_frame(combined[KEYS])).to_numpy()
    expected_end_days = (regime.area_share * regime.month_end_days).groupby([regime[key] for key in KEYS], sort=False).sum().reindex(pd.MultiIndex.from_frame(combined[KEYS])).to_numpy()
    maximum_error = 0.0
    for observed, expected, label in [
        (combined.spei_mean.to_numpy(), expected_spei, "SPEI"),
        (combined.month_end_spei_mean.to_numpy(), expected_month_end, "month-end SPEI"),
        (combined.weighted_window_days.to_numpy(), expected_days, "window days"),
        (combined.weighted_month_end_days.to_numpy(), expected_end_days, "month-end days"),
    ]:
        ok, error = same(observed, expected)
        maximum_error = max(maximum_error, error)
        if not ok:
            raise ValueError(f"combined {label} does not close")
        checks += len(observed)
    clipped = grouped.tail_clipped_months.max().reindex(pd.MultiIndex.from_frame(combined[KEYS])).to_numpy() > 0
    if not np.array_equal(combined.any_tail_clipped.to_numpy(), clipped):
        raise ValueError("tail clip allocation differs")
    checks += len(combined)
    current_summary = (
        combined.groupby(["scenario", "crop", "window", "scale"], sort=True).spei_mean
        .agg(["count", "mean"]).reset_index().to_dict("records")
    )
    saved_summary = result["descriptive_unweighted_summary"]
    if len(current_summary) != len(saved_summary):
        raise ValueError("summary row count differs")
    maximum_summary_error = 0.0
    for current, saved in zip(current_summary, saved_summary, strict=True):
        for key in ("scenario", "crop", "window", "scale", "count"):
            if current[key] != saved[key]:
                raise ValueError("summary key/count differs")
        error = abs(current["mean"] - saved["mean"])
        maximum_summary_error = max(maximum_summary_error, error)
        if error > 1e-13:
            raise ValueError("summary mean differs")
        checks += 6
    calendars = {(crop, irrigation): calendar(crop, irrigation) for crop in ("mai", "soy") for irrigation in ("noirr", "firr")}
    with xr.open_dataset(INPUT_CUBE, engine="h5netcdf", cache=False) as cube:
        months = pd.DatetimeIndex(cube.month.values)
        lookup = {(month.year, month.month): index for index, month in enumerate(months)}
        scenarios = {str(value): index for index, value in enumerate(cube.scenario.values)}
        scales = {int(value): index for index, value in enumerate(cube.scale.values)}
        positions = {(float(lat), float(lon) % 360): index for index, (lat, lon) in enumerate(zip(cube.latitude.values, cube.longitude.values))}
        spei_values = cube.spei.values
        clip_values = cube.cdf_clip_code.values
        fixed = np.linspace(0, len(regime) - 1, 24, dtype=int)
        for row in regime.iloc[fixed].itertuples(index=False):
            ci, cj, plant, maturity = calendars[(row.crop, row.irrigation)]
            dates = spans(int(row.harvest_year), plant[ci[row.lat], cj[row.lon_360]], maturity[ci[row.lat], cj[row.lon_360]])
            start, end = dates[row.window]
            if row.window_start != start.isoformat() or row.window_end != end.isoformat():
                raise ValueError("saved window dates differ from raw calendar")
            metric = window_metrics(
                spei_values[scenarios[row.scenario], scales[row.scale], :, positions[(row.lat, row.lon_360)]],
                clip_values[scenarios[row.scenario], scales[row.scale], :, positions[(row.lat, row.lon_360)]],
                lookup, start, end,
            )
            if metric["status"] != row.status:
                raise ValueError("sample status differs")
            for field in ("spei_mean", "month_end_spei_mean"):
                if abs(metric[field] - getattr(row, field)) > 1e-12:
                    raise ValueError(f"sample {field} differs")
            for field in ("overlap_days", "month_end_days", "source_months", "tail_clipped_months"):
                if metric[field] != getattr(row, field):
                    raise ValueError(f"sample {field} differs")
            checks += 9
    output = {
        "schema": "gfdl_future_spei_crop_windows_validation_v1", "status": "passed",
        "input_result_sha256": sha(result_path), "checks": checks,
        "combined_rows": len(combined), "regime_rows": len(regime),
        "maximum_allocation_absolute_error": maximum_error,
        "maximum_summary_absolute_error": maximum_summary_error,
        "fixed_raw_calendar_cube_samples": 24,
        "gates_confirmed_false": ["outcome_used", "response", "causal", "damage", "scc"],
        "limitation": "Independent feature-allocation audit, not independent climate evidence or an impact estimate."
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    print(json.dumps(output, sort_keys=True))


if __name__ == "__main__":
    main()
