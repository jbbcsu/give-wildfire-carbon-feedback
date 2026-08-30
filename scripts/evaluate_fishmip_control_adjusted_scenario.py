#!/usr/bin/env python3
"""Compare one forced FishMIP scenario with its preindustrial-control pair."""
from __future__ import annotations

import argparse
import hashlib
import json
import tomllib
from pathlib import Path

from evaluate_fishmip_picontrol_drift import validate_picontrol_pair
from evaluate_fishmip_scenario_benchmark import annual_density, common_support, period_mean
from validate_fishmip_content import plan_row, validate_pair


ROLE = "biophysical_control_adjusted_scenario_diagnostic_not_pulse_welfare_or_scc"


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
    require(config.get("role") == ROLE, "control-adjusted diagnostic role changed")
    require(config.get("control_scenario") == "picontrol", "control scenario changed")
    require(config.get("forced_scenario") in {"ssp126", "ssp585"}, "forced scenario is not registered")
    require(
        config.get("support_rule") == "intersection_across_control_and_forced_historical_future_files",
        "support rule changed",
    )
    require(config.get("spatial_summary") == "cosine_latitude_weighted_mean_density", "spatial summary changed")
    require(config.get("temporal_summary") == "mean_of_twelve_monthly_spatial_means", "temporal summary changed")
    stages = config.get("allowed_acquisition_stages")
    require(
        isinstance(stages, list) and set(stages) == {"content_smoke", "deferred_full_matrix"},
        "allowed acquisition stages changed",
    )
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


def evaluate(
    config: dict[str, object],
    config_path: Path,
    plan: Path,
    forced_historical: Path,
    forced_future: Path,
    control_historical: Path,
    control_future: Path,
) -> dict[str, object]:
    allowed = set(map(str, config["allowed_acquisition_stages"]))
    paths = [forced_historical, forced_future, control_historical, control_future]
    rows = [plan_row(plan, path.name, allowed_stages=allowed) for path in paths]
    forced_historical_row, forced_future_row, control_historical_row, control_future_row = rows
    for row in rows:
        require(row["model"] == config["model"], "input model differs from config")
        require(row["climate_forcing"] == config["climate_forcing"], "input forcing differs from config")
    require(forced_future_row["climate_scenario"] == config["forced_scenario"], "forced scenario differs from config")
    require(forced_historical_row["soc_scenario"] == config["historical_soc_scenario"], "forced historical social scenario changed")
    require(forced_future_row["soc_scenario"] == config["future_soc_scenario"], "forced future social scenario changed")
    require(control_historical_row["soc_scenario"] == forced_historical_row["soc_scenario"], "historical social scenarios differ")
    require(control_future_row["soc_scenario"] == forced_future_row["soc_scenario"], "future social scenarios differ")
    for row, prefix in ((forced_historical_row, "historical"), (forced_future_row, "future")):
        require(int(row["start_year"]) == int(config[f"{prefix}_start_year"]), f"{prefix} start year changed")
        require(int(row["end_year"]) == int(config[f"{prefix}_end_year"]), f"{prefix} end year changed")

    forced_pair = validate_pair(forced_historical, forced_historical_row, forced_future, forced_future_row)
    control_config = {**config, "model": config["model"], "climate_forcing": config["climate_forcing"]}
    control_pair = validate_picontrol_pair(
        control_historical, control_historical_row, control_future, control_future_row, control_config
    )
    support, latitude = common_support(paths)
    reference_start = int(config["reference_start_year"])
    reference_end = int(config["reference_end_year"])
    forced_historical_annual = annual_density(
        forced_historical,
        int(forced_historical_row["start_year"]),
        int(forced_historical_row["end_year"]),
        support,
        latitude,
    )
    forced_future_annual = annual_density(
        forced_future, int(forced_future_row["start_year"]), int(forced_future_row["end_year"]), support, latitude
    )
    control_historical_annual = annual_density(
        control_historical,
        int(control_historical_row["start_year"]),
        int(control_historical_row["end_year"]),
        support,
        latitude,
    )
    control_future_annual = annual_density(
        control_future,
        int(control_future_row["start_year"]),
        int(control_future_row["end_year"]),
        support,
        latitude,
    )
    forced_reference = period_mean(forced_historical_annual, reference_start, reference_end)
    control_reference = period_mean(control_historical_annual, reference_start, reference_end)
    require(forced_reference > 0 and control_reference > 0, "reference densities must be positive")
    reporting = []
    for period in config["reporting_periods"]:
        start = int(period["start_year"])
        end = int(period["end_year"])
        forced_change = period_mean(forced_future_annual, start, end) / forced_reference - 1.0
        control_change = period_mean(control_future_annual, start, end) / control_reference - 1.0
        reporting.append({
            "id": str(period["id"]),
            "start_year": start,
            "end_year": end,
            "forced_relative_change": forced_change,
            "control_relative_change": control_change,
            "difference_in_relative_changes": forced_change - control_change,
        })
    return {
        "version": config["version"],
        "role": ROLE,
        "model": config["model"],
        "climate_forcing": config["climate_forcing"],
        "forced_scenario": config["forced_scenario"],
        "control_scenario": "picontrol",
        "historical_soc_scenario": config["historical_soc_scenario"],
        "future_soc_scenario": config["future_soc_scenario"],
        "support_rule": config["support_rule"],
        "common_finite_grid_cells": int(support.sum()),
        "forced_pair_validation": forced_pair["result"],
        "control_pair_validation": control_pair["result"],
        "reference_start_year": reference_start,
        "reference_end_year": reference_end,
        "forced_reference_mean_density_g_m2": forced_reference,
        "control_reference_mean_density_g_m2": control_reference,
        "reporting_periods": reporting,
        "inputs": [
            {"file_name": path.name, "bytes": int(row["bytes"]), "sha512": row["sha512"]}
            for path, row in zip(paths, rows, strict=True)
        ],
        "config_sha256": sha256(config_path),
        "implementation_sha256": sha256(Path(__file__)),
        "inference_limit": "Difference-in-relative-changes on one support intersection is a structural control adjustment, not causal attribution or a marginal pulse response.",
        "absolute_model_levels_averaged": False,
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
    parser.add_argument("--forced-historical", type=Path, required=True)
    parser.add_argument("--forced-future", type=Path, required=True)
    parser.add_argument("--control-historical", type=Path, required=True)
    parser.add_argument("--control-future", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    config_path = args.config.resolve()
    result = evaluate(
        load_config(config_path),
        config_path,
        args.plan,
        args.forced_historical,
        args.forced_future,
        args.control_historical,
        args.control_future,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.out.with_suffix(args.out.suffix + ".partial")
    temporary.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(args.out)
    changes = ", ".join(
        f"{period['id']}={100 * float(period['difference_in_relative_changes']):.2f}pp"
        for period in result["reporting_periods"]
    )
    print(f"FishMIP control-adjusted {result['forced_scenario']} passed on {result['common_finite_grid_cells']} cells: {changes}")


if __name__ == "__main__":
    main()
