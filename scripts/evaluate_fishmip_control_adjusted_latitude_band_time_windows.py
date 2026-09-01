#!/usr/bin/env python3
"""Audit temporal robustness of control-adjusted FishMIP latitude magnitudes."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from evaluate_fishmip_control_adjusted_latitude_band_magnitudes import summarize_band_magnitudes
from evaluate_fishmip_control_adjusted_spatial_consensus import (
    EXPERIMENTS,
    normalized_control_adjusted_change,
    read_complete_plan,
)
from evaluate_fishmip_control_adjusted_spatial_time_windows import FUTURE_WINDOWS
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


def summarize_temporal_bands(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    expected = {
        (scenario, start, end, band, forcing, model)
        for scenario in SCENARIOS
        for start, end in FUTURE_WINDOWS
        for band, _, _ in LATITUDE_BANDS
        for forcing in FORCINGS
        for model in MODELS
    }
    indexed: dict[tuple[str, int, int, str, str, str], dict[str, object]] = {}
    for row in rows:
        period = row.get("future_period")
        require(isinstance(period, dict), "future-period identity is absent")
        key = (
            str(row.get("climate_scenario")),
            int(period.get("start_year", -1)),
            int(period.get("end_year", -1)),
            str(row.get("latitude_band")),
            str(row.get("climate_forcing")),
            str(row.get("ecosystem_model")),
        )
        require(key not in indexed, "scenario-window-band trajectory is duplicated")
        mean = float(row["band_mean_normalized_control_adjusted_change"])
        require(np.isfinite(mean), "band mean is nonfinite")
        indexed[key] = row
    require(set(indexed) == expected, "temporal latitude audit lacks the exact product")

    output: list[dict[str, object]] = []
    for scenario in SCENARIOS:
        for band, _, _ in LATITUDE_BANDS:
            window_rows: list[dict[str, object]] = []
            for start, end in FUTURE_WINDOWS:
                values = [
                    float(indexed[(scenario, start, end, band, forcing, model)]["band_mean_normalized_control_adjusted_change"])
                    for forcing in FORCINGS
                    for model in MODELS
                ]
                window_rows.append({
                    "start_year": start,
                    "end_year": end,
                    "negative_trajectory_count": int(sum(value < 0 for value in values)),
                    "minimum_band_mean_normalized_change": min(values),
                    "maximum_band_mean_normalized_change": max(values),
                })
            output.append({
                "climate_scenario": scenario,
                "latitude_band": band,
                "windows": window_rows,
                "all_four_negative_in_every_window": all(row["negative_trajectory_count"] == 4 for row in window_rows),
                "first_window_all_four_negative": next(
                    (
                        {"start_year": row["start_year"], "end_year": row["end_year"]}
                        for row in window_rows
                        if row["negative_trajectory_count"] == 4
                    ),
                    None,
                ),
            })
    return output


def evaluate(plan_path: Path, raw_root: Path) -> dict[str, object]:
    plan = read_complete_plan(plan_path)
    reference: dict[tuple[str, str, str], np.ndarray] = {}
    future: dict[tuple[str, str, str, int, int], np.ndarray] = {}
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
                    reference[(forcing, model, label)] = values
                    support = np.isfinite(values) if support is None else support & np.isfinite(values)
                else:
                    for start, end in FUTURE_WINDOWS:
                        values, lat, lon = period_cell_mean(path, row, start, end)
                        future[(forcing, model, label, start, end)] = values
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
    require(bool(support.any()), "all-window 20-file common support is empty")

    trajectory_rows: list[dict[str, object]] = []
    for start, end in FUTURE_WINDOWS:
        for scenario in SCENARIOS:
            changes: dict[tuple[str, str], np.ndarray] = {}
            for forcing in FORCINGS:
                for model in MODELS:
                    change, _ = normalized_control_adjusted_change(
                        reference[(forcing, model, "forced_historical")],
                        future[(forcing, model, f"{scenario}_future", start, end)],
                        reference[(forcing, model, "control_historical")],
                        future[(forcing, model, "control_future", start, end)],
                        support,
                        latitude,
                    )
                    changes[(forcing, model)] = change
            rows, _ = summarize_band_magnitudes(changes, support, latitude)
            trajectory_rows.extend({
                "climate_scenario": scenario,
                "future_period": {"start_year": start, "end_year": end},
                **row,
            } for row in rows)

    return {
        "schema": "fishmip_control_adjusted_latitude_band_time_windows_v1",
        "status": "validated_temporal_latitude_band_structural_magnitude_sensitivity_only",
        "reference_period": {"start_year": REFERENCE[0], "end_year": REFERENCE[1]},
        "future_periods": [{"start_year": start, "end_year": end} for start, end in FUTURE_WINDOWS],
        "support_rule": "intersection_across_all_20_frozen_files_and_all_registered_decades",
        "trajectory_results": trajectory_rows,
        "temporal_band_summaries": summarize_temporal_bands(trajectory_rows),
        "inputs": receipts,
        "plan": {"path": display_path(plan_path), "sha256": sha256(plan_path)},
        "implementation": {"path": display_path(Path(__file__).resolve()), "sha256": sha256(Path(__file__).resolve())},
        "absolute_model_levels_averaged": False,
        "country_or_eez_allocation_performed": False,
        "forced_response_estimated": False,
        "matched_co2_pulse": False,
        "welfare_estimated": False,
        "damage_estimated": False,
        "scc_authorized": False,
        "disclaimer": "Temporal latitude-band magnitudes are structural FishMIP scenario diagnostics, not probabilities, country allocation, welfare, damages, or SCC evidence.",
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
    print("FishMIP temporal latitude-band magnitude audit passed")


if __name__ == "__main__":
    main()
