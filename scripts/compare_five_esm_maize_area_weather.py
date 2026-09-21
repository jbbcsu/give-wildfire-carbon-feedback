#!/usr/bin/env python3
"""Fixed-area five-ESM maize weather contrasts; climate exposure only."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import shutil

from compare_three_esm_maize_area_weather import (
    FEATURES, INTERIM, ROOT, SCENARIOS, WEIGHTS_SHA, YEARS,
    load_weights, read_panel,
)


ESMS = ("gfdl-esm4", "ipsl-cm6a-lr", "mpi-esm1-2-hr", "mri-esm2-0", "ukesm1-0-ll")


def summarize(records: list[dict], matched_count: int, matched_area: float) -> dict:
    for row in records:
        annual = {}
        for feature in FEATURES:
            annual[feature] = {
                "area_weighted": math.fsum(tile["area_numerators"][feature]
                                             for tile in row["tile_ledgers"]) / matched_area,
                "equal_matched_cell": math.fsum(tile["equal_sums"][feature]
                                                  for tile in row["tile_ledgers"]) / matched_count,
            }
        row["annual_means"] = annual
        if not math.isclose(
            annual["precip_mm"]["area_weighted"],
            sum(annual[f"stage{s}_precip_mm"]["area_weighted"] for s in (1, 2, 3)),
            abs_tol=1e-5, rel_tol=1e-9,
        ):
            raise ValueError("area-weighted stage totals do not reconcile")
    contrasts = {}
    for esm in ESMS:
        contrasts[esm] = {}
        for scenario in SCENARIOS[1:]:
            contrasts[esm][scenario] = {}
            for feature in FEATURES:
                contrasts[esm][scenario][feature] = {}
                for measure in ("area_weighted", "equal_matched_cell"):
                    def mean(selected: str) -> float:
                        values = [row["annual_means"][feature][measure] for row in records
                                  if row["esm"] == esm and row["scenario"] == selected]
                        if len(values) != len(YEARS):
                            raise ValueError("missing fixed eight-year panel")
                        return math.fsum(values) / len(YEARS)
                    contrasts[esm][scenario][feature][measure] = mean(scenario) - mean("ssp126")
    return contrasts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    if out.exists() or not out.is_relative_to(INTERIM) or shutil.disk_usage(ROOT).free < 130 * 2**30:
        parser.error("fresh ignored output and disk reserve required")
    weights, original_area = load_weights()
    records: list[dict] = []
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
    if common is None:
        raise ValueError("empty five-ESM panel")
    count = len(common)
    area = math.fsum(weights[key] for key in common)
    if count != 30654 or not (0 < area <= original_area):
        raise ValueError("fixed matched support differs")
    contrasts = summarize(records, count, area)
    output = {
        "status": "five_esm_fixed_maize_area_weather_only_not_forced_response_or_scc",
        "crop": "mai", "irrigation": "noirr", "weight_year": 2000,
        "weights_sha256": WEIGHTS_SHA, "original_positive_area_cells": len(weights),
        "original_positive_area_ha": original_area,
        "matched_calendar_cells": count, "matched_area_ha": area,
        "matched_area_fraction": area / original_area,
        "years": list(YEARS), "esms": list(ESMS), "scenarios": list(SCENARIOS),
        "annual_panels": records, "scenario_minus_ssp126": contrasts,
        "models_are_not_probability_draws": True,
        "no_yield_data_read": True, "yield_damage_scc_estimated": False,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(output, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"status": output["status"],
                      "matched_area_fraction": output["matched_area_fraction"],
                      "scenario_minus_ssp126": contrasts}))


if __name__ == "__main__":
    main()
