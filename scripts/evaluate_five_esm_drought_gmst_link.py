#!/usr/bin/env python3
"""Evaluate the preregistered five-ESM drought--GMST endpoint link."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "FIVE_ESM_DROUGHT_GMST_LINK_PROTOCOL_20260922.md"
ESMS = ("gfdl-esm4", "ipsl-cm6a-lr", "mpi-esm1-2-hr", "mri-esm2-0", "ukesm1-0-ll")
SCENARIOS = ("ssp126", "ssp370", "ssp585")
MEMBERS = {esm: ("r1i1p1f2" if esm == "ukesm1-0-ll" else "r1i1p1f1") for esm in ESMS}
CONTRASTS = (("ssp370_minus_ssp126", "ssp370"), ("ssp585_minus_ssp126", "ssp585"))


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def gmst_path(esm: str, scenario: str) -> Path:
    return ROOT / "data/interim/isimip3b" / f"{esm}_{MEMBERS[esm]}_{scenario}_gmst_2091_2100.parquet"


def fit(points: list[dict]) -> dict:
    denominator = math.fsum(point["gmst_difference_k"] ** 2 for point in points)
    require(math.isfinite(denominator) and denominator > 0, "positive finite GMST denominator required")
    slope = math.fsum(point["gmst_difference_k"] * point["spei_difference"] for point in points) / denominator
    scored = []
    for point in points:
        predicted = slope * point["gmst_difference_k"]
        scored.append({**point, "predicted_spei_difference": predicted,
                       "residual": point["spei_difference"] - predicted})
    rmse = math.sqrt(math.fsum(row["residual"] ** 2 for row in scored) / len(scored))
    zero = math.sqrt(math.fsum(row["spei_difference"] ** 2 for row in scored) / len(scored))
    return {"slope_spei_per_k": slope, "denominator_k2": denominator,
            "rmse": rmse, "zero_change_rmse": zero, "rmse_improvement": zero - rmse,
            "points": scored}


def score(slope: float, points: list[dict]) -> dict:
    residuals = [point["spei_difference"] - slope * point["gmst_difference_k"] for point in points]
    rmse = math.sqrt(math.fsum(value * value for value in residuals) / len(residuals))
    zero = math.sqrt(math.fsum(point["spei_difference"] ** 2 for point in points) / len(points))
    return {"test_points": len(points), "rmse": rmse, "zero_change_rmse": zero,
            "rmse_improvement": zero - rmse, "passes": rmse < zero}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix", type=Path, required=True)
    parser.add_argument("--validation", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    matrix_path = args.matrix if args.matrix.is_absolute() else ROOT / args.matrix
    validation_path = args.validation if args.validation.is_absolute() else ROOT / args.validation
    output = args.output if args.output.is_absolute() else ROOT / args.output
    require(not output.exists(), "fresh link output required")
    matrix = json.loads(matrix_path.read_text())
    validation = json.loads(validation_path.read_text())
    require(validation["status"] == "passed" and validation["matrix_sha256"] == digest(matrix_path),
            "matrix validation binding differs")

    gmst = {}
    gmst_sources = []
    for esm in ESMS:
        for scenario in SCENARIOS:
            path = gmst_path(esm, scenario)
            require(path.is_file(), f"GMST source missing: {path.name}")
            frame = pd.read_parquet(path)
            require(list(frame.columns) == ["esm_id", "member_id", "scenario", "gmst_source_id", "year", "gmst_value_k", "daily_count"],
                    "GMST schema differs")
            require(len(frame) == 10 and set(frame.year.astype(int)) == set(range(2091, 2101)), "GMST years differ")
            require(frame.member_id.astype(str).eq(MEMBERS[esm]).all() and frame.scenario.astype(str).eq(scenario).all(),
                    "GMST member/scenario differs")
            selected = frame[frame.year.astype(int).between(2092, 2099)]
            require(len(selected) == 8 and selected.gmst_value_k.map(math.isfinite).all(), "eight finite GMST years required")
            gmst[(esm, scenario)] = math.fsum(float(value) for value in selected.gmst_value_k) / 8
            gmst_sources.append({"esm": esm, "scenario": scenario, "path": str(path.relative_to(ROOT)),
                                 "sha256": digest(path), "years": list(range(2092, 2100)),
                                 "mean_gmst_k": gmst[(esm, scenario)]})

    means = {(row["esm"], row["scenario"], row["crop"], row["window"], row["scale_months"], row["irrigation"]):
             row["area_year_weighted_mean_spei"] for row in matrix["case_means"]}
    feature_keys = sorted({key[2:] for key in means})
    require(len(feature_keys) == 90, "feature-cell count differs")
    records = []
    for crop, window, scale, irrigation in feature_keys:
        points = []
        for esm in ESMS:
            for label, higher in CONTRASTS:
                points.append({"esm": esm, "contrast": label,
                               "gmst_difference_k": gmst[(esm, higher)] - gmst[(esm, "ssp126")],
                               "spei_difference": means[(esm, higher, crop, window, scale, irrigation)] -
                                                  means[(esm, "ssp126", crop, window, scale, irrigation)]})
        full = fit(points)
        esm_holdouts = []
        for held in ESMS:
            fitted = fit([point for point in points if point["esm"] != held])
            scored = score(fitted["slope_spei_per_k"], [point for point in points if point["esm"] == held])
            esm_holdouts.append({"held_out_esm": held, "training_points": 8,
                                 "training_slope_spei_per_k": fitted["slope_spei_per_k"], **scored})
        scenario_holdouts = []
        for held, _ in CONTRASTS:
            fitted = fit([point for point in points if point["contrast"] != held])
            scored = score(fitted["slope_spei_per_k"], [point for point in points if point["contrast"] == held])
            scenario_holdouts.append({"held_out_contrast": held, "training_points": 5,
                                      "training_slope_spei_per_k": fitted["slope_spei_per_k"], **scored})
        esm_pass = all(row["passes"] for row in esm_holdouts)
        scenario_pass = all(row["passes"] for row in scenario_holdouts)
        records.append({"crop": crop, "window": window, "scale_months": scale, "irrigation": irrigation,
                        "full_fit": full, "whole_esm_holdouts": esm_holdouts,
                        "whole_scenario_holdouts": scenario_holdouts,
                        "whole_esm_rule_passes": esm_pass, "whole_scenario_rule_passes": scenario_pass,
                        "combined_predictive_rule_passes": esm_pass and scenario_pass})
    primary = [row for row in records if row["window"] == "season" and row["scale_months"] == 3 and row["irrigation"] == "noirr"]
    require(len(primary) == 2, "two primary crop records required")
    by_crop = {crop: {"cells": len([row for row in records if row["crop"] == crop]),
                      "whole_esm_passes": sum(row["whole_esm_rule_passes"] for row in records if row["crop"] == crop),
                      "whole_scenario_passes": sum(row["whole_scenario_rule_passes"] for row in records if row["crop"] == crop),
                      "combined_passes": sum(row["combined_predictive_rule_passes"] for row in records if row["crop"] == crop)}
               for crop in ("mai", "soy")}
    result = {"schema": "five_esm_drought_gmst_endpoint_link_v1",
              "status": "completed_endpoint_scenario_link_pending_independent_validation",
              "role": "descriptive_multi_forcing_endpoint_link_not_attribution_transient_emulator_yield_damage_or_scc",
              "protocol": {"path": str(PROTOCOL.relative_to(ROOT)), "sha256": digest(PROTOCOL)},
              "sources": {"matrix_path": str(matrix_path.relative_to(ROOT)), "matrix_sha256": digest(matrix_path),
                          "validation_path": str(validation_path.relative_to(ROOT)), "validation_sha256": digest(validation_path),
                          "gmst": gmst_sources},
              "fit_definition": "origin_constrained_equal_endpoint_weight_spei_difference_on_same_realization_gmst_difference",
              "records": records, "primary_records": primary, "summary_by_crop": by_crop,
              "interpretation": "Holdouts reuse the same climate ensemble. Slopes are scenario-endpoint diagnostics, not probabilities, attribution, CO2-only or marginal-pulse responses.",
              "gates": {"endpoint_diagnostic": False, "transient_climate_response": False, "yield_response": False,
                        "damage": False, "scc": False},
              "implementation": {"path": str(Path(__file__).resolve().relative_to(ROOT)),
                                 "sha256": digest(Path(__file__).resolve())}}
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".partial")
    temporary.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    temporary.replace(output)
    print(json.dumps({"status": result["status"], "records": len(records), "summary_by_crop": by_crop}))


if __name__ == "__main__":
    main()
