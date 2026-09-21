#!/usr/bin/env python3
"""Predeclared additional-ESM 2092--99 maize weather comparisons, source only."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import tomllib

import numpy as np
import pandas as pd

from audit_gfdl_2032_2039_maize_crossyear import digest, require
from continue_isimip3b_global_maize_tiles import SOURCES, destination
from diagnose_ukesm_six_weather_windows import FEATURES, KEY, SCENARIOS, SEASON, STAGE, ordered, summaries
from run_gfdl_single_year_global_tile_pilot import ROOT


ESM = "ipsl-cm6a-lr"
YEARS = tuple(range(2092, 2100))
OUT = ROOT / "data/interim/ipsl_late_window_weather_diagnostic_20260917.json"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--esm", choices=(ESM, "mpi-esm1-2-hr", "gfdl-esm4", "mri-esm2-0"), default=ESM)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    esm = args.esm
    prefix = {ESM: "ipsl", "mpi-esm1-2-hr": "mpi",
              "gfdl-esm4": "gfdl", "mri-esm2-0": "mri"}[esm]
    out = (args.output.resolve() if args.output is not None else
           ROOT / f"data/interim/{prefix}_late_window_weather_diagnostic_20260917.json")
    require(out.is_relative_to(ROOT / "data/interim"), "diagnostic output must remain ignored interim data")
    if out.exists():
        raise FileExistsError(out)
    audits, gmst = {}, {}
    for scenario in SCENARIOS:
        current_qc = ROOT / f"data/interim/{esm}_{scenario}_2092_2099_mai_noirr_crossyear_qc_20260921.json"
        legacy_qc = ROOT / f"data/interim/{esm}_{scenario}_2092_2099_mai_noirr_crossyear_qc_20260917.json"
        qc = current_qc if current_qc.exists() else legacy_qc
        report = json.loads(qc.read_text())
        require((report["schema"], report["status"], report["esm"], report["scenario"],
                 report["years"], report["season_rows"], report["stage_rows"])
                == (f"{esm}_{scenario}_2092_2099_mai_noirr_crossyear_source_qc_v1",
                    "passed_source_only_not_gmt_response_yield_damage_or_scc",
                    esm, scenario, list(YEARS), 539360, 1618080),
                f"eight-year source audit incomplete: {scenario}")
        audits[scenario] = digest(qc)
        receipt = tomllib.loads(SOURCES[(esm, scenario, 2092)].read_text())
        pinned = receipt["same_realization_gmst"]
        path = ROOT / pinned["output"]
        require(path.is_file() and digest(path) == pinned["output_sha256"],
                f"GMST output hash changed: {scenario}")
        frame = pd.read_parquet(path).sort_values("year")
        require((receipt["esm"].lower(), receipt["member"], receipt["scenario"])
                == (esm, "r1i1p1f1", scenario)
                and frame.year.tolist() == pinned["years"]
                and frame.daily_count.tolist() == pinned["daily_counts"]
                and np.allclose(frame.gmst_value_k, pinned["gmst_values_k"], atol=1e-10, rtol=0)
                and set(frame.esm_id.str.lower()) == {esm}
                and set(frame.member_id) == {"r1i1p1f1"}
                and set(frame.scenario) == {scenario}
                and set(frame.gmst_source_id) == {pinned["source_id"]}
                and set(YEARS).issubset(set(frame.year)),
                f"GMST realization/value mismatch: {scenario}")
        gmst[scenario] = float(frame.set_index("year").loc[list(YEARS), "gmst_value_k"].mean())

    differences = {f"{scenario}_minus_ssp126": {name: [] for name in FEATURES}
                   for scenario in ("ssp370", "ssp585")}
    cells = 0
    for start in range(0, 360, 10):
        means = {}
        reference = None
        for scenario in SCENARIOS:
            values = {name: [] for name in FEATURES}
            for year in YEARS:
                tile = destination(esm, scenario, year) / f"lat{start:03d}_{start+10:03d}"
                manifest = json.loads((tile.parent / "global_manifest.json").read_text())
                record = manifest["tiles"][start // 10]
                require((manifest["esm"], manifest["member"], manifest["scenario"],
                         manifest["harvest_year"], record["lat_start"], record["lat_stop"])
                        == (esm, "r1i1p1f1", scenario, year, start, start+10)
                        and record == json.loads((tile / "validation.json").read_text()),
                        f"tile identity changed: {scenario} {year} {start}")
                spath, tpath = tile / "season.parquet", tile / "stages.parquet"
                require(digest(spath) == record["season_sha256"]
                        and digest(tpath) == record["stages_sha256"],
                        f"feature hash changed: {scenario} {year} {start}")
                season = ordered(spath, KEY)
                stages = ordered(tpath, KEY + ("stage_id",))
                keys = season.loc[:, KEY].to_numpy()
                if reference is None:
                    reference = keys
                else:
                    require(np.array_equal(keys, reference), "scenario-year calendar keys shifted")
                require(len(stages) == 3 * len(season)
                        and len(season) == record["season_rows"]
                        and set(season.harvest_year) <= {year}
                        and set(stages.harvest_year) <= {year}
                        and np.array_equal(stages.stage_id.to_numpy().reshape(-1, 3),
                                           np.tile([1, 2, 3], (len(season), 1)))
                        and np.array_equal(stages.loc[:, KEY].to_numpy().reshape(-1, 3, len(KEY)),
                                           np.repeat(keys[:, None, :], 3, axis=1)),
                        f"stage/season support changed: {scenario} {year} {start}")
                rain = stages.precip_mm.to_numpy(dtype=np.float64).reshape(-1, 3)
                require(np.allclose(rain.sum(axis=1),
                                    season.precip_mm.to_numpy(dtype=np.float64), atol=1e-6, rtol=1e-9),
                        "stage precipitation does not sum to season")
                for name in SEASON:
                    values[name].append(season[name].to_numpy(dtype=np.float64))
                for i, name in enumerate(STAGE):
                    values[name].append(rain[:, i])
            means[scenario] = {name: np.mean(np.stack(parts), axis=0)
                               for name, parts in values.items()}
        cells += len(reference)
        for scenario in ("ssp370", "ssp585"):
            label = f"{scenario}_minus_ssp126"
            for name in FEATURES:
                differences[label][name].append(means[scenario][name] - means["ssp126"][name])
    require(cells == 67420, "full crop-calendar cell support incomplete")
    for label, fields in differences.items():
        require(np.allclose(np.concatenate(fields["precip_mm"]),
                            sum(np.concatenate(fields[name]) for name in STAGE),
                            atol=1e-6, rtol=1e-9), f"stage rainfall contrast mismatch: {label}")
    out.write_text(json.dumps({
        "schema": f"{prefix}_late_unweighted_crop_calendar_weather_diagnostic_v1",
        "status": "descriptive_source_only_not_forced_response_yield_damage_or_scc",
        "esm": esm, "member": "r1i1p1f1", "years": list(YEARS),
        "calendar_cells": cells, "crop": "mai", "irrigation": "noirr",
        "source_crossyear_audit_sha256": audits,
        "same_realization_eight_year_mean_gmst_k": gmst,
        "contrast_statistics": {label: {name: summaries(np.concatenate(parts))
                                        for name, parts in fields.items()}
                                for label, fields in differences.items()},
        "weighting": "equal-calendar-cell, no land-area or crop-production weights",
        "no_yield_data_read": True,
    }, indent=2, sort_keys=True) + "\n")
    print(f"saved two {esm} source-only weather comparisons over {cells} cells")


if __name__ == "__main__":
    main()
