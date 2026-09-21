#!/usr/bin/env python3
"""Bounded, source-only UKESM rainfed-maize climate-window contrasts.

Protocol: UKESM_SIX_WINDOW_WEATHER_DIAGNOSTIC_PROTOCOL_20260917.md.
No crop yields, crop weights, damage coefficients, or SCC inputs are read.
"""
from __future__ import annotations

import json
import tomllib

import numpy as np
import pandas as pd

from audit_gfdl_2032_2039_maize_crossyear import digest, require
from continue_isimip3b_global_maize_tiles import SOURCES, destination
from run_gfdl_single_year_global_tile_pilot import ROOT


OUT = ROOT / "data/interim/ukesm_six_window_weather_diagnostic_20260917.json"
SCENARIOS = ("ssp126", "ssp370", "ssp585")
WINDOWS = {"mid": tuple(range(2042, 2050)), "late": tuple(range(2092, 2100))}
SEASON = ("precip_mm", "wet_days_n", "cdd_max_days", "rx1day_mm", "rx5day_mm", "tmean_c")
STAGE = tuple(f"stage_{i}_precip_mm" for i in (1, 2, 3))
FEATURES = SEASON + STAGE
KEY = ("lat", "lon", "crop", "irrigation")


def ordered(path, keys):
    return pd.read_parquet(path).sort_values(list(keys)).reset_index(drop=True)


def summaries(values):
    values = np.asarray(values, dtype=np.float64)
    require(np.isfinite(values).all(), "nonfinite cell contrasts")
    return {
        "equal_cell_mean": float(np.mean(values)),
        "equal_cell_median": float(np.median(values)),
        "equal_cell_p05": float(np.quantile(values, .05)),
        "equal_cell_p95": float(np.quantile(values, .95)),
        "fraction_cells_positive": float(np.mean(values > 0)),
    }


