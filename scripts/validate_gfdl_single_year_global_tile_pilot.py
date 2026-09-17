#!/usr/bin/env python3
"""Independent key, arithmetic, old-output, and daily-source checks for one tile."""
from __future__ import annotations

from datetime import datetime, timedelta
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr


ROOT = Path(__file__).resolve().parents[1]
PILOT = ROOT / "data/interim/gfdl_ssp126_global_2032_maize_tile_20260917"
OLD = ROOT / "data/interim/isimip3b_gfdl_ssp126_2031_2040_smoke"
PR = ROOT / "data/raw/isimip3b/gfdl-esm4/ssp126/pr/gfdl-esm4_r1i1p1f1_w5e5_ssp126_pr_global_daily_2031_2040.nc"
TAS = ROOT / "data/raw/isimip3b/gfdl-esm4/ssp126/tas/gfdl-esm4_r1i1p1f1_w5e5_ssp126_tas_global_daily_2031_2040.nc"
RESULT = PILOT / "independent_validation.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def close(a: float, b: float, label: str, tolerance: float = 1e-8) -> None:
    if not np.isfinite(a) or not np.isfinite(b) or abs(a - b) > tolerance:
        raise AssertionError(f"{label}: {a} != {b}")


def main() -> None:
    if RESULT.exists():
        raise FileExistsError(RESULT)
    season_path = PILOT / "season_lat100_110.parquet"
    stages_path = PILOT / "stages_lat100_110.parquet"
    season = pd.read_parquet(season_path)
    stages = pd.read_parquet(stages_path)
    if len(season) == 0 or len(stages) != 3 * len(season):
        raise AssertionError("empty or incomplete three-stage tile")
    key = ["harvest_year", "lat", "lon", "crop", "irrigation"]
    stage_key = key + ["stage_id"]
    if season.duplicated(key).any() or stages.duplicated(stage_key).any():
        raise AssertionError("duplicate seasonal or stage key")
    if set(season.harvest_year) != {2032} or set(season.crop) != {"mai"} or set(season.irrigation) != {"noirr"}:
        raise AssertionError("unexpected year/crop/calendar")
    if set(stages.stage_id) != {1, 2, 3}:
        raise AssertionError("stage ids incomplete")
    for label, output in (("season", season_path), ("stages", stages_path)):
        receipt = json.loads((PILOT / f"{label}_lat100_110.resource.json").read_text())
        if receipt["status"] != "completed" or receipt["sampled_peak_group_rss_bytes"] > 512 * 2**20:
            raise AssertionError(f"{label} resource gate failed")
        if receipt["sampled_peak_new_disk_bytes"] > 64 * 2**20:
            raise AssertionError(f"{label} owned-output gate failed")
        if not output.is_file():
            raise AssertionError(f"{label} output missing")

    with xr.open_dataset(PR, engine="h5netcdf") as pr_ds, xr.open_dataset(TAS, engine="h5netcdf") as tas_ds:
        expected_lats = pr_ds.lat.values[100:110]
        if not np.array_equal(np.sort(season.lat.unique()), np.sort(expected_lats)):
            raise AssertionError("tile latitude coverage differs from daily source")
        if not np.array_equal(pr_ds.lon.values, tas_ds.lon.values):
            raise AssertionError("source longitudes differ")
        if not np.array_equal(pr_ds.time.values, tas_ds.time.values):
            raise AssertionError("source daily times differ")
        if not (pr_ds.pr.attrs.get("units") == "kg m-2 s-1" and tas_ds.tas.attrs.get("units") == "K"):
            raise AssertionError("source units changed")

        # Positions are deterministic on the complete key-sorted tile, not selected
        # by the value or sign of a precipitation or yield outcome.
        ordered = season.sort_values(key).reset_index(drop=True)
        positions = sorted({0, len(ordered) // 4, len(ordered) // 2, 3 * len(ordered) // 4, len(ordered) - 1})
        for position in positions:
            row = ordered.iloc[position]
            start = datetime(int(row.plant_year), 1, 1) + timedelta(days=int(row.plant_doy) - 1)
            end = datetime(2032, 1, 1) + timedelta(days=int(row.maturity_doy) - 1)
            pr_source = pr_ds.pr.sel(lat=float(row.lat), lon=float(row.lon), time=slice(start, end)).values
            tas_source = tas_ds.tas.sel(lat=float(row.lat), lon=float(row.lon), time=slice(start, end)).values
            if pr_source.dtype != np.float32 or tas_source.dtype != np.float32:
                raise AssertionError("source numeric dtype changed")
            # Preserve the published builder's pointwise source-dtype unit
            # conversion, while keeping independent reductions below.
            pr_day = (pr_source * 86400).astype(np.float64)
            tas_day = (tas_source - 273.15).astype(np.float64)
            pr_precise = pr_source.astype(np.float64) * 86400
            tas_precise = tas_source.astype(np.float64) - 273.15
            if len(pr_day) != int(row.season_days) or len(tas_day) != len(pr_day):
                raise AssertionError("sample daily length differs")
            wet = pr_day >= 1.0
            run = longest = 0
            for is_wet in wet:
                run = 0 if is_wet else run + 1
                longest = max(longest, run)
            rx5 = max(sum(pr_day[i:i + 5]) for i in range(len(pr_day) - 4))
            for field, value in (
                ("precip_mm", math.fsum(map(float, pr_day))),
                ("rx1day_mm", np.max(pr_day)), ("rx5day_mm", rx5),
            ):
                close(float(row[field]), float(value), f"source sample {position} {field}")
            tas_mean_builder = float(np.mean(tas_day.astype(np.float32)))
            close(float(row.tmean_c), tas_mean_builder,
                  f"source sample {position} source-dtype mean")
            roundoff = np.abs(pr_day - pr_precise)
            close(float(row.precip_mm), float(math.fsum(map(float, pr_precise))),
                  f"source sample {position} high-precision rain bound",
                  tolerance=float(math.fsum(map(float, roundoff)) + 1e-8))
            close(float(row.tmean_c), float(math.fsum(map(float, tas_precise)) / len(tas_precise)),
                  f"source sample {position} high-precision temperature bound",
                  tolerance=float(abs(tas_mean_builder - math.fsum(map(float, tas_day)) / len(tas_day))
                                  + math.fsum(map(float, np.abs(tas_day - tas_precise))) / len(tas_day) + 1e-8))
            if int(row.wet_days_n) != int(np.sum(wet)) or int(row.cdd_max_days) != longest:
                raise AssertionError(f"source sample {position} wet/dry count differs")

    grouped = stages.groupby(key, sort=False)
    aggregate = grouped.agg(stage_days=("stage_days", "sum"), precip_mm=("precip_mm", "sum"),
                            wet_days_n=("wet_days_n", "sum"), rx1day_mm=("rx1day_mm", "max"),
                            max_stage_cdd=("cdd_max_days", "max"))
    joint = season.set_index(key).join(aggregate, rsuffix="_stage", how="left", validate="one_to_one")
    if joint.isna().any(axis=None):
        raise AssertionError("stage join incomplete")
    if not np.array_equal(joint.season_days.to_numpy(), joint.stage_days.to_numpy()):
        raise AssertionError("stage days do not sum to season")
    if not np.array_equal(joint.wet_days_n.to_numpy(), joint.wet_days_n_stage.to_numpy()):
        raise AssertionError("stage wet days do not sum to season")
    if np.max(np.abs(joint.precip_mm.to_numpy() - joint.precip_mm_stage.to_numpy())) > 1e-8:
        raise AssertionError("stage rain does not sum to season")
    if np.max(np.abs(joint.rx1day_mm.to_numpy() - joint.rx1day_mm_stage.to_numpy())) > 1e-8:
        raise AssertionError("stage Rx1day does not reproduce season")
    if (joint.max_stage_cdd > joint.cdd_max_days).any():
        raise AssertionError("stage dry spell exceeds whole season")

    previous = (
        ("season", OLD / "mai_noirr_2032_2039_lat100_102_features.parquet", season),
        ("stages", OLD / "mai_noirr_2032_2039_lat100_102_stages.parquet", stages),
    )
    parity_rows = {}
    for label, old_path, current in previous:
        old = pd.read_parquet(old_path)
        old = old.loc[old.harvest_year == 2032].sort_values(stage_key if label == "stages" else key).reset_index(drop=True)
        current = current.loc[current.lat.isin(expected_lats[:2])].sort_values(stage_key if label == "stages" else key).reset_index(drop=True)
        pd.testing.assert_frame_equal(current, old, check_exact=True)
        parity_rows[label] = len(current)

    report = {
        "schema": "gfdl_ssp126_2032_maize_global_tile_independent_validation_v1",
        "status": "passed_engineering_tile_only_not_global_or_scc",
        "latitude_index_range": [100, 110],
        "season_rows": len(season), "stage_rows": len(stages),
        "old_two_row_exact_parity_rows": parity_rows,
        "independent_daily_sample_positions": positions,
        "independent_daily_sample_count": len(positions),
        "season_sha256": sha256(season_path), "stages_sha256": sha256(stages_path),
        "no_yield_data_read": True,
    }
    RESULT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
