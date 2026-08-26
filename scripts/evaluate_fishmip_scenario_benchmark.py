#!/usr/bin/env python3
"""Compute a support-matched FishMIP scenario-density benchmark.

This diagnostic is deliberately limited to the validated scenario files. It
does not construct a marginal CO2 pulse, translate catch density to welfare,
or calculate an SCC.
"""
from __future__ import annotations

import argparse
import json
import tomllib
from pathlib import Path

import numpy as np
import xarray as xr

from validate_fishmip_content import plan_row, validate_pair


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def load_config(path: Path) -> dict[str, object]:
    with path.open("rb") as stream:
        config = tomllib.load(stream)
    require(config.get("role") == "biophysical_scenario_benchmark_not_pulse_welfare_or_scc", "benchmark role changed")
    require(config.get("support_rule") == "intersection_of_time_stable_finite_masks", "support rule changed")
    require(config.get("spatial_summary") == "cosine_latitude_weighted_mean_density", "spatial summary changed")
    require(config.get("temporal_summary") == "mean_of_twelve_monthly_spatial_means", "temporal summary changed")
    models = config.get("models")
    require(isinstance(models, list) and len(models) >= 2 and len(models) == len(set(models)), "models must be distinct")
    stages = config.get("allowed_acquisition_stages", ["content_smoke"])
    require(
        isinstance(stages, list)
        and set(stages).issubset({"content_smoke", "deferred_full_matrix"})
        and bool(stages),
        "allowed acquisition stages are invalid",
    )
    periods = config.get("reporting_periods")
    require(isinstance(periods, list) and periods, "at least one reporting period is required")
    seen: set[str] = set()
    for period in periods:
        require(isinstance(period, dict), "reporting period must be a table")
        identifier = str(period.get("id", ""))
        require(identifier and identifier not in seen, "reporting-period ids must be nonblank and unique")
        seen.add(identifier)
        require(int(period["start_year"]) <= int(period["end_year"]), "reporting period is reversed")
    return config


def parse_model_paths(values: list[str], name: str) -> dict[str, Path]:
    result: dict[str, Path] = {}
    for value in values:
        model, separator, path = value.partition("=")
        require(bool(separator) and bool(model) and bool(path), f"{name} entries must be MODEL=PATH")
        require(model not in result, f"duplicate {name} model {model}")
        result[model] = Path(path)
    return result


def common_support(paths: list[Path]) -> tuple[np.ndarray, np.ndarray]:
    support: np.ndarray | None = None
    latitude: np.ndarray | None = None
    for path in paths:
        with xr.open_dataset(path, engine="h5netcdf", decode_times=False) as dataset:
            current_latitude = np.asarray(dataset["lat"].values, dtype=float)
            current = np.isfinite(dataset["tc"].isel(time=0).values)
            if support is None:
                support = current
                latitude = current_latitude
            else:
                require(np.array_equal(current_latitude, latitude), "model latitude grids differ")
                require(current.shape == support.shape, "model grid shapes differ")
                support &= current
    assert support is not None and latitude is not None
    require(bool(support.any()), "common model support is empty")
    return support, latitude


def annual_density(path: Path, start_year: int, end_year: int, support: np.ndarray, latitude: np.ndarray) -> list[dict[str, float | int]]:
    weights = np.cos(np.deg2rad(latitude))[:, None] * np.ones((1, support.shape[1]), dtype=float)
    weights = np.where(support, weights, 0.0)
    denominator = float(weights.sum())
    require(np.isfinite(denominator) and denominator > 0, "common-support weights are invalid")
    records: list[dict[str, float | int]] = []
    with xr.open_dataset(path, engine="h5netcdf", decode_times=False) as dataset:
        require(dataset.sizes["time"] == (end_year - start_year + 1) * 12, "file does not contain twelve months per declared year")
        tc = dataset["tc"]
        for index, year in enumerate(range(start_year, end_year + 1)):
            values = np.asarray(tc.isel(time=slice(index * 12, (index + 1) * 12)).values, dtype=float)
            require(values.shape[0] == 12, "year does not contain twelve monthly values")
            require(bool(np.isfinite(values[:, support]).all()), "common-support cell became missing")
            require(bool((values[:, support] >= 0).all()), "common-support catch density is negative")
            supported = np.where(support[None, :, :], values, 0.0)
            monthly = (supported * weights[None, :, :]).sum(axis=(1, 2)) / denominator
            records.append({"year": year, "annual_mean_density_g_m2": float(monthly.mean())})
    return records


