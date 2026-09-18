#!/usr/bin/env python3
"""Independent audit of fixed-area weather ledger and seven raw source tiles."""
import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
INTERIM = ROOT / "data/interim"
WEIGHT_FILE = INTERIM / "mirca_os_v2/irrigation_shares_2000.parquet"
WEIGHT_SHA = "7512ffc580928a03f75bbce5f3d4263c9bb2c631a8ff04075973acb4b149e4ba"
FEATURES = ("precip_mm", "stage1_precip_mm", "stage2_precip_mm", "stage3_precip_mm",
            "wet_days_n", "cdd_max_days", "rx1day_mm", "rx5day_mm", "tmean_c")
ESMS = ("ukesm1-0-ll", "ipsl-cm6a-lr", "mpi-esm1-2-hr")
SCENARIOS = ("ssp126", "ssp370", "ssp585")
YEARS = tuple(range(2092, 2100))
SAMPLES = (("ukesm1-0-ll", "ssp126", 2092), ("ukesm1-0-ll", "ssp370", 2095),
           ("ukesm1-0-ll", "ssp585", 2099), ("ipsl-cm6a-lr", "ssp126", 2092),
           ("ipsl-cm6a-lr", "ssp585", 2099), ("mpi-esm1-2-hr", "ssp126", 2092),
           ("mpi-esm1-2-hr", "ssp585", 2099))


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def close(actual, expected, label, rel=2e-10, abs_=2e-7):
    if not math.isclose(float(actual), float(expected), rel_tol=rel, abs_tol=abs_):
        raise AssertionError(f"{label}: saved {actual}, recomputed {expected}")


