#!/usr/bin/env python3
"""Audit spatial breadth of validated FishMIP late-century scenario changes.

The output contains aggregate grid-cell sign shares and normalized change
quantiles only.  It does not export cell values, average incompatible model
levels, construct a marginal CO2 pulse, translate catch to welfare, or
authorize a GIVE/SCC input.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from urllib.parse import urlparse

import numpy as np
import xarray as xr


FORCINGS = ("gfdl-esm4", "ipsl-cm6a-lr")
MODELS = ("boats", "ecoocean")
SCENARIOS = ("ssp126", "ssp585")
REFERENCE = (2005, 2014)
FUTURE = (2081, 2090)
ROOT = Path(__file__).resolve().parents[1]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha512(path: Path) -> str:
    digest = hashlib.sha512()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def read_plan(path: Path) -> dict[tuple[str, str, str], dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    selected: dict[tuple[str, str, str], dict[str, str]] = {}
    for row in rows:
        key = (row["climate_forcing"], row["model"], row["climate_scenario"])
        if key[0] not in FORCINGS or key[1] not in MODELS or key[2] not in {"historical", *SCENARIOS}:
            continue
        if key in selected:
            raise ValueError(f"acquisition plan duplicates {key}")
        selected[key] = row
    expected = {
        (forcing, model, scenario)
        for forcing in FORCINGS for model in MODELS for scenario in ("historical", *SCENARIOS)
    }
    require(set(selected) == expected, "acquisition plan lacks the exact spatial-audit matrix")
    return selected


def raw_path(root: Path, row: dict[str, str]) -> Path:
    name = Path(urlparse(row["file_url"]).path).name
    path = root / row["climate_forcing"] / row["model"] / name
    require(path.is_file(), f"raw FishMIP file is missing: {path}")
    require(path.stat().st_size == int(row["bytes"]), f"raw FishMIP size differs: {path}")
    require(sha512(path) == row["sha512"], f"raw FishMIP SHA-512 differs: {path}")
    return path


def period_cell_mean(path: Path, row: dict[str, str], start: int, end: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    file_start = int(row["start_year"])
    file_end = int(row["end_year"])
    require(file_start <= start <= end <= file_end, f"period {start}-{end} lies outside {path.name}")
    first = (start - file_start) * 12
    stop = (end - file_start + 1) * 12
    with xr.open_dataset(path, engine="h5netcdf", decode_times=False) as dataset:
        require("tc" in dataset and dataset["tc"].dims == ("time", "lat", "lon"), f"{path.name} schema changed")
        require(dataset["tc"].attrs.get("units") == "g m-2", f"{path.name} units changed")
        require(dataset.sizes["time"] == (file_end - file_start + 1) * 12, f"{path.name} time size changed")
        values = np.asarray(dataset["tc"].isel(time=slice(first, stop)).values, dtype=float)
        latitude = np.asarray(dataset["lat"].values, dtype=float)
        longitude = np.asarray(dataset["lon"].values, dtype=float)
    require(values.shape[0] == (end - start + 1) * 12, f"{path.name} period is incomplete")
    return np.mean(values, axis=0), latitude, longitude


def summarize_distribution(
    reference: np.ndarray,
    future: np.ndarray,
    support: np.ndarray,
    latitude: np.ndarray,
) -> dict[str, object]:
    require(reference.shape == future.shape == support.shape, "spatial arrays have different shapes")
    require(reference.shape[0] == len(latitude), "latitude length differs from spatial arrays")
    require(bool(support.any()), "common support is empty")
    require(bool(np.isfinite(reference[support]).all()), "reference is nonfinite on common support")
    require(bool(np.isfinite(future[support]).all()), "future is nonfinite on common support")
    require(bool((reference[support] >= 0).all() and (future[support] >= 0).all()), "catch density is negative")
    weights = np.cos(np.deg2rad(latitude))[:, None] * np.ones((1, support.shape[1]))
    weights = np.where(support, weights, 0.0)
    denominator = float(np.sum(weights))
    require(np.isfinite(denominator) and denominator > 0, "spatial weights are invalid")
    reference_global = float(np.sum(np.where(support, reference, 0.0) * weights) / denominator)
    future_global = float(np.sum(np.where(support, future, 0.0) * weights) / denominator)
    require(reference_global > 0 and np.isfinite(future_global), "global period means are invalid")
    delta = future[support] - reference[support]
    normalized = delta / reference_global
    supported_weights = weights[support]
    lower = delta < 0
    higher = delta > 0
    unchanged = delta == 0
    require(bool((lower | higher | unchanged).all()), "change signs are incomplete")
    quantiles = np.quantile(normalized, [0.05, 0.25, 0.5, 0.75, 0.95])
    return {
        "common_finite_grid_cells": int(support.sum()),
        "reference_area_weighted_mean_density_g_m2": reference_global,
        "future_area_weighted_mean_density_g_m2": future_global,
        "area_weighted_relative_change": future_global / reference_global - 1.0,
        "unweighted_cell_share_lower": float(np.mean(lower)),
        "unweighted_cell_share_higher": float(np.mean(higher)),
        "unweighted_cell_share_exactly_unchanged": float(np.mean(unchanged)),
        "area_weighted_cell_share_lower": float(np.sum(supported_weights[lower]) / np.sum(supported_weights)),
        "area_weighted_cell_share_higher": float(np.sum(supported_weights[higher]) / np.sum(supported_weights)),
        "area_weighted_cell_share_exactly_unchanged": float(np.sum(supported_weights[unchanged]) / np.sum(supported_weights)),
        "cell_change_divided_by_model_reference_mean_quantiles": {
            key: float(value) for key, value in zip(("p05", "p25", "p50", "p75", "p95"), quantiles)
        },
    }


def matrix_index(matrix: dict[str, object]) -> dict[tuple[str, str, str], dict[str, object]]:
    require(matrix.get("schema") == "fishmip_scenario_benchmark_matrix_v1", "scenario matrix schema changed")
    require(matrix.get("matched_co2_pulse") is False, "scenario matrix claims a matched pulse")
    require(matrix.get("welfare_estimated") is False and matrix.get("scc_authorized") is False, "scenario matrix opens welfare/SCC use")
    result: dict[tuple[str, str, str], dict[str, object]] = {}
    for benchmark in matrix["benchmarks"]:
        for model in benchmark["models"]:
            key = (benchmark["climate_forcing"], benchmark["climate_scenario"], model["model"])
            require(key not in result, "scenario matrix duplicates a forcing/scenario/model row")
            result[key] = model
    expected = {(forcing, scenario, model) for forcing in FORCINGS for scenario in SCENARIOS for model in MODELS}
    require(set(result) == expected, "scenario matrix factorial is incomplete")
    return result


def evaluate(plan_path: Path, matrix_path: Path, raw_root: Path) -> dict[str, object]:
    plan = read_plan(plan_path)
    matrix = json.loads(matrix_path.read_text(encoding="utf-8"))
    indexed = matrix_index(matrix)
    results: list[dict[str, object]] = []
    input_receipts: list[dict[str, object]] = []
    for forcing in FORCINGS:
        paths: dict[tuple[str, str], Path] = {}
        for model in MODELS:
            for scenario in ("historical", *SCENARIOS):
                row = plan[(forcing, model, scenario)]
                path = raw_path(raw_root, row)
                paths[(model, scenario)] = path
                input_receipts.append({
                    "climate_forcing": forcing,
                    "model": model,
                    "scenario": scenario,
                    "path": display_path(path),
                    "bytes": path.stat().st_size,
                    "sha512": row["sha512"],
                })

        arrays: dict[tuple[str, str], np.ndarray] = {}
        latitude: np.ndarray | None = None
        longitude: np.ndarray | None = None
        support: np.ndarray | None = None
        for model in MODELS:
            historical_row = plan[(forcing, model, "historical")]
            reference, lat, lon = period_cell_mean(
                paths[(model, "historical")], historical_row, REFERENCE[0], REFERENCE[1]
            )
            arrays[(model, "historical")] = reference
            for scenario in SCENARIOS:
                future, future_lat, future_lon = period_cell_mean(
                    paths[(model, scenario)], plan[(forcing, model, scenario)], FUTURE[0], FUTURE[1]
                )
                require(np.array_equal(lat, future_lat) and np.array_equal(lon, future_lon), "historical/future grid changed")
                arrays[(model, scenario)] = future
            if latitude is None:
                latitude, longitude = lat, lon
            else:
                require(np.array_equal(latitude, lat) and np.array_equal(longitude, lon), "ecosystem-model grids differ")
        assert latitude is not None and longitude is not None
        for values in arrays.values():
            current = np.isfinite(values)
            support = current if support is None else support & current
        assert support is not None
        expected_support = next(
            int(row["common_finite_grid_cells"])
            for row in matrix["benchmarks"] if row["climate_forcing"] == forcing
        )
        require(int(support.sum()) == expected_support, "common support differs from validated scenario matrix")

        for model in MODELS:
            for scenario in SCENARIOS:
                summary = summarize_distribution(
                    arrays[(model, "historical")], arrays[(model, scenario)], support, latitude
                )
                benchmark = indexed[(forcing, scenario, model)]
                require(
                    abs(summary["reference_area_weighted_mean_density_g_m2"] - float(benchmark["reference_mean_density_g_m2"])) <= 1e-12,
                    "spatial audit reference mean differs from scenario matrix",
                )
                require(
                    abs(summary["area_weighted_relative_change"] - float(benchmark["relative_change_from_reference"]["late"])) <= 1e-10,
                    "spatial audit late-century change differs from scenario matrix",
                )
                results.append({
                    "climate_forcing": forcing,
                    "climate_scenario": scenario,
                    "ecosystem_model": model,
                    **summary,
                })
    lower_counts = sum(float(row["area_weighted_cell_share_lower"]) > 0.5 for row in results)
    return {
        "schema": "fishmip_spatial_change_distribution_v1",
        "status": "validated_biophysical_spatial_scenario_diagnostic_only",
        "implementation": {
            "path": display_path(Path(__file__).resolve()),
            "sha256": sha256(Path(__file__).resolve()),
        },
        "reference_period": {"start_year": REFERENCE[0], "end_year": REFERENCE[1]},
        "future_period": {"start_year": FUTURE[0], "end_year": FUTURE[1]},
        "support_rule": "forcing_specific_intersection_across_two_ecosystem_models_and_all_three_experiments",
        "normalization_rule": "cell_change_divided_by_same_model_forcing_common_support_reference_mean",
        "results": results,
        "area_weighted_majority_lower_count_out_of_8": lower_counts,
        "inputs": input_receipts,
        "plan": {"path": display_path(plan_path), "sha256": sha256(plan_path)},
        "scenario_matrix": {"path": display_path(matrix_path), "sha256": sha256(matrix_path)},
        "absolute_model_levels_averaged": False,
        "observed_catch": False,
        "matched_co2_pulse": False,
        "welfare_estimated": False,
        "damage_estimated": False,
        "scc_authorized": False,
        "disclaimer": (
            "Grid-cell scenario density changes are not observed catch, welfare, marginal CO2-pulse "
            "damages, or SCC evidence; scenario and ecosystem-model trajectories remain separate."
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
    print(
        "FishMIP spatial-change distribution passed: "
        f"{len(result['results'])} trajectories, "
        f"area-weighted majority lower in {result['area_weighted_majority_lower_count_out_of_8']}/8"
    )


if __name__ == "__main__":
    main()
