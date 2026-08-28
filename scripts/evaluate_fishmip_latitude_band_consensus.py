#!/usr/bin/env python3
"""Audit end-century FishMIP sign consensus in fixed latitude bands."""

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


FUTURE = (2091, 2100)
LATITUDE_BANDS = (
    ("south_high", -90.0, -40.0),
    ("south_mid", -40.0, -20.0),
    ("tropics", -20.0, 20.0),
    ("north_mid", 20.0, 40.0),
    ("north_high", 40.0, 90.0),
)


def summarize_bands(
    changes: list[np.ndarray], support: np.ndarray, latitude: np.ndarray
) -> list[dict[str, object]]:
    require(support.shape[0] == len(latitude), "latitude-band support shape changed")
    assigned = np.zeros_like(latitude, dtype=bool)
    global_weights = (
        np.cos(np.deg2rad(latitude))[:, None] * np.ones((1, support.shape[1]))
    )[support]
    require(float(global_weights.sum()) > 0, "global common-support weight is empty")

    results: list[dict[str, object]] = []
    for index, (label, lower, upper) in enumerate(LATITUDE_BANDS):
        rows = (latitude >= lower) & (latitude < upper)
        if index == len(LATITUDE_BANDS) - 1:
            rows = (latitude >= lower) & (latitude <= upper)
        require(not bool((assigned & rows).any()), "latitude bands overlap")
        assigned |= rows
        band_support = support & rows[:, None]
        summary = summarize_consensus(changes, band_support, latitude)
        band_weights = (
            np.cos(np.deg2rad(latitude))[:, None] * np.ones((1, support.shape[1]))
        )[band_support]
        results.append({
            "latitude_band": label,
            "lower_bound_degrees_north_inclusive": lower,
            "upper_bound_degrees_north_exclusive": upper,
            "area_weighted_share_of_global_common_support": float(
                band_weights.sum() / global_weights.sum()
            ),
            **summary,
        })
    require(bool(assigned.all()), "latitude bands do not cover the full grid")
    require(
        sum(int(row["common_finite_grid_cells"]) for row in results) == int(support.sum()),
        "latitude-band common-support counts do not conserve the global count",
    )
    require(
        abs(sum(float(row["area_weighted_share_of_global_common_support"]) for row in results) - 1.0)
        <= 1e-12,
        "latitude-band area weights do not conserve global support",
    )
    return results


def evaluate(plan_path: Path, raw_root: Path) -> dict[str, object]:
    plan = read_plan(plan_path)
    reference: dict[tuple[str, str], np.ndarray] = {}
    future: dict[tuple[str, str, str], np.ndarray] = {}
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
                values, future_lat, future_lon = period_cell_mean(path, row, *FUTURE)
                require(
                    np.array_equal(lat, future_lat) and np.array_equal(lon, future_lon),
                    "historical/future grid changed",
                )
                future[(forcing, model, scenario)] = values
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
    for scenario in SCENARIOS:
        changes = [
            future[(forcing, model, scenario)] - reference[(forcing, model)]
            for forcing in FORCINGS
            for model in MODELS
        ]
        for row in summarize_bands(changes, support, latitude):
            results.append({"climate_scenario": scenario, **row})

    require(
        len(results) == len(SCENARIOS) * len(LATITUDE_BANDS),
        "latitude-band result is incomplete",
    )
    return {
        "schema": "fishmip_latitude_band_sign_consensus_v1",
        "status": "validated_biophysical_latitude_band_sign_consensus_only",
        "reference_period": {"start_year": REFERENCE[0], "end_year": REFERENCE[1]},
        "future_period": {"start_year": FUTURE[0], "end_year": FUTURE[1]},
        "support_rule": "intersection_across_all_12_files_for_fixed_end_century_window",
        "trajectory_count_per_scenario_band": 4,
        "latitude_bands_fixed_before_evaluation": True,
        "results": results,
        "inputs": receipts,
        "plan": {"path": display_path(plan_path), "sha256": sha256(plan_path)},
        "implementation": {
            "path": display_path(Path(__file__).resolve()),
            "sha256": sha256(Path(__file__).resolve()),
        },
        "absolute_model_levels_averaged": False,
        "country_or_eez_allocation_performed": False,
        "scenario_contrast_is_marginal_pulse": False,
        "observed_catch": False,
        "welfare_estimated": False,
        "damage_estimated": False,
        "scc_authorized": False,
        "disclaimer": (
            "Latitude-band scenario catch-density signs are not country or EEZ allocation, "
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
    print(
        "FishMIP latitude-band consensus passed: "
        + ", ".join(
            f"{row['climate_scenario']} {row['latitude_band']}="
            f"{row['area_weighted_cell_share_at_least_three_lower']:.4f}"
            for row in result["results"]
        )
    )


if __name__ == "__main__":
    main()