def period_mean(records: list[dict[str, float | int]], start: int, end: int) -> float:
    values = [float(row["annual_mean_density_g_m2"]) for row in records if start <= int(row["year"]) <= end]
    require(len(values) == end - start + 1, f"period {start}-{end} is incomplete")
    result = float(np.mean(values))
    require(np.isfinite(result), f"period {start}-{end} is nonfinite")
    return result


def evaluate(
    config: dict[str, object],
    plan: Path,
    historical: dict[str, Path],
    future: dict[str, Path],
) -> dict[str, object]:
    models = [str(model) for model in config["models"]]
    require(set(historical) == set(models), "historical model set differs from config")
    require(set(future) == set(models), "future model set differs from config")
    all_paths = [historical[model] for model in models] + [future[model] for model in models]
    support, latitude = common_support(all_paths)
    ref_start = int(config["reference_start_year"])
    ref_end = int(config["reference_end_year"])
    output_models: list[dict[str, object]] = []
    allowed_stages = set(map(str, config.get("allowed_acquisition_stages", ["content_smoke"])))
    for model in models:
        historical_row = plan_row(plan, historical[model].name, allowed_stages=allowed_stages)
        future_row = plan_row(plan, future[model].name, allowed_stages=allowed_stages)
        require(historical_row["model"] == model and future_row["model"] == model, "plan/model assignment changed")
        require(historical_row["climate_forcing"] == config["climate_forcing"], "historical forcing differs from config")
        require(future_row["climate_forcing"] == config["climate_forcing"], "future forcing differs from config")
        require(future_row["climate_scenario"] == config["climate_scenario"], "future scenario differs from config")
        require(int(historical_row["start_year"]) == int(config["historical_start_year"]), "historical start year changed")
        require(int(historical_row["end_year"]) == int(config["historical_end_year"]), "historical end year changed")
        require(int(future_row["start_year"]) == int(config["future_start_year"]), "future start year changed")
        require(int(future_row["end_year"]) == int(config["future_end_year"]), "future end year changed")
        pair = validate_pair(historical[model], historical_row, future[model], future_row)
        historical_annual = annual_density(
            historical[model], int(historical_row["start_year"]), int(historical_row["end_year"]), support, latitude
        )
        future_annual = annual_density(
            future[model], int(future_row["start_year"]), int(future_row["end_year"]), support, latitude
        )
        reference = period_mean(historical_annual, ref_start, ref_end)
        require(reference > 0, "reference-period density must be positive for relative change")
        reporting = []
        for period in config["reporting_periods"]:
            start = int(period["start_year"])
            end = int(period["end_year"])
            value = period_mean(future_annual, start, end)
            reporting.append(
                {
                    "id": str(period["id"]),
                    "start_year": start,
                    "end_year": end,
                    "mean_density_g_m2": value,
                    "absolute_change_from_reference_g_m2": value - reference,
                    "relative_change_from_reference": value / reference - 1.0,
                }
            )
        output_models.append(
            {
                "model": model,
                "historical_file": historical[model].name,
                "future_file": future[model].name,
                "pair_validation": pair["result"],
                "reference_start_year": ref_start,
                "reference_end_year": ref_end,
                "reference_mean_density_g_m2": reference,
                "reporting_periods": reporting,
                "annual": historical_annual + future_annual,
            }
        )
    return {
        "version": config["version"],
        "role": config["role"],
        "climate_forcing": config["climate_forcing"],
        "climate_scenario": config["climate_scenario"],
        "support_rule": config["support_rule"],
        "common_finite_grid_cells": int(support.sum()),
        "spatial_summary": config["spatial_summary"],
        "temporal_summary": config["temporal_summary"],
        "models": output_models,
        "matched_co2_pulse": False,
        "welfare_output": False,
        "scc_authorized": False,
        "result": "passed",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--historical", action="append", required=True, metavar="MODEL=PATH")
    parser.add_argument("--future", action="append", required=True, metavar="MODEL=PATH")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = evaluate(
        load_config(args.config),
        args.plan,
        parse_model_paths(args.historical, "historical"),
        parse_model_paths(args.future, "future"),
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"FishMIP scenario benchmark passed on {result['common_finite_grid_cells']} common cells")


if __name__ == "__main__":
    main()
