#!/usr/bin/env python3
"""Audit late-century FishMIP grid-cell sign consensus without averaging levels."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from evaluate_fishmip_spatial_change_distribution import (
    FORCINGS,
    FUTURE,
    MODELS,
    REFERENCE,
    ROOT,
    SCENARIOS,
    display_path,
    period_cell_mean,
    raw_path,
    read_plan,
    require,
    sha256,
)


def summarize_consensus(changes: list[np.ndarray], support: np.ndarray, latitude: np.ndarray) -> dict[str, object]:
    require(len(changes) == 4, "consensus requires the exact two-forcing by two-model matrix")
    require(all(change.shape == support.shape for change in changes), "consensus arrays have different shapes")
    require(support.shape[0] == len(latitude) and bool(support.any()), "consensus support is invalid")
    stacked = np.stack([change[support] for change in changes])
    require(bool(np.isfinite(stacked).all()), "consensus changes are nonfinite")
    lower_count = np.sum(stacked < 0, axis=0)
    higher_count = np.sum(stacked > 0, axis=0)
    unchanged_count = np.sum(stacked == 0, axis=0)
    require(bool(np.all(lower_count + higher_count + unchanged_count == 4)), "consensus signs are incomplete")
    weights = (np.cos(np.deg2rad(latitude))[:, None] * np.ones((1, support.shape[1])))[support]
    require(bool(np.isfinite(weights).all()) and float(weights.sum()) > 0, "consensus weights are invalid")

    unweighted = {str(count): float(np.mean(lower_count == count)) for count in range(5)}
    area_weighted = {
        str(count): float(weights[lower_count == count].sum() / weights.sum()) for count in range(5)
    }
    return {
        "common_finite_grid_cells": int(support.sum()),
        "unweighted_cell_share_by_lower_trajectory_count": unweighted,
        "area_weighted_cell_share_by_lower_trajectory_count": area_weighted,
        "unweighted_cell_share_unanimously_lower": unweighted["4"],
        "area_weighted_cell_share_unanimously_lower": area_weighted["4"],
        "unweighted_cell_share_at_least_three_lower": unweighted["3"] + unweighted["4"],
        "area_weighted_cell_share_at_least_three_lower": area_weighted["3"] + area_weighted["4"],
        "unweighted_cell_share_with_any_higher_trajectory": float(np.mean(higher_count > 0)),
        "area_weighted_cell_share_with_any_higher_trajectory": float(weights[higher_count > 0].sum() / weights.sum()),
        "unweighted_cell_share_with_any_exactly_unchanged_trajectory": float(np.mean(unchanged_count > 0)),
    }


def evaluate(plan_path: Path, raw_root: Path) -> dict[str, object]:
    plan = read_plan(plan_path)
    arrays: dict[tuple[str, str, str], np.ndarray] = {}
    latitude: np.ndarray | None = None
    longitude: np.ndarray | None = None
    support: np.ndarray | None = None
    receipts = []
    for forcing in FORCINGS:
        for model in MODELS:
            historical_row = plan[(forcing, model, "historical")]
            historical_path = raw_path(raw_root, historical_row)
            reference, lat, lon = period_cell_mean(historical_path, historical_row, *REFERENCE)
            arrays[(forcing, model, "historical")] = reference
            receipts.append({"climate_forcing": forcing, "ecosystem_model": model, "scenario": "historical", "path": display_path(historical_path), "sha512": historical_row["sha512"]})
            for scenario in SCENARIOS:
                row = plan[(forcing, model, scenario)]
                path = raw_path(raw_root, row)
                future, future_lat, future_lon = period_cell_mean(path, row, *FUTURE)
                require(np.array_equal(lat, future_lat) and np.array_equal(lon, future_lon), "historical/future grid changed")
                arrays[(forcing, model, scenario)] = future
                receipts.append({"climate_forcing": forcing, "ecosystem_model": model, "scenario": scenario, "path": display_path(path), "sha512": row["sha512"]})
            if latitude is None:
                latitude, longitude = lat, lon
            else:
                require(np.array_equal(latitude, lat) and np.array_equal(longitude, lon), "forcing/model grids differ")
    assert latitude is not None
    for values in arrays.values():
        finite = np.isfinite(values)
        support = finite if support is None else support & finite
    assert support is not None

    scenario_results = []
    for scenario in SCENARIOS:
        changes = [
            arrays[(forcing, model, scenario)] - arrays[(forcing, model, "historical")]
            for forcing in FORCINGS for model in MODELS
        ]
        scenario_results.append({"climate_scenario": scenario, **summarize_consensus(changes, support, latitude)})
    return {
        "schema": "fishmip_spatial_sign_consensus_v1",
        "status": "validated_biophysical_cross_matrix_sign_consensus_only",
        "reference_period": {"start_year": REFERENCE[0], "end_year": REFERENCE[1]},
        "future_period": {"start_year": FUTURE[0], "end_year": FUTURE[1]},
        "support_rule": "intersection_across_two_forcings_two_ecosystem_models_and_historical_ssp126_ssp585",
        "trajectory_count_per_scenario": 4,
        "results": scenario_results,
        "inputs": receipts,
        "plan": {"path": display_path(plan_path), "sha256": sha256(plan_path)},
        "implementation": {"path": display_path(Path(__file__).resolve()), "sha256": sha256(Path(__file__).resolve())},
        "absolute_model_levels_averaged": False,
        "scenario_contrast_is_marginal_pulse": False,
        "observed_catch": False,
        "welfare_estimated": False,
        "damage_estimated": False,
        "scc_authorized": False,
        "disclaimer": "Sign consensus across scenario catch-density trajectories is not observed catch, welfare, a matched carbon pulse, damages, or SCC evidence.",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--raw-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = evaluate(args.plan.resolve(), args.raw_root.resolve())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.out.with_suffix(args.out.suffix + ".partial")
    temporary.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(args.out)
    print("FishMIP spatial consensus passed: " + ", ".join(
        f"{row['climate_scenario']} unanimous-lower area share={row['area_weighted_cell_share_unanimously_lower']:.4f}"
        for row in result["results"]
    ))


if __name__ == "__main__":
    main()
