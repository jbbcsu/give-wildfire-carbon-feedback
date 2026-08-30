#!/usr/bin/env python3
"""Audit the complete FishMIP control-adjusted diagnostic matrix."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


DRIFT_ROLE = "biophysical_picontrol_drift_diagnostic_not_forced_response_pulse_welfare_or_scc"
ADJUSTED_ROLE = "biophysical_control_adjusted_scenario_diagnostic_not_pulse_welfare_or_scc"
OUTPUT_ROLE = "cross_model_control_adjusted_structural_sensitivity_not_pulse_welfare_damage_or_scc"
MODELS = {"boats", "ecoocean"}
FORCINGS = {"gfdl-esm4", "ipsl-cm6a-lr"}
SCENARIOS = {"ssp126", "ssp585"}
PERIODS = {"near", "mid", "late"}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def periods_by_id(receipt: dict[str, object]) -> dict[str, dict[str, object]]:
    periods = receipt.get("reporting_periods")
    require(isinstance(periods, list), "reporting periods are missing")
    indexed = {str(period["id"]): period for period in periods}
    require(set(indexed) == PERIODS and len(indexed) == len(periods), "reporting periods are incomplete or duplicated")
    return indexed


def audit(drift_paths: list[Path], adjusted_paths: list[Path]) -> dict[str, object]:
    require(len(drift_paths) == 4, "exactly four drift receipts are required")
    require(len(adjusted_paths) == 8, "exactly eight adjusted receipts are required")
    drift: dict[tuple[str, str], tuple[dict[str, object], Path]] = {}
    for path in drift_paths:
        receipt = load(path)
        require(receipt.get("result") == "passed" and receipt.get("role") == DRIFT_ROLE, "invalid drift receipt")
        key = (str(receipt["climate_forcing"]), str(receipt["model"]))
        require(key not in drift, "duplicate drift matrix cell")
        periods_by_id(receipt)
        drift[key] = (receipt, path)
    require(set(drift) == {(forcing, model) for forcing in FORCINGS for model in MODELS}, "drift matrix is incomplete")

    adjusted: dict[tuple[str, str, str], tuple[dict[str, object], Path]] = {}
    for path in adjusted_paths:
        receipt = load(path)
        require(receipt.get("result") == "passed" and receipt.get("role") == ADJUSTED_ROLE, "invalid adjusted receipt")
        key = (str(receipt["climate_forcing"]), str(receipt["model"]), str(receipt["forced_scenario"]))
        require(key not in adjusted, "duplicate adjusted matrix cell")
        adjusted[key] = (receipt, path)
    expected = {(forcing, model, scenario) for forcing in FORCINGS for model in MODELS for scenario in SCENARIOS}
    require(set(adjusted) == expected, "adjusted matrix is incomplete")

    cells = []
    grouped = {(scenario, period): [] for scenario in sorted(SCENARIOS) for period in sorted(PERIODS)}
    for key in sorted(adjusted):
        forcing, model, scenario = key
        receipt, path = adjusted[key]
        control, _ = drift[(forcing, model)]
        require(receipt["common_finite_grid_cells"] == control["common_finite_grid_cells"], "support differs from drift receipt")
        require(receipt["reference_start_year"] == control["reference_start_year"], "reference start differs")
        require(receipt["reference_end_year"] == control["reference_end_year"], "reference end differs")
        adjusted_periods = periods_by_id(receipt)
        control_periods = periods_by_id(control)
        changes = {}
        for period in sorted(PERIODS):
            adjusted_period = adjusted_periods[period]
            control_period = control_periods[period]
            require(adjusted_period["start_year"] == control_period["start_year"], "period start differs")
            require(adjusted_period["end_year"] == control_period["end_year"], "period end differs")
            require(adjusted_period["control_relative_change"] == control_period["relative_change_from_reference"], "control change differs")
            change = float(adjusted_period["difference_in_relative_changes"])
            changes[period] = change
            grouped[(scenario, period)].append(change)
        cells.append({
            "climate_forcing": forcing,
            "model": model,
            "scenario": scenario,
            "common_finite_grid_cells": int(receipt["common_finite_grid_cells"]),
            "difference_in_relative_changes": changes,
            "receipt": path.name,
        })

    sign_summary = []
    for (scenario, period), values in sorted(grouped.items()):
        negative = sum(value < 0 for value in values)
        positive = sum(value > 0 for value in values)
        zero = len(values) - negative - positive
        sign_summary.append({
            "scenario": scenario,
            "period": period,
            "cell_count": len(values),
            "negative_count": negative,
            "positive_count": positive,
            "zero_count": zero,
            "all_negative": negative == len(values),
            "minimum_difference_in_relative_changes": min(values),
            "maximum_difference_in_relative_changes": max(values),
        })

    inputs = []
    for kind, paths in (("drift", drift_paths), ("adjusted", adjusted_paths)):
        for path in sorted(paths):
            inputs.append({"kind": kind, "file_name": path.name, "sha256": sha256(path)})
    return {
        "version": "fishmip_control_adjusted_matrix_audit_v1",
        "role": OUTPUT_ROLE,
        "matrix_dimensions": {"climate_forcings": sorted(FORCINGS), "models": sorted(MODELS), "scenarios": sorted(SCENARIOS)},
        "matrix_cell_count": len(cells),
        "cells": cells,
        "sign_summary": sign_summary,
        "inputs": inputs,
        "inference_limit": "Cross-cell sign counts describe structural sensitivity only; the receipts do not identify a forced response or marginal pulse.",
        "forced_response_estimated": False,
        "matched_co2_pulse": False,
        "welfare_estimated": False,
        "damage_estimated": False,
        "scc_authorized": False,
        "result": "passed",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--drift", type=Path, action="append", required=True)
    parser.add_argument("--adjusted", type=Path, action="append", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.drift, args.adjusted)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.out.with_suffix(args.out.suffix + ".partial")
    temporary.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(args.out)
    universal = [f"{row['scenario']}/{row['period']}" for row in result["sign_summary"] if row["all_negative"]]
    print(f"FishMIP control-adjusted matrix passed: {result['matrix_cell_count']} cells; all-negative={','.join(universal) or 'none'}")


if __name__ == "__main__":
    main()
