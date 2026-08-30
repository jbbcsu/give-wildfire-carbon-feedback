#!/usr/bin/env python3
"""Audit temporal robustness of FishMIP control-adjusted spatial signs.

This repeats the exact 20-file structural sensitivity over three fixed future
decades.  It is not causal attribution, a matched carbon pulse, welfare,
damages, or an SCC calculation.
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
    summarize_adjusted_change,
)
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


FUTURE_WINDOWS = ((2021, 2030), (2041, 2050), (2081, 2090))


def summarize_time_window_robustness(consensus: list[dict[str, object]]) -> list[dict[str, object]]:
    expected = {
        (scenario, start, end)
        for scenario in SCENARIOS
        for start, end in FUTURE_WINDOWS
    }
    seen: set[tuple[str, int, int]] = set()
    for row in consensus:
        window = row.get("future_period")
        require(isinstance(window, dict), "future-period identity is absent")
        key = (
            str(row.get("climate_scenario")),
            int(window.get("start_year", -1)),
            int(window.get("end_year", -1)),
        )
        require(key not in seen, "scenario-window consensus is duplicated")
        seen.add(key)
        for field in (
            "area_weighted_cell_share_at_least_three_lower",
            "area_weighted_cell_share_unanimously_lower",
        ):
            value = float(row[field])
            require(np.isfinite(value) and 0 <= value <= 1, f"{field} is invalid")
    require(seen == expected, "consensus lacks the exact scenario-window product")

    summaries: list[dict[str, object]] = []
    for scenario in SCENARIOS:
        rows = [row for row in consensus if row["climate_scenario"] == scenario]
        rows.sort(key=lambda row: int(row["future_period"]["start_year"]))
        at_least_three = [float(row["area_weighted_cell_share_at_least_three_lower"]) for row in rows]
        unanimous = [float(row["area_weighted_cell_share_unanimously_lower"]) for row in rows]
        summaries.append({
            "climate_scenario": scenario,
            "future_windows": [row["future_period"] for row in rows],
            "area_weighted_at_least_three_lower_min": min(at_least_three),
            "area_weighted_at_least_three_lower_max": max(at_least_three),
            "area_weighted_unanimously_lower_min": min(unanimous),
            "area_weighted_unanimously_lower_max": max(unanimous),
            "at_least_three_lower_is_monotone_non_decreasing": all(
                right >= left for left, right in zip(at_least_three, at_least_three[1:])
            ),
            "unanimously_lower_is_monotone_non_decreasing": all(
                right >= left for left, right in zip(unanimous, unanimous[1:])
            ),
        })
    return summaries


def evaluate(plan_path: Path, raw_root: Path) -> dict[str, object]:
    plan = read_complete_plan(plan_path)
    reference_arrays: dict[tuple[str, str, str], np.ndarray] = {}
    future_arrays: dict[tuple[str, str, str, int, int], np.ndarray] = {}
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
                    reference_arrays[(forcing, model, label)] = values
                    finite = np.isfinite(values)
                    support = finite if support is None else support & finite
                else:
                    for start, end in FUTURE_WINDOWS:
                        values, lat, lon = period_cell_mean(path, row, start, end)
                        future_arrays[(forcing, model, label, start, end)] = values
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
    require(int(support.sum()) > 0, "all-window 20-file common support is empty")

    results: list[dict[str, object]] = []
    consensus: list[dict[str, object]] = []
    for start, end in FUTURE_WINDOWS:
        for scenario in SCENARIOS:
            changes: list[np.ndarray] = []
            for forcing in FORCINGS:
                for model in MODELS:
                    change, global_summary = normalized_control_adjusted_change(
                        reference_arrays[(forcing, model, "forced_historical")],
                        future_arrays[(forcing, model, f"{scenario}_future", start, end)],
                        reference_arrays[(forcing, model, "control_historical")],
                        future_arrays[(forcing, model, "control_future", start, end)],
                        support,
                        latitude,
                    )
                    changes.append(change)
                    results.append({
                        "climate_forcing": forcing,
                        "ecosystem_model": model,
                        "climate_scenario": scenario,
                        "future_period": {"start_year": start, "end_year": end},
                        **global_summary,
                        **summarize_adjusted_change(change, support, latitude),
                    })
            consensus.append({
                "climate_scenario": scenario,
                "future_period": {"start_year": start, "end_year": end},
                **summarize_consensus(changes, support, latitude),
            })

    robustness = summarize_time_window_robustness(consensus)
    return {
        "schema": "fishmip_control_adjusted_spatial_time_windows_v1",
        "status": "validated_temporal_structural_control_adjusted_spatial_sensitivity_only",
        "reference_period": {"start_year": REFERENCE[0], "end_year": REFERENCE[1]},
        "future_periods": [{"start_year": start, "end_year": end} for start, end in FUTURE_WINDOWS],
        "support_rule": "intersection_across_all_20_frozen_files_and_all_registered_decades",
        "normalization_rule": (
            "forced_cell_change_divided_by_forced_global_reference_mean_minus_"
            "control_cell_change_divided_by_control_global_reference_mean"
        ),
        "results": results,
        "consensus": consensus,
        "temporal_robustness": robustness,
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
            "Temporal persistence of cell signs after a structural control adjustment is not causal forced "
            "response, observed catch, welfare, a matched carbon pulse, damages, or SCC evidence."
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
    print("FishMIP control-adjusted spatial time-window audit passed: " + ", ".join(
        f"{row['climate_scenario']} at-least-three-lower="
        f"{row['area_weighted_at_least_three_lower_min']:.4f}--"
        f"{row['area_weighted_at_least_three_lower_max']:.4f}"
        for row in result["temporal_robustness"]
    ))


if __name__ == "__main__":
    main()
