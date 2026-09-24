#!/usr/bin/env python3
"""Independently validate the quarantined global-maize market sensitivity.

This script deliberately does not import the builder or market-accounting
implementation.  It reconstructs adaptation, winsorization, aggregation, and
closed-market surplus from the cell exports and the documented equations.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd


ADAPTATION = {
    "fixed": (0.0, 0.0),
    "trend": (0.003, 0.35),
    "upper": (0.007, 0.70),
}


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def exprel(value: float) -> float:
    return math.expm1(value) / value if value else 1.0


def independent_damage(baseline_value: float, supply: float, demand: float, log_shift: float) -> float:
    """Damage from a supply shift, derived directly at the zero-shift baseline."""
    change_log_price = -log_shift / (supply + demand)
    z = (1.0 - demand) * change_log_price
    total_surplus_change = baseline_value * log_shift / (1.0 + supply) * exprel(z)
    return -total_surplus_change


def close(actual: float, expected: float, label: str, *, rtol: float = 2e-11, atol: float = 1e-4) -> None:
    if not math.isclose(actual, expected, rel_tol=rtol, abs_tol=atol):
        raise AssertionError(f"{label}: actual={actual!r}, expected={expected!r}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("fresh output required")

    result = json.loads(args.input.read_text(encoding="utf-8"))
    if result["schema"] != "hultgren_global_maize_market_sensitivity/v1":
        raise AssertionError("unexpected source schema")
    if result["claim_gates"] != {
        "agriculture_replacement": False,
        "damage_or_scc": False,
        "paper_welfare_replication": False,
        "structural_market_sensitivity": True,
    }:
        raise AssertionError("claim gates changed")

    frames: dict[str, pd.DataFrame] = {}
    for source in result["sources"]:
        path = Path(source["path"])
        if digest(path) != source["sha256"]:
            raise AssertionError(f"source hash mismatch: {path}")
        frame = pd.read_parquet(
            path,
            columns=["climate_model", "harvest_year", "analysis_weight", "precipitation_delta_log_yield"],
        )
        if len(frame) != source["rows"] or frame["climate_model"].nunique() != 1:
            raise AssertionError(f"source structure mismatch: {path}")
        model = str(frame["climate_model"].iloc[0])
        if model != source["climate_model"] or model in frames:
            raise AssertionError(f"source model mismatch: {path}")
        frames[model] = frame
    if len(frames) != 5:
        raise AssertionError("five unique models required")

    baseline = float(result["baseline_value"])
    checked_records = 0
    maximum_absolute_error = 0.0
    for scenario, scenario_result in result["scenarios"].items():
        rate, cap = ADAPTATION[scenario]
        adapted: dict[str, np.ndarray] = {}
        for model, frame in frames.items():
            raw = frame["precipitation_delta_log_yield"].to_numpy(dtype=np.float64)
            year = frame["harvest_year"].to_numpy(dtype=np.int32)
            factor = 1.0 - np.minimum(rate * np.maximum(year - 2020, 0), cap)
            adapted[model] = np.where(raw < 0.0, raw * factor, raw)
        lower, upper = np.quantile(np.concatenate(list(adapted.values())), [0.01, 0.99], method="linear")
        close(float(scenario_result["winsorization"]["lower_delta_log_yield"]), float(lower), f"{scenario} lower", atol=1e-13)
        close(float(scenario_result["winsorization"]["upper_delta_log_yield"]), float(upper), f"{scenario} upper", atol=1e-13)

        for case in scenario_result["cases"]:
            model = case["climate_model"]
            frame = frames[model]
            supply = float(case["supply_elasticity"])
            demand = float(case["demand_elasticity_magnitude"])
            exponent = 1.0 if case["yield_to_supply_mapping"] == "horizontal_output" else 1.0 + supply
            annual_damage = []
            for record in case["annual"]:
                year = int(record["harvest_year"])
                mask = frame["harvest_year"].to_numpy(dtype=np.int32) == year
                weights = frame.loc[mask, "analysis_weight"].to_numpy(dtype=np.float64)
                response = np.clip(adapted[model][mask], lower, upper)
                supply_ratio = float(np.dot(weights, np.exp(exponent * response)) / weights.sum())
                log_shift = math.log(supply_ratio)
                damage = independent_damage(baseline, supply, demand, log_shift)
                close(float(record["supply_ratio"]), supply_ratio, f"{scenario}/{model}/{year} supply ratio", atol=1e-13)
                close(float(record["log_supply_shift"]), log_shift, f"{scenario}/{model}/{year} log shift", atol=1e-13)
                close(float(record["damage_change"]), damage, f"{scenario}/{model}/{year} damage")
                close(float(record["total_surplus_change"]), -damage, f"{scenario}/{model}/{year} surplus")
                maximum_absolute_error = max(maximum_absolute_error, abs(float(record["damage_change"]) - damage))
                annual_damage.append(damage)
                checked_records += 1
            mean_damage = float(np.mean(annual_damage))
            close(float(case["mean_annual_damage_change"]), mean_damage, f"{scenario}/{model} mean damage")
            close(float(case["mean_annual_total_surplus_change"]), -mean_damage, f"{scenario}/{model} mean surplus")

    audit = {
        "schema": "hultgren_global_maize_market_sensitivity_validation/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "pass",
        "source": {"path": str(args.input), "sha256": digest(args.input)},
        "validation": {
            "independent_of_builder_and_market_core": True,
            "models_checked": sorted(frames),
            "scenarios_checked": sorted(result["scenarios"]),
            "annual_case_records_checked": checked_records,
            "maximum_absolute_damage_error_usd": maximum_absolute_error,
            "source_hashes_checked": True,
            "claim_gates_checked": True,
        },
        "interpretation": "Numerical validation only; it does not elevate the quarantined structural sensitivity to a causal damage estimate or SCC result.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(audit, indent=2))


if __name__ == "__main__":
    main()
