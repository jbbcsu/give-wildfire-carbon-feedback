#!/usr/bin/env python3
"""Independently validate five-ESM drought-matrix aggregation arithmetic."""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
import statistics


ROOT = Path(__file__).resolve().parents[1]
ESMS = ("gfdl-esm4", "ipsl-cm6a-lr", "mpi-esm1-2-hr", "mri-esm2-0", "ukesm1-0-ll")


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8*1024*1024), b""):
            value.update(block)
    return value.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def close(actual: float, expected: float, label: str) -> float:
    difference = abs(float(actual)-float(expected))
    require(math.isclose(float(actual), float(expected), rel_tol=2e-14, abs_tol=2e-14), f"matrix arithmetic differs: {label}")
    return difference


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    matrix_path = args.matrix if args.matrix.is_absolute() else ROOT/args.matrix
    output = args.output if args.output.is_absolute() else ROOT/args.output
    require(not output.exists(), "fresh validation output required")
    matrix = json.loads(matrix_path.read_text()); require(len(matrix["sources"]) == 15, "matrix source count differs")
    annual = {}; checks = 0; maximum = 0.0
    for source in matrix["sources"]:
        summary_path = ROOT/source["summary_path"]; validation_path = ROOT/source["validation_path"]
        require(digest(summary_path) == source["summary_sha256"] and digest(validation_path) == source["validation_sha256"], "matrix source identity differs")
        validation = json.loads(validation_path.read_text())
        require(validation["status"] == "passed" and validation["summary_sha256"] == source["summary_sha256"], "source validation binding differs")
        summary = json.loads(summary_path.read_text())
        for record in summary["records"]:
            key = (source["esm"], source["scenario"], record["crop"], record["window"], record["scale_months"], record["irrigation"])
            annual.setdefault(key, []).append(record)
        checks += 3
    observed_means = {(r["esm"], r["scenario"], r["crop"], r["window"], r["scale_months"], r["irrigation"]): r for r in matrix["case_means"]}
    require(len(observed_means) == len(annual) == 1350, "case-mean factorial differs")
    expected_means = {}
    for key, records in annual.items():
        require(len(records) == 8, "annual case count differs")
        complete = math.fsum(r["complete_area_ha"] for r in records)
        declared = math.fsum(r["declared_area_ha"] for r in records)
        mean = math.fsum(r["area_weighted_mean_spei"]*r["complete_area_ha"] for r in records)/complete
        expected_means[key] = mean; observed = observed_means[key]
        for actual, expected, label in ((observed["area_year_weighted_mean_spei"], mean, "case mean"),
                                        (observed["complete_area_year_fraction"], complete/declared, "coverage"),
                                        (observed["annual_min_spei"], min(r["area_weighted_mean_spei"] for r in records), "minimum"),
                                        (observed["annual_max_spei"], max(r["area_weighted_mean_spei"] for r in records), "maximum")):
            maximum = max(maximum, close(actual, expected, label)); checks += 1
    observed_contrasts = {(r["contrast"], r["esm"], r["crop"], r["window"], r["scale_months"], r["irrigation"]): r["spei_difference"] for r in matrix["model_contrasts"]}
    require(len(observed_contrasts) == 900, "model-contrast factorial differs")
    expected_contrasts = {}
    for label, higher, lower in (("ssp370_minus_ssp126", "ssp370", "ssp126"), ("ssp585_minus_ssp126", "ssp585", "ssp126")):
        for key in [item for item in expected_means if item[1] == higher]:
            esm, _, crop, window, scale, irrigation = key
            contrast_key = (label, esm, crop, window, scale, irrigation)
            expected = expected_means[key]-expected_means[(esm, lower, crop, window, scale, irrigation)]
            expected_contrasts[contrast_key] = expected
            maximum = max(maximum, close(observed_contrasts[contrast_key], expected, "model contrast")); checks += 1
    groups = defaultdict(list)
    for key, value in expected_contrasts.items():
        groups[(key[0], key[2], key[3], key[4], key[5])].append((key[1], value))
    observed_cross = {(r["contrast"], r["crop"], r["window"], r["scale_months"], r["irrigation"]): r for r in matrix["cross_model"]}
    require(len(observed_cross) == len(groups) == 180, "cross-model factorial differs")
    for key, pairs in groups.items():
        record = observed_cross[key]; pairs = sorted(pairs); values = [value for _, value in pairs]
        require(record["named_model_spei_differences"] == {esm: value for esm, value in pairs}, "named-model values differ")
        maximum = max(maximum, close(record["five_model_mean_spei_difference"], statistics.fmean(values), "cross mean"))
        maximum = max(maximum, close(record["five_model_median_spei_difference"], statistics.median(values), "cross median"))
        require((record["negative_models"], record["positive_models"], record["zero_models"]) ==
                (sum(v < 0 for v in values), sum(v > 0 for v in values), sum(v == 0 for v in values)), "sign counts differ")
        checks += 4
    result = {"schema": "five_esm_late_drought_crop_matrix_validation_v1", "status": "passed",
              "role": "independent_matrix_arithmetic_validation_not_yield_damage_or_scc",
              "matrix_sha256": digest(matrix_path), "source_cases": 15, "case_means": 1350,
              "model_contrasts": 900, "cross_model_records": 180, "checks": checks,
              "maximum_numeric_absolute_difference": maximum,
              "implementation": {"path": str(Path(__file__).resolve().relative_to(ROOT)), "sha256": digest(Path(__file__).resolve())},
              "gates": {"five_esm_exposure_matrix": True, "yield_response": False, "damage": False, "scc": False}}
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix+".partial")
    temporary.write_text(json.dumps(result, indent=2, sort_keys=True)+"\n"); temporary.replace(output)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
