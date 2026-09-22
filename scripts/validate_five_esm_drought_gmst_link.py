#!/usr/bin/env python3
"""Independently recompute the five-ESM drought--GMST endpoint diagnostic."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
ESMS = ("gfdl-esm4", "ipsl-cm6a-lr", "mpi-esm1-2-hr", "mri-esm2-0", "ukesm1-0-ll")
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


def close(actual: float, expected: float, label: str) -> float:
    difference = abs(float(actual) - float(expected))
    require(math.isclose(float(actual), float(expected), rel_tol=2e-14, abs_tol=2e-14),
            f"numeric disagreement: {label}")
    return difference


def regression(points: list[tuple[str, str, float, float]]) -> tuple[float, float]:
    denominator = math.fsum(x * x for _, _, x, _ in points)
    require(denominator > 0 and math.isfinite(denominator), "invalid independent denominator")
    return math.fsum(x * y for _, _, x, y in points) / denominator, denominator


def metrics(slope: float, points: list[tuple[str, str, float, float]]) -> tuple[float, float]:
    rmse = math.sqrt(math.fsum((y - slope * x) ** 2 for _, _, x, y in points) / len(points))
    zero = math.sqrt(math.fsum(y * y for _, _, _, y in points) / len(points))
    return rmse, zero


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result_path = args.result if args.result.is_absolute() else ROOT / args.result
    output = args.output if args.output.is_absolute() else ROOT / args.output
    require(not output.exists(), "fresh independent validation output required")
    observed = json.loads(result_path.read_text())
    require(digest(ROOT / observed["protocol"]["path"]) == observed["protocol"]["sha256"], "protocol binding differs")
    matrix_path = ROOT / observed["sources"]["matrix_path"]
    validation_path = ROOT / observed["sources"]["validation_path"]
    require(digest(matrix_path) == observed["sources"]["matrix_sha256"] and
            digest(validation_path) == observed["sources"]["validation_sha256"], "matrix source hashes differ")
    matrix = json.loads(matrix_path.read_text())
    validation = json.loads(validation_path.read_text())
    require(validation["status"] == "passed" and validation["matrix_sha256"] == digest(matrix_path), "matrix validation differs")

    gmst = {}; checks = 0; maximum = 0.0
    require(len(observed["sources"]["gmst"]) == 15, "GMST source count differs")
    for source in observed["sources"]["gmst"]:
        path = ROOT / source["path"]
        require(digest(path) == source["sha256"], "GMST source hash differs")
        frame = pd.read_parquet(path)
        selected = frame[frame.year.astype(int).isin(range(2092, 2100))]
        require(len(selected) == 8 and sorted(selected.year.astype(int)) == list(range(2092, 2100)), "GMST support differs")
        mean = math.fsum(float(value) for value in selected.gmst_value_k) / 8
        maximum = max(maximum, close(source["mean_gmst_k"], mean, "GMST mean")); checks += 3
        gmst[(source["esm"], source["scenario"])] = mean
    require(len(gmst) == 15, "unique GMST key count differs")

    means = {(row["esm"], row["scenario"], row["crop"], row["window"], row["scale_months"], row["irrigation"]):
             row["area_year_weighted_mean_spei"] for row in matrix["case_means"]}
    record_lookup = {(row["crop"], row["window"], row["scale_months"], row["irrigation"]): row for row in observed["records"]}
    require(len(record_lookup) == 90, "observed feature record count differs")
    expected_flags = {}
    for key in sorted({item[2:] for item in means}):
        crop, window, scale, irrigation = key
        record = record_lookup[key]
        points = []
        for esm in ESMS:
            for label, higher in CONTRASTS:
                x = gmst[(esm, higher)] - gmst[(esm, "ssp126")]
                y = means[(esm, higher, crop, window, scale, irrigation)] - means[(esm, "ssp126", crop, window, scale, irrigation)]
                points.append((esm, label, x, y))
        slope, denominator = regression(points); rmse, zero = metrics(slope, points)
        for actual, expected, label in ((record["full_fit"]["slope_spei_per_k"], slope, "full slope"),
                                        (record["full_fit"]["denominator_k2"], denominator, "denominator"),
                                        (record["full_fit"]["rmse"], rmse, "full rmse"),
                                        (record["full_fit"]["zero_change_rmse"], zero, "zero rmse"),
                                        (record["full_fit"]["rmse_improvement"], zero-rmse, "full improvement")):
            maximum = max(maximum, close(actual, expected, label)); checks += 1
        observed_points = {(row["esm"], row["contrast"]): row for row in record["full_fit"]["points"]}
        require(len(observed_points) == 10, "full point count differs")
        for esm, contrast, x, y in points:
            row = observed_points[(esm, contrast)]
            for actual, expected, label in ((row["gmst_difference_k"], x, "point x"),
                                            (row["spei_difference"], y, "point y"),
                                            (row["predicted_spei_difference"], slope*x, "point prediction"),
                                            (row["residual"], y-slope*x, "point residual")):
                maximum = max(maximum, close(actual, expected, label)); checks += 1
        esm_pass = True
        observed_esm = {row["held_out_esm"]: row for row in record["whole_esm_holdouts"]}
        require(set(observed_esm) == set(ESMS), "ESM holdout keys differ")
        for held in ESMS:
            training = [point for point in points if point[0] != held]; test = [point for point in points if point[0] == held]
            held_slope, _ = regression(training); held_rmse, held_zero = metrics(held_slope, test); passed = held_rmse < held_zero
            row = observed_esm[held]
            require(row["training_points"] == 8 and row["test_points"] == 2 and row["passes"] is passed, "ESM holdout flags differ")
            for actual, expected, label in ((row["training_slope_spei_per_k"], held_slope, "ESM slope"),
                                            (row["rmse"], held_rmse, "ESM rmse"),
                                            (row["zero_change_rmse"], held_zero, "ESM zero"),
                                            (row["rmse_improvement"], held_zero-held_rmse, "ESM improvement")):
                maximum = max(maximum, close(actual, expected, label)); checks += 1
            esm_pass &= passed
        scenario_pass = True
        observed_scenario = {row["held_out_contrast"]: row for row in record["whole_scenario_holdouts"]}
        require(set(observed_scenario) == {label for label, _ in CONTRASTS}, "scenario holdout keys differ")
        for held, _ in CONTRASTS:
            training = [point for point in points if point[1] != held]; test = [point for point in points if point[1] == held]
            held_slope, _ = regression(training); held_rmse, held_zero = metrics(held_slope, test); passed = held_rmse < held_zero
            row = observed_scenario[held]
            require(row["training_points"] == 5 and row["test_points"] == 5 and row["passes"] is passed, "scenario holdout flags differ")
            for actual, expected, label in ((row["training_slope_spei_per_k"], held_slope, "scenario slope"),
                                            (row["rmse"], held_rmse, "scenario rmse"),
                                            (row["zero_change_rmse"], held_zero, "scenario zero"),
                                            (row["rmse_improvement"], held_zero-held_rmse, "scenario improvement")):
                maximum = max(maximum, close(actual, expected, label)); checks += 1
            scenario_pass &= passed
        require(record["whole_esm_rule_passes"] is esm_pass and record["whole_scenario_rule_passes"] is scenario_pass and
                record["combined_predictive_rule_passes"] is (esm_pass and scenario_pass), "combined flags differ")
        checks += 3; expected_flags[key] = (esm_pass, scenario_pass, esm_pass and scenario_pass)
    require(observed["primary_records"] == [record_lookup[(crop, "season", 3, "noirr")] for crop in ("mai", "soy")],
            "primary record selection differs")
    expected_summary = {crop: {"cells": 45,
                               "whole_esm_passes": sum(flags[0] for key, flags in expected_flags.items() if key[0] == crop),
                               "whole_scenario_passes": sum(flags[1] for key, flags in expected_flags.items() if key[0] == crop),
                               "combined_passes": sum(flags[2] for key, flags in expected_flags.items() if key[0] == crop)}
                        for crop in ("mai", "soy")}
    require(observed["summary_by_crop"] == expected_summary, "summary counts differ"); checks += 8

    result = {"schema": "five_esm_drought_gmst_endpoint_link_validation_v1", "status": "passed",
              "role": "independent_endpoint_link_arithmetic_validation_not_attribution_yield_damage_or_scc",
              "result_sha256": digest(result_path), "feature_records": 90, "gmst_sources": 15,
              "numeric_checks": checks, "maximum_numeric_absolute_difference": maximum,
              "summary_by_crop": expected_summary,
              "gates": {"endpoint_diagnostic": True, "transient_climate_response": False,
                        "yield_response": False, "damage": False, "scc": False},
              "implementation": {"path": str(Path(__file__).resolve().relative_to(ROOT)),
                                 "sha256": digest(Path(__file__).resolve())}}
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".partial")
    temporary.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n"); temporary.replace(output)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
