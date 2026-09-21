#!/usr/bin/env python3
"""Independent eight-year, 36-tile source-only ESM calendar/feature audit."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

from audit_gfdl_2032_2039_maize_crossyear import check_features, digest, require
from continue_isimip3b_global_maize_tiles import MEMBERS, destination, source_context
from run_gfdl_single_year_global_tile_pilot import ROOT, CALENDAR
from run_ukesm_four_year_tile_pilot import OUT as PILOT


KEY = ["harvest_year", "lat", "lon", "crop", "irrigation"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--esm", choices=("ukesm1-0-ll", "ipsl-cm6a-lr", "mpi-esm1-2-hr", "mri-esm2-0", "gfdl-esm4"), default="ukesm1-0-ll")
    parser.add_argument("--window", choices=("mid", "late"), default="late")
    parser.add_argument("--scenario", choices=("ssp126", "ssp370", "ssp585"), default="ssp126")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    esm, window, scenario = args.esm, args.window, args.scenario
    require(esm == "ukesm1-0-ll" or window == "late" or
            (esm == "mri-esm2-0" and window == "mid" and scenario == "ssp585") or
            (esm == "gfdl-esm4" and window == "mid" and scenario == "ssp126"),
            "additional ESM/window combination is not registered")
    require(window == "late" or esm != "mri-esm2-0" or scenario == "ssp585",
            "MRI mid-century audit registered only for SSP5-8.5")
    require(window == "late" or esm != "gfdl-esm4" or scenario == "ssp126",
            "GFDL mid-century audit registered only for SSP1-2.6")
    years = tuple(range(2042, 2050)) if window == "mid" else tuple(range(2092, 2100))
    anchor_year = years[0]
    prefix = "ukesm" if esm == "ukesm1-0-ll" else esm
    output = (args.output.resolve() if args.output is not None else
              ROOT / f"data/interim/{prefix}_{scenario}_{anchor_year}_{years[-1]}_mai_noirr_crossyear_qc_20260917.json")
    require(output.is_relative_to(ROOT / "data/interim"), "cross-year output must remain ignored interim data")
    if output.exists():
        raise FileExistsError(output)
    source, receipt_path, pr, tas = source_context(esm, scenario, anchor_year)
    pilot_required = esm == "ukesm1-0-ll" and window == "late" and scenario == "ssp126"
    if pilot_required:
        independent_pilot = json.loads((PILOT / "independent_validation.json").read_text())
        require(independent_pilot["status"] == "passed_tile_scalability_only_not_global_response_yield_damage_or_scc"
                and independent_pilot["pilot_manifest_sha256"] == digest(PILOT / "pilot_manifest.json")
                and independent_pilot["fixed_new_raw_cell_checks"] == 9,
                "four-year pilot receipt/identity changed")
    manifests: dict[int, dict] = {}
    for year in years:
        directory = destination(esm, scenario, year)
        manifest_path = directory / "global_manifest.json"
        manifest = json.loads(manifest_path.read_text())
        independent = json.loads((directory / "independent_global_validation.json").read_text())
        resource = json.loads((directory / "independent_validation.resource.json").read_text())
        require(manifest["schema"] == "isimip3b_global_mai_noirr_source_only_tiles_v1"
                and manifest["source_receipt_sha256"] == digest(receipt_path)
                and manifest["precip_sha512"] == source["precipitation"]["sha512"]
                and manifest["temperature_sha512"] == source["paired_temperature"]["sha512"]
                and (manifest["esm"], manifest["member"], manifest["scenario"], manifest["harvest_year"])
                == (esm, MEMBERS[esm], scenario, year)
                and len(manifest["tiles"]) == 36,
                f"source or manifest identity failed: {year}")
        expected_status = ("passed_one_year_second_esm_source_features_only_not_response_damage_or_scc"
                           if esm == "ukesm1-0-ll" else
                           "passed_one_year_source_features_only_not_response_damage_or_scc")
        require(independent["status"] == expected_status
                and independent["global_manifest_sha256"] == digest(manifest_path)
                and independent["fixed_raw_daily_sample_count"] == 21
                and (independent["season_rows"], independent["stage_rows"])
                == (manifest["season_rows"], manifest["stage_rows"]),
                f"independent daily-source check failed: {year}")
        require(resource["status"] == "completed"
                and resource["sampled_peak_group_rss_bytes"] <= 512 * 2**20
                and resource["sampled_peak_new_disk_bytes"] <= 64 * 2**20,
                f"resource limit failed: {year}")
        manifests[year] = manifest
    pilot_frames = ({label: pd.read_parquet(PILOT / f"{label}.parquet")
                     for label in ("season", "stages")} if pilot_required else {})
    count_season = count_stages = rain_changed = temperature_changed = pilot_checks = 0
    with (xr.open_dataset(CALENDAR, engine="h5netcdf") as cal,
          xr.open_dataset(pr, engine="h5netcdf") as p,
          xr.open_dataset(tas, engine="h5netcdf") as t):
        require(np.array_equal(cal.lat.values, p.lat.values)
                and np.array_equal(cal.lon.values, p.lon.values)
                and np.array_equal(p.lat.values, t.lat.values)
                and np.array_equal(p.lon.values, t.lon.values)
                and np.array_equal(p.time.values, t.time.values),
                "paired daily source/calendar coordinates changed")
        for start in range(0, 360, 10):
            stop = start + 10
            planting = cal.planting_day.isel(lat=slice(start, stop)).values
            maturity = cal.maturity_day.isel(lat=slice(start, stop)).values
            valid = np.isfinite(planting) & np.isfinite(maturity) & (planting >= 1) & (maturity >= 1)
            row_index, col_index = np.where(valid)
            expected = set(zip(p.lat.values[start:stop][row_index].astype(float),
                               p.lon.values[col_index].astype(float)))
            baseline_frame: pd.DataFrame | None = None
            for year in years:
                tile = destination(esm, scenario, year) / f"lat{start:03d}_{stop:03d}"
                record = manifests[year]["tiles"][start // 10]
                require((record["lat_start"], record["lat_stop"]) == (start, stop)
                        and json.loads((tile / "validation.json").read_text()) == record,
                        f"tile manifest/receipt mismatch: {year} {start}")
                frames = {}
                for label, period in (("season", "season_days"), ("stages", "stage_days")):
                    path = tile / f"{label}.parquet"
                    require(digest(path) == record[f"{label}_sha256"],
                            f"feature hash changed: {year} {start} {label}")
                    frame = pd.read_parquet(path)
                    check_features(frame, period, f"{year} {start} {label}")
                    require(set(frame.harvest_year) <= {year}
                            and set(frame.crop) <= {"mai"}
                            and set(frame.irrigation) <= {"noirr"},
                            f"feature identity changed: {year} {start} {label}")
                    frames[label] = frame
                season, stages = frames["season"], frames["stages"]
                pairs = list(zip(season.lat.astype(float), season.lon.astype(float)))
                require(len(pairs) == len(expected) == len(set(pairs))
                        and set(pairs) == expected
                        and len(stages) == 3 * len(season)
                        and not stages.duplicated(KEY + ["stage_id"]).any(),
                        f"calendar/three-stage support failed: {year} {start}")
                if year == anchor_year:
                    baseline_frame = season.sort_values(["lat", "lon"]).reset_index(drop=True)
                elif baseline_frame is not None and len(season):
                    ordered = season.sort_values(["lat", "lon"]).reset_index(drop=True)
                    require(np.array_equal(ordered[["lat", "lon"]].values,
                                           baseline_frame[["lat", "lon"]].values),
                            f"cross-year calendar cells shifted: {year} {start}")
                    rain_changed += int(np.count_nonzero(
                        ordered.precip_mm.to_numpy() != baseline_frame.precip_mm.to_numpy()))
                    temperature_changed += int(np.count_nonzero(
                        ordered.tmean_c.to_numpy() != baseline_frame.tmean_c.to_numpy()))
                if pilot_required and start == 100 and year in range(2092, 2096):
                    for label, frame in frames.items():
                        sort_key = KEY + (["stage_id"] if label == "stages" else [])
                        other = pilot_frames[label].loc[pilot_frames[label].harvest_year == year]
                        pd.testing.assert_frame_equal(
                            frame.sort_values(sort_key).reset_index(drop=True),
                            other.sort_values(sort_key).reset_index(drop=True), check_exact=True,
                        )
                        pilot_checks += 1
                count_season += len(season)
                count_stages += len(stages)
    require(rain_changed > 0 and temperature_changed > 0,
            "cross-year weather features did not change")
    require(pilot_checks == (8 if pilot_required else 0)
            and count_season == sum(manifests[y]["season_rows"] for y in years)
            and count_stages == sum(manifests[y]["stage_rows"] for y in years),
            "global counts or exact pilot parity failed")
    result = {
        "schema": f"{prefix}_{scenario}_{anchor_year}_{years[-1]}_mai_noirr_crossyear_source_qc_v1",
        "status": "passed_source_only_not_gmt_response_yield_damage_or_scc",
        "esm": esm, "scenario": scenario, "years": list(years), "tiles_per_year": 36,
        "season_rows": count_season, "stage_rows": count_stages,
        f"rain_values_different_from_{anchor_year}": rain_changed,
        f"temperature_values_different_from_{anchor_year}": temperature_changed,
        "exact_four_year_pilot_frame_comparisons": pilot_checks,
        "fixed_raw_daily_checks_in_each_year": 21,
        "no_yield_data_read": True,
    }
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
