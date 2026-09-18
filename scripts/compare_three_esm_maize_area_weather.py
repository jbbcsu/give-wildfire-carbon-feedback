#!/usr/bin/env python3
"""Fixed-MIRCA-area direct-daily maize weather contrasts; no yield or SCC."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import shutil

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
INTERIM = ROOT / "data/interim"
WEIGHTS = INTERIM / "mirca_os_v2/irrigation_shares_2000.parquet"
WEIGHTS_SHA = "7512ffc580928a03f75bbce5f3d4263c9bb2c631a8ff04075973acb4b149e4ba"
ESMS = ("ukesm1-0-ll", "ipsl-cm6a-lr", "mpi-esm1-2-hr")
SCENARIOS = ("ssp126", "ssp370", "ssp585")
YEARS = tuple(range(2092, 2100))
FEATURES = ("precip_mm", "stage1_precip_mm", "stage2_precip_mm", "stage3_precip_mm",
            "wet_days_n", "cdd_max_days", "rx1day_mm", "rx5day_mm", "tmean_c")
SEASON_COLUMNS = ("lat", "lon_360", "precip_mm", "wet_days_n", "cdd_max_days",
                  "rx1day_mm", "rx5day_mm", "tmean_c")
STAGE_COLUMNS = ("lat", "lon_360", "stage_id", "precip_mm", "stage_fractions")


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def load_weights():
    if sha(WEIGHTS) != WEIGHTS_SHA:
        raise ValueError("fixed MIRCA-OS source changed")
    frame = pd.read_parquet(WEIGHTS, columns=["lat", "lon_360", "crop", "irrigation",
                                              "rainfed_area_ha", "weight_vintage", "weight_source_id"])
    frame = frame.loc[frame.crop.eq("mai") & frame.irrigation.eq("noirr")].copy()
    if (len(frame) != 33362 or set(frame.weight_vintage) != {"fixed_2000"}
            or frame[["lat", "lon_360"]].duplicated().any()
            or not frame.rainfed_area_ha.map(math.isfinite).all()
            or frame.rainfed_area_ha.lt(0).any()):
        raise ValueError("MIRCA maize rainfed weights differ")
    positive = frame.loc[frame.rainfed_area_ha.gt(0)]
    if len(positive) != 30821:
        raise ValueError("fixed rainfed-maize positive-area cell count changed")
    weights = {(float(row.lat), float(row.lon_360)): float(row.rainfed_area_ha)
               for row in positive.itertuples(index=False)}
    return weights, float(positive.rainfed_area_ha.sum())


def source_directory(esm, scenario, year):
    return INTERIM / f"isimip3b_global_{esm}_{scenario}_{year}_mai_noirr_full_20260917"


def parse_tile(season_path, stages_path, expected_season_sha, expected_stage_sha, weights):
    if sha(season_path) != expected_season_sha or sha(stages_path) != expected_stage_sha:
        raise ValueError("source tile checksum differs")
    season = pd.read_parquet(season_path, columns=list(SEASON_COLUMNS))
    stages = pd.read_parquet(stages_path, columns=list(STAGE_COLUMNS))
    if len(stages) != 3*len(season) or season[["lat", "lon_360"]].duplicated().any():
        raise ValueError("tile season/stage count or key differs")
    stage_map = {}
    for row in stages.itertuples(index=False):
        key = (float(row.lat), float(row.lon_360))
        if row.stage_id not in (1, 2, 3) or row.stage_fractions != "0,0.3,0.7,1":
            raise ValueError("stage definition differs")
        bucket = stage_map.setdefault(key, {})
        if row.stage_id in bucket or not math.isfinite(row.precip_mm) or row.precip_mm < 0:
            raise ValueError("stage rainfall invalid or duplicated")
        bucket[int(row.stage_id)] = float(row.precip_mm)
    if len(stage_map) != len(season):
        raise ValueError("stage/season support differs")
    area_numerators = {feature: 0.0 for feature in FEATURES}
    equal_sums = {feature: 0.0 for feature in FEATURES}
    matched = set()
    for row in season.itertuples(index=False):
        key = (float(row.lat), float(row.lon_360))
        stages3 = stage_map.get(key)
        if stages3 is None or set(stages3) != {1, 2, 3}:
            raise ValueError("missing or duplicate stage key")
        fields = {"precip_mm": float(row.precip_mm),
                  "stage1_precip_mm": stages3[1], "stage2_precip_mm": stages3[2],
                  "stage3_precip_mm": stages3[3],
                  "wet_days_n": float(row.wet_days_n),
                  "cdd_max_days": float(row.cdd_max_days),
                  "rx1day_mm": float(row.rx1day_mm), "rx5day_mm": float(row.rx5day_mm),
                  "tmean_c": float(row.tmean_c)}
        if (not all(math.isfinite(value) for value in fields.values())
                or any(fields[name] < 0 for name in FEATURES if name != "tmean_c")
                or not math.isclose(sum(stages3.values()), fields["precip_mm"], abs_tol=2e-5, rel_tol=1e-7)):
            raise ValueError("source weather physicality or stage sum failed")
        weight = weights.get(key)
        if weight is not None:
            matched.add(key)
            for feature, value in fields.items():
                area_numerators[feature] += weight*value
                equal_sums[feature] += value
    return {"calendar_rows": len(season), "matched_rows": len(matched),
            "matched_area_ha": math.fsum(weights[key] for key in matched),
            "area_numerators": area_numerators, "equal_sums": equal_sums}, matched


def read_panel(esm, scenario, year, weights):
    directory = source_directory(esm, scenario, year)
    manifest_file, validation_file = directory / "global_manifest.json", directory / "independent_global_validation.json"
    manifest, validation = json.loads(manifest_file.read_text()), json.loads(validation_file.read_text())
    if (manifest["esm"] != esm or manifest["scenario"] != scenario or manifest["harvest_year"] != year
            or manifest["season_rows"] != 67420 or manifest["stage_rows"] != 202260
            or validation["global_manifest_sha256"] != sha(manifest_file)
            or validation["season_rows"] != 67420 or validation["stage_rows"] != 202260
            or not str(validation["status"]).startswith("passed_") or len(manifest["tiles"]) != 36):
        raise ValueError("independent global feature source gate failed")
    tiles = []
    matched = set()
    for tile in manifest["tiles"]:
        start, stop = tile["lat_start"], tile["lat_stop"]
        folder = directory / f"lat{start:03d}_{stop:03d}"
        ledger, subset = parse_tile(folder / "season.parquet", folder / "stages.parquet",
                                    tile["season_sha256"], tile["stages_sha256"], weights)
        if len(subset & matched):
            raise ValueError("same positive-area key in multiple tiles")
        matched.update(subset)
        ledger.update(lat_start=start, lat_stop=stop)
        tiles.append(ledger)
    if sum(row["calendar_rows"] for row in tiles) != 67420:
        raise ValueError("annual source calendar count differs")
    output = {"esm": esm, "scenario": scenario, "year": year,
              "global_manifest_sha256": sha(manifest_file),
              "independent_validation_sha256": sha(validation_file),
              "tile_ledgers": tiles, "matched_count": len(matched),
              "matched_area_ha": math.fsum(weights[key] for key in matched)}
    return output, matched


def summarize(records, matched_count, matched_area):
    for row in records:
        annual = {}
        for feature in FEATURES:
            annual[feature] = {
                "area_weighted": math.fsum(tile["area_numerators"][feature] for tile in row["tile_ledgers"])/matched_area,
                "equal_matched_cell": math.fsum(tile["equal_sums"][feature] for tile in row["tile_ledgers"])/matched_count,
            }
        row["annual_means"] = annual
        if not math.isclose(annual["precip_mm"]["area_weighted"],
                            sum(annual[f"stage{s}_precip_mm"]["area_weighted"] for s in (1, 2, 3)),
                            abs_tol=1e-5, rel_tol=1e-9):
            raise ValueError("area-weighted stage totals do not reconcile")
    contrasts = {}
    for esm in ESMS:
        contrasts[esm] = {}
        for scenario in SCENARIOS[1:]:
            contrasts[esm][scenario] = {}
            for feature in FEATURES:
                contrasts[esm][scenario][feature] = {}
                for measure in ("area_weighted", "equal_matched_cell"):
                    def mean(s):
                        values = [row["annual_means"][feature][measure] for row in records
                                  if row["esm"] == esm and row["scenario"] == s]
                        if len(values) != 8:
                            raise ValueError("missing fixed eight-year panel")
                        return math.fsum(values)/8
                    contrasts[esm][scenario][feature][measure] = mean(scenario) - mean("ssp126")
    return contrasts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    if (out.exists() or not out.is_relative_to(INTERIM)
            or shutil.disk_usage(ROOT).free < 130*2**30):
        parser.error("fresh ignored output and disk reserve required")
    weights, original_area = load_weights()
    records = []
    common = None
    for esm in ESMS:
        for scenario in SCENARIOS:
            for year in YEARS:
                row, matched = read_panel(esm, scenario, year, weights)
                if common is None:
                    common = matched
                elif matched != common:
                    raise ValueError(f"positive-area climate support differs: {esm} {scenario} {year}")
                records.append(row)
                print("validated", esm, scenario, year, len(matched), flush=True)
    count = len(common)
    area = math.fsum(weights[key] for key in common)
    if count != 30654 or not (0 < area <= original_area):
        raise ValueError("fixed matched support differs from key-only pilot")
    contrasts = summarize(records, count, area)
    output = {"status": "three_esm_fixed_maize_area_weather_only_not_forced_response_or_scc",
              "crop": "mai", "irrigation": "noirr", "weight_year": 2000,
              "weights_sha256": WEIGHTS_SHA, "original_positive_area_cells": len(weights),
              "original_positive_area_ha": original_area,
              "matched_calendar_cells": count, "matched_area_ha": area,
              "matched_area_fraction": area/original_area,
              "years": list(YEARS), "esms": list(ESMS), "scenarios": list(SCENARIOS),
              "annual_panels": records, "scenario_minus_ssp126": contrasts,
              "no_yield_data_read": True, "yield_damage_scc_estimated": False}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(output, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"status": output["status"], "matched_area_fraction": output["matched_area_fraction"],
                      "scenario_minus_ssp126": contrasts}))


if __name__ == "__main__":
    main()
