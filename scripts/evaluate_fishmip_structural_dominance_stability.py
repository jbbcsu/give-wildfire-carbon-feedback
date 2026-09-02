#!/usr/bin/env python3
"""Audit stability and practical separation of FishMIP structural contrasts."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


SCENARIOS = ["ssp126", "ssp585"]
WINDOWS = [(2021, 2030), (2041, 2050), (2081, 2090)]
BANDS = ["south_high", "south_mid", "tropics", "north_mid", "north_high"]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def evaluate(source: dict[str, object], material_ratio: float = 1.25) -> dict[str, object]:
    require(source.get("schema") == "fishmip_structural_contrast_sensitivity_v1", "source schema changed")
    require(source.get("status") == "validated_structural_sensitivity_not_probability_variance_or_scc", "source status changed")
    require(source.get("probability_or_variance_decomposition") is False, "source claims probability or variance decomposition")
    require(material_ratio > 1, "material dominance ratio must exceed one")
    cells = source.get("cells", [])
    require(len(cells) == 30, "source cell count changed")
    indexed = {}
    detailed = []
    for cell in cells:
        scenario = str(cell["climate_scenario"])
        period = cell["future_period"]
        window = (int(period["start_year"]), int(period["end_year"]))
        band = str(cell["latitude_band"])
        key = (scenario, window, band)
        require(key not in indexed, "source cell key is duplicated")
        climate = float(cell["climate_forcing_contrast_ipsl_minus_gfdl"]["root_mean_square_contrast"])
        ecosystem = float(cell["ecosystem_model_contrast_ecoocean_minus_boats"]["root_mean_square_contrast"])
        require(climate > 0 and ecosystem > 0, "RMS contrasts must be positive")
        winner = "climate_forcing" if climate > ecosystem else "ecosystem_model"
        require(winner == cell["larger_rms_structural_contrast"], "reported structural winner is inconsistent")
        ratio = max(climate, ecosystem) / min(climate, ecosystem)
        record = {
            "climate_scenario": scenario,
            "future_period": {"start_year": window[0], "end_year": window[1]},
            "latitude_band": band,
            "larger_rms_structural_contrast": winner,
            "larger_to_smaller_rms_ratio": ratio,
            "material_dominance_at_fixed_ratio": ratio >= material_ratio,
        }
        indexed[key] = record
        detailed.append(record)
    require(set(indexed) == {(scenario, window, band) for scenario in SCENARIOS for window in WINDOWS for band in BANDS}, "source key product changed")

    scenario_pairs = []
    for window in WINDOWS:
        for band in BANDS:
            low, high = indexed[("ssp126", window, band)], indexed[("ssp585", window, band)]
            scenario_pairs.append({
                "future_period": {"start_year": window[0], "end_year": window[1]},
                "latitude_band": band,
                "same_larger_axis_across_scenarios": low["larger_rms_structural_contrast"] == high["larger_rms_structural_contrast"],
                "both_scenarios_materially_dominant": low["material_dominance_at_fixed_ratio"] and high["material_dominance_at_fixed_ratio"],
            })

    window_groups = []
    for scenario in SCENARIOS:
        for band in BANDS:
            group = [indexed[(scenario, window, band)] for window in WINDOWS]
            window_groups.append({
                "climate_scenario": scenario,
                "latitude_band": band,
                "same_larger_axis_across_all_windows": len({row["larger_rms_structural_contrast"] for row in group}) == 1,
                "all_windows_materially_dominant": all(row["material_dominance_at_fixed_ratio"] for row in group),
            })

    return {
        "schema": "fishmip_structural_dominance_stability_v1",
        "status": "validated_structural_dominance_sensitivity_not_probability_variance_or_scc",
        "material_dominance_ratio_threshold": material_ratio,
        "cells": detailed,
        "summary": {
            "materially_dominant_cells": sum(row["material_dominance_at_fixed_ratio"] for row in detailed),
            "near_tie_cells": sum(not row["material_dominance_at_fixed_ratio"] for row in detailed),
            "same_larger_axis_across_scenarios": sum(row["same_larger_axis_across_scenarios"] for row in scenario_pairs),
            "scenario_pairs": len(scenario_pairs),
            "same_larger_axis_across_all_windows": sum(row["same_larger_axis_across_all_windows"] for row in window_groups),
            "scenario_band_window_groups": len(window_groups),
        },
        "scenario_pair_stability": scenario_pairs,
        "window_stability": window_groups,
        "probability_or_variance_decomposition": False,
        "forced_response_estimated": False,
        "country_or_eez_allocation_performed": False,
        "matched_co2_pulse": False,
        "welfare_estimated": False,
        "damage_estimated": False,
        "scc_authorized": False,
        "disclaimer": "Dominance ratios and stability counts are descriptive sensitivity checks on four model structures, not probabilities, variance shares, causal forced responses, or welfare evidence.",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--material-ratio", type=float, default=1.25)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    source = json.loads(args.source.read_text(encoding="utf-8"))
    result = evaluate(source, args.material_ratio)
    result["source"] = {"path": args.source.as_posix(), "sha256": sha256(args.source)}
    result["implementation"] = {"path": Path(__file__).as_posix(), "sha256": sha256(Path(__file__))}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"FishMIP structural dominance: {result['summary']['materially_dominant_cells']}/30 material, {result['summary']['same_larger_axis_across_scenarios']}/15 scenario-stable")


if __name__ == "__main__":
    main()
