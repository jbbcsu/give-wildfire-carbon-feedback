#!/usr/bin/env python3
"""Build a non-SCC structural maize-welfare sensitivity from audited summaries."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.constant_elasticity_market import (  # noqa: E402
    Market,
    paired_surplus,
    productivity_to_supply,
)

RESPONSE = ROOT / "data/interim/epic_caraib_geography_20260908/result.json"
BASELINE = ROOT / "data/interim/welfare_baseline_ledger_20260914_v2/result.json"
PRICE = ROOT / "config/price_basis_registry.toml"
PROTOCOL = ROOT / "STRUCTURAL_WELFARE_BENCHMARK_PROTOCOL_20260919.md"
DEFAULT_OUTPUT = ROOT / "data/interim/structural_welfare_benchmark_v2_20260919/result.json"

ELASTICITIES = (
    ("hultgren_pair_008_002", 0.08, 0.02, False),
    ("hultgren_pair_010_004", 0.10, 0.04, True),
    ("hultgren_pair_050_006", 0.50, 0.06, False),
)
MAPPINGS = ("horizontal_output", "fixed_input_cost")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def finite_positive(value: object, label: str) -> float:
    x = float(value)
    if not math.isfinite(x) or x <= 0:
        raise ValueError(f"{label} must be finite and positive")
    return x


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    response = json.loads(RESPONSE.read_text())
    baseline = json.loads(BASELINE.read_text())
    with PRICE.open("rb") as f:
        price = tomllib.load(f)

    if response.get("status") != "epic_caraib_geographic_decomposition_complete":
        raise ValueError("unexpected physical-response status")
    if baseline.get("status") != "nonmonetary_baseline_value_proxy_ledger_complete":
        raise ValueError("unexpected baseline-ledger status")
    if baseline.get("physical_response_applied") or baseline.get("damage_calculated"):
        raise ValueError("baseline ledger is not an unmodified value proxy")
    scalar = finite_positive(price["central_scalar"], "price scalar")
    if price.get("output_units") != "USD2005":
        raise ValueError("price registry output must be USD2005")

    value_by_country_regime: dict[tuple[str, str], dict] = {}
    total_common_value_source = 0.0
    for row in baseline["country_regime_rows"]:
        key = (row["country"], row["regime"])
        if key in value_by_country_regime:
            raise ValueError(f"duplicate baseline key {key}")
        value_by_country_regime[key] = row
        value = row["common_response_value_proxy_thousand_constant_2014_2016_USD"]
        if value is not None:
            total_common_value_source += float(value)

    grouped: dict[tuple[str, str, str, str], list[dict]] = defaultdict(list)
    for row in response["summaries"]:
        key = (row["crop_model"], row["climate_model"], row["scenario"], row["calendar"])
        grouped[key].append(row)
    if len(grouped) != 16:
        raise ValueError(f"expected 16 model/climate/scenario/calendar cases, found {len(grouped)}")

    cases = []
    country_diagnostics = []
    for case_key in sorted(grouped):
        crop_model, climate_model, scenario, calendar = case_key
        regimes_by_country: dict[str, list[dict]] = defaultdict(list)
        for row in grouped[case_key]:
            regimes_by_country[row["country"]].append(row)

        for elasticity_id, supply_e, demand_e, central in ELASTICITIES:
            for mapping in MAPPINGS:
                damage = 0.0
                benefit = 0.0
                valued = 0.0
                missing_value = 0.0
                invalid = 0.0
                invalid_records = []
                country_count = 0
                valued_country_count = 0
                missing_country_count = 0
                invalid_country_count = 0
                country_changes = []
                minimum_supply = None
                minimum_supply_country = None
                for country in sorted(regimes_by_country):
                    rows = regimes_by_country[country]
                    country_count += 1
                    parts = []
                    country_missing = False
                    country_common_production = 0.0
                    for row in rows:
                        ledger = value_by_country_regime.get((country, row["regime"]))
                        if ledger is None:
                            raise ValueError(f"response key absent from baseline ledger: {country}/{row['regime']}")
                        common_prod = float(row["common_production_mt"])
                        if common_prod <= 0:
                            raise ValueError("response summaries must have positive common production")
                        country_common_production += common_prod
                        value_source = ledger["common_response_value_proxy_thousand_constant_2014_2016_USD"]
                        if value_source is None:
                            # A dollar amount is unknown; production is retained but cannot be valued.
                            country_missing = True
                            continue
                        value_usd2005 = finite_positive(value_source, "covered value") * scalar
                        multiplier = 1.0 + float(row["effects"]["joint"]["conditional_country_percent"]) / 100.0
                        parts.append((row["regime"], value_usd2005, multiplier))

                    # Never treat a partially valued country as a complete country market.
                    if country_missing:
                        missing_country_count += 1
                        missing_value += country_common_production
                        continue
                    if not parts:
                        missing_country_count += 1
                        continue
                    country_value = sum(v for _, v, _ in parts)
                    bad = [(regime, a) for regime, _, a in parts if not math.isfinite(a) or a <= 0]
                    if bad:
                        invalid_country_count += 1
                        invalid += country_value
                        invalid_records.append({"country": country, "regimes": bad,
                                                "covered_value_thousand_USD2005": country_value})
                        continue

                    weighted_supply = 0.0
                    for _, value, multiplier in parts:
                        log_productivity = math.log(multiplier)
                        s_r = productivity_to_supply(log_productivity, supply_e, convention=mapping)
                        weighted_supply += value / country_value * math.exp(s_r)
                    s_market = math.log(weighted_supply)
                    market = Market(supply_e, demand_e, country_value, "thousand_USD2005")
                    welfare = paired_surplus(market, 0.0, s_market)
                    damage += welfare["damage_change"]
                    benefit += welfare["total_surplus_change"]
                    valued += country_value
                    valued_country_count += 1
                    country_changes.append((country, welfare["damage_change"]))
                    if minimum_supply is None or weighted_supply < minimum_supply:
                        minimum_supply = weighted_supply
                        minimum_supply_country = country

                    if central and mapping == "horizontal_output":
                        country_diagnostics.append({
                            "crop_model": crop_model,
                            "climate_model": climate_model,
                            "scenario": scenario,
                            "calendar": calendar,
                            "country": country,
                            "covered_value_thousand_USD2005": country_value,
                            "market_productivity_multiplier": weighted_supply,
                            "damage_thousand_USD2005": welfare["damage_change"],
                        })

                log_admissible = invalid_country_count == 0
                absolute_sum = sum(abs(v) for _, v in country_changes)
                largest_country, largest_damage = max(
                    country_changes, key=lambda item: abs(item[1]), default=(None, None)
                )
                cases.append({
                    "crop_model": crop_model,
                    "climate_model": climate_model,
                    "scenario": scenario,
                    "calendar": calendar,
                    "adaptation": "fixed",
                    "market_geography": "country",
                    "elasticity_id": elasticity_id,
                    "supply_elasticity": supply_e,
                    "demand_elasticity_magnitude": demand_e,
                    "central_elasticity": central,
                    "yield_to_supply_mapping": mapping,
                    "country_count_with_positive_common_production": country_count,
                    "valued_country_count": valued_country_count,
                    "missing_value_country_count": missing_country_count,
                    "invalid_response_country_count": invalid_country_count,
                    "valued_common_support_thousand_USD2005": valued,
                    "invalid_response_common_support_thousand_USD2005": invalid,
                    "missing_value_proxy_production_mt_not_dollars": missing_value,
                    "valid_subset_damage_thousand_USD2005": damage,
                    "valid_subset_total_surplus_change_thousand_USD2005": benefit,
                    "all_valued_country_responses_log_admissible": log_admissible,
                    "minimum_market_supply_multiplier": minimum_supply,
                    "minimum_market_supply_multiplier_country": minimum_supply_country,
                    "largest_absolute_country_damage_country": largest_country,
                    "largest_absolute_country_damage_thousand_USD2005": largest_damage,
                    "largest_absolute_country_share_of_absolute_changes": (
                        abs(largest_damage) / absolute_sum if absolute_sum and largest_damage is not None else None
                    ),
                    "structural_damage_interpretation_authorized": False,
                    "invalid_responses": invalid_records,
                })

    output = {
        "status": "structural_welfare_research_benchmark_complete",
        "version": 2,
        "supersedes_retained_output": "data/interim/structural_welfare_benchmark_20260919/result.json",
        "estimand": "period_mean_joint_temperature_precipitation_maize_structural_sensitivity",
        "period_contrast": "2031_2060_minus_1981_2010",
        "adaptation_cases_calculated": ["fixed"],
        "adaptation_cases_not_calibrated": ["trend", "upper"],
        "source_common_support_value_thousand_constant_2014_2016_USD": total_common_value_source,
        "price_scalar_to_USD2005": scalar,
        "case_count": len(cases),
        "cases": cases,
        "central_horizontal_country_diagnostics": country_diagnostics,
        "limitations": [
            "structural crop-model benchmark rather than empirical causal response",
            "maize and supported common footprint only",
            "period-mean scenario contrast rather than annual or emissions-pulse path",
            "no standalone precipitation attribution monetized",
            "missing baseline values and invalid response multipliers are not imputed",
            "trend and upper adaptation cases are not calibrated",
        ],
        "empirical_damage_authorized": False,
        "agriculture_replacement_authorized": False,
        "give_export_authorized": False,
        "scc_authorized": False,
        "source_bindings": {
            "physical_response_sha256": sha256(RESPONSE),
            "baseline_value_ledger_sha256": sha256(BASELINE),
            "price_registry_sha256": sha256(PRICE),
            "market_code_sha256": sha256(ROOT / "src/constant_elasticity_market.py"),
            "protocol_sha256": sha256(PROTOCOL),
            "builder_sha256": sha256(Path(__file__)),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
