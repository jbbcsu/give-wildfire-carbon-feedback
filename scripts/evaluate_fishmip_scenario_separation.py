#!/usr/bin/env python3
"""Audit annual SSP5-8.5 minus SSP1-2.6 FishMIP scenario separation.

The comparison remains within each climate forcing and ecosystem model on the
previously validated common spatial support.  It is a scenario diagnostic,
not a matched carbon pulse, observed-catch calibration, welfare estimate, or
SCC input.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import xarray as xr

from evaluate_fishmip_spatial_change_distribution import (
    FORCINGS,
    MODELS,
    ROOT,
    SCENARIOS,
    display_path,
    matrix_index,
    period_cell_mean,
    raw_path,
    read_plan,
    require,
)


YEARS = tuple(range(2015, 2101))
PERIODS = {
    "near": (2021, 2030),
    "mid": (2041, 2050),
    "late": (2081, 2090),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def weighted_mean(values: np.ndarray, support: np.ndarray, weights: np.ndarray) -> float:
    require(values.shape == support.shape == weights.shape, "weighted-mean arrays differ")
    require(bool(np.isfinite(values[support]).all()), "supported values are nonfinite")
    denominator = float(np.sum(weights[support]))
    require(np.isfinite(denominator) and denominator > 0, "spatial weights are invalid")
    return float(np.sum(values[support] * weights[support]) / denominator)


def annual_density_series(
    path: Path,
    row: dict[str, str],
    support: np.ndarray,
    weights: np.ndarray,
) -> np.ndarray:
    file_start = int(row["start_year"])
    file_end = int(row["end_year"])
    require(file_start <= YEARS[0] and file_end >= YEARS[-1], f"future years lie outside {path.name}")
    result: list[float] = []
    with xr.open_dataset(path, engine="h5netcdf", decode_times=False) as dataset:
        require("tc" in dataset and dataset["tc"].dims == ("time", "lat", "lon"), f"{path.name} schema changed")
        require(dataset["tc"].attrs.get("units") == "g m-2", f"{path.name} units changed")
        for year in YEARS:
            first = (year - file_start) * 12
            values = np.asarray(dataset["tc"].isel(time=slice(first, first + 12)).values, dtype=float)
            require(values.shape[0] == 12, f"{path.name} has an incomplete year {year}")
            result.append(weighted_mean(np.mean(values, axis=0), support, weights))
    array = np.asarray(result, dtype=float)
    require(array.shape == (len(YEARS),) and bool(np.isfinite(array).all()), "annual density series is invalid")
    return array


def persistence_summary(normalized_difference: np.ndarray) -> dict[str, object]:
    values = np.asarray(normalized_difference, dtype=float)
    require(values.shape == (len(YEARS),), "scenario-separation series has the wrong length")
    require(bool(np.isfinite(values).all()), "scenario-separation series is nonfinite")
    lower = values < 0
    longest = 0
    current = 0
    first_ten_year_start: int | None = None
    for index, flag in enumerate(lower):
        current = current + 1 if flag else 0
        longest = max(longest, current)
        if current == 10 and first_ten_year_start is None:
            first_ten_year_start = YEARS[index - 9]
    period_means = {}
    for name, (start, end) in PERIODS.items():
        mask = np.asarray([(start <= year <= end) for year in YEARS])
        require(int(mask.sum()) == 10, f"{name} period is incomplete")
        period_means[name] = float(np.mean(values[mask]))
    return {
        "years": [YEARS[0], YEARS[-1]],
        "year_count": len(YEARS),
        "ssp585_lower_than_ssp126_years": int(lower.sum()),
        "ssp585_higher_than_ssp126_years": int((values > 0).sum()),
        "exactly_equal_years": int((values == 0).sum()),
        "longest_consecutive_ssp585_lower_years": int(longest),
        "first_ten_consecutive_ssp585_lower_start_year": first_ten_year_start,
        "normalized_difference_period_means": period_means,
        "normalized_difference_minimum": float(np.min(values)),
        "normalized_difference_maximum": float(np.max(values)),
    }


def evaluate(plan_path: Path, matrix_path: Path, raw_root: Path) -> dict[str, object]:
    plan = read_plan(plan_path)
    matrix = json.loads(matrix_path.read_text(encoding="utf-8"))
    indexed = matrix_index(matrix)
    results: list[dict[str, object]] = []
    receipts: list[dict[str, object]] = []
    for forcing in FORCINGS:
        paths: dict[tuple[str, str], Path] = {}
        latitude: np.ndarray | None = None
        longitude: np.ndarray | None = None
        support: np.ndarray | None = None
        for model in MODELS:
            for scenario in ("historical", *SCENARIOS):
                row = plan[(forcing, model, scenario)]
                path = raw_path(raw_root, row)
                paths[(model, scenario)] = path
                receipts.append({
                    "climate_forcing": forcing,
                    "ecosystem_model": model,
                    "scenario": scenario,
                    "path": display_path(path),
                    "bytes": path.stat().st_size,
                    "sha512": row["sha512"],
                })
                with xr.open_dataset(path, engine="h5netcdf", decode_times=False) as dataset:
                    current_latitude = np.asarray(dataset["lat"].values, dtype=float)
                    current_longitude = np.asarray(dataset["lon"].values, dtype=float)
                    first = np.asarray(dataset["tc"].isel(time=0).values, dtype=float)
                if latitude is None:
                    latitude, longitude = current_latitude, current_longitude
                else:
                    require(
                        np.array_equal(latitude, current_latitude) and np.array_equal(longitude, current_longitude),
                        "scenario-separation grids differ",
                    )
                current_support = np.isfinite(first)
                support = current_support if support is None else support & current_support
        assert latitude is not None and longitude is not None and support is not None
        expected_support = next(
            int(row["common_finite_grid_cells"])
            for row in matrix["benchmarks"] if row["climate_forcing"] == forcing
        )
        require(int(support.sum()) == expected_support, "common support differs from scenario matrix")
        weights = np.cos(np.deg2rad(latitude))[:, None] * np.ones((1, len(longitude)))

        for model in MODELS:
            reference_grid, _, _ = period_cell_mean(
                paths[(model, "historical")], plan[(forcing, model, "historical")], 2005, 2014
            )
            reference = weighted_mean(reference_grid, support, weights)
            require(reference > 0, "historical reference density is not positive")
            series = {
                scenario: annual_density_series(
                    paths[(model, scenario)], plan[(forcing, model, scenario)], support, weights
                )
                for scenario in SCENARIOS
            }
            normalized = (series["ssp585"] - series["ssp126"]) / reference
            summary = persistence_summary(normalized)
            for period, value in summary["normalized_difference_period_means"].items():
                expected = (
                    float(indexed[(forcing, "ssp585", model)]["relative_change_from_reference"][period])
                    - float(indexed[(forcing, "ssp126", model)]["relative_change_from_reference"][period])
                )
                require(abs(float(value) - expected) <= 1e-10, "scenario separation differs from matrix")
            results.append({
                "climate_forcing": forcing,
                "ecosystem_model": model,
                "common_finite_grid_cells": int(support.sum()),
                "historical_reference_mean_density_g_m2": reference,
                **summary,
            })
    return {
        "schema": "fishmip_scenario_separation_v1",
        "status": "validated_biophysical_scenario_separation_only",
        "comparison": "annual_ssp585_minus_ssp126_divided_by_same_forcing_model_2005_2014_reference",
        "support_rule": "forcing_specific_intersection_across_two_ecosystem_models_and_historical_ssp126_ssp585",
        "implementation": {"path": display_path(Path(__file__).resolve()), "sha256": sha256(Path(__file__).resolve())},
        "plan": {"path": display_path(plan_path), "sha256": sha256(plan_path)},
        "scenario_matrix": {"path": display_path(matrix_path), "sha256": sha256(matrix_path)},
        "results": results,
        "inputs": receipts,
        "absolute_model_levels_averaged": False,
        "observed_catch": False,
        "matched_co2_pulse": False,
        "welfare_estimated": False,
        "damage_estimated": False,
        "scc_authorized": False,
        "disclaimer": (
            "Within-model scenario separation is not observed catch, a matched carbon pulse, welfare, "
            "damage, or SCC evidence; no absolute ecosystem-model levels are averaged."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--matrix", type=Path, required=True)
    parser.add_argument("--raw-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = evaluate(args.plan.resolve(), args.matrix.resolve(), args.raw_root.resolve())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.out.with_suffix(args.out.suffix + ".partial")
    temporary.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(args.out)
    print(f"FishMIP scenario separation passed for {len(result['results'])} forcing/model trajectories")


if __name__ == "__main__":
    main()
