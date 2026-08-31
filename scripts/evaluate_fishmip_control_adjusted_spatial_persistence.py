#!/usr/bin/env python3
"""Audit persistent FishMIP control-adjusted grid-cell signs across decades.

For each forcing/model trajectory, a cell is persistently lower only when its
normalized forced-minus-control change is negative in every registered future
window.  This is a structural sensitivity, not causal attribution, observed
catch, a matched carbon pulse, welfare, damages, or an SCC calculation.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from evaluate_fishmip_control_adjusted_spatial_consensus import (
    EXPERIMENTS,
    normalized_control_adjusted_change,
    read_complete_plan,
)
from evaluate_fishmip_control_adjusted_spatial_time_windows import FUTURE_WINDOWS
from evaluate_fishmip_spatial_change_distribution import (
    FORCINGS,
    MODELS,
    REFERENCE,
    SCENARIOS,
    display_path,
    period_cell_mean,
    raw_path,
    require,
    sha256,
)
from evaluate_fishmip_spatial_consensus import summarize_consensus


def summarize_persistent_consensus(
    window_changes: dict[tuple[str, str, str], list[np.ndarray]],
    support: np.ndarray,
    latitude: np.ndarray,
) -> list[dict[str, object]]:
    """Summarize cells negative in every window for each trajectory."""
    expected = {
        (scenario, forcing, model)
        for scenario in SCENARIOS
        for forcing in FORCINGS
        for model in MODELS
    }
    require(set(window_changes) == expected, "persistent audit lacks the exact scenario/forcing/model product")
    results: list[dict[str, object]] = []
    for scenario in SCENARIOS:
        persistent_changes: list[np.ndarray] = []
        trajectory_results: list[dict[str, object]] = []
        for forcing in FORCINGS:
            for model in MODELS:
                changes = window_changes[(scenario, forcing, model)]
                require(len(changes) == len(FUTURE_WINDOWS), "trajectory lacks the exact future-window product")
                require(all(change.shape == support.shape for change in changes), "trajectory spatial shape changed")
                stacked = np.stack(changes)
                require(bool(np.isfinite(stacked[:, support]).all()), "trajectory contains nonfinite support values")
                maximum_change = np.full(support.shape, np.nan, dtype=float)
                maximum_change[support] = np.max(stacked[:, support], axis=0)
                persistent_changes.append(maximum_change)
                persistent_lower = maximum_change[support] < 0
                weights = (np.cos(np.deg2rad(latitude))[:, None] * np.ones(support.shape))[support]
                trajectory_results.append({
                    "climate_forcing": forcing,
                    "ecosystem_model": model,
                    "unweighted_cell_share_lower_in_every_window": float(np.mean(persistent_lower)),
                    "area_weighted_cell_share_lower_in_every_window": float(
                        weights[persistent_lower].sum() / weights.sum()
                    ),
                })
        results.append({
            "climate_scenario": scenario,
            "trajectory_persistence": trajectory_results,
            **summarize_consensus(persistent_changes, support, latitude),
        })
    return results


def evaluate(plan_path: Path, raw_root: Path) -> dict[str, object]:
    plan = read_complete_plan(plan_path)
    references: dict[tuple[str, str, str], np.ndarray] = {}
    futures: dict[tuple[str, str, str, int, int], np.ndarray] = {}
    latitude: np.ndarray | None = None
    longitude: np.ndarray | None = None
    support: np.ndarray | None = None
    receipts: list[dict[str, object]] = []

    for forcing in FORCINGS:
        for model in MODELS:
            for label, scenario, period in EXPERIMENTS:
                row = plan[(forcing, model, f"{period}:{scenario}")]
                path = raw_path(raw_root, row)
                if period == "historical":
                    values, lat, lon = period_cell_mean(path, row, *REFERENCE)
                    references[(forcing, model, label)] = values
                    support = np.isfinite(values) if support is None else support & np.isfinite(values)
                else:
                    for start, end in FUTURE_WINDOWS:
                        values, lat, lon = period_cell_mean(path, row, start, end)
                        futures[(forcing, model, label, start, end)] = values
                        support = np.isfinite(values) if support is None else support & np.isfinite(values)
                if latitude is None:
                    latitude, longitude = lat, lon
                else:
                    require(np.array_equal(latitude, lat) and np.array_equal(longitude, lon), "matrix grids differ")
                receipts.append({
                    "climate_forcing": forcing,
                    "ecosystem_model": model,
                    "experiment": label,
                    "path": display_path(path),
                    "bytes": int(row["bytes"]),
                    "sha512": row["sha512"],
                })

    assert latitude is not None and support is not None
    require(int(support.sum()) > 0, "all-window 20-file common support is empty")
    window_changes: dict[tuple[str, str, str], list[np.ndarray]] = {}
    for scenario in SCENARIOS:
        for forcing in FORCINGS:
            for model in MODELS:
                changes: list[np.ndarray] = []
                for start, end in FUTURE_WINDOWS:
                    change, _ = normalized_control_adjusted_change(
                        references[(forcing, model, "forced_historical")],
                        futures[(forcing, model, f"{scenario}_future", start, end)],
                        references[(forcing, model, "control_historical")],
                        futures[(forcing, model, "control_future", start, end)],
                        support,
                        latitude,
                    )
                    changes.append(change)
                window_changes[(scenario, forcing, model)] = changes

    return {
        "schema": "fishmip_control_adjusted_spatial_persistence_v1",
        "status": "validated_temporal_persistent_structural_spatial_sensitivity_only",
        "reference_period": {"start_year": REFERENCE[0], "end_year": REFERENCE[1]},
        "future_periods": [{"start_year": start, "end_year": end} for start, end in FUTURE_WINDOWS],
        "persistent_lower_rule": "maximum_adjusted_change_across_registered_windows_is_strictly_negative",
        "support_rule": "intersection_across_all_20_frozen_files_and_all_registered_decades",
        "normalization_rule": (
            "forced_cell_change_divided_by_forced_global_reference_mean_minus_"
            "control_cell_change_divided_by_control_global_reference_mean"
        ),
        "results": summarize_persistent_consensus(window_changes, support, latitude),
        "inputs": receipts,
        "plan": {"path": display_path(plan_path), "sha256": sha256(plan_path)},
        "implementation": {"path": display_path(Path(__file__).resolve()), "sha256": sha256(Path(__file__).resolve())},
        "absolute_model_levels_averaged": False,
        "social_forcing_constant_across_historical_future_join": False,
        "forced_response_estimated": False,
        "observed_catch": False,
        "matched_co2_pulse": False,
        "welfare_estimated": False,
        "damage_estimated": False,
        "scc_authorized": False,
        "disclaimer": (
            "Persistent cell signs after a structural control adjustment are not causal forced responses, "
            "observed catch, welfare, a matched carbon pulse, damages, or SCC evidence."
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
    print("FishMIP persistent spatial-sign audit passed: " + ", ".join(
        f"{row['climate_scenario']} persistent at-least-three-lower="
        f"{row['area_weighted_cell_share_at_least_three_lower']:.4f}"
        for row in result["results"]
    ))


if __name__ == "__main__":
    main()
