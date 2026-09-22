#!/usr/bin/env python3
"""Assemble validated case summaries into a five-ESM drought matrix."""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
import statistics


ROOT = Path(__file__).resolve().parents[1]
PAIR_ROOT = ROOT/"data/interim/five_esm_late_drought_20260921"
ESMS = ("gfdl-esm4", "ipsl-cm6a-lr", "mpi-esm1-2-hr", "mri-esm2-0", "ukesm1-0-ll")
SCENARIOS = ("ssp126", "ssp370", "ssp585")
CONTRASTS = (("ssp370_minus_ssp126", "ssp370", "ssp126"), ("ssp585_minus_ssp126", "ssp585", "ssp126"))


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8*1024*1024), b""):
            value.update(block)
    return value.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output if args.output.is_absolute() else ROOT/args.output
    require(not output.exists(), "fresh matrix output required")
    sources = []; annual = {}
    for esm in ESMS:
        for scenario in SCENARIOS:
            directory = PAIR_ROOT/f"{esm}_{scenario}"
            summary_path = directory/"crop_window_summary.json"; validation_path = directory/"crop_window_validation.json"
            require(summary_path.is_file() and validation_path.is_file(), f"validated case missing: {esm}/{scenario}")
            summary = json.loads(summary_path.read_text()); validation = json.loads(validation_path.read_text())
            require(validation["status"] == "passed" and validation["summary_sha256"] == digest(summary_path), "crop-window validation binding failed")
            require(len(summary["records"]) == 720, "case factorial differs")
            sources.append({"esm": esm, "scenario": scenario, "summary_path": str(summary_path.relative_to(ROOT)),
                            "summary_sha256": digest(summary_path), "validation_path": str(validation_path.relative_to(ROOT)),
                            "validation_sha256": digest(validation_path)})
            for record in summary["records"]:
                key = (esm, scenario, record["crop"], record["window"], record["scale_months"], record["irrigation"])
                annual.setdefault(key, []).append(record)
    require(len(annual) == 5*3*2*5*3*3 and all(len(records) == 8 for records in annual.values()), "annual matrix is incomplete")
    means = {}
    case_means = []
    for key in sorted(annual):
        esm, scenario, crop, window, scale, irrigation = key; records = annual[key]
        complete_area_years = math.fsum(r["complete_area_ha"] for r in records)
        mean = math.fsum(r["area_weighted_mean_spei"]*r["complete_area_ha"] for r in records)/complete_area_years
        fraction = math.fsum(r["complete_area_ha"] for r in records)/math.fsum(r["declared_area_ha"] for r in records)
        means[key] = mean
        case_means.append({"esm": esm, "scenario": scenario, "crop": crop, "window": window,
                           "scale_months": scale, "irrigation": irrigation,
                           "area_year_weighted_mean_spei": mean, "complete_area_year_fraction": fraction,
                           "annual_min_spei": min(r["area_weighted_mean_spei"] for r in records),
                           "annual_max_spei": max(r["area_weighted_mean_spei"] for r in records)})
    model_contrasts = []
    for label, higher, lower in CONTRASTS:
        for esm in ESMS:
            for crop in ("mai", "soy"):
                for window in ("season", "stage1", "stage2", "stage3", "preplant90"):
                    for scale in (1, 3, 6):
                        for irrigation in ("noirr", "firr", "combined"):
                            value = means[(esm, higher, crop, window, scale, irrigation)]-means[(esm, lower, crop, window, scale, irrigation)]
                            model_contrasts.append({"contrast": label, "esm": esm, "crop": crop, "window": window,
                                                    "scale_months": scale, "irrigation": irrigation, "spei_difference": value})
    grouped = defaultdict(list)
    for record in model_contrasts:
        key = (record["contrast"], record["crop"], record["window"], record["scale_months"], record["irrigation"])
        grouped[key].append((record["esm"], record["spei_difference"]))
    cross_model = []
    for key in sorted(grouped):
        values = sorted(grouped[key]); numbers = [value for _, value in values]
        require([esm for esm, _ in values] == sorted(ESMS), "named-model contrast set differs")
        cross_model.append({"contrast": key[0], "crop": key[1], "window": key[2], "scale_months": key[3],
                            "irrigation": key[4], "named_model_spei_differences": {esm: value for esm, value in values},
                            "five_model_mean_spei_difference": statistics.fmean(numbers),
                            "five_model_median_spei_difference": statistics.median(numbers),
                            "negative_models": sum(value < 0 for value in numbers),
                            "positive_models": sum(value > 0 for value in numbers),
                            "zero_models": sum(value == 0 for value in numbers)})
    result = {"schema": "five_esm_late_drought_crop_matrix_v1",
              "status": "five_esm_crop_calendar_area_weighted_drought_exposure_pending_independent_matrix_validation",
              "role": "scenario_exposure_only_not_anthropogenic_attribution_yield_damage_or_scc",
              "period": {"source": "2091-2100", "harvest_years": list(range(2092, 2100))},
              "esms": list(ESMS), "scenarios": list(SCENARIOS), "sources": sources,
              "case_means": case_means, "model_contrasts": model_contrasts, "cross_model": cross_model,
              "interpretation": "Named-model signs are not probabilities or confidence intervals; scenario contrasts are not marginal CO2-pulse responses.",
              "implementation": {"path": str(Path(__file__).resolve().relative_to(ROOT)), "sha256": digest(Path(__file__).resolve())},
              "gates": {"five_esm_exposure_matrix": False, "yield_response": False, "damage": False, "scc": False}}
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix+".partial")
    temporary.write_text(json.dumps(result, indent=2, sort_keys=True)+"\n"); temporary.replace(output)
    print(json.dumps({"status": result["status"], "case_means": len(case_means),
                      "model_contrasts": len(model_contrasts), "cross_model": len(cross_model)}))


if __name__ == "__main__":
    main()
