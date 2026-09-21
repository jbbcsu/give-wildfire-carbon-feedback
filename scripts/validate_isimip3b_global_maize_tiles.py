#!/usr/bin/env python3
"""Independently validate one registered ESM-year panel from raw daily sources."""
from __future__ import annotations

import argparse
import json

import numpy as np
import pandas as pd
import xarray as xr

from audit_gfdl_2032_2039_maize_crossyear import check_features, digest, require
from continue_isimip3b_global_maize_tiles import destination, source_context
from run_gfdl_single_year_global_tile_pilot import ROOT, CALENDAR
from validate_gfdl_2032_maize_global_tiles import SAMPLE_TILE_STARTS, daily_sample


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--esm", default="ukesm1-0-ll")
    parser.add_argument("--scenario", default="ssp126")
    parser.add_argument("--year", type=int, default=2092)
    args = parser.parse_args()
    esm, scenario, year = args.esm, args.scenario, args.year
    receipt, receipt_path, pr, tas = source_context(esm, scenario, year)
    out_root = destination(esm, scenario, year)
    output = out_root / "independent_global_validation.json"
    if output.exists():
        raise FileExistsError(output)
    manifest_path = out_root / "global_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    require(manifest["schema"] == "isimip3b_global_mai_noirr_source_only_tiles_v1"
            and manifest["status"] == "complete_engineering_pending_independent_validation_not_response_damage_or_scc"
            and (manifest["esm"], manifest["member"], manifest["scenario"], manifest["harvest_year"])
            == (esm, receipt["member"], scenario, year)
            and manifest["source_receipt_sha256"] == digest(receipt_path)
            and manifest["precip_sha512"] == receipt["precipitation"]["sha512"]
            and manifest["temperature_sha512"] == receipt["paired_temperature"]["sha512"],
            "global manifest/source binding failed")
    tiles = manifest["tiles"]
    require(len(tiles) == 36 and [(r["lat_start"], r["lat_stop"]) for r in tiles]
            == [(i, i + 10) for i in range(0, 360, 10)],
            "global latitude partition failed")
    season_count = stage_count = 0
    global_keys: set[tuple[float, float]] = set()
    samples: list[tuple[str, pd.Series]] = []
    with (xr.open_dataset(CALENDAR, engine="h5netcdf") as cal,
          xr.open_dataset(pr, engine="h5netcdf") as pr_ds,
          xr.open_dataset(tas, engine="h5netcdf") as tas_ds):
        require(np.array_equal(cal.lat.values, pr_ds.lat.values)
                and np.array_equal(cal.lon.values, pr_ds.lon.values)
                and np.array_equal(pr_ds.lat.values, tas_ds.lat.values)
                and np.array_equal(pr_ds.lon.values, tas_ds.lon.values)
                and np.array_equal(pr_ds.time.values, tas_ds.time.values)
                and pr_ds.pr.attrs.get("units") == "kg m-2 s-1"
                and tas_ds.tas.attrs.get("units") == "K",
                "source/calendar coordinates, time or units failed")
        for record in tiles:
            start, stop = int(record["lat_start"]), int(record["lat_stop"])
            tile = out_root / f"lat{start:03d}_{stop:03d}"
            require(json.loads((tile / "validation.json").read_text()) == record,
                    f"tile receipt/manifest mismatch: {tile}")
            season_path, stage_path = tile / "season.parquet", tile / "stages.parquet"
            require(digest(season_path) == record["season_sha256"]
                    and digest(stage_path) == record["stages_sha256"],
                    f"tile feature file changed: {tile}")
            season, stages = pd.read_parquet(season_path), pd.read_parquet(stage_path)
            require(len(season) == record["season_rows"] and len(stages) == record["stage_rows"]
                    and len(stages) == 3 * len(season), f"tile row counts differ: {tile}")
            cal_slice = cal.isel(lat=slice(start, stop))
            planting, maturity = cal_slice.planting_day.values, cal_slice.maturity_day.values
            valid = np.isfinite(planting) & np.isfinite(maturity) & (planting >= 1) & (maturity >= 1)
            row, col = np.where(valid)
            expected = set(zip(cal.lat.values[start:stop][row].astype(float),
                               cal.lon.values[col].astype(float)))
            pairs = list(zip(season.lat.astype(float), season.lon.astype(float)))
            require(len(pairs) == len(expected) == len(set(pairs)) and set(pairs) == expected,
                    f"exact crop-calendar mask failed: {tile}")
            for pair in pairs:
                require(pair not in global_keys, f"cross-tile duplicate crop cell: {pair}")
                global_keys.add(pair)
            for label, frame, period in (("season", season, "season_days"),
                                         ("stage", stages, "stage_days")):
                require(set(frame.harvest_year) <= {year} and set(frame.crop) <= {"mai"}
                        and set(frame.irrigation) <= {"noirr"},
                        f"{label} identity mismatch: {tile}")
                check_features(frame, period, f"{tile} {label}")
            if start in SAMPLE_TILE_STARTS:
                ordered = season.sort_values(["lat", "lon"]).reset_index(drop=True)
                require(len(ordered) > 0, f"fixed raw-sample tile empty: {tile}")
                for position in sorted({0, len(ordered) // 2, len(ordered) - 1}):
                    samples.append((f"lat{start:03d}_{stop:03d} row{position}", ordered.iloc[position]))
            season_count += len(season)
            stage_count += len(stages)
        require(len(samples) == 21, "fixed raw sample count differs")
        for label, row in samples:
            daily_sample(row, pr_ds, tas_ds, label)
    require(season_count == manifest["season_rows"] and stage_count == manifest["stage_rows"]
            and len(global_keys) == season_count, "global aggregate rows/keys differ")
    result = {
        "schema": "isimip3b_global_mai_noirr_independent_validation_v1",
        "status": ("passed_one_year_second_esm_source_features_only_not_response_damage_or_scc"
                   if esm == "ukesm1-0-ll" else
                   "passed_one_year_source_features_only_not_response_damage_or_scc"),
        "esm": esm, "scenario": scenario, "harvest_year": year,
        "tiles": len(tiles), "season_rows": season_count, "stage_rows": stage_count,
        "unique_cell_year_keys": len(global_keys), "fixed_raw_daily_sample_count": len(samples),
        "raw_sample_tiles": list(SAMPLE_TILE_STARTS),
        "global_manifest_sha256": digest(manifest_path), "no_yield_data_read": True,
    }
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