def source_tile_check(row, weight_frame, start=190):
    esm, scenario, year = row["esm"], row["scenario"], row["year"]
    directory = INTERIM / f"isimip3b_global_{esm}_{scenario}_{year}_mai_noirr_full_20260917"
    tile = next(x for x in row["tile_ledgers"] if x["lat_start"] == start)
    folder = directory / f"lat{start:03d}_{start+10:03d}"
    season = pd.read_parquet(folder / "season.parquet", columns=["lat", "lon_360", "precip_mm",
        "wet_days_n", "cdd_max_days", "rx1day_mm", "rx5day_mm", "tmean_c"])
    stages = pd.read_parquet(folder / "stages.parquet", columns=["lat", "lon_360", "stage_id", "precip_mm"])
    if len(stages) != 3*len(season):
        raise ValueError("sample stage count differs")
    p = stages.pivot(index=["lat", "lon_360"], columns="stage_id", values="precip_mm")
    if list(p.columns) != [1, 2, 3]:
        raise ValueError("sample stage ids differ")
    p.columns = ["stage1_precip_mm", "stage2_precip_mm", "stage3_precip_mm"]
    full = season.merge(p.reset_index(), on=["lat", "lon_360"], validate="one_to_one")
    if len(full) != len(season):
        raise ValueError("sample stage merge differs")
    matched = full.merge(weight_frame, on=["lat", "lon_360"], how="inner", validate="one_to_one")
    if len(matched) != tile["matched_rows"] or len(season) != tile["calendar_rows"]:
        raise AssertionError("sample tile support differs")
    close(matched.rainfed_area_ha.sum(), tile["matched_area_ha"], "sample matched area")
    checks = 3
    for feature in FEATURES:
        values = matched[feature].to_numpy(dtype=float)
        weights = matched.rainfed_area_ha.to_numpy(dtype=float)
        close(math.fsum((float(v)*float(w) for v, w in zip(values, weights))),
              tile["area_numerators"][feature], "sample area numerator " + feature)
        close(math.fsum(float(v) for v in values), tile["equal_sums"][feature],
              "sample equal sum " + feature)
        checks += 2
    return checks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    source, out = args.result.resolve(), args.out.resolve()
    if (not source.is_relative_to(INTERIM) or not out.is_relative_to(INTERIM) or out.exists()):
        parser.error("ignored source and fresh output required")
    saved = json.loads(source.read_text())
    if (saved["status"] != "three_esm_fixed_maize_area_weather_only_not_forced_response_or_scc"
            or saved["weights_sha256"] != WEIGHT_SHA or sha(WEIGHT_FILE) != WEIGHT_SHA):
        raise ValueError("wrong primary result or weight file changed")
    weights = pd.read_parquet(WEIGHT_FILE, columns=["lat", "lon_360", "crop", "irrigation", "rainfed_area_ha"])
    weights = weights.loc[weights.crop.eq("mai") & weights.irrigation.eq("noirr") & weights.rainfed_area_ha.gt(0),
                          ["lat", "lon_360", "rainfed_area_ha"]]
    if len(weights) != 30821 or weights[["lat", "lon_360"]].duplicated().any():
        raise ValueError("weight support differs")
    close(weights.rainfed_area_ha.sum(), saved["original_positive_area_ha"], "original area")
    if (saved["matched_calendar_cells"] != 30654 or not
            (0 < saved["matched_area_ha"] <= saved["original_positive_area_ha"])):
        raise ValueError("matched support differs")
    close(saved["matched_area_ha"]/saved["original_positive_area_ha"],
          saved["matched_area_fraction"], "matched area fraction")
    records = saved["annual_panels"]
    if len(records) != 72 or len({(r["esm"], r["scenario"], r["year"]) for r in records}) != 72:
        raise ValueError("annual panel matrix incomplete")
    annual_checks = 0
    for row in records:
        if (row["esm"] not in ESMS or row["scenario"] not in SCENARIOS
                or row["year"] not in YEARS or len(row["tile_ledgers"]) != 36):
            raise ValueError("panel identity or tile count differs")
        directory = INTERIM / f"isimip3b_global_{row['esm']}_{row['scenario']}_{row['year']}_mai_noirr_full_20260917"
        manifest_file = directory / "global_manifest.json"
        validation_file = directory / "independent_global_validation.json"
        if (sha(manifest_file) != row["global_manifest_sha256"]
                or sha(validation_file) != row["independent_validation_sha256"]
                or json.loads(validation_file.read_text())["global_manifest_sha256"] != sha(manifest_file)):
            raise ValueError("bound source manifest/validation differs")
        tiles = row["tile_ledgers"]
        if [x["lat_start"] for x in tiles] != list(range(0, 360, 10)):
            raise ValueError("latitude tile order differs")
        if sum(x["calendar_rows"] for x in tiles) != 67420 or sum(x["matched_rows"] for x in tiles) != 30654:
            raise AssertionError("annual tile support differs")
        close(math.fsum(x["matched_area_ha"] for x in tiles), saved["matched_area_ha"], "annual area")
        for feature in FEATURES:
            area_sum = math.fsum(x["area_numerators"][feature] for x in tiles)
            equal_sum = math.fsum(x["equal_sums"][feature] for x in tiles)
            close(area_sum/saved["matched_area_ha"], row["annual_means"][feature]["area_weighted"], "annual weighted " + feature)
            close(equal_sum/30654, row["annual_means"][feature]["equal_matched_cell"], "annual equal " + feature)
            annual_checks += 2
    contrast_checks = 0
    for esm in ESMS:
        for scenario in SCENARIOS[1:]:
            for feature in FEATURES:
                for measure in ("area_weighted", "equal_matched_cell"):
                    current = [r["annual_means"][feature][measure] for r in records if r["esm"] == esm and r["scenario"] == scenario]
                    baseline = [r["annual_means"][feature][measure] for r in records if r["esm"] == esm and r["scenario"] == "ssp126"]
                    if len(current) != 8 or len(baseline) != 8:
                        raise ValueError("scenario year count differs")
                    expected = math.fsum(current)/8 - math.fsum(baseline)/8
                    close(expected, saved["scenario_minus_ssp126"][esm][scenario][feature][measure], "contrast " + feature)
                    contrast_checks += 1
    sample_checks = 0
    for esm, scenario, year in SAMPLES:
        row = next(r for r in records if (r["esm"], r["scenario"], r["year"]) == (esm, scenario, year))
        sample_checks += source_tile_check(row, weights)
    output = {"status": "independent_fixed_area_weather_ledger_and_source_sample_passed",
              "primary_sha256": sha(source), "annual_numeric_checks": annual_checks,
              "contrast_numeric_checks": contrast_checks,
              "fixed_source_tile_checks": sample_checks,
              "bound_annual_source_manifests": len(records),
              "no_yield_damage_scc_estimated": True}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps(output))


if __name__ == "__main__":
    main()
