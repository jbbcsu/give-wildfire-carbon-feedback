#!/usr/bin/env python3
"""Audit late-century control-adjusted FishMIP magnitudes by latitude band.

The fixed bands expose where each model trajectory contributes to its global
normalized change.  They are not countries, EEZs, welfare, or a marginal CO2
pulse, and absolute catch-density levels are never averaged across models.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from evaluate_fishmip_control_adjusted_spatial_consensus import (
    EXPERIMENTS,
    FUTURE,
    normalized_control_adjusted_change,
    read_complete_plan,
)
from evaluate_fishmip_latitude_band_consensus import LATITUDE_BANDS
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


def area_weights(latitude: np.ndarray, shape: tuple[int, int]) -> np.ndarray:
    require(shape[0] == len(latitude), "latitude shape changed")
    weights = np.cos(np.deg2rad(latitude))[:, None] * np.ones((1, shape[1]))
    require(bool(np.isfinite(weights).all()) and bool((weights >= 0).all()), "area weights are invalid")
    return weights


def summarize_band_magnitudes(
    changes: dict[tuple[str, str], np.ndarray],
    support: np.ndarray,
    latitude: np.ndarray,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    expected = {(forcing, model) for forcing in FORCINGS for model in MODELS}
    require(set(changes) == expected, "latitude magnitude audit lacks the exact trajectory product")
    require(support.ndim == 2 and support.shape[0] == len(latitude), "support shape changed")
    require(bool(support.any()), "common support is empty")
    weights = area_weights(latitude, support.shape)
    global_weight = float(weights[support].sum())
    require(global_weight > 0, "common-support area weight is empty")

    trajectory_rows: list[dict[str, object]] = []
    band_rows: list[dict[str, object]] = []
    assigned = np.zeros(len(latitude), dtype=bool)
    band_contributions: dict[tuple[str, str], float] = {key: 0.0 for key in expected}
    for index, (label, lower, upper) in enumerate(LATITUDE_BANDS):
        latitude_rows = (latitude >= lower) & (latitude < upper)
        if index == len(LATITUDE_BANDS) - 1:
            latitude_rows = (latitude >= lower) & (latitude <= upper)
        require(not bool((assigned & latitude_rows).any()), "latitude bands overlap")
        assigned |= latitude_rows
        band_support = support & latitude_rows[:, None]
        band_weight = float(weights[band_support].sum())
        require(band_weight > 0, f"latitude band {label} has no common support")
        band_means: list[float] = []
        for forcing in FORCINGS:
            for model in MODELS:
                values = changes[(forcing, model)]
                require(values.shape == support.shape, "trajectory shape changed")
                require(bool(np.isfinite(values[support]).all()), "trajectory contains nonfinite support values")
                selected = values[band_support]
                selected_weights = weights[band_support]
                mean = float(np.sum(selected * selected_weights) / band_weight)
                negative_share = float(selected_weights[selected < 0].sum() / band_weight)
                contribution = float(np.sum(selected * selected_weights) / global_weight)
                band_contributions[(forcing, model)] += contribution
                band_means.append(mean)
                trajectory_rows.append({
                    "latitude_band": label,
                    "lower_bound_degrees_north_inclusive": lower,
                    "upper_bound_degrees_north_exclusive": upper,
                    "climate_forcing": forcing,
                    "ecosystem_model": model,
                    "common_finite_grid_cells": int(band_support.sum()),
                    "area_weighted_share_of_global_common_support": band_weight / global_weight,
                    "band_mean_normalized_control_adjusted_change": mean,
                    "band_contribution_to_global_normalized_change": contribution,
                    "area_weighted_cell_share_negative": negative_share,
                })
        band_rows.append({
            "latitude_band": label,
            "lower_bound_degrees_north_inclusive": lower,
            "upper_bound_degrees_north_exclusive": upper,
            "negative_trajectory_count": int(sum(value < 0 for value in band_means)),
            "trajectory_count": len(band_means),
            "minimum_band_mean_normalized_change": float(min(band_means)),
            "maximum_band_mean_normalized_change": float(max(band_means)),
        })

    require(bool(assigned.all()), "latitude bands do not cover the full grid")
    for key, values in changes.items():
        global_mean = float(np.sum(values[support] * weights[support]) / global_weight)
        require(
            abs(band_contributions[key] - global_mean) <= 1e-12,
            f"latitude-band contributions do not reconcile for {key}",
        )
    return trajectory_rows, band_rows


def evaluate(plan_path: Path, raw_root: Path) -> dict[str, object]:
    plan = read_complete_plan(plan_path)
    arrays: dict[tuple[str, str, str], np.ndarray] = {}
    latitude: np.ndarray | None = None
    longitude: np.ndarray | None = None
    support: np.ndarray | None = None
    receipts: list[dict[str, object]] = []
    for forcing in FORCINGS:
        for model in MODELS:
            for label, scenario, period in EXPERIMENTS:
                row = plan[(forcing, model, f"{period}:{scenario}")]
                path = raw_path(raw_root, row)
                start, end = REFERENCE if period == "historical" else FUTURE
                values, lat, lon = period_cell_mean(path, row, start, end)
                arrays[(forcing, model, label)] = values
                finite = np.isfinite(values)
                support = finite if support is None else support & finite
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
    require(int(support.sum()) > 0, "20-file common support is empty")

    results: list[dict[str, object]] = []
    band_summaries: list[dict[str, object]] = []
    for scenario in SCENARIOS:
        changes: dict[tuple[str, str], np.ndarray] = {}
        for forcing in FORCINGS:
            for model in MODELS:
                change, _ = normalized_control_adjusted_change(
                    arrays[(forcing, model, "forced_historical")],
                    arrays[(forcing, model, f"{scenario}_future")],
                    arrays[(forcing, model, "control_historical")],
                    arrays[(forcing, model, "control_future")],
                    support,
                    latitude,
                )
                changes[(forcing, model)] = change
        trajectory_rows, summary_rows = summarize_band_magnitudes(changes, support, latitude)
        results.extend({"climate_scenario": scenario, **row} for row in trajectory_rows)
        band_summaries.extend({"climate_scenario": scenario, **row} for row in summary_rows)

    return {
        "schema": "fishmip_control_adjusted_latitude_band_magnitudes_v1",
        "status": "validated_latitude_band_structural_magnitude_sensitivity_only",
        "reference_period": {"start_year": REFERENCE[0], "end_year": REFERENCE[1]},
        "future_period": {"start_year": FUTURE[0], "end_year": FUTURE[1]},
        "latitude_bands": [
            {"label": label, "lower_bound": lower, "upper_bound": upper}
            for label, lower, upper in LATITUDE_BANDS
        ],
        "support_rule": "intersection_across_all_20_frozen_scenario_and_control_files",
        "normalization_rule": (
            "forced_cell_change_divided_by_forced_global_reference_mean_minus_"
            "control_cell_change_divided_by_control_global_reference_mean"
        ),
        "results": results,
        "band_summaries": band_summaries,
        "inputs": receipts,
        "plan": {"path": display_path(plan_path), "sha256": sha256(plan_path)},
        "implementation": {"path": display_path(Path(__file__).resolve()), "sha256": sha256(Path(__file__).resolve())},
        "absolute_model_levels_averaged": False,
        "social_forcing_constant_across_historical_future_join": False,
        "country_or_eez_allocation_performed": False,
        "forced_response_estimated": False,
        "observed_catch": False,
        "matched_co2_pulse": False,
        "welfare_estimated": False,
        "damage_estimated": False,
        "scc_authorized": False,
        "disclaimer": (
            "Latitude-band magnitudes after a structural control adjustment are not causal forced responses, "
            "country or EEZ allocation, observed catch, welfare, damages, or SCC evidence."
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
    print("FishMIP latitude-band magnitude audit passed")


if __name__ == "__main__":
    main()
