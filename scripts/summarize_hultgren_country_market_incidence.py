#!/usr/bin/env python3
"""Summarize central fixed national-maize-market incidence by GIVE region."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

VALUE = "maize_gross_production_value_constant_2014_2016_usd"


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--market-result", type=Path, required=True)
    parser.add_argument("--fund-mapping", type=Path, required=True)
    parser.add_argument("--fund-order", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), "fresh output required")
    market = json.loads(args.market_result.read_text(encoding="utf-8"))
    require(market["schema"] == "hultgren_country_maize_market_sensitivity/v1", "market schema differs")
    weight_path = Path(market["weights"]["path"])
    require(digest(weight_path) == market["weights"]["sha256"], "weight hash differs")
    weights = pd.read_parquet(weight_path, columns=["iso3", "native_lat_index", "native_lon_index", VALUE])
    with args.fund_mapping.open(newline="", encoding="utf-8-sig") as stream:
        mapping = {row["ISO3"]: row["fundregion"] for row in csv.DictReader(stream)}
    with args.fund_order.open(newline="", encoding="utf-8") as stream:
        order = [row["fund_region"] for row in csv.DictReader(stream)]
    require(len(order) == 16 and len(set(order)) == 16, "FUND order differs")

    fixed = market["scenarios"]["fixed"]
    lower = float(fixed["winsorization"]["lower_delta_log_yield"])
    upper = float(fixed["winsorization"]["upper_delta_log_yield"])
    cases = {
        case["climate_model"]: case
        for case in fixed["cases"]
        if case["central_elasticity"] and case["yield_to_supply_mapping"] == "horizontal_output"
    }
    require(len(cases) == 5, "five central cases required")
    supply, demand = 0.10, 0.04
    country_model = []
    region_model: dict[tuple[str, str], float] = defaultdict(float)
    for source in market["sources"]:
        path = Path(source["path"])
        require(digest(path) == source["sha256"], f"source hash differs: {path}")
        frame = pd.read_parquet(path, columns=["climate_model", "harvest_year", "native_lat_index", "native_lon_index", "precipitation_delta_log_yield"])
        model = str(frame["climate_model"].iloc[0])
        merged = frame.merge(weights, on=["native_lat_index", "native_lon_index"], how="inner", validate="many_to_many")
        support = merged.drop_duplicates(["iso3", "native_lat_index", "native_lon_index"])
        baseline = support.groupby("iso3", sort=True)[VALUE].sum()
        missing = sorted(set(baseline.index) - set(mapping))
        annual_country: dict[str, list[float]] = defaultdict(list)
        for _, group in merged.groupby("harvest_year", sort=True):
            response = np.clip(group["precipitation_delta_log_yield"].to_numpy(dtype=np.float64), lower, upper)
            output = pd.Series(
                group[VALUE].to_numpy(dtype=np.float64) * np.exp(response), index=group.index
            ).groupby(group["iso3"], sort=True).sum()
            aligned = baseline.loc[output.index]
            shift = np.log(output.to_numpy(dtype=np.float64) / aligned.to_numpy(dtype=np.float64))
            change_price = -shift / (supply + demand)
            z = (1.0 - demand) * change_price
            exprel = np.ones_like(z)
            nonzero = z != 0.0
            exprel[nonzero] = np.expm1(z[nonzero]) / z[nonzero]
            damage = -aligned.to_numpy(dtype=np.float64) * shift / (1.0 + supply) * exprel
            for iso, value in zip(output.index, damage, strict=True):
                annual_country[str(iso)].append(float(value))
        for iso in sorted(annual_country):
            mean_damage = float(np.mean(annual_country[iso]))
            region = mapping.get(iso, "UNMAPPED")
            country_model.append({
                "climate_model": model, "iso3": iso, "fund_region": region,
                "baseline_value": float(baseline[iso]), "mean_annual_damage_change": mean_damage,
            })
            region_model[(model, region)] += mean_damage
        reconstructed = sum(row["mean_annual_damage_change"] for row in country_model if row["climate_model"] == model)
        require(math.isclose(reconstructed, float(cases[model]["mean_annual_damage_change"]), rel_tol=2e-11, abs_tol=1e-4), f"global total differs: {model}")

    region_records = []
    output_regions = order + ["UNMAPPED"]
    for model in sorted(cases):
        for region in output_regions:
            region_records.append({"climate_model": model, "fund_region": region, "mean_annual_damage_change": region_model[(model, region)]})
    ensemble_regions = []
    for region in output_regions:
        values = [region_model[(model, region)] for model in sorted(cases)]
        ensemble_regions.append({
            "fund_region": region, "equal_model_mean_annual_damage_change": float(np.mean(values)),
            "minimum_model_mean_annual_damage_change": float(np.min(values)),
            "maximum_model_mean_annual_damage_change": float(np.max(values)),
        })
    ensemble_countries = []
    country_frame = pd.DataFrame(country_model)
    for iso, group in country_frame.groupby("iso3", sort=True):
        ensemble_countries.append({
            "iso3": iso, "fund_region": str(group["fund_region"].iloc[0]),
            "baseline_value": float(group["baseline_value"].iloc[0]),
            "equal_model_mean_annual_damage_change": float(group["mean_annual_damage_change"].mean()),
            "minimum_model_mean_annual_damage_change": float(group["mean_annual_damage_change"].min()),
            "maximum_model_mean_annual_damage_change": float(group["mean_annual_damage_change"].max()),
        })
    result = {
        "schema": "hultgren_country_market_central_fixed_incidence/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "structural_country_market_incidence_not_primary_damage_or_scc",
        "specification": {"adaptation": "fixed", "supply_elasticity": supply, "demand_elasticity_magnitude": demand, "yield_to_supply_mapping": "horizontal_output", "price_basis": "constant_2014_2016_usd"},
        "sources": {
            "market_result": {"path": str(args.market_result), "sha256": digest(args.market_result)},
            "fund_mapping": {"path": str(args.fund_mapping), "sha256": digest(args.fund_mapping)},
            "fund_order": {"path": str(args.fund_order), "sha256": digest(args.fund_order)},
        },
        "coverage": {
            "models": len(cases), "countries": len(ensemble_countries), "fund_regions": len(order),
            "unmapped_countries": missing,
            "unmapped_baseline_value": float(sum(row["baseline_value"] for row in ensemble_countries if row["fund_region"] == "UNMAPPED")),
        },
        "country_model_records": country_model,
        "fund_region_model_records": region_records,
        "country_equal_model_summaries": ensemble_countries,
        "fund_region_equal_model_summaries": ensemble_regions,
        "interpretation": "incidence of the quarantined central fixed national-maize-market sensitivity; UNMAPPED is preserved rather than imputed; not a marginal pulse, complete agriculture damage, GIVE damage, or SCC",
        "claim_gates": {"incidence_accounting": True, "damage_or_scc": False},
        "implementation": {"path": str(Path(__file__).resolve().relative_to(Path(__file__).resolve().parents[1])), "sha256": digest(Path(__file__).resolve())},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    ranked = sorted(ensemble_regions, key=lambda row: row["equal_model_mean_annual_damage_change"], reverse=True)
    print(json.dumps({"status": result["status"], "fund_regions_ranked": ranked}, indent=2))


if __name__ == "__main__":
    main()
