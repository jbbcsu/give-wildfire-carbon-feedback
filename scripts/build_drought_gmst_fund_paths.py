#!/usr/bin/env python3
"""Build a fail-closed global-maize drought/GMST marginal-damage sensitivity."""
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

from build_epa_fair_hultgren_quantity_damage_paths import ADAPTATION, PULSES, VALUE, adaptation_factors, country_market_damage
from build_epa_fair_hultgren_quantity_fund_paths import validated_price_registry

ROOT = Path(__file__).resolve().parents[1]
PULSE = 0.000025
PRICE_2005_TO_2020 = 1.2987749131468274


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("panel", "panel_receipt", "association", "association_validation", "climate_link",
                 "climate_validation", "fair", "fair_receipt", "fund_mapping", "fund_order",
                 "price_registry", "output", "receipt"):
        parser.add_argument(f"--{name.replace('_', '-')}", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists() and not args.receipt.exists(), "fresh outputs required")

    panel_receipt = json.loads(args.panel_receipt.read_text())
    association = json.loads(args.association.read_text())
    association_validation = json.loads(args.association_validation.read_text())
    climate = json.loads(args.climate_link.read_text())
    climate_validation = json.loads(args.climate_validation.read_text())
    fair_receipt = json.loads(args.fair_receipt.read_text())
    require(panel_receipt["output"]["sha256"] == digest(args.panel), "panel hash differs")
    require(association["status"] == "completed" and association["crop"] == "maize", "association source differs")
    require(association_validation["status"] == "passed", "association validation absent")
    require(climate["schema"] == "five_esm_drought_gmst_endpoint_link_v1", "climate-link source differs")
    require(climate_validation["status"] == "passed", "climate-link validation absent")
    require(fair_receipt["paths_sha256"] == digest(args.fair), "FAIR paths differ")
    require(fair_receipt["zero_pulse_identity"] and fair_receipt["pre_pulse_identity"]
            and fair_receipt["decreasing_pulse_convergence"], "FAIR validation gates failed")

    fit = next(item for item in association["fits"]
               if item["family"] == "spei_3_season" and item["clustering"] == "country_proxy")
    contrast = fit["contrasts"]["spei_3_season_plus_1"]
    response_cases = {
        "lower_95": float(contrast["log_yield_interval"][0]),
        "central": float(contrast["log_yield_contrast"]),
        "upper_95": float(contrast["log_yield_interval"][1]),
    }
    climate_record = next(item for item in climate["records"]
                          if item["crop"] == "mai" and item["window"] == "season"
                          and item["scale_months"] == 3 and item["irrigation"] == "noirr")
    require(climate_record["combined_predictive_rule_passes"] is True, "climate endpoint gate failed")
    spei_per_k = float(climate_record["full_fit"]["slope_spei_per_k"])
    require(spei_per_k < 0 and all(value > 0 for value in response_cases.values()), "source signs differ")

    panel = pd.read_parquet(args.panel, columns=["iso3", VALUE])
    country_value = panel.groupby("iso3", observed=True)[VALUE].sum().sort_index()
    require(country_value.gt(0).all(), "nonpositive represented maize value")
    with args.fund_mapping.open(newline="", encoding="utf-8-sig") as stream:
        country_region = {row["ISO3"]: row["fundregion"] for row in csv.DictReader(stream)}
    with args.fund_order.open(newline="", encoding="utf-8") as stream:
        regions = [row["fund_region"] for row in csv.DictReader(stream)]
    require(len(regions) == len(set(regions)) == 16, "FUND region order differs")
    missing_mapping = sorted(set(country_value.index) - set(country_region))
    # The archived GIVE/FUND crosswalk omits ATG.  Preserve the established
    # project policy: exclude it transparently rather than invent a region.
    require(missing_mapping == ["ATG"], f"unexpected represented countries lack FUND mapping: {missing_mapping}")
    omitted_value = float(country_value.loc[missing_mapping].sum())
    total_value_before_mapping = float(country_value.sum())
    country_value = country_value.drop(index=missing_mapping)
    region_index = {name: index for index, name in enumerate(regions)}
    positions = np.asarray([region_index[country_region[country]] for country in country_value.index], dtype=int)
    values = country_value.to_numpy(float)
    _registry, price_scalar = validated_price_registry(args.price_registry)

    fair = pd.read_csv(args.fair)
    years = np.arange(2020, 2301, dtype=int)
    paths = {pulse: fair.loc[fair.pulse_size_gtc.eq(pulse) & fair.year.isin(years)]
             .sort_values("year").difference_k.to_numpy(float) for pulse in PULSES}
    require(all(len(path) == len(years) for path in paths.values()), "FAIR horizon incomplete")
    require(np.all(paths[0.0] == 0), "zero-pulse temperature path differs")

    normalized_damage = {}
    records = []
    for response_case, response_per_spei in response_cases.items():
        log_yield_per_k = response_per_spei * spei_per_k
        require(log_yield_per_k < 0, "drought response must reduce yield under warming")
        for adaptation in ADAPTATION:
            for pulse in PULSES:
                raw = log_yield_per_k * paths[pulse]
                adapted = np.where(raw < 0, raw * adaptation_factors(years, adaptation), raw)
                ratio = np.exp(adapted)
                country_ratios = np.broadcast_to(ratio, (len(values), len(years)))
                damage = country_market_damage(values, country_ratios)
                global_damage = damage.sum(axis=0)
                if pulse > 0:
                    normalized_damage[(response_case, adaptation, pulse)] = global_damage / pulse
                if pulse != PULSE:
                    continue
                regional = np.zeros((len(regions), len(years)), dtype=float)
                np.add.at(regional, positions, damage)
                require(float(np.max(np.abs(regional.sum(axis=0) - global_damage))) < 1e-6,
                        "regional damage reconciliation differs")
                for year_index, year in enumerate(years):
                    for region_index_value, region in enumerate(regions):
                        records.append({"response_case": response_case, "adaptation": adaptation,
                                        "year": int(year), "fund_region": region,
                                        "marginal_damage_difference_billion_usd2005":
                                            float(regional[region_index_value, year_index] * price_scalar / 1e9)})

    convergence = 0.0
    for response_case in response_cases:
        for adaptation in ADAPTATION:
            small = normalized_damage[(response_case, adaptation, 0.000025)]
            next_value = normalized_damage[(response_case, adaptation, 0.00005)]
            scale = max(float(np.max(np.abs(small))), float(np.max(np.abs(next_value))), 1e-30)
            convergence = max(convergence, float(np.max(np.abs(small - next_value))) / scale)
    require(convergence <= 2e-4, "shrinking-pulse convergence failed")

    output = pd.DataFrame(records).sort_values(["response_case", "adaptation", "year", "fund_region"])
    require(len(output) == 3 * 3 * 281 * 16 and not output.duplicated(
        ["response_case", "adaptation", "year", "fund_region"]).any(), "output support differs")
    require(output.loc[output.year.eq(2020), "marginal_damage_difference_billion_usd2005"].eq(0).all(),
            "pre-pulse identity failed")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(args.output, index=False)
    receipt = {
        "schema": "drought_gmst_fund_paths_v1", "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "structural_sensitivity_paths_ready_for_paired_give_not_causal_drought_scc",
        "definition": "global maize SPEI-3 historical association times five-ESM endpoint SPEI/GMST slope and paired FAIR marginal temperature, valued in separate national maize markets",
        "response": {"cases_log_yield_per_spei": response_cases, "spei_per_k": spei_per_k,
                     "log_yield_per_k": {name: value * spei_per_k for name, value in response_cases.items()}},
        "support": {"response_cases": list(response_cases), "adaptation": list(ADAPTATION),
                    "years": [2020, 2300], "fund_regions": regions, "rows": len(output),
                    "countries": int(len(country_value)),
                    "mapping_exclusion": {"iso3": missing_mapping,
                        "represented_value_constant_2014_2016_usd": omitted_value,
                        "share_of_represented_value": omitted_value / total_value_before_mapping}},
        "validation": {"regional_reconciliation": True, "zero_and_pre_pulse_identity": True,
                       "maximum_25k_vs_50k_normalized_convergence_relative_error": convergence},
        "currency": {"input": "constant_2014_2016_USD", "output": "billion_USD2005",
                     "source_to_2005_scalar": price_scalar, "report_2005_to_2020_scalar": PRICE_2005_TO_2020},
        "sources": {name: {"path": str(path), "sha256": digest(path)} for name, path in {
            "panel": args.panel, "panel_receipt": args.panel_receipt, "association": args.association,
            "association_validation": args.association_validation, "climate_link": args.climate_link,
            "climate_validation": args.climate_validation, "fair": args.fair, "fair_receipt": args.fair_receipt,
            "fund_mapping": args.fund_mapping, "fund_order": args.fund_order, "price_registry": args.price_registry}.items()},
        "output": {"path": str(args.output), "bytes": args.output.stat().st_size, "sha256": digest(args.output)},
        "gates": {"paired_give_engineering": False, "structural_sensitivity": True,
                  "causal_drought_attribution": False, "central_precipitation_scc": False},
        "limitations": [
            "The global SPEI response is a historical association whose country-holdout predictive gain over rainfall was not robust.",
            "The SPEI/GMST slope is a late-century multi-forcing endpoint relationship, not a transient CO2-only attribution estimate.",
            "The drought response is applied uniformly to represented maize production; other crops, irrigation adaptation, trade and storage are omitted.",
            "Response intervals condition on the fitted historical model and do not include climate-link or structural uncertainty.",
            "Antigua and Barbuda is excluded because ATG is absent from the archived GIVE/FUND crosswalk; no region is guessed.",
        ],
        "implementation": {"path": str(Path(__file__).resolve().relative_to(ROOT)), "sha256": digest(Path(__file__))},
    }
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": receipt["status"], "response": receipt["response"],
                      "support": receipt["support"], "validation": receipt["validation"]}, indent=2))


if __name__ == "__main__":
    main()
