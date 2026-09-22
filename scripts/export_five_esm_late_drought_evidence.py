#!/usr/bin/env python3
"""Export a compact, validated evidence record from the five-ESM drought matrix."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PRIMARY_KEYS = ((crop, contrast) for crop in ("mai", "soy") for contrast in
                ("ssp370_minus_ssp126", "ssp585_minus_ssp126"))


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix", type=Path, required=True)
    parser.add_argument("--validation", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    matrix_path = args.matrix if args.matrix.is_absolute() else ROOT / args.matrix
    validation_path = args.validation if args.validation.is_absolute() else ROOT / args.validation
    output = args.output if args.output.is_absolute() else ROOT / args.output
    require(not output.exists(), "fresh evidence output required")
    matrix = json.loads(matrix_path.read_text())
    validation = json.loads(validation_path.read_text())
    require(validation["status"] == "passed", "matrix validation did not pass")
    require(validation["matrix_sha256"] == digest(matrix_path), "validation is not bound to matrix")
    require(validation["source_cases"] == 15 and validation["checks"] == 7065,
            "matrix validation coverage differs")
    require(len(matrix["case_means"]) == 1350 and len(matrix["model_contrasts"]) == 900 and
            len(matrix["cross_model"]) == 180, "matrix factorial differs")

    primary = []
    lookup = {(row["crop"], row["contrast"], row["window"], row["scale_months"], row["irrigation"]): row
              for row in matrix["cross_model"]}
    for crop, contrast in PRIMARY_KEYS:
        row = lookup[(crop, contrast, "season", 3, "noirr")]
        primary.append(row)

    sign_robustness = []
    for crop in ("mai", "soy"):
        for contrast in ("ssp370_minus_ssp126", "ssp585_minus_ssp126"):
            rows = [row for row in matrix["cross_model"]
                    if row["crop"] == crop and row["contrast"] == contrast]
            require(len(rows) == 45, "crop/contrast robustness cell count differs")
            sign_robustness.append({
                "crop": crop,
                "contrast": contrast,
                "feature_cells": 45,
                "all_five_models_negative": sum(row["negative_models"] == 5 for row in rows),
                "at_least_four_models_negative": sum(row["negative_models"] >= 4 for row in rows),
                "all_five_models_positive": sum(row["positive_models"] == 5 for row in rows),
                "at_least_four_models_positive": sum(row["positive_models"] >= 4 for row in rows),
            })

    result = {
        "schema": "five_esm_late_drought_public_evidence_v1",
        "status": "validated_scenario_exposure_evidence",
        "role": "scenario_exposure_only_not_attribution_yield_damage_or_scc",
        "period": matrix["period"],
        "sources": {
            "matrix_path": str(matrix_path.relative_to(ROOT)),
            "matrix_sha256": digest(matrix_path),
            "validation_path": str(validation_path.relative_to(ROOT)),
            "validation_sha256": digest(validation_path),
            "source_cases": validation["source_cases"],
            "independent_checks": validation["checks"],
            "maximum_numeric_absolute_difference": validation["maximum_numeric_absolute_difference"],
        },
        "primary_rainfed_season_spei3": primary,
        "sign_robustness_across_windows_scales_and_irrigation_bases": sign_robustness,
        "interpretation": [
            "SPEI is a precipitation-minus-reference-evapotranspiration moisture balance standardized to the frozen 1982-2011 observational baseline.",
            "Negative differences indicate drier standardized crop-calendar moisture in the higher-forcing scenario relative to SSP1-2.6 for the same named ESM.",
            "Five named-model signs are neither probabilities nor confidence intervals.",
            "Scenario contrasts include multiple forcings and internal variability and are not anthropogenic attribution, per-kelvin responses, marginal CO2-pulse responses, yield effects, damages, or SCC estimates.",
        ],
        "gates": {"climate_scenario_exposure": True, "yield_response": False, "damage": False, "scc": False},
        "implementation": {"path": str(Path(__file__).resolve().relative_to(ROOT)),
                           "sha256": digest(Path(__file__).resolve())},
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".partial")
    temporary.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    temporary.replace(output)
    print(json.dumps({"status": result["status"], "primary_records": len(primary),
                      "robustness_records": len(sign_robustness)}))


if __name__ == "__main__":
    main()
