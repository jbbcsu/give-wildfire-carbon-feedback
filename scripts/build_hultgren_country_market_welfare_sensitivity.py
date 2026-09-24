#!/usr/bin/env python3
"""Build a quarantined separate-country maize-market sensitivity.

This improves on the one-global-market benchmark by clearing each represented
country separately. It remains fully anticipated and omits the published
expectations/storage layer, trade, other crops, and a marginal emissions pulse.
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

ROOT = Path(__file__).resolve().parents[1]
VALUE_COLUMN = "maize_gross_production_value_constant_2014_2016_usd"
ADAPTATION = {
    "fixed": {"annual_attenuation_rate": 0.0, "cap": 0.0},
    "trend": {"annual_attenuation_rate": 0.003, "cap": 0.35},
    "upper": {"annual_attenuation_rate": 0.007, "cap": 0.70},
}
ELASTICITIES = [
    ("hultgren_008_002", 0.08, 0.02, False),
    ("hultgren_010_004", 0.10, 0.04, True),
    ("hultgren_050_006", 0.50, 0.06, False),
]
MAPPINGS = ("horizontal_output", "fixed_input_cost")


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def adaptation_factor(year: np.ndarray, scenario: str) -> np.ndarray:
    spec = ADAPTATION[scenario]
    return 1.0 - np.minimum(spec["annual_attenuation_rate"] * np.maximum(year - 2020, 0), spec["cap"])


def damage_from_log_shift(value: np.ndarray, supply: float, demand: float, log_shift: np.ndarray) -> np.ndarray:
    change_log_price = -log_shift / (supply + demand)
    z = (1.0 - demand) * change_log_price
    exprel = np.ones_like(z)
    nonzero = z != 0.0
    exprel[nonzero] = np.expm1(z[nonzero]) / z[nonzero]
    return -value * log_shift / (1.0 + supply) * exprel


def country_year_damage(
    frame: pd.DataFrame, baseline: pd.Series, response: np.ndarray,
    lower: float, upper: float, exponent: float, supply: float, demand: float,
    value_column: str = VALUE_COLUMN,
) -> tuple[float, float, float]:
    capped = np.clip(response, lower, upper)
    weighted_output = frame[value_column].to_numpy(dtype=np.float64) * np.exp(exponent * capped)
    output = pd.Series(weighted_output, index=frame.index).groupby(frame["iso3"], sort=True).sum()
    aligned = baseline.loc[output.index]
    ratios = output.to_numpy(dtype=np.float64) / aligned.to_numpy(dtype=np.float64)
    require(np.isfinite(ratios).all() and (ratios > 0.0).all(), "invalid country supply ratio")
    shifts = np.log(ratios)
    damages = damage_from_log_shift(aligned.to_numpy(dtype=np.float64), supply, demand, shifts)
    return float(damages.sum()), float(np.min(ratios)), float(np.max(ratios))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", action="append", type=Path, required=True)
    parser.add_argument("--weights", type=Path, required=True)
    parser.add_argument("--weights-receipt", type=Path, required=True)
    parser.add_argument("--value-column", default=VALUE_COLUMN)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), "fresh output required")

    receipt = json.loads(args.weights_receipt.read_text(encoding="utf-8"))
    require(receipt["schema"] in {
        "hultgren_country_cell_maize_value_weights/v1",
        "hultgren_country_cell_maize_value_weights_current_rebased/v1",
        "hultgren_country_cell_maize_value_weights_common_price/v1",
    }, "weight schema differs")
    require(receipt["output"]["sha256"] == digest(args.weights), "weight hash differs")
    weights = pd.read_parquet(args.weights)
    required_weights = {"iso3", "native_lat_index", "native_lon_index", args.value_column}
    require(required_weights <= set(weights.columns), "weight columns differ")
    require(not weights.duplicated(["iso3", "native_lat_index", "native_lon_index"]).any(), "duplicate country-cell weights")
    require(weights[args.value_column].gt(0.0).all(), "nonpositive weights")

    frames: dict[str, pd.DataFrame] = {}
    sources = []
    for path in args.input:
        frame = pd.read_parquet(path)
        require(frame["climate_model"].nunique() == 1 and frame["harvest_year"].nunique() == 9, f"input support differs: {path}")
        require(not frame.duplicated(["harvest_year", "native_lat_index", "native_lon_index"]).any(), f"duplicate cell-year: {path}")
        model = str(frame["climate_model"].iloc[0])
        require(model not in frames, f"duplicate model: {model}")
        frames[model] = frame
        sources.append({"path": str(path), "sha256": digest(path), "rows": len(frame), "climate_model": model})
    require(len(frames) == 5, "five climate models required")

    joined: dict[str, pd.DataFrame] = {}
    baselines: dict[str, pd.Series] = {}
    for model, frame in frames.items():
        merged = frame.drop(columns=["analysis_weight"]).merge(
            weights, on=["native_lat_index", "native_lon_index"], how="inner", validate="many_to_many"
        )
        require(merged["harvest_year"].nunique() == 9 and not merged.empty, f"empty joined support: {model}")
        counts = merged.groupby(["iso3", "native_lat_index", "native_lon_index"])["harvest_year"].nunique()
        require(counts.eq(9).all(), f"unbalanced country-cell years: {model}")
        support = merged.drop_duplicates(["iso3", "native_lat_index", "native_lon_index"])
        baseline = support.groupby("iso3", sort=True)[args.value_column].sum()
        require((baseline > 0.0).all(), f"invalid country baseline: {model}")
        joined[model] = merged
        baselines[model] = baseline
    reference = next(iter(baselines.values()))
    for model, baseline in baselines.items():
        require(baseline.index.equals(reference.index), f"country support differs: {model}")
        require(np.allclose(baseline.to_numpy(), reference.to_numpy(), rtol=1e-12, atol=1e-4), f"country values differ: {model}")

    scenarios = {}
    for scenario in ADAPTATION:
        unique_adapted: dict[str, np.ndarray] = {}
        joined_adapted: dict[str, np.ndarray] = {}
        for model, frame in frames.items():
            raw = frame["precipitation_delta_log_yield"].to_numpy(dtype=np.float64)
            factor = adaptation_factor(frame["harvest_year"].to_numpy(dtype=np.int32), scenario)
            unique_adapted[model] = np.where(raw < 0.0, raw * factor, raw)
            merged = joined[model]
            raw_joined = merged["precipitation_delta_log_yield"].to_numpy(dtype=np.float64)
            factor_joined = adaptation_factor(merged["harvest_year"].to_numpy(dtype=np.int32), scenario)
            joined_adapted[model] = np.where(raw_joined < 0.0, raw_joined * factor_joined, raw_joined)
        lower, upper = np.quantile(np.concatenate(list(unique_adapted.values())), [0.01, 0.99], method="linear")
        cases = []
        for elasticity_id, supply, demand, central in ELASTICITIES:
            for mapping in MAPPINGS:
                exponent = 1.0 if mapping == "horizontal_output" else 1.0 + supply
                for model, merged in joined.items():
                    annual = []
                    years = merged["harvest_year"].to_numpy(dtype=np.int32)
                    for year in sorted(merged["harvest_year"].unique()):
                        mask = years == year
                        damage, minimum_ratio, maximum_ratio = country_year_damage(
                            merged.loc[mask], baselines[model], joined_adapted[model][mask],
                            float(lower), float(upper), exponent, supply, demand, args.value_column,
                        )
                        annual.append({
                            "harvest_year": int(year), "damage_change": damage,
                            "total_surplus_change": -damage,
                            "minimum_country_supply_ratio": minimum_ratio,
                            "maximum_country_supply_ratio": maximum_ratio,
                        })
                    cases.append({
                        "climate_model": model, "elasticity_id": elasticity_id,
                        "supply_elasticity": supply, "demand_elasticity_magnitude": demand,
                        "central_elasticity": central, "yield_to_supply_mapping": mapping,
                        "represented_country_count": len(baselines[model]),
                        "represented_baseline_value": float(baselines[model].sum()),
                        "mean_annual_damage_change": float(np.mean([row["damage_change"] for row in annual])),
                        "mean_annual_total_surplus_change": float(np.mean([row["total_surplus_change"] for row in annual])),
                        "annual": annual,
                    })
        scenarios[scenario] = {
            "adaptation": {**ADAPTATION[scenario], "base_year": 2020, "application": "attenuate negative cell log responses only"},
            "winsorization": {"lower_delta_log_yield": float(lower), "upper_delta_log_yield": float(upper), "pooling": "five unique cell-ESM-year response arrays after adaptation, before country-cell expansion"},
            "cases": cases,
        }

    result = {
        "schema": "hultgren_country_maize_market_sensitivity/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "structural_country_market_sensitivity_not_primary_welfare_damage_or_scc",
        "sources": sources,
        "weights": {"path": str(args.weights), "sha256": digest(args.weights), "receipt": str(args.weights_receipt), "receipt_sha256": digest(args.weights_receipt)},
        "market": "separate fully anticipated frictionless national maize markets; no expectations, unexpected weather, storage, trade, other crops, or marginal emissions pulse",
        "baseline_value_unit": receipt.get("units", "constant_2014_2016_usd"),
        "value_column": args.value_column,
        "represented_country_count": len(reference),
        "represented_baseline_value": float(reference.sum()),
        "elasticities": [{"id": i, "supply": s, "demand_magnitude": d, "central": c} for i, s, d, c in ELASTICITIES],
        "scenarios": scenarios,
        "interpretation": "descriptive late-century SSP585-minus-SSP126 country-maize-market sensitivity; not published welfare replication, marginal pulse damage, GIVE damage, or SCC",
        "claim_gates": {"structural_market_sensitivity": True, "paper_welfare_replication": False, "agriculture_replacement": False, "damage_or_scc": False},
        "implementation": {"path": str(Path(__file__).resolve().relative_to(ROOT)), "sha256": digest(Path(__file__).resolve())},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    central = [case for case in scenarios["fixed"]["cases"] if case["central_elasticity"] and case["yield_to_supply_mapping"] == "horizontal_output"]
    print(json.dumps({"status": result["status"], "countries": len(reference), "baseline_value": float(reference.sum()), "fixed_central_horizontal": central}, indent=2))


if __name__ == "__main__":
    main()
