#!/usr/bin/env python3
"""Compare one global maize market with the saved country-market sensitivity."""
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
from src.constant_elasticity_market import Market, paired_surplus, productivity_to_supply  # noqa: E402

RESPONSE = ROOT / "data/interim/epic_caraib_geography_20260908/result.json"
BASELINE = ROOT / "data/interim/welfare_baseline_ledger_20260914_v2/result.json"
COUNTRY = ROOT / "data/interim/structural_welfare_benchmark_v2_20260919/result.json"
PRICE = ROOT / "config/price_basis_registry.toml"
PROTOCOL = ROOT / "GLOBAL_MARKET_WELFARE_SENSITIVITY_PROTOCOL_20260919.md"
DEFAULT_OUTPUT = ROOT / "data/interim/global_market_welfare_sensitivity_20260919/result.json"

ELASTICITIES = (
    ("hultgren_pair_008_002", 0.08, 0.02, False),
    ("hultgren_pair_010_004", 0.10, 0.04, True),
    ("hultgren_pair_050_006", 0.50, 0.06, False),
)
MAPPINGS = ("horizontal_output", "fixed_input_cost")


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    physical = json.loads(RESPONSE.read_text())
    baseline = json.loads(BASELINE.read_text())
    country = json.loads(COUNTRY.read_text())
    with PRICE.open("rb") as f:
        price = tomllib.load(f)
    scalar = float(price["central_scalar"])
    if not math.isfinite(scalar) or scalar <= 0:
        raise ValueError("invalid price scalar")

    ledger = {(r["country"], r["regime"]): r for r in baseline["country_regime_rows"]}
    country_cases = {}
    for row in country["cases"]:
        key = (row["crop_model"], row["climate_model"], row["scenario"], row["calendar"],
               row["elasticity_id"], row["yield_to_supply_mapping"])
        country_cases[key] = row

    grouped: dict[tuple[str, str, str, str], list[dict]] = defaultdict(list)
    for row in physical["summaries"]:
        grouped[(row["crop_model"], row["climate_model"], row["scenario"], row["calendar"])].append(row)

    cases = []
    for case4 in sorted(grouped):
        rows = grouped[case4]
        for elasticity_id, es, ed, central in ELASTICITIES:
            for mapping in MAPPINGS:
                key = case4 + (elasticity_id, mapping)
                country_row = country_cases[key]
                parts = []
                missing_production = 0.0
                invalid_rows = []
                for row in rows:
                    source = ledger[(row["country"], row["regime"])]
                    raw_value = source["common_response_value_proxy_thousand_constant_2014_2016_USD"]
                    if raw_value is None:
                        missing_production += float(row["common_production_mt"])
                        continue
                    value = float(raw_value) * scalar
                    multiplier = 1.0 + float(row["effects"]["joint"]["conditional_country_percent"]) / 100.0
                    if not math.isfinite(multiplier) or multiplier <= 0:
                        invalid_rows.append({
                            "country": row["country"],
                            "regime": row["regime"],
                            "productivity_multiplier": multiplier,
                            "covered_value_thousand_USD2005": value,
                        })
                    parts.append((row["country"], row["regime"], value, multiplier))

                total_value = sum(p[2] for p in parts)
                if total_value <= 0:
                    raise ValueError("no positive valued support")
                admissible = not invalid_rows
                global_supply = global_damage = None
                min_multiplier = min(p[3] for p in parts)
                min_identity = [(p[0], p[1]) for p in parts if p[3] == min_multiplier][0]
                if admissible:
                    supply_sum = 0.0
                    for _, _, value, multiplier in parts:
                        shift = productivity_to_supply(math.log(multiplier), es, convention=mapping)
                        supply_sum += value / total_value * math.exp(shift)
                    global_supply = supply_sum
                    global_damage = paired_surplus(
                        Market(es, ed, total_value, "thousand_USD2005"), 0.0, math.log(supply_sum)
                    )["damage_change"]

                country_damage = float(country_row["valid_subset_damage_thousand_USD2005"])
                cases.append({
                    "crop_model": case4[0],
                    "climate_model": case4[1],
                    "scenario": case4[2],
                    "calendar": case4[3],
                    "adaptation": "fixed",
                    "elasticity_id": elasticity_id,
                    "supply_elasticity": es,
                    "demand_elasticity_magnitude": ed,
                    "central_elasticity": central,
                    "yield_to_supply_mapping": mapping,
                    "valued_common_support_thousand_USD2005": total_value,
                    "missing_value_proxy_production_mt_not_dollars": missing_production,
                    "minimum_regime_productivity_multiplier": min_multiplier,
                    "minimum_regime_productivity_identity": {
                        "country": min_identity[0], "regime": min_identity[1]
                    },
                    "invalid_response_count": len(invalid_rows),
                    "invalid_responses": invalid_rows,
                    "global_market_log_admissible": admissible,
                    "global_market_supply_multiplier": global_supply,
                    "global_market_damage_thousand_USD2005": global_damage,
                    "country_market_valid_subset_damage_thousand_USD2005": country_damage,
                    "global_minus_country_damage_thousand_USD2005": (
                        global_damage - country_damage if global_damage is not None else None
                    ),
                    "global_to_country_damage_ratio": (
                        global_damage / country_damage
                        if global_damage is not None and country_damage != 0 else None
                    ),
                    "structural_damage_interpretation_authorized": False,
                })

    output = {
        "status": "global_market_structural_sensitivity_complete",
        "case_count": len(cases),
        "market_geography": "single_global_maize_market",
        "comparison_market_geography": "separate_country_maize_markets",
        "period_contrast": "2031_2060_minus_1981_2010",
        "cases": cases,
        "limitations": [
            "global integration is prespecified sensitivity rather than preferred geography",
            "structural crop response rather than empirical causal response",
            "maize and covered common support only",
            "period mean rather than annual matched emissions pulse",
            "no trade cost, storage, cross-crop substitution or adaptation calibration",
        ],
        "empirical_damage_authorized": False,
        "agriculture_replacement_authorized": False,
        "give_export_authorized": False,
        "scc_authorized": False,
        "source_bindings": {
            "physical_response_sha256": digest(RESPONSE),
            "baseline_value_ledger_sha256": digest(BASELINE),
            "country_market_result_sha256": digest(COUNTRY),
            "price_registry_sha256": digest(PRICE),
            "market_code_sha256": digest(ROOT / "src/constant_elasticity_market.py"),
            "protocol_sha256": digest(PROTOCOL),
            "builder_sha256": digest(Path(__file__)),
        },
    }
    if len(cases) != 96:
        raise ValueError(f"expected 96 cases, found {len(cases)}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