def main():
    if OUT.exists():
        raise FileExistsError(OUT)
    qc_hashes = {}
    gmst = {}
    for scenario in SCENARIOS:
        gmst[scenario] = {}
        for window, years in WINDOWS.items():
            qc = ROOT / f"data/interim/ukesm_{scenario}_{years[0]}_{years[-1]}_mai_noirr_crossyear_qc_20260917.json"
            record = json.loads(qc.read_text())
            require(record["status"] == "passed_source_only_not_gmt_response_yield_damage_or_scc"
                    and record["schema"] == f"ukesm_{scenario}_{years[0]}_{years[-1]}_mai_noirr_crossyear_source_qc_v1"
                    and record.get("scenario", scenario) == scenario and record["years"] == list(years)
                    and record["tiles_per_year"] == 36
                    and record["season_rows"] == 539360
                    and record["stage_rows"] == 1618080,
                    f"incomplete eight-year source audit: {scenario} {window}")
            qc_hashes[f"{scenario}_{window}"] = digest(qc)
            receipt_path = SOURCES[("ukesm1-0-ll", scenario, years[0])]
            receipt = tomllib.loads(receipt_path.read_text())
            source = receipt["same_realization_gmst"]
            path = ROOT / source["output"]
            require(path.is_file() and digest(path) == source["output_sha256"],
                    f"GMST digest changed: {scenario} {window}")
            frame = pd.read_parquet(path).sort_values("year")
            require((receipt["esm"].lower(), receipt["member"], receipt["scenario"])
                    == ("ukesm1-0-ll", "r1i1p1f2", scenario)
                    and frame.year.tolist() == source["years"]
                    and frame.daily_count.tolist() == source["daily_counts"]
                    and np.allclose(frame.gmst_value_k, source["gmst_values_k"], atol=1e-10, rtol=0)
                    and set(frame.esm_id.str.lower()) == {"ukesm1-0-ll"}
                    and set(frame.member_id) == {"r1i1p1f2"}
                    and set(frame.scenario) == {scenario}
                    and set(frame.gmst_source_id) == {source["source_id"]}
                    and set(years).issubset(set(frame.year)),
                    f"GMST values/realization mismatch: {scenario} {window}")
            gmst[scenario][window] = float(frame.set_index("year").loc[list(years), "gmst_value_k"].mean())

    contrasts = {f"{scenario}_{window}_minus_ssp126_{window}": {name: [] for name in FEATURES}
                 for window in WINDOWS for scenario in ("ssp370", "ssp585")}
    contrasts.update({f"{scenario}_late_minus_mid": {name: [] for name in FEATURES}
                      for scenario in SCENARIOS})
    cell_total = 0
    for start in range(0, 360, 10):
        means = {}
        reference_keys = None
        for scenario in SCENARIOS:
            for window, years in WINDOWS.items():
                data = {name: [] for name in FEATURES}
                for year in years:
                    tile = destination("ukesm1-0-ll", scenario, year) / f"lat{start:03d}_{start+10:03d}"
                    manifest = json.loads((tile.parent / "global_manifest.json").read_text())
                    record = manifest["tiles"][start // 10]
                    require((manifest["esm"], manifest["member"], manifest["scenario"],
                             manifest["harvest_year"], record["lat_start"], record["lat_stop"])
                            == ("ukesm1-0-ll", "r1i1p1f2", scenario, year, start, start+10)
                            and record == json.loads((tile / "validation.json").read_text()),
                            f"manifest/tile changed: {scenario} {year} {start}")
                    spath, tpath = tile / "season.parquet", tile / "stages.parquet"
                    require(digest(spath) == record["season_sha256"]
                            and digest(tpath) == record["stages_sha256"],
                            f"feature hash changed: {scenario} {year} {start}")
                    season = ordered(spath, KEY)
                    stages = ordered(tpath, KEY + ("stage_id",))
                    keys = season.loc[:, KEY].to_numpy()
                    if reference_keys is None:
                        reference_keys = keys
                    else:
                        require(np.array_equal(keys, reference_keys),
                                f"calendar cell shifted: {scenario} {year} {start}")
                    require(len(season) == record["season_rows"]
                            and len(stages) == 3 * len(season)
                            and set(season.harvest_year) <= {year}
                            and set(stages.harvest_year) <= {year}
                            and np.array_equal(stages.stage_id.to_numpy().reshape(-1, 3),
                                               np.tile(np.array([1, 2, 3]), (len(season), 1)))
                            and np.array_equal(stages.loc[:, KEY].to_numpy().reshape(-1, 3, len(KEY)),
                                               np.repeat(keys[:, None, :], 3, axis=1)),
                            f"stage/season keys shifted: {scenario} {year} {start}")
                    stage_rain = stages.precip_mm.to_numpy(dtype=np.float64).reshape(-1, 3)
                    require(np.allclose(stage_rain.sum(axis=1),
                                        season.precip_mm.to_numpy(dtype=np.float64), atol=1e-6, rtol=1e-9),
                            f"stage rain not additive: {scenario} {year} {start}")
                    for name in SEASON:
                        data[name].append(season[name].to_numpy(dtype=np.float64))
                    for i, name in enumerate(STAGE):
                        data[name].append(stage_rain[:, i])
                means[(scenario, window)] = {name: np.mean(np.stack(data[name]), axis=0)
                                             for name in FEATURES}
        cell_total += len(reference_keys)
        for window in WINDOWS:
            for scenario in ("ssp370", "ssp585"):
                label = f"{scenario}_{window}_minus_ssp126_{window}"
                for name in FEATURES:
                    contrasts[label][name].append(means[(scenario, window)][name] -
                                                   means[("ssp126", window)][name])
        for scenario in SCENARIOS:
            label = f"{scenario}_late_minus_mid"
            for name in FEATURES:
                contrasts[label][name].append(means[(scenario, "late")][name] -
                                               means[(scenario, "mid")][name])
    require(cell_total == 67420, "full calendar support incomplete")
    results = {label: {name: summaries(np.concatenate(parts)) for name, parts in fields.items()}
               for label, fields in contrasts.items()}
    for label, fields in contrasts.items():
        require(np.allclose(np.concatenate(fields["precip_mm"]),
                            sum(np.concatenate(fields[name]) for name in STAGE),
                            atol=1e-6, rtol=1e-9), f"window stage rain mismatch: {label}")
    OUT.write_text(json.dumps({
        "schema": "ukesm_six_window_unweighted_crop_calendar_weather_diagnostic_v1",
        "status": "descriptive_source_only_not_forced_response_yield_damage_or_scc",
        "esm": "ukesm1-0-ll", "member": "r1i1p1f2", "crop": "mai", "irrigation": "noirr",
        "window_years": {name: list(years) for name, years in WINDOWS.items()},
        "calendar_cells_per_scenario_window": cell_total,
        "source_crossyear_audit_sha256": qc_hashes,
        "same_realization_eight_year_mean_gmst_k": gmst,
        "contrast_statistics": results,
        "weighting": "equal-calendar-cell, no land-area or crop-production weights",
        "no_yield_data_read": True,
    }, indent=2, sort_keys=True) + "\n")
    print(f"saved seven weather-only comparisons over {cell_total} cells to {OUT}")


if __name__ == "__main__":
    main()
