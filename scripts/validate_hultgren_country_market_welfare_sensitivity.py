#!/usr/bin/env python3
"""Independently validate the separate-country maize-market sensitivity."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

VALUE = "maize_gross_production_value_constant_2014_2016_usd"
ADAPTATION = {"fixed": (0.0, 0.0), "trend": (0.003, 0.35), "upper": (0.007, 0.70)}


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def close(actual: float, expected: float, label: str, *, rtol: float = 2e-11, atol: float = 1e-4) -> None:
    if not math.isclose(actual, expected, rel_tol=rtol, abs_tol=atol):
        raise AssertionError(f"{label}: {actual!r} != {expected!r}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("fresh output required")
    result = json.loads(args.input.read_text(encoding="utf-8"))
    if result["schema"] != "hultgren_country_maize_market_sensitivity/v1":
        raise AssertionError("unexpected schema")
    if result["claim_gates"]["damage_or_scc"] or result["claim_gates"]["agriculture_replacement"]:
        raise AssertionError("claim gate promoted")

    weight_path = Path(result["weights"]["path"])
    if digest(weight_path) != result["weights"]["sha256"]:
        raise AssertionError("weight hash differs")
    weights = pd.read_parquet(weight_path, columns=["iso3", "native_lat_index", "native_lon_index", VALUE])
    frames: dict[str, pd.DataFrame] = {}
    joined: dict[str, pd.DataFrame] = {}
    baselines: dict[str, pd.Series] = {}
    for source in result["sources"]:
        path = Path(source["path"])
        if digest(path) != source["sha256"]:
            raise AssertionError(f"source hash differs: {path}")
        frame = pd.read_parquet(path, columns=["climate_model", "harvest_year", "native_lat_index", "native_lon_index", "precipitation_delta_log_yield"])
        model = str(frame["climate_model"].iloc[0])
        if model != source["climate_model"] or len(frame) != source["rows"]:
            raise AssertionError(f"source identity differs: {path}")
        merged = frame.merge(weights, on=["native_lat_index", "native_lon_index"], how="inner", validate="many_to_many")
        support = merged.drop_duplicates(["iso3", "native_lat_index", "native_lon_index"])
        baseline = support.groupby("iso3", sort=True)[VALUE].sum()
        frames[model], joined[model], baselines[model] = frame, merged, baseline
    if len(frames) != 5:
        raise AssertionError("five models required")

    checked = 0
    maximum_error = 0.0
    for scenario, scenario_result in result["scenarios"].items():
        rate, cap = ADAPTATION[scenario]
        unique_adapted: dict[str, np.ndarray] = {}
        joined_adapted: dict[str, np.ndarray] = {}
        for model, frame in frames.items():
            raw = frame["precipitation_delta_log_yield"].to_numpy(dtype=np.float64)
            year = frame["harvest_year"].to_numpy(dtype=np.int32)
            factor = 1.0 - np.minimum(rate * np.maximum(year - 2020, 0), cap)
            unique_adapted[model] = np.where(raw < 0.0, raw * factor, raw)
            merged = joined[model]
            raw_joined = merged["precipitation_delta_log_yield"].to_numpy(dtype=np.float64)
            joined_year = merged["harvest_year"].to_numpy(dtype=np.int32)
            joined_factor = 1.0 - np.minimum(rate * np.maximum(joined_year - 2020, 0), cap)
            joined_adapted[model] = np.where(raw_joined < 0.0, raw_joined * joined_factor, raw_joined)
        lower, upper = np.quantile(np.concatenate(list(unique_adapted.values())), [0.01, 0.99], method="linear")
        close(float(scenario_result["winsorization"]["lower_delta_log_yield"]), float(lower), f"{scenario} lower", atol=1e-13)
        close(float(scenario_result["winsorization"]["upper_delta_log_yield"]), float(upper), f"{scenario} upper", atol=1e-13)

        for case in scenario_result["cases"]:
            model = case["climate_model"]
            merged = joined[model]
            baseline = baselines[model]
            supply = float(case["supply_elasticity"])
            demand = float(case["demand_elasticity_magnitude"])
            exponent = 1.0 if case["yield_to_supply_mapping"] == "horizontal_output" else 1.0 + supply
            years = merged["harvest_year"].to_numpy(dtype=np.int32)
            damages = []
            for record in case["annual"]:
                year = int(record["harvest_year"])
                mask = years == year
                subset = merged.loc[mask]
                response = np.clip(joined_adapted[model][mask], lower, upper)
                output = pd.Series(
                    subset[VALUE].to_numpy(dtype=np.float64) * np.exp(exponent * response), index=subset.index
                ).groupby(subset["iso3"], sort=True).sum()
                aligned = baseline.loc[output.index]
                ratios = output.to_numpy(dtype=np.float64) / aligned.to_numpy(dtype=np.float64)
                shifts = np.log(ratios)
                change_price = -shifts / (supply + demand)
                z = (1.0 - demand) * change_price
                exprel = np.where(z == 0.0, 1.0, np.expm1(z) / z)
                damage = float((-aligned.to_numpy(dtype=np.float64) * shifts / (1.0 + supply) * exprel).sum())
                close(float(record["minimum_country_supply_ratio"]), float(ratios.min()), f"{scenario}/{model}/{year} minimum", atol=1e-13)
                close(float(record["maximum_country_supply_ratio"]), float(ratios.max()), f"{scenario}/{model}/{year} maximum", atol=1e-13)
                close(float(record["damage_change"]), damage, f"{scenario}/{model}/{year} damage")
                close(float(record["total_surplus_change"]), -damage, f"{scenario}/{model}/{year} surplus")
                maximum_error = max(maximum_error, abs(float(record["damage_change"]) - damage))
                damages.append(damage)
                checked += 1
            close(float(case["mean_annual_damage_change"]), float(np.mean(damages)), f"{scenario}/{model} mean")

    audit = {
        "schema": "hultgren_country_maize_market_sensitivity_validation/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "pass",
        "source": {"path": str(args.input), "sha256": digest(args.input)},
        "validation": {
            "independent_of_builder_and_market_core": True,
            "annual_case_records_checked": checked,
            "maximum_absolute_damage_error_usd": maximum_error,
            "country_count": result["represented_country_count"],
            "source_and_weight_hashes_checked": True,
            "claim_gates_checked": True,
        },
        "interpretation": "Numerical validation only; no causal damage, agriculture-replacement, or SCC gate is opened.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(audit, indent=2))


if __name__ == "__main__":
    main()
