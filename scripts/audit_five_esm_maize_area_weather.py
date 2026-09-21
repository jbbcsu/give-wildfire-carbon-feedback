#!/usr/bin/env python3
"""Independent ledger and source-tile audit of the five-ESM weather matrix."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import pandas as pd

from audit_three_esm_maize_area_weather import close, sha, source_tile_check
from compare_five_esm_maize_area_weather import ESMS
from compare_three_esm_maize_area_weather import FEATURES, INTERIM, SCENARIOS, WEIGHTS, WEIGHTS_SHA, YEARS


SAMPLES = (
    ("gfdl-esm4", "ssp126", 2092), ("gfdl-esm4", "ssp585", 2099),
    ("ipsl-cm6a-lr", "ssp126", 2092), ("ipsl-cm6a-lr", "ssp585", 2099),
    ("mpi-esm1-2-hr", "ssp126", 2092), ("mpi-esm1-2-hr", "ssp585", 2099),
    ("mri-esm2-0", "ssp126", 2092), ("mri-esm2-0", "ssp585", 2099),
    ("ukesm1-0-ll", "ssp126", 2092), ("ukesm1-0-ll", "ssp585", 2099),
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    source, out = args.result.resolve(), args.out.resolve()
    if not source.is_relative_to(INTERIM) or not out.is_relative_to(INTERIM) or out.exists():
        parser.error("ignored source and fresh output required")
    saved = json.loads(source.read_text())
    if (saved["status"] != "five_esm_fixed_maize_area_weather_only_not_forced_response_or_scc"
            or saved["weights_sha256"] != WEIGHTS_SHA or sha(WEIGHTS) != WEIGHTS_SHA
            or saved["esms"] != list(ESMS) or saved["scenarios"] != list(SCENARIOS)
            or saved["years"] != list(YEARS)):
        raise ValueError("wrong primary result or frozen matrix changed")
    weights = pd.read_parquet(WEIGHTS, columns=["lat", "lon_360", "crop", "irrigation", "rainfed_area_ha"])
    weights = weights.loc[
        weights.crop.eq("mai") & weights.irrigation.eq("noirr") & weights.rainfed_area_ha.gt(0),
        ["lat", "lon_360", "rainfed_area_ha"],
    ]
    if len(weights) != 30821 or weights[["lat", "lon_360"]].duplicated().any():
        raise ValueError("weight support differs")
    close(weights.rainfed_area_ha.sum(), saved["original_positive_area_ha"], "original area")
    close(saved["matched_area_ha"] / saved["original_positive_area_ha"],
          saved["matched_area_fraction"], "matched area fraction")
    records = saved["annual_panels"]
    expected = len(ESMS) * len(SCENARIOS) * len(YEARS)
    if len(records) != expected or len({(r["esm"], r["scenario"], r["year"]) for r in records}) != expected:
        raise ValueError("annual panel matrix incomplete")
    annual_checks = 0
    for row in records:
        if row["esm"] not in ESMS or row["scenario"] not in SCENARIOS or row["year"] not in YEARS:
            raise ValueError("annual panel identity differs")
        directory = INTERIM / f"isimip3b_global_{row['esm']}_{row['scenario']}_{row['year']}_mai_noirr_full_20260917"
        manifest_file = directory / "global_manifest.json"
        validation_file = directory / "independent_global_validation.json"
        if (sha(manifest_file) != row["global_manifest_sha256"]
                or sha(validation_file) != row["independent_validation_sha256"]
                or json.loads(validation_file.read_text())["global_manifest_sha256"] != sha(manifest_file)):
            raise ValueError("bound source manifest/validation differs")
        tiles = row["tile_ledgers"]
        if len(tiles) != 36 or [x["lat_start"] for x in tiles] != list(range(0, 360, 10)):
            raise ValueError("latitude tile order differs")
        if sum(x["calendar_rows"] for x in tiles) != 67420 or sum(x["matched_rows"] for x in tiles) != 30654:
            raise ValueError("annual tile support differs")
        close(math.fsum(x["matched_area_ha"] for x in tiles), saved["matched_area_ha"], "annual area")
        for feature in FEATURES:
            area_sum = math.fsum(x["area_numerators"][feature] for x in tiles)
            equal_sum = math.fsum(x["equal_sums"][feature] for x in tiles)
            close(area_sum / saved["matched_area_ha"], row["annual_means"][feature]["area_weighted"],
                  "annual weighted " + feature)
            close(equal_sum / saved["matched_calendar_cells"], row["annual_means"][feature]["equal_matched_cell"],
                  "annual equal " + feature)
            annual_checks += 2
    contrast_checks = 0
    for esm in ESMS:
        for scenario in SCENARIOS[1:]:
            for feature in FEATURES:
                for measure in ("area_weighted", "equal_matched_cell"):
                    current = [r["annual_means"][feature][measure] for r in records
                               if r["esm"] == esm and r["scenario"] == scenario]
                    baseline = [r["annual_means"][feature][measure] for r in records
                                if r["esm"] == esm and r["scenario"] == "ssp126"]
                    if len(current) != 8 or len(baseline) != 8:
                        raise ValueError("scenario year count differs")
                    value = math.fsum(current) / 8 - math.fsum(baseline) / 8
                    close(value, saved["scenario_minus_ssp126"][esm][scenario][feature][measure],
                          "contrast " + feature)
                    contrast_checks += 1
    sample_checks = 0
    for esm, scenario, year in SAMPLES:
        row = next(r for r in records if (r["esm"], r["scenario"], r["year"]) == (esm, scenario, year))
        sample_checks += source_tile_check(row, weights)
    output = {
        "status": "independent_five_esm_fixed_area_weather_ledger_and_source_sample_passed",
        "primary_sha256": sha(source), "annual_numeric_checks": annual_checks,
        "contrast_numeric_checks": contrast_checks, "fixed_source_tile_checks": sample_checks,
        "bound_annual_source_manifests": len(records), "no_yield_damage_scc_estimated": True,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps(output))


if __name__ == "__main__":
    main()
