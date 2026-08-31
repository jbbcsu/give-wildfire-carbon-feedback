#!/usr/bin/env python3
"""Partition persistent control-adjusted FishMIP signs by latitude band.

This combines the predeclared three-window same-cell persistence rule with the
existing five exhaustive latitude bands.  It remains a structural sensitivity,
not causal attribution, observed-catch validation, welfare, damages, or SCC.
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
from evaluate_fishmip_latitude_band_consensus import LATITUDE_BANDS, summarize_bands
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


def persistent_band_results(
    window_changes: dict[tuple[str, str, str], list[np.ndarray]],
    support: np.ndarray,
    latitude: np.ndarray,
) -> list[dict[str, object]]:
    expected = {
        (scenario, forcing, model)
        for scenario in SCENARIOS
        for forcing in FORCINGS
        for model in MODELS
    }
    require(set(window_changes) == expected, "persistent latitude audit lacks the exact trajectory product")
    results: list[dict[str, object]] = []
    for scenario in SCENARIOS:
        persistent_changes: list[np.ndarray] = []
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
        for row in summarize_bands(persistent_changes, support, latitude):
            results.append({"climate_scenario": scenario, **row})
    require(
        len(results) == len(SCENARIOS) * len(LATITUDE_BANDS),
        "persistent latitude-band result is incomplete",
    )
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
        "schema": "fishmip_control_adjusted_spatial_persistence_latitude_bands_v1",
        "status": "validated_latitude_band_persistent_structural_spatial_sensitivity_only",
        "reference_period": {"start_year": REFERENCE[0], "end_year": REFERENCE[1]},
        "future_periods": [{"start_year": start, "end_year": end} for start, end in FUTURE_WINDOWS],
        "latitude_bands": [
            {"label": label, "lower_bound": lower, "upper_bound": upper}
            for label, lower, upper in LATITUDE_BANDS
        ],
        "latitude_bands_fixed_before_evaluation": True,
        "persistent_lower_rule": "maximum_adjusted_change_across_registered_windows_is_strictly_negative",
        "support_rule": "intersection_across_all_20_frozen_files_and_all_registered_decades",
        "normalization_rule": (
            "forced_cell_change_divided_by_forced_global_reference_mean_minus_"
            "control_cell_change_divided_by_control_global_reference_mean"
        ),
        "results": persistent_band_results(window_changes, support, latitude),
        "inputs": receipts,
        "plan": {"path": display_path(plan_path), "sha256": sha256(plan_path)},
        "implementation": {"path": display_path(Path(__file__).resolve()), "sha256": sha256(Path(__file__).resolve())},
        "absolute_model_levels_averaged": False,
        "social_forcing_constant_across_historical_future_join": False,
        "forced_response_estimated": False,
        "observed_catch": False,
        "country_or_eez_allocation_performed": False,
        "matched_co2_pulse": False,
        "welfare_estimated": False,
        "damage_estimated": False,
        "scc_authorized": False,
        "disclaimer": (
            "Latitude-band persistent signs after a structural control adjustment are not causal forced "
            "responses, observed catch, country or EEZ allocation, welfare, damages, or SCC evidence."
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
    print("FishMIP persistent latitude-band audit passed: " + ", ".join(
        f"{row['climate_scenario']} {row['latitude_band']}="
        f"{row['area_weighted_cell_share_at_least_three_lower']:.4f}"
        for row in result["results"]
    ))


if __name__ == "__main__":
    main()
