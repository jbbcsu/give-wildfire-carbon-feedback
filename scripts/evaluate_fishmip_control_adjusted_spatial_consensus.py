#!/usr/bin/env python3
"""Audit FishMIP control-adjusted spatial signs on the exact 20-file support.

This is a structural sensitivity diagnostic.  It does not identify a forced
climate response because the historical/future social forcing changes at the
2015 join, and it does not construct a marginal carbon pulse or welfare.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np

from evaluate_fishmip_spatial_change_distribution import (
    FORCINGS,
    MODELS,
    REFERENCE,
    ROOT,
    SCENARIOS,
    display_path,
    period_cell_mean,
    raw_path,
    require,
    sha256,
)
from evaluate_fishmip_spatial_consensus import summarize_consensus


FUTURE = (2081, 2090)
EXPERIMENTS = (
    ("forced_historical", "historical", "historical"),
    ("control_historical", "picontrol", "historical"),
    ("control_future", "picontrol", "future"),
    ("ssp126_future", "ssp126", "future"),
    ("ssp585_future", "ssp585", "future"),
)


def read_complete_plan(path: Path) -> dict[tuple[str, str, str], dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    selected: dict[tuple[str, str, str], dict[str, str]] = {}
    for row in rows:
        key = (row["climate_forcing"], row["model"], f"{row['period']}:{row['climate_scenario']}")
        if key[0] not in FORCINGS or key[1] not in MODELS:
            continue
        if key in selected:
            raise ValueError(f"acquisition plan duplicates {key}")
        selected[key] = row
    expected = {
        (forcing, model, f"{period}:{scenario}")
        for forcing in FORCINGS
        for model in MODELS
        for _, scenario, period in EXPERIMENTS
    }
    require(set(selected) == expected, "acquisition plan lacks the exact 20-file control-adjusted matrix")
    for (_, _, experiment), row in selected.items():
        period, _ = experiment.split(":", 1)
        expected_social_scenario = "histsoc" if period == "historical" else "2015soc-from-histsoc"
        require(row["soc_scenario"] == expected_social_scenario, "social-forcing identity changed")
        require(row["acquisition_stage"] in {"content_smoke", "deferred_full_matrix"},
                "acquisition stage is not admitted")
    return selected


def area_weighted_mean(values: np.ndarray, support: np.ndarray, latitude: np.ndarray) -> float:
    require(values.shape == support.shape and values.shape[0] == len(latitude), "spatial shape changed")
    require(bool(support.any()) and bool(np.isfinite(values[support]).all()), "spatial support is invalid")
    require(bool((values[support] >= 0).all()), "catch density is negative")
    weights = (np.cos(np.deg2rad(latitude))[:, None] * np.ones((1, support.shape[1])))[support]
    require(bool(np.isfinite(weights).all()) and float(weights.sum()) > 0, "spatial weights are invalid")
    return float(np.sum(values[support] * weights) / np.sum(weights))


def normalized_control_adjusted_change(
    forced_reference: np.ndarray,
    forced_future: np.ndarray,
    control_reference: np.ndarray,
    control_future: np.ndarray,
    support: np.ndarray,
    latitude: np.ndarray,
) -> tuple[np.ndarray, dict[str, float]]:
    arrays = (forced_reference, forced_future, control_reference, control_future)
    require(all(array.shape == support.shape for array in arrays), "control-adjusted arrays have different shapes")
    for array in arrays:
        require(bool(np.isfinite(array[support]).all()), "control-adjusted input is nonfinite")
        require(bool((array[support] >= 0).all()), "control-adjusted input is negative")
    forced_scale = area_weighted_mean(forced_reference, support, latitude)
    control_scale = area_weighted_mean(control_reference, support, latitude)
    require(forced_scale > 0 and control_scale > 0, "reference mean density must be positive")
    adjusted = np.full(support.shape, np.nan, dtype=float)
    adjusted[support] = (
        (forced_future[support] - forced_reference[support]) / forced_scale
        - (control_future[support] - control_reference[support]) / control_scale
    )
    weights = (np.cos(np.deg2rad(latitude))[:, None] * np.ones((1, support.shape[1])))[support]
    mean_adjustment = float(np.sum(adjusted[support] * weights) / np.sum(weights))
    forced_relative_change = area_weighted_mean(forced_future, support, latitude) / forced_scale - 1.0
    control_relative_change = area_weighted_mean(control_future, support, latitude) / control_scale - 1.0
    require(abs(mean_adjustment - (forced_relative_change - control_relative_change)) <= 1e-12,
            "spatial adjustment does not reconcile to the global difference in relative changes")
    return adjusted, {
        "forced_reference_mean_density_g_m2": forced_scale,
        "control_reference_mean_density_g_m2": control_scale,
        "forced_relative_change": forced_relative_change,
        "control_relative_change": control_relative_change,
        "difference_in_relative_changes": mean_adjustment,
    }


def summarize_adjusted_change(change: np.ndarray, support: np.ndarray, latitude: np.ndarray) -> dict[str, float | int]:
    require(change.shape == support.shape and change.shape[0] == len(latitude), "adjusted-change shape changed")
    values = change[support]
    require(bool(values.size) and bool(np.isfinite(values).all()), "adjusted change is nonfinite or empty")
    weights = (np.cos(np.deg2rad(latitude))[:, None] * np.ones((1, support.shape[1])))[support]
    require(float(weights.sum()) > 0, "adjusted-change weights are empty")
    lower = values < 0
    higher = values > 0
    unchanged = values == 0
    require(bool((lower | higher | unchanged).all()), "adjusted-change signs are incomplete")
    quantiles = np.quantile(values, [0.05, 0.25, 0.5, 0.75, 0.95])
    return {
        "common_finite_grid_cells": int(support.sum()),
        "unweighted_cell_share_lower": float(np.mean(lower)),
        "area_weighted_cell_share_lower": float(weights[lower].sum() / weights.sum()),
        "unweighted_cell_share_higher": float(np.mean(higher)),
        "area_weighted_cell_share_higher": float(weights[higher].sum() / weights.sum()),
        "unweighted_cell_share_exactly_unchanged": float(np.mean(unchanged)),
        "area_weighted_cell_share_exactly_unchanged": float(weights[unchanged].sum() / weights.sum()),
        "normalized_adjusted_change_quantiles": {
            key: float(value) for key, value in zip(("p05", "p25", "p50", "p75", "p95"), quantiles)
        },
    }


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
                receipts.append({
                    "climate_forcing": forcing,
                    "ecosystem_model": model,
                    "experiment": label,
                    "path": display_path(path),
                    "bytes": int(row["bytes"]),
                    "sha512": row["sha512"],
                })
                if latitude is None:
                    latitude, longitude = lat, lon
                else:
                    require(np.array_equal(latitude, lat) and np.array_equal(longitude, lon), "matrix grids differ")
                finite = np.isfinite(values)
                support = finite if support is None else support & finite
    assert latitude is not None and support is not None
    require(int(support.sum()) > 0, "20-file common support is empty")

    results: list[dict[str, object]] = []
    consensus: list[dict[str, object]] = []
    for scenario in SCENARIOS:
        changes: list[np.ndarray] = []
        for forcing in FORCINGS:
            for model in MODELS:
                change, global_summary = normalized_control_adjusted_change(
                    arrays[(forcing, model, "forced_historical")],
                    arrays[(forcing, model, f"{scenario}_future")],
                    arrays[(forcing, model, "control_historical")],
                    arrays[(forcing, model, "control_future")],
                    support,
                    latitude,
                )
                changes.append(change)
                results.append({
                    "climate_forcing": forcing,
                    "ecosystem_model": model,
                    "climate_scenario": scenario,
                    **global_summary,
                    **summarize_adjusted_change(change, support, latitude),
                })
        consensus.append({"climate_scenario": scenario, **summarize_consensus(changes, support, latitude)})

    return {
        "schema": "fishmip_control_adjusted_spatial_consensus_v1",
        "status": "validated_structural_control_adjusted_spatial_sensitivity_only",
        "reference_period": {"start_year": REFERENCE[0], "end_year": REFERENCE[1]},
        "future_period": {"start_year": FUTURE[0], "end_year": FUTURE[1]},
        "support_rule": "intersection_across_all_20_frozen_scenario_and_control_files",
        "normalization_rule": (
            "forced_cell_change_divided_by_forced_global_reference_mean_minus_"
            "control_cell_change_divided_by_control_global_reference_mean"
        ),
        "results": results,
        "consensus": consensus,
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
            "Cell signs after a structural control adjustment are not causal forced responses, observed catch, "
            "welfare, a matched carbon pulse, damages, or SCC evidence."
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
    print("FishMIP control-adjusted spatial consensus passed: " + ", ".join(
        f"{row['climate_scenario']} unanimous-lower={row['area_weighted_cell_share_unanimously_lower']:.4f}"
        for row in result["consensus"]
    ))


if __name__ == "__main__":
    main()
