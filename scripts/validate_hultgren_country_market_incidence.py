#!/usr/bin/env python3
"""Validate the country-to-FUND aggregation of maize-market incidence."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def close(left: float, right: float, label: str) -> None:
    if not math.isclose(left, right, rel_tol=2e-11, abs_tol=1e-4):
        raise AssertionError(f"{label}: {left!r} != {right!r}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("fresh output required")
    result = json.loads(args.input.read_text(encoding="utf-8"))
    if result["schema"] != "hultgren_country_market_central_fixed_incidence/v1" or result["claim_gates"]["damage_or_scc"]:
        raise AssertionError("schema or claim gate differs")
    for source in result["sources"].values():
        if digest(Path(source["path"])) != source["sha256"]:
            raise AssertionError(f"source hash differs: {source['path']}")
    market = json.loads(Path(result["sources"]["market_result"]["path"]).read_text(encoding="utf-8"))
    with Path(result["sources"]["fund_mapping"]["path"]).open(newline="", encoding="utf-8-sig") as stream:
        mapping = {row["ISO3"]: row["fundregion"] for row in csv.DictReader(stream)}
    with Path(result["sources"]["fund_order"]["path"]).open(newline="", encoding="utf-8") as stream:
        order = [row["fund_region"] for row in csv.DictReader(stream)]

    countries = pd.DataFrame(result["country_model_records"])
    regions = pd.DataFrame(result["fund_region_model_records"])
    country_ensemble = pd.DataFrame(result["country_equal_model_summaries"])
    region_ensemble = pd.DataFrame(result["fund_region_equal_model_summaries"])
    if len(countries) != 5 * 116 or countries.duplicated(["climate_model", "iso3"]).any():
        raise AssertionError("country-model support differs")
    expected_region = countries["iso3"].map(mapping).fillna("UNMAPPED")
    if not expected_region.equals(countries["fund_region"]):
        raise AssertionError("country-to-region mapping differs")
    expected_labels = order + ["UNMAPPED"]
    if len(regions) != 5 * len(expected_labels) or set(regions["fund_region"]) != set(expected_labels):
        raise AssertionError("region-model support differs")
    models = sorted(countries["climate_model"].unique())
    central_cases = {
        case["climate_model"]: case
        for case in market["scenarios"]["fixed"]["cases"]
        if case["central_elasticity"] and case["yield_to_supply_mapping"] == "horizontal_output"
    }
    checks = 0
    for model in models:
        source = countries.loc[countries["climate_model"].eq(model)]
        grouped = source.groupby("fund_region")["mean_annual_damage_change"].sum()
        reported = regions.loc[regions["climate_model"].eq(model)].set_index("fund_region")["mean_annual_damage_change"]
        for region in expected_labels:
            close(float(grouped.get(region, 0.0)), float(reported[region]), f"{model}/{region}")
            checks += 1
        close(float(source["mean_annual_damage_change"].sum()), float(central_cases[model]["mean_annual_damage_change"]), f"{model}/global")
        checks += 1
    for iso, group in countries.groupby("iso3"):
        row = country_ensemble.loc[country_ensemble["iso3"].eq(iso)].iloc[0]
        close(float(group["mean_annual_damage_change"].mean()), float(row["equal_model_mean_annual_damage_change"]), f"{iso}/ensemble")
        checks += 1
    for region, group in regions.groupby("fund_region"):
        row = region_ensemble.loc[region_ensemble["fund_region"].eq(region)].iloc[0]
        close(float(group["mean_annual_damage_change"].mean()), float(row["equal_model_mean_annual_damage_change"]), f"{region}/ensemble")
        checks += 1
    missing = sorted(set(countries.loc[countries["fund_region"].eq("UNMAPPED"), "iso3"]))
    if missing != result["coverage"]["unmapped_countries"]:
        raise AssertionError("unmapped list differs")
    baseline = country_ensemble.loc[country_ensemble["fund_region"].eq("UNMAPPED"), "baseline_value"].sum()
    close(float(baseline), float(result["coverage"]["unmapped_baseline_value"]), "unmapped baseline")

    audit = {
        "schema": "hultgren_country_market_central_fixed_incidence_validation/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "pass",
        "source": {"path": str(args.input), "sha256": digest(args.input)},
        "validation": {"numeric_and_mapping_checks": checks, "models": len(models), "countries": len(country_ensemble), "reported_fund_regions": len(order), "unmapped_countries": missing},
        "interpretation": "Aggregation validation only; no damage or SCC gate is opened.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(audit, indent=2))


if __name__ == "__main__":
    main()
