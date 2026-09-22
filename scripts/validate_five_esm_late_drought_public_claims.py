#!/usr/bin/env python3
"""Validate public drought-exposure evidence and manuscript claims."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def resolve(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix", type=Path, required=True)
    parser.add_argument("--validation", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--results-report", type=Path, required=True)
    parser.add_argument("--manuscript", type=Path, required=True)
    parser.add_argument("--methods", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    paths = {key: resolve(getattr(args, key)) for key in
             ("matrix", "validation", "evidence", "results_report", "manuscript", "methods")}
    output = resolve(args.output)
    require(not output.exists(), "fresh claims-validation output required")
    matrix = json.loads(paths["matrix"].read_text())
    validation = json.loads(paths["validation"].read_text())
    evidence = json.loads(paths["evidence"].read_text())
    require(validation["status"] == "passed" and validation["matrix_sha256"] == digest(paths["matrix"]),
            "matrix validation binding differs")
    require(evidence["sources"]["matrix_sha256"] == digest(paths["matrix"]), "evidence matrix binding differs")
    require(evidence["sources"]["validation_sha256"] == digest(paths["validation"]), "evidence validation binding differs")
    require(evidence["gates"] == {"climate_scenario_exposure": True, "yield_response": False,
                                   "damage": False, "scc": False}, "evidence gates differ")

    lookup = {(row["crop"], row["contrast"], row["window"], row["scale_months"], row["irrigation"]): row
              for row in matrix["cross_model"]}
    primary = [lookup[(crop, contrast, "season", 3, "noirr")]
               for crop in ("mai", "soy")
               for contrast in ("ssp370_minus_ssp126", "ssp585_minus_ssp126")]
    require(primary == evidence["primary_rainfed_season_spei3"], "public primary records differ")
    robustness = []
    for crop in ("mai", "soy"):
        for contrast in ("ssp370_minus_ssp126", "ssp585_minus_ssp126"):
            rows = [row for row in matrix["cross_model"] if row["crop"] == crop and row["contrast"] == contrast]
            robustness.append({"crop": crop, "contrast": contrast, "feature_cells": 45,
                               "all_five_models_negative": sum(row["negative_models"] == 5 for row in rows),
                               "at_least_four_models_negative": sum(row["negative_models"] >= 4 for row in rows),
                               "all_five_models_positive": sum(row["positive_models"] == 5 for row in rows),
                               "at_least_four_models_positive": sum(row["positive_models"] >= 4 for row in rows)})
    require(robustness == evidence["sign_robustness_across_windows_scales_and_irrigation_bases"],
            "public robustness records differ")

    exact_claims = {
        "results_report": ("-0.617", "-0.885", "-0.536", "-0.883", "7,065 checks",
                           "scenario-exposure", "not yield effects"),
        "manuscript": ("-0.449/-0.662", "-0.326/-0.542", "not probabilities"),
        "methods": ("1,350 ESM--scenario--crop--window--scale--area", "7,065 checks",
                    "not probabilities, confidence intervals"),
    }
    claim_checks = 0
    for name, needles in exact_claims.items():
        text = paths[name].read_text()
        for needle in needles:
            require(needle in text, f"public claim missing from {name}: {needle}")
            claim_checks += 1

    result = {"schema": "five_esm_late_drought_public_claims_validation_v1", "status": "passed",
              "role": "claim_transcription_and_binding_validation_not_yield_damage_or_scc",
              "matrix_sha256": digest(paths["matrix"]), "validation_sha256": digest(paths["validation"]),
              "evidence_sha256": digest(paths["evidence"]), "primary_records_checked": len(primary),
              "robustness_records_checked": len(robustness), "text_claim_checks": claim_checks,
              "documents": {name: {"path": str(path.relative_to(ROOT)), "sha256": digest(path)}
                            for name, path in paths.items() if name not in ("matrix", "validation", "evidence")},
              "gates": {"claims_transcription": True, "yield_response": False, "damage": False, "scc": False},
              "implementation": {"path": str(Path(__file__).resolve().relative_to(ROOT)),
                                 "sha256": digest(Path(__file__).resolve())}}
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".partial")
    temporary.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    temporary.replace(output)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
