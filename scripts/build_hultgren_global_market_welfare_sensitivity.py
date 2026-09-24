#!/usr/bin/env python3
"""Build a quarantined global-maize market sensitivity from cell responses.

This fully anticipated, single-global-market benchmark uses published candidate
elasticity pairs and published-style 1% log-impact winsorization.  It is not
the Hultgren country/expectations/storage model, a marginal pulse, or SCC.
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

from src.constant_elasticity_market import Market, paired_surplus

ROOT = Path(__file__).resolve().parents[1]
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
    specification = ADAPTATION[scenario]
    attenuation = np.minimum(specification["annual_attenuation_rate"] * np.maximum(year - 2020, 0), specification["cap"])
    return 1.0 - attenuation


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", action="append", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), "fresh output required")
    frames, sources = [], []
    for path in args.input:
        frame = pd.read_parquet(path)
        require(frame.climate_model.nunique() == 1, f"multiple models: {path}")
        require(frame.harvest_year.nunique() == 9, f"year support differs: {path}")
        require(frame.analysis_weight.gt(0).all(), f"nonpositive weight: {path}")
        frames.append(frame)
        sources.append({"path": str(path), "sha256": digest(path), "rows": len(frame), "climate_model": frame.climate_model.iloc[0]})
    models = [frame.climate_model.iloc[0] for frame in frames]
    require(len(models) == len(set(models)) == 5, "five unique climate models required")
    baseline_values = []
    for frame in frames:
        annual = frame.groupby("harvest_year", sort=True).analysis_weight.sum().to_numpy(dtype=np.float64)
        require(np.allclose(annual, annual[0], rtol=1e-10, atol=1e-3), "baseline value changes across years")
        baseline_values.append(float(annual[0]))
    require(np.allclose(baseline_values, baseline_values[0], rtol=1e-10, atol=1e-3), "baseline value differs across models")
    baseline_value = baseline_values[0]

    scenarios = {}
    for scenario in ADAPTATION:
        adjusted_frames = []
        for frame in frames:
            raw = frame.precipitation_delta_log_yield.to_numpy(dtype=np.float64)
            factors = adaptation_factor(frame.harvest_year.to_numpy(dtype=np.int32), scenario)
            adjusted = np.where(raw < 0.0, raw * factors, raw)
            current = frame.copy()
            current["adapted_delta_log_yield"] = adjusted
            adjusted_frames.append(current)
        pooled = np.concatenate([frame.adapted_delta_log_yield.to_numpy(dtype=np.float64) for frame in adjusted_frames])
        lower, upper = np.quantile(pooled, [0.01, 0.99], method="linear")
        cases = []
        for elasticity_id, supply, demand, central in ELASTICITIES:
            market = Market(supply, demand, baseline_value, "constant_2014_2016_usd")
            for mapping in MAPPINGS:
                exponent = 1.0 if mapping == "horizontal_output" else 1.0 + supply
                for model, frame in zip(models, adjusted_frames, strict=True):
                    annual_records = []
                    for year, group in frame.groupby("harvest_year", sort=True):
                        weight = group.analysis_weight.to_numpy(dtype=np.float64)
                        capped = np.clip(group.adapted_delta_log_yield.to_numpy(dtype=np.float64), lower, upper)
                        supply_ratio = float(np.dot(weight, np.exp(exponent * capped)) / weight.sum())
                        require(math.isfinite(supply_ratio) and supply_ratio > 0.0, "invalid supply ratio")
                        log_shift = math.log(supply_ratio)
                        welfare = paired_surplus(market, 0.0, log_shift)
                        annual_records.append({
                            "harvest_year": int(year), "supply_ratio": supply_ratio,
                            "log_supply_shift": log_shift,
                            "total_surplus_change": welfare["total_surplus_change"],
                            "damage_change": welfare["damage_change"],
                        })
                    cases.append({
                        "climate_model": model, "elasticity_id": elasticity_id,
                        "supply_elasticity": supply, "demand_elasticity_magnitude": demand,
                        "central_elasticity": central, "yield_to_supply_mapping": mapping,
                        "mean_annual_total_surplus_change": float(np.mean([row["total_surplus_change"] for row in annual_records])),
                        "mean_annual_damage_change": float(np.mean([row["damage_change"] for row in annual_records])),
                        "annual": annual_records,
                    })
        scenarios[scenario] = {
            "adaptation": {**ADAPTATION[scenario], "base_year": 2020, "application": "attenuate negative cell log responses only"},
            "winsorization": {"lower_delta_log_yield": float(lower), "upper_delta_log_yield": float(upper), "pooling": "all cell-ESM-years after adaptation scenario"},
            "cases": cases,
        }
    result = {
        "schema": "hultgren_global_maize_market_sensitivity/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "structural_global_market_sensitivity_not_primary_welfare_damage_or_scc",
        "sources": sources,
        "baseline_value": baseline_value,
        "baseline_value_unit": "constant_2014_2016_usd",
        "market": "one fully anticipated frictionless global maize market; no expectations, unexpected weather, storage, stockout, trade costs, or other crops",
        "elasticities": [{"id": i, "supply": s, "demand_magnitude": d, "central": c} for i, s, d, c in ELASTICITIES],
        "yield_to_supply_mappings": {
            "horizontal_output": "log supply shift equals cell log productivity shift before aggregation",
            "fixed_input_cost": "cell log supply shift equals (1+supply elasticity) times log productivity shift before aggregation",
        },
        "scenarios": scenarios,
        "interpretation": "descriptive late-century SSP585-minus-SSP126 single-crop market sensitivity; not the paper's primary national market, not dynamic storage welfare, not a marginal emissions pulse, not GIVE damage, and not SCC",
        "claim_gates": {"structural_market_sensitivity": True, "paper_welfare_replication": False, "agriculture_replacement": False, "damage_or_scc": False},
        "implementation": {"path": str(Path(__file__).resolve().relative_to(ROOT)), "sha256": digest(Path(__file__).resolve()), "market_core": "src/constant_elasticity_market.py", "market_core_sha256": digest(ROOT / "src/constant_elasticity_market.py")},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    central = [case for case in scenarios["fixed"]["cases"] if case["central_elasticity"] and case["yield_to_supply_mapping"] == "horizontal_output"]
    print(json.dumps({"status": result["status"], "fixed_central_horizontal": central}, indent=2))


if __name__ == "__main__":
    main()
