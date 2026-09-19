#!/usr/bin/env python3
"""Same-cell historical weather-domain support for future rainfed maize.

This reads weather only. It estimates no yield response, damages, or SCC.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import shutil

import numpy as np
import pandas as pd
import pyarrow.parquet as pq


ROOT = Path(__file__).resolve().parents[1]
INTERIM = ROOT / "data/interim"
AREA_RESULT = INTERIM / "three_esm_maize_area_weather_20260918/result.json"
AREA_RESULT_SHA = "027bd174738cb8de16c218b4674c33e7360c88f50bf719ef9a901769976b44f1"
WEIGHTS = INTERIM / "mirca_os_v2/irrigation_shares_2000.parquet"
WEIGHTS_SHA = "7512ffc580928a03f75bbce5f3d4263c9bb2c631a8ff04075973acb4b149e4ba"
HIST = (
    (INTERIM / "mai_noirr_1982_1989_stage_estimation_panel_v2.parquet", "2a144ce55416be5c7e452fc0e64f505b8e53413a11365b75da3c2f92a3b61bae", 1982, 1989, "wide"),
    (INTERIM / "continuous_global_panel_1982_2016_v1/assembled_middle_1990_2011/direct_season/mai_noirr_1990_2011.parquet", "6554bf09890e3d3fc6791d5f650259a7aa28c2c51102091938895204acd64c0e", 1990, 2011, "season"),
    (INTERIM / "continuous_global_panel_1982_2016_v1/assembled_middle_1990_2011/direct_stage/mai_noirr_1990_2011.parquet", "a5f5324f16cd7992b219cb56e6a230c575fc19e2ebdd49b02cc08b1ff0c3b186", 1990, 2011, "stages"),
    (INTERIM / "mai_noirr_2012_2016_features.parquet", "32b127f6a2e8ba14d22cf073ce4ceb2b9f2a9967b18da180591cef8f48552b97", 2012, 2016, "season"),
    (INTERIM / "mai_noirr_2012_2016_stage_features.parquet", "43c7208aa8597f29be767ca999d6b3cce0cc66508f0bbf40bdf404611f8c75d4", 2012, 2016, "stages"),
)
FEATURES = ("precip_mm", "wet_days_n", "cdd_max_days", "rx1day_mm", "rx5day_mm", "tmean_c",
            "stage1_precip_mm", "stage2_precip_mm", "stage3_precip_mm")
SEASON = FEATURES[:6]
STAGES = FEATURES[6:]
YEARS = range(1982, 2017)


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def area_weights_and_support(area_record):
    if sha(WEIGHTS) != WEIGHTS_SHA:
        raise ValueError("fixed area source changed")
    frame = pd.read_parquet(WEIGHTS, columns=["lat", "lon_360", "crop", "irrigation", "rainfed_area_ha"])
    frame = frame.loc[frame.crop.eq("mai") & frame.irrigation.eq("noirr") & frame.rainfed_area_ha.gt(0)]
    weights = {(float(row.lat), float(row.lon_360)): float(row.rainfed_area_ha)
               for row in frame.itertuples(index=False)}
    first = area_record["annual_panels"][0]
    source = INTERIM / f"isimip3b_global_{first['esm']}_{first['scenario']}_{first['year']}_mai_noirr_full_20260917"
    keys = set()
    for tile in first["tile_ledgers"]:
        path = source / f"lat{tile['lat_start']:03d}_{tile['lat_stop']:03d}/season.parquet"
        frame = pd.read_parquet(path, columns=["lat", "lon_360"])
        keys.update((float(a), float(b)) for a, b in zip(frame.lat, frame.lon_360)
                         if (float(a), float(b)) in weights)
    if len(keys) != area_record["matched_calendar_cells"] or len(keys) != 30654:
        raise ValueError("fixed crop-area matched support changed")
    ordered = sorted(keys)
    area = math.fsum(weights[k] for k in ordered)
    if not math.isclose(area, area_record["matched_area_ha"], abs_tol=1e-4):
        raise ValueError("fixed crop-area matched hectares changed")
    return ordered, np.array([weights[k] for k in ordered], dtype=np.float64)


def fill_historical(ordered):
    index = {key: i for i, key in enumerate(ordered)}
    panel = np.full((len(ordered), len(YEARS), len(FEATURES)), np.nan, dtype=np.float64)
    per_source = []
    for path, expected, start, end, kind in HIST:
        if sha(path) != expected:
            raise ValueError("historical weather file changed: " + str(path))
        columns = ["harvest_year", "lat", "lon_360"]
        columns += list(FEATURES if kind == "wide" else (SEASON + ("wet_day_threshold_mm",) if kind == "season" else ("stage_id", "precip_mm", "stage_fractions")))
        if kind == "wide":
            columns.append("wet_day_threshold_mm")
        source_rows, matched_rows = 0, 0
        for batch in pq.ParquetFile(path).iter_batches(batch_size=50000, columns=columns):
            data = batch.to_pydict()
            n = len(data["harvest_year"])
            source_rows += n
            positions = np.fromiter((index.get((float(a), float(b)), -1)
                                     for a, b in zip(data["lat"], data["lon_360"])), dtype=np.int32, count=n)
            chosen = np.flatnonzero(positions >= 0)
            if not len(chosen):
                continue
            matched_rows += len(chosen)
            rows = positions[chosen]
            years = np.array(data["harvest_year"], dtype=np.int16)[chosen]
            if not np.all((start <= years) & (years <= end)):
                raise ValueError("historical year outside source block")
            years = years - 1982
            if kind in ("wide", "season"):
                if len(np.unique(rows.astype(np.int64) * len(YEARS) + years)) != len(rows):
                    raise ValueError("duplicate historical cell-year within batch")
                threshold = np.array(data["wet_day_threshold_mm"], dtype=float)[chosen]
                if not np.all(threshold == 1.0):
                    raise ValueError("historical wet-day threshold changed")
                names = FEATURES if kind == "wide" else SEASON
                for feature_id, name in enumerate(names):
                    values = np.array(data[name], dtype=float)[chosen]
                    if not np.isfinite(values).all() or (name != "tmean_c" and np.any(values < 0)):
                        raise ValueError("historical weather invalid")
                    if not np.isnan(panel[rows, years, feature_id]).all():
                        raise ValueError("duplicate historical cell-year-feature")
                    panel[rows, years, feature_id] = values
            else:
                stage_ids = np.array(data["stage_id"], dtype=int)[chosen]
                if (not np.all((1 <= stage_ids) & (stage_ids <= 3))
                        or any(data["stage_fractions"][int(i)] != "0,0.3,0.7,1" for i in chosen)):
                    raise ValueError("historical stage definition changed")
                values = np.array(data["precip_mm"], dtype=float)[chosen]
                if not np.isfinite(values).all() or np.any(values < 0):
                    raise ValueError("historical stage rainfall invalid")
                ids = 5 + stage_ids
                if len(np.unique((rows.astype(np.int64) * len(YEARS) + years) * len(FEATURES) + ids)) != len(rows):
                    raise ValueError("duplicate historical stage cell-year within batch")
                if not np.isnan(panel[rows, years, ids]).all():
                    raise ValueError("duplicate historical stage cell-year")
                panel[rows, years, ids] = values
        per_source.append({"path": str(path.relative_to(ROOT)), "sha256": expected,
                           "kind": kind, "source_rows": source_rows,
                           "matched_rows": matched_rows})
    if not np.isfinite(panel).all():
        raise ValueError("missing or nonfinite 35-year matched historical weather")
    reconciliation_max_mm = float(np.max(np.abs(panel[:, :, 0] - panel[:, :, 6:9].sum(axis=2))))
    if reconciliation_max_mm > 1e-3:
        raise ValueError(f"historical stage rain does not sum to season: {reconciliation_max_mm}")
    return panel, per_source, reconciliation_max_mm


def bounds(panel):
    lower = np.min(panel, axis=1)
    upper = np.max(panel, axis=1)
    percentiles = np.quantile(panel, (0.05, 0.95), axis=1)
    return lower, upper, percentiles[0], percentiles[1]


def audit_future(panel_rows, ordered, weights, bound):
    index = {key: i for i, key in enumerate(ordered)}
    lower, upper, p05, p95 = bound
    annual = []
    area = math.fsum(weights)
    for source in panel_rows:
        esm, scenario, year = source["esm"], source["scenario"], source["year"]
        directory = INTERIM / f"isimip3b_global_{esm}_{scenario}_{year}_mai_noirr_full_20260917"
        manifest = json.loads((directory / "global_manifest.json").read_text())
        if (sha(directory / "global_manifest.json") != source["global_manifest_sha256"]
                or sha(directory / "independent_global_validation.json") != source["independent_validation_sha256"]):
            raise ValueError("future source receipt changed")
        tile_specs = {x["lat_start"]: x for x in manifest["tiles"]}
        values = np.full((len(ordered), len(FEATURES)), np.nan, dtype=np.float64)
        for tile in source["tile_ledgers"]:
            start, stop = tile["lat_start"], tile["lat_stop"]
            folder = directory / f"lat{start:03d}_{stop:03d}"
            spec = tile_specs[start]
            season_path, stage_path = folder / "season.parquet", folder / "stages.parquet"
            if sha(season_path) != spec["season_sha256"] or sha(stage_path) != spec["stages_sha256"]:
                raise ValueError("future source tile changed")
            season = pd.read_parquet(season_path, columns=["lat", "lon_360", "wet_day_threshold_mm", *SEASON])
            stages = pd.read_parquet(stage_path, columns=["lat", "lon_360", "stage_id", "precip_mm", "stage_fractions"])
            for row in season.itertuples(index=False):
                i = index.get((float(row.lat), float(row.lon_360)))
                if i is None:
                    continue
                if row.wet_day_threshold_mm != 1.0 or not np.isnan(values[i, 0]):
                    raise ValueError("future threshold or duplicate key differs")
                values[i, :6] = [float(getattr(row, name)) for name in SEASON]
            for row in stages.itertuples(index=False):
                i = index.get((float(row.lat), float(row.lon_360)))
                if i is None:
                    continue
                if row.stage_id not in (1, 2, 3) or row.stage_fractions != "0,0.3,0.7,1":
                    raise ValueError("future stage definition differs")
                col = 5 + int(row.stage_id)
                if not np.isnan(values[i, col]):
                    raise ValueError("duplicate future stage")
                values[i, col] = float(row.precip_mm)
        if not np.isfinite(values).all() or np.any(values[:, [0, 1, 2, 3, 4, 6, 7, 8]] < 0):
            raise ValueError("future support or weather physicality differs")
        if not np.allclose(values[:, 0], values[:, 6:9].sum(axis=1), rtol=1e-7, atol=2e-5):
            raise ValueError("future stage rain does not sum to season")
        below = values < lower
        above = values > upper
        outside = (values < p05) | (values > p95)
        flags = {"below_min": below, "above_max": above, "outside_5_95": outside}
        record = {"esm": esm, "scenario": scenario, "year": year,
                  "source_global_manifest_sha256": source["global_manifest_sha256"],
                  "matched_cells": len(ordered), "matched_area_ha": area,
                  "feature_area_fractions": {
                      name: {feature: float(np.sum(weights[mask[:, j]])/area)
                             for j, feature in enumerate(FEATURES)}
                      for name, mask in flags.items()},
                  "any_feature_outside_minmax_area_fraction": float(np.sum(weights[np.any(below | above, axis=1)])/area)}
        annual.append(record)
        print("scored", esm, scenario, year, flush=True)
    return annual


def summarize(annual):
    summary = {}
    for esm in ("ukesm1-0-ll", "ipsl-cm6a-lr", "mpi-esm1-2-hr"):
        summary[esm] = {}
        for scenario in ("ssp126", "ssp370", "ssp585"):
            group = [row for row in annual if row["esm"] == esm and row["scenario"] == scenario]
            if len(group) != 8:
                raise ValueError("future eight-year scenario block incomplete")
            summary[esm][scenario] = {
                "mean_area_fraction": {
                    name: {feature: math.fsum(row["feature_area_fractions"][name][feature] for row in group)/8
                           for feature in FEATURES}
                    for name in ("below_min", "above_max", "outside_5_95")},
                "any_feature_outside_minmax_mean_area_fraction": math.fsum(
                    row["any_feature_outside_minmax_area_fraction"] for row in group)/8,
            }
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    out = args.out_dir.resolve()
    if (out.exists() or not out.is_relative_to(INTERIM)
            or shutil.disk_usage(ROOT).free < 130*2**30):
        parser.error("fresh ignored output and disk reserve required")
    if sha(AREA_RESULT) != AREA_RESULT_SHA:
        raise ValueError("fixed future area-weather result changed")
    area_record = json.loads(AREA_RESULT.read_text())
    ordered, weights = area_weights_and_support(area_record)
    historic, inputs, historical_reconciliation_max_mm = fill_historical(ordered)
    limits = bounds(historic)
    annual = audit_future(area_record["annual_panels"], ordered, weights, limits)
    out.mkdir(parents=True)
    npz = out / "historical_cell_feature_bounds.npz"
    np.savez_compressed(npz, lat=np.array([x[0] for x in ordered]), lon_360=np.array([x[1] for x in ordered]),
                        hectares=weights, **{name: value for name, value in zip(("min", "max", "p05", "p95"), limits)})
    output = {"status": "same_cell_historical_future_weather_support_only_not_yield_damage_scc",
              "future_area_result_sha256": AREA_RESULT_SHA, "historical_inputs": inputs,
              "historical_years": [1982, 2016], "future_years": [2092, 2099],
              "matched_cells": len(ordered), "matched_area_ha": math.fsum(weights),
              "historical_stage_season_max_abs_difference_mm": historical_reconciliation_max_mm,
              "features": list(FEATURES), "bounds_sha256": sha(npz),
              "annual": annual, "esm_scenario_summary": summarize(annual),
              "no_yield_magnitude_read": True, "yield_damage_scc_estimated": False}
    (out / "result.json").write_text(json.dumps(output, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"status": output["status"], "matched_cells": len(ordered),
                      "esm_scenario_summary": output["esm_scenario_summary"]}))


if __name__ == "__main__":
    main()
