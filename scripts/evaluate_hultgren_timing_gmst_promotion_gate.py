#!/usr/bin/env python3
"""Test whether the five-ESM precipitation-timing increment is stable per kelvin.

This is an outcome-blind promotion gate for an already-computed diagnostic. It
does not estimate an SCC. The timing increment is the published-response net
precipitation effect minus the reference path that scales every crop phase by
the same proportional quantity change.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path


COMPONENTS = {
    "net_precipitation": "precipitation_all_income_support",
    "quantity_reference": "precipitation_quantity_reference_scaling",
    "timing_distribution_increment": "precipitation_distribution_residual",
}


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def origin_slope(points: list[dict[str, float]]) -> float:
    denominator = sum(point["gmst_difference_k"] ** 2 for point in points)
    require(denominator > 0.0, "nonpositive slope denominator")
    return sum(point["gmst_difference_k"] * point["delta_log_yield"] for point in points) / denominator


def evaluate_component(points: list[dict[str, float]]) -> dict[str, object]:
    slope = origin_slope(points)
    holdouts = []
    for held_out in points:
        training = [point for point in points if point["climate_model"] != held_out["climate_model"]]
        training_slope = origin_slope(training)
        prediction = training_slope * held_out["gmst_difference_k"]
        error = held_out["delta_log_yield"] - prediction
        zero_error = held_out["delta_log_yield"]
        holdouts.append({
            "held_out_climate_model": held_out["climate_model"],
            "training_slope_delta_log_yield_per_k": training_slope,
            "observed_delta_log_yield": held_out["delta_log_yield"],
            "predicted_delta_log_yield": prediction,
            "absolute_error": abs(error),
            "zero_change_absolute_error": abs(zero_error),
            "improves_on_zero_change": abs(error) < abs(zero_error),
        })
    ratios = [point["delta_log_yield"] / point["gmst_difference_k"] for point in points]
    signs = [math.copysign(1.0, point["delta_log_yield"]) if point["delta_log_yield"] != 0.0 else 0.0 for point in points]
    rmse = math.sqrt(sum((point["delta_log_yield"] - slope * point["gmst_difference_k"]) ** 2 for point in points) / len(points))
    zero_rmse = math.sqrt(sum(point["delta_log_yield"] ** 2 for point in points) / len(points))
    return {
        "origin_constrained_slope_delta_log_yield_per_k": slope,
        "endpoint_slopes_delta_log_yield_per_k": ratios,
        "endpoint_slope_minimum": min(ratios),
        "endpoint_slope_maximum": max(ratios),
        "models_negative": sum(sign < 0 for sign in signs),
        "models_positive": sum(sign > 0 for sign in signs),
        "models_zero": sum(sign == 0 for sign in signs),
        "sign_stable": len(set(signs)) == 1,
        "rmse": rmse,
        "zero_change_rmse": zero_rmse,
        "rmse_improvement_over_zero": zero_rmse - rmse,
        "whole_esm_holdouts": holdouts,
        "all_whole_esm_holdouts_improve_on_zero": all(row["improves_on_zero_change"] for row in holdouts),
        "points": points,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--transport-summary", type=Path, required=True)
    parser.add_argument("--gmst-link", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), "fresh output required")

    transport = json.loads(args.transport_summary.read_text(encoding="utf-8"))
    gmst = json.loads(args.gmst_link.read_text(encoding="utf-8"))
    require(transport["schema"] == "hultgren_named_esm_yield_transport_summary/v2", "transport schema differs")
    require(transport["analysis_weighting"]["unit"] == "mt", "production weighting required")
    require(transport["scenario_contrast"] == {"comparison": "SSP5-8.5", "reference": "SSP1-2.6"}, "scenario contrast differs")

    gmst_record = next(
        record for record in gmst["primary_records"]
        if record["crop"] == "mai" and record["irrigation"] == "noirr"
        and record["scale_months"] == 3 and record["window"] == "season"
    )
    gmst_by_model = {
        point["esm"].upper(): float(point["gmst_difference_k"])
        for point in gmst_record["full_fit"]["points"]
        if point["contrast"] == "ssp585_minus_ssp126"
    }
    aliases = {
        "GFDL-ESM4": "GFDL-ESM4", "IPSL-CM6A-LR": "IPSL-CM6A-LR",
        "MPI-ESM1-2-HR": "MPI-ESM1-2-HR", "MRI-ESM2-0": "MRI-ESM2-0",
        "UKESM1-0-LL": "UKESM1-0-LL",
    }
    require(set(gmst_by_model) == set(aliases), "GMST five-model support differs")

    fixed = transport["support_sensitivities"]["full"]["fixed"]
    results = {}
    for label, source_label in COMPONENTS.items():
        source_rows = fixed[source_label]["named_model_results"]
        by_model = {row["climate_model"]: float(row["weighted_mean_delta_log_yield"]) for row in source_rows}
        require(set(by_model) == set(aliases), f"{label} five-model support differs")
        points = [{
            "climate_model": model,
            "gmst_difference_k": gmst_by_model[aliases[model]],
            "delta_log_yield": by_model[model],
        } for model in aliases]
        results[label] = evaluate_component(points)

    timing = results["timing_distribution_increment"]
    quantity = results["quantity_reference"]
    timing_share = abs(timing["origin_constrained_slope_delta_log_yield_per_k"]) / abs(quantity["origin_constrained_slope_delta_log_yield_per_k"])
    gates = {
        "timing_increment_sign_stable_across_five_esms": timing["sign_stable"],
        "timing_increment_all_whole_esm_holdouts_improve_on_zero": timing["all_whole_esm_holdouts_improve_on_zero"],
        "timing_increment_promoted_to_marginal_scc": bool(timing["sign_stable"] and timing["all_whole_esm_holdouts_improve_on_zero"]),
        "quantity_reference_sign_stable_across_five_esms": quantity["sign_stable"],
        "damage_or_scc": False,
    }
    result = {
        "schema": "hultgren_timing_gmst_promotion_gate/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "timing_increment_not_promoted" if not gates["timing_increment_promoted_to_marginal_scc"] else "timing_increment_screen_passed_not_scc",
        "estimand": "production-weighted Hultgren maize precipitation-response components per kelvin for the late-century SSP5-8.5 minus SSP1-2.6 contrast",
        "fit_definition": "origin-constrained equal-endpoint-weight response-on-same-realization-GMST difference",
        "components": results,
        "timing_increment_absolute_slope_share_of_quantity_reference": timing_share,
        "promotion_rule": "timing increment requires one sign across all five named ESMs and every whole-ESM holdout must improve absolute prediction error over zero change",
        "gates": gates,
        "sources": {
            "transport_summary": {"path": str(args.transport_summary), "sha256": digest(args.transport_summary)},
            "gmst_link": {"path": str(args.gmst_link), "sha256": digest(args.gmst_link)},
        },
        "limitations": [
            "The five endpoints are named climate-model sensitivities, not probability draws.",
            "The response contrast combines one late-century scenario pair and cannot validate a transient or CO2-only precipitation response.",
            "The timing increment is a reference-path residual, not a unique causal decomposition.",
            "This gate neither monetizes the response nor computes an SCC.",
        ],
        "implementation": {"path": str(Path(__file__).resolve()), "sha256": digest(Path(__file__).resolve())},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "gates": gates, "timing_share": timing_share, "components": {key: {"slope": value["origin_constrained_slope_delta_log_yield_per_k"], "sign_stable": value["sign_stable"], "all_holdouts": value["all_whole_esm_holdouts_improve_on_zero"]} for key, value in results.items()}}, indent=2))


if __name__ == "__main__":
    main()
