#!/usr/bin/env python3
"""Evaluate one checksum-pinned FishMIP preindustrial-control pair.

The result is a bounded baseline-drift diagnostic.  It is not a forced climate
response, a marginal-CO2 pulse, a welfare estimate, a damage function, or an
SCC input.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import tomllib
from pathlib import Path

import numpy as np
import xarray as xr

from evaluate_fishmip_scenario_benchmark import annual_density, common_support, period_mean
from validate_fishmip_content import expected_time, plan_row, validate


ROLE = "biophysical_picontrol_drift_diagnostic_not_forced_response_pulse_welfare_or_scc"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_config(path: Path) -> dict[str, object]:
    with path.open("rb") as stream:
        config = tomllib.load(stream)
    require(config.get("role") == ROLE, "preindustrial-control diagnostic role changed")
    require(config.get("climate_scenario") == "picontrol", "diagnostic must use picontrol")
    require(config.get("support_rule") == "intersection_of_time_stable_finite_masks", "support rule changed")
    require(config.get("spatial_summary") == "cosine_latitude_weighted_mean_density", "spatial summary changed")
    require(config.get("temporal_summary") == "mean_of_twelve_monthly_spatial_means", "temporal summary changed")
    stages = config.get("allowed_acquisition_stages")
    require(stages == ["deferred_full_matrix"], "control files must remain in the pinned deferred stage")
    periods = config.get("reporting_periods")
    require(isinstance(periods, list) and bool(periods), "reporting periods are missing")
    identifiers: set[str] = set()
    for period in periods:
        require(isinstance(period, dict), "reporting period must be a table")
        identifier = str(period.get("id", ""))
        require(identifier and identifier not in identifiers, "reporting-period IDs must be unique")
        identifiers.add(identifier)
        require(int(period["start_year"]) <= int(period["end_year"]), "reporting period is reversed")
    return config


def validate_picontrol_pair(
    historical_path: Path,
    historical_row: dict[str, str],
    future_path: Path,
    future_row: dict[str, str],
    config: dict[str, object],
) -> dict[str, object]:
    for row, label in ((historical_row, "historical"), (future_row, "future")):
        require(row["climate_scenario"] == "picontrol", f"{label} file is not picontrol")
        require(row["model"] == config["model"], f"{label} model differs from config")
        require(row["climate_forcing"] == config["climate_forcing"], f"{label} forcing differs from config")
    require(historical_row["soc_scenario"] == config["historical_soc_scenario"], "historical social scenario changed")
    require(future_row["soc_scenario"] == config["future_soc_scenario"], "future social scenario changed")
    require(historical_row["version"] == future_row["version"], "control-pair versions differ")
    require(int(future_row["start_year"]) == int(historical_row["end_year"]) + 1, "control-pair years are not contiguous")

    historical_audit = validate(historical_path, historical_row)
    future_audit = validate(future_path, future_row)
    expected_combined, units, calendar = expected_time({**historical_row, "end_year": future_row["end_year"]})
    with xr.open_dataset(historical_path, engine="h5netcdf", decode_times=False) as historical, xr.open_dataset(
        future_path, engine="h5netcdf", decode_times=False
    ) as future:
        combined_time = np.concatenate([historical["time"].values, future["time"].values])
        require(np.array_equal(combined_time, expected_combined), "control-pair chronology is not contiguous")
        require(np.array_equal(historical["lat"].values, future["lat"].values), "control-pair latitude grids differ")
        require(np.array_equal(historical["lon"].values, future["lon"].values), "control-pair longitude grids differ")
        historical_mask = np.isfinite(historical["tc"].isel(time=0).values)
        future_mask = np.isfinite(future["tc"].isel(time=0).values)
        require(np.array_equal(historical_mask, future_mask), "control-pair finite/missing masks differ")
    return {
        "result": "passed",
        "calendar": calendar,
        "time_units": units,
        "finite_grid_cells": historical_audit["always_finite_grid_cells"],
        "missing_grid_cells": historical_audit["always_missing_grid_cells"],
        "historical_content_result": historical_audit["result"],
        "future_content_result": future_audit["result"],
    }


def evaluate(
    config: dict[str, object],
    config_path: Path,
    plan: Path,
    historical_path: Path,
    future_path: Path,
) -> dict[str, object]:
    allowed = set(map(str, config["allowed_acquisition_stages"]))
    historical_row = plan_row(plan, historical_path.name, allowed_stages=allowed)
    future_row = plan_row(plan, future_path.name, allowed_stages=allowed)
    for row, prefix in ((historical_row, "historical"), (future_row, "future")):
        require(int(row["start_year"]) == int(config[f"{prefix}_start_year"]), f"{prefix} start year changed")
        require(int(row["end_year"]) == int(config[f"{prefix}_end_year"]), f"{prefix} end year changed")
    pair = validate_picontrol_pair(historical_path, historical_row, future_path, future_row, config)
    support, latitude = common_support([historical_path, future_path])
    require(int(support.sum()) == int(pair["finite_grid_cells"]), "support count differs from content audit")

    historical_annual = annual_density(
        historical_path, int(historical_row["start_year"]), int(historical_row["end_year"]), support, latitude
    )
    future_annual = annual_density(
        future_path, int(future_row["start_year"]), int(future_row["end_year"]), support, latitude
    )
    reference_start = int(config["reference_start_year"])
    reference_end = int(config["reference_end_year"])
    reference = period_mean(historical_annual, reference_start, reference_end)
    require(reference > 0, "control reference density must be positive")
    reporting = []
    for period in config["reporting_periods"]:
        start = int(period["start_year"])
        end = int(period["end_year"])
        value = period_mean(future_annual, start, end)
        reporting.append({
            "id": str(period["id"]),
            "start_year": start,
            "end_year": end,
            "mean_density_g_m2": value,
            "absolute_change_from_reference_g_m2": value - reference,
            "relative_change_from_reference": value / reference - 1.0,
        })
    return {
        "version": config["version"],
        "role": ROLE,
        "model": config["model"],
        "climate_forcing": config["climate_forcing"],
        "climate_scenario": "picontrol",
        "historical_soc_scenario": config["historical_soc_scenario"],
        "future_soc_scenario": config["future_soc_scenario"],
        "pair_validation": pair,
        "common_finite_grid_cells": int(support.sum()),
        "reference_start_year": reference_start,
        "reference_end_year": reference_end,
        "reference_mean_density_g_m2": reference,
        "reporting_periods": reporting,
        "inputs": [
            {"file_name": historical_path.name, "bytes": int(historical_row["bytes"]), "sha512": historical_row["sha512"]},
            {"file_name": future_path.name, "bytes": int(future_row["bytes"]), "sha512": future_row["sha512"]},
        ],
        "config_sha256": sha256(config_path),
        "implementation_sha256": sha256(Path(__file__)),
        "control_inference_limit": "The climate input is picontrol, but social forcing changes from histsoc to 2015soc-from-histsoc; the result diagnoses this model pair and is not pure autonomous ecological drift.",
        "forced_response_estimated": False,
        "matched_co2_pulse": False,
        "welfare_estimated": False,
        "damage_estimated": False,
        "scc_authorized": False,
        "result": "passed",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--historical", type=Path, required=True)
    parser.add_argument("--future", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    config_path = args.config.resolve()
    result = evaluate(load_config(config_path), config_path, args.plan, args.historical, args.future)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.out.with_suffix(args.out.suffix + ".partial")
    temporary.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(args.out)
    changes = ", ".join(
        f"{period['id']}={100 * float(period['relative_change_from_reference']):.2f}%"
        for period in result["reporting_periods"]
    )
    print(f"FishMIP piControl drift passed on {result['common_finite_grid_cells']} cells: {changes}")


if __name__ == "__main__":
    main()
