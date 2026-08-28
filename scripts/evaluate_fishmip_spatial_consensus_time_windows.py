#!/usr/bin/env python3
"""Audit FishMIP sign-consensus robustness across fixed late-century decades."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from evaluate_fishmip_spatial_change_distribution import (
    FORCINGS,
    MODELS,
    REFERENCE,
    SCENARIOS,
    display_path,
    period_cell_mean,
    raw_path,
    read_plan,
    require,
    sha256,
)
from evaluate_fishmip_spatial_consensus import summarize_consensus


FUTURE_WINDOWS = ((2071, 2080), (2081, 2090), (2091, 2100))


def evaluate(plan_path: Path, raw_root: Path) -> dict[str, object]:
    plan = read_plan(plan_path)
    reference: dict[tuple[str, str], np.ndarray] = {}
    future: dict[tuple[str, str, str, int, int], np.ndarray] = {}
    latitude: np.ndarray | None = None
    longitude: np.ndarray | None = None
    support: np.ndarray | None = None
    receipts: list[dict[str, object]] = []

    for forcing in FORCINGS:
        for model in MODELS:
            historical_row = plan[(forcing, model, "historical")]
            historical_path = raw_path(raw_root, historical_row)
            values, lat, lon = period_cell_mean(historical_path, historical_row, *REFERENCE)
            reference[(forcing, model)] = values
            receipts.append({
                "climate_forcing": forcing,
                "ecosystem_model": model,
                "scenario": "historical",
                "path": display_path(historical_path),
                "sha512": historical_row["sha512"],
            })
            for scenario in SCENARIOS:
                row = plan[(forcing, model, scenario)]
                path = raw_path(raw_root, row)
                for start, end in FUTURE_WINDOWS:
                    values, future_lat, future_lon = period_cell_mean(path, row, start, end)
                    require(
                        np.array_equal(lat, future_lat) and np.array_equal(lon, future_lon),
                        "historical/future grid changed",
                    )
                    future[(forcing, model, scenario, start, end)] = values
                receipts.append({
                    "climate_forcing": forcing,
                    "ecosystem_model": model,
                    "scenario": scenario,
                    "path": display_path(path),
                    "sha512": row["sha512"],
                })
            if latitude is None:
                latitude, longitude = lat, lon
            else:
                require(
                    np.array_equal(latitude, lat) and np.array_equal(longitude, lon),
                    "forcing/model grids differ",
                )

    assert latitude is not None
    for values in [*reference.values(), *future.values()]:
        finite = np.isfinite(values)
        support = finite if support is None else support & finite
    assert support is not None

    results: list[dict[str, object]] = []
    for start, end in FUTURE_WINDOWS:
        for scenario in SCENARIOS:
            changes = [
                future[(forcing, model, scenario, start, end)] - reference[(forcing, model)]
                for forcing in FORCINGS
                for model in MODELS
            ]
            results.append({
                "future_start_year": start,
                "future_end_year": end,
                "climate_scenario": scenario,
                **summarize_consensus(changes, support, latitude),
            })

    require(len(results) == len(FUTURE_WINDOWS) * len(SCENARIOS), "time-window result is incomplete")
    return {
        "schema": "fishmip_spatial_sign_consensus_time_windows_v1",
        "status": "validated_biophysical_time_window_robustness_only",
        "reference_period": {"start_year": REFERENCE[0], "end_year": REFERENCE[1]},
        "future_windows": [
            {"start_year": start, "end_year": end} for start, end in FUTURE_WINDOWS
        ],
        "support_rule": "intersection_across_all_12_files_and_all_three_fixed_future_decades",
        "trajectory_count_per_scenario_window": 4,
        "results": results,
        "inputs": receipts,
        "plan": {"path": display_path(plan_path), "sha256": sha256(plan_path)},
        "implementation": {"path": display_path(Path(__file__).resolve()), "sha256": sha256(Path(__file__).resolve())},
        "absolute_model_levels_averaged": False,
        "scenario_contrast_is_marginal_pulse": False,
        "observed_catch": False,
        "welfare_estimated": False,
        "damage_estimated": False,
        "scc_authorized": False,
        "disclaimer": (
            "Temporal robustness of scenario catch-density signs is not observed catch, welfare, "
            "a matched carbon pulse, damages, or SCC evidence."
        ),
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
    print("FishMIP temporal sign-consensus robustness passed: " + ", ".join(
        f"{row['climate_scenario']} {row['future_start_year']}-{row['future_end_year']}="
        f"{row['area_weighted_cell_share_unanimously_lower']:.4f}"
        for row in result["results"]
    ))


if __name__ == "__main__":
    main()
