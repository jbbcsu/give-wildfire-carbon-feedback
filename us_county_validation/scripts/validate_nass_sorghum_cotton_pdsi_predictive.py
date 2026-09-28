#!/usr/bin/env python3
"""Independently validate frozen sorghum/cotton PDSI predictive results."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import pandas as pd

PROJECT = Path(__file__).resolve().parents[2]
MODELS = {"trend_only", "season_linear", "season_quadratic", "stage_linear"}
COMPARISONS = {
    "season_linear_vs_trend": ("trend_only", "season_linear"),
    "stage_linear_vs_season_linear": ("season_linear", "stage_linear"),
    "season_quadratic_vs_season_linear": ("season_linear", "season_quadratic"),
}


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 << 20), b""):
            value.update(block)
    return value.hexdigest()


def require(value: bool, message: str) -> None:
    if not value:
        raise ValueError(message)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--validation-out", type=Path, required=True)
    args = parser.parse_args()
    payload = json.loads(args.result.read_text())
    for item in payload["inputs"].values():
        path = PROJECT / item["path"]
        require(digest(path) == item["sha256"], f"input hash differs: {path}")
    require(payload["moisture_family"] == "pdsi_only_not_stacked_with_direct_rainfall_temperature_or_other_drought_indices", "moisture family differs")
    require(not payload["coefficients_emitted"] and not payload["row_predictions_emitted"], "forbidden row output emitted")
    for gate in ["causal_claim_authorized", "irrigation_treatment_claim_authorized", "national_representativeness_claim_authorized", "future_drought_claim_authorized", "global_transfer_authorized", "damage_claim_authorized", "scc_claim_authorized"]:
        require(payload[gate] is False, f"claim gate opened: {gate}")
    rows = pd.DataFrame(payload["results"])
    require(len(rows) == 112, "unexpected result row count")
    require(set(rows.model) == MODELS, "model set differs")
    for column in ["rmse", "mae", "r2_oos", "correlation"]:
        require(rows[column].dropna().map(lambda value: math.isfinite(float(value))).all(), f"nonfinite {column}")
    require((rows.rmse > 0).all() and (rows.mae >= 0).all(), "invalid loss")
    require(rows.level_endpoints_disjoint.eq(True).all(), "endpoint overlap flag differs")
    for (crop, practice, split, split_id), group in rows.groupby(["crop", "practice", "split", "split_id"], observed=True):
        require(set(group.model) == MODELS and len(group) == 4, "fold does not contain four models")
        require(group.training_rows.nunique() == 1 and group.test_rows.nunique() == 1, "fold sample differs by model")
    summary_lookup = {(item["crop"], item["practice"]): item for item in payload["summaries"]}
    require(len(summary_lookup) == 4, "summary strata differ")
    for (crop, practice), group in rows.groupby(["crop", "practice"], observed=True):
        summary = summary_lookup[(crop, practice)]
        require(len(summary["eligible_development_states"]) == 6, "eligible state count differs")
        for name, (comparator, candidate) in COMPARISONS.items():
            recorded = summary[name]
            require((recorded["comparator"], recorded["candidate"]) == (comparator, candidate), "comparison labels differ")
            decisions = []
            for (split, split_id), fold in group.groupby(["split", "split_id"], observed=True):
                values = fold.set_index("model").rmse.astype(float)
                improvement = float(values[comparator] - values[candidate])
                floor = max(0.0001, 0.01 * float(values[comparator]))
                key = f"{split}:{split_id}"
                observed = recorded["folds"][key]
                require(abs(observed["rmse_improvement"] - improvement) <= 1e-15, "improvement differs")
                require(abs(observed["required_floor"] - floor) <= 1e-15, "floor differs")
                require(observed["passed"] == (improvement >= floor), "fold decision differs")
                decisions.append(improvement >= floor)
            require(recorded["all_folds_pass"] == all(decisions), "all-fold decision differs")
    joined = pd.read_parquet(PROJECT / payload["inputs"]["joined_panel"]["path"])
    support = {}
    for (crop, practice), frame in joined.groupby(["crop", "practice"], observed=True):
        frame = frame.sort_values(["county_geoid", "harvest_year"])
        previous = frame.groupby("county_geoid", observed=True).harvest_year.shift(1)
        differences = frame.loc[frame.harvest_year.sub(previous).eq(1)]
        support[f"{crop}:{practice}"] = len(differences)
    require(all(payload["first_difference_support"][key]["difference_rows"] == value for key, value in support.items()), "support count differs")
    passed = {
        name: sum(bool(item[name]["all_folds_pass"]) for item in payload["summaries"])
        for name in COMPARISONS
    }
    result = {
        "status": "validated_frozen_predictive_scores_and_gates",
        "result_sha256": digest(args.result), "result_rows": len(rows), "strata": len(summary_lookup),
        "all_fold_pass_counts_out_of_four_strata": passed,
        "coefficients_or_predictions_emitted": False,
        "causal_damage_or_scc_authorized": False,
    }
    args.validation_out.parent.mkdir(parents=True, exist_ok=True)
    args.validation_out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
