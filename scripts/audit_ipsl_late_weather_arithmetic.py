#!/usr/bin/env python3
"""Independent grouped-table arithmetic check of additional-ESM weather."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from audit_gfdl_2032_2039_maize_crossyear import digest, require
from continue_isimip3b_global_maize_tiles import destination
from diagnose_ipsl_late_weather_window import ESM, FEATURES, OUT, SCENARIOS, SEASON, STAGE, YEARS
from run_gfdl_single_year_global_tile_pilot import ROOT


AUDIT = ROOT / "data/interim/ipsl_late_window_weather_arithmetic_audit_20260917.json"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--esm", choices=(ESM, "mpi-esm1-2-hr", "gfdl-esm4", "mri-esm2-0"), default=ESM)
    parser.add_argument("--source", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    esm = args.esm
    prefix = {ESM: "ipsl", "mpi-esm1-2-hr": "mpi",
              "gfdl-esm4": "gfdl", "mri-esm2-0": "mri"}[esm]
    source = (args.source.resolve() if args.source is not None else
              ROOT / f"data/interim/{prefix}_late_window_weather_diagnostic_20260917.json")
    output = (args.output.resolve() if args.output is not None else
              ROOT / f"data/interim/{prefix}_late_window_weather_arithmetic_audit_20260917.json")
    require(source.is_relative_to(ROOT / "data/interim")
            and output.is_relative_to(ROOT / "data/interim"),
            "arithmetic inputs/outputs must remain ignored interim data")
    if output.exists():
        raise FileExistsError(output)
    saved = json.loads(source.read_text())
    require(saved["schema"] == f"{prefix}_late_unweighted_crop_calendar_weather_diagnostic_v1"
            and saved["status"] == "descriptive_source_only_not_forced_response_yield_damage_or_scc"
            and saved["esm"] == esm and saved["years"] == list(YEARS)
            and saved["calendar_cells"] == 67420,
            "IPSL diagnostic identity mismatch")
    for scenario in SCENARIOS:
        current_qc = ROOT / f"data/interim/{esm}_{scenario}_2092_2099_mai_noirr_crossyear_qc_20260921.json"
        legacy_qc = ROOT / f"data/interim/{esm}_{scenario}_2092_2099_mai_noirr_crossyear_qc_20260917.json"
        qc = current_qc if current_qc.exists() else legacy_qc
        require(digest(qc) == saved["source_crossyear_audit_sha256"][scenario],
                f"source audit changed: {scenario}")
    labels = ("ssp370_minus_ssp126", "ssp585_minus_ssp126")
    parts = {label: {name: [] for name in FEATURES} for label in labels}
    cell_count = 0
    for start in range(0, 360, 10):
        averaged = {}
        for scenario in SCENARIOS:
            seasons, stages = [], []
            for year in YEARS:
                tile = destination(esm, scenario, year) / f"lat{start:03d}_{start+10:03d}"
                seasons.append(pd.read_parquet(tile / "season.parquet", columns=["lat", "lon", *SEASON]))
                stages.append(pd.read_parquet(tile / "stages.parquet",
                                              columns=["lat", "lon", "stage_id", "precip_mm"]))
            year_mean = pd.concat(seasons, ignore_index=True).groupby(["lat", "lon"], sort=True)[
                list(SEASON)].agg(["mean", "count"])
            require(np.all(year_mean.loc[:, (slice(None), "count")].to_numpy() == 8),
                    "season cell lacks eight years")
            frame = year_mean.loc[:, (slice(None), "mean")].droplevel(1, axis=1)
            stage_mean = pd.concat(stages, ignore_index=True).groupby(
                ["lat", "lon", "stage_id"], sort=True).precip_mm.agg(["mean", "count"])
            require(np.all(stage_mean["count"] == 8), "stage cell lacks eight years")
            pivot = stage_mean["mean"].unstack("stage_id")
            if frame.empty:
                require(pivot.empty, "stage without season")
                for name in STAGE:
                    frame[name] = np.empty(0, dtype=np.float64)
            else:
                require(pivot.columns.tolist() == [1, 2, 3]
                        and pivot.index.equals(frame.index), "stage/season support differs")
                for i, name in enumerate(STAGE, 1):
                    frame[name] = pivot[i]
            require(np.allclose(frame.precip_mm.to_numpy(dtype=np.float64),
                                frame.loc[:, list(STAGE)].sum(axis=1).to_numpy(dtype=np.float64),
                                atol=1e-6, rtol=1e-9), "stage mean rain not additive")
            averaged[scenario] = frame
        baseline = averaged["ssp126"].index
        cell_count += len(baseline)
        require(all(frame.index.equals(baseline) for frame in averaged.values()),
                "cross-scenario calendar support differs")
        for scenario in ("ssp370", "ssp585"):
            label = f"{scenario}_minus_ssp126"
            difference = averaged[scenario] - averaged["ssp126"]
            for name in FEATURES:
                parts[label][name].append(difference[name].to_numpy(dtype=np.float64))
    require(cell_count == 67420, "global calendar support incomplete")
    checks = 0
    for label, features in parts.items():
        for name, tiles in features.items():
            values = np.concatenate(tiles)
            require(len(values) == cell_count and np.isfinite(values).all(),
                    "invalid contrast values")
            independent = {
                "equal_cell_mean": np.average(values),
                "equal_cell_median": np.percentile(values, 50),
                "equal_cell_p05": np.percentile(values, 5),
                "equal_cell_p95": np.percentile(values, 95),
                "fraction_cells_positive": np.count_nonzero(values > 0) / len(values),
            }
            for statistic, value in independent.items():
                require(np.isclose(value, saved["contrast_statistics"][label][name][statistic],
                                   atol=1e-8, rtol=1e-10),
                        f"independent arithmetic mismatch: {label} {name} {statistic}")
                checks += 1
    output.write_text(json.dumps({
        "schema": f"{prefix}_late_independent_grouped_arithmetic_audit_v1",
        "status": "passed_descriptive_weather_only_not_forced_response_yield_damage_or_scc",
        "diagnostic_sha256": digest(source), "equal_calendar_cells": cell_count,
        "independent_statistic_comparisons": checks, "no_yield_data_read": True,
    }, indent=2, sort_keys=True) + "\n")
    print(f"independent {esm} grouped-table audit passed: {checks} statistics")


if __name__ == "__main__":
    main()
