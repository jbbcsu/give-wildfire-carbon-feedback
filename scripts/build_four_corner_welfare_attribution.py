#!/usr/bin/env python3
"""Evaluate four crop-yield corners, then Shapley-decompose global welfare."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path
import sys
import tomllib

import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.constant_elasticity_market import Market, paired_surplus  # noqa: E402

PHYSICAL = ROOT / "data/interim/epic_caraib_global_comparison_20260908/result.json"
CELLS = ROOT / "data/interim/epic_caraib_geography_20260908/country_cell_production.parquet"
BASELINE = ROOT / "data/interim/welfare_baseline_ledger_20260914_v2/result.json"
PRIOR_GLOBAL = ROOT / "data/interim/global_market_welfare_sensitivity_20260919/result.json"
PRICE = ROOT / "config/price_basis_registry.toml"
PROTOCOL = ROOT / "FOUR_CORNER_WELFARE_ATTRIBUTION_PROTOCOL_20260919.md"
DEFAULT_OUTPUT = ROOT / "data/interim/four_corner_welfare_attribution_20260919/result.json"

ELASTICITIES = (
    ("hultgren_pair_008_002", 0.08, 0.02, False),
    ("hultgren_pair_010_004", 0.10, 0.04, True),
    ("hultgren_pair_050_006", 0.50, 0.06, False),
)
MAPPINGS = ("horizontal_output", "fixed_input_cost")
CORNERS = ("y00", "y10", "y01", "y11")


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    physical = json.loads(PHYSICAL.read_text())
    baseline = json.loads(BASELINE.read_text())
    prior = json.loads(PRIOR_GLOBAL.read_text())
    with PRICE.open("rb") as f:
        scalar = float(tomllib.load(f)["central_scalar"])

    cell = pq.read_table(CELLS).to_pandas()
    cell = cell.loc[cell.common_response & (cell.production_mt > 0),
                    ["country", "regime", "latitude", "longitude", "production_mt"]].copy()
    if cell.duplicated(["country", "regime", "latitude", "longitude"]).any():
        raise ValueError("duplicate country/cell/regime production key")
    value_rows = {(r["country"], r["regime"]): r for r in baseline["country_regime_rows"]}
    prior_cases = {
        (r["crop_model"], r["climate_model"], r["scenario"], r["calendar"],
         r["elasticity_id"], r["yield_to_supply_mapping"]): r
        for r in prior["cases"]
    }
    grouped = defaultdict(list)
    for row in physical["summaries"]:
        grouped[(row["crop_model"], row["climate_model"], row["scenario"], row["calendar"])].append(row)
    if len(grouped) != 16 or any(len(rows) != 2 for rows in grouped.values()):
        raise ValueError("expected 16 physical cases with two regimes each")

    physical_cases = {}
    ledger_bindings = []
    for case4 in sorted(grouped):
        aggregate_rows = []
        negative = {corner: {"cell_count": 0, "production_mt": 0.0,
                             "covered_value_proxy_thousand_USD2005": 0.0}
                    for corner in CORNERS}
        missing_production = 0.0
        for summary in sorted(grouped[case4], key=lambda r: r["regime"]):
            path = ROOT / summary["ledger_path"]
            if digest(path) != summary["ledger_sha256"]:
                raise ValueError(f"ledger hash mismatch: {path}")
            ledger_bindings.append({"path": summary["ledger_path"], "sha256": summary["ledger_sha256"]})
            ledger = pq.read_table(path, columns=["latitude", "longitude", "baseline_tDM_ha",
                                                  "y00", "y10", "y01", "y11"]).to_pandas()
            if ledger.duplicated(["latitude", "longitude"]).any():
                raise ValueError(f"duplicate ledger coordinate: {path}")
            support = cell.loc[cell.regime == summary["regime"]]
            merged = support.merge(ledger, on=["latitude", "longitude"], how="left", validate="many_to_one")
            if merged[list(CORNERS) + ["baseline_tDM_ha"]].isna().any().any():
                raise ValueError(f"missing physical corner on common support: {path}")
            if not ((merged.baseline_tDM_ha > 0) & (merged.y00 > 0)).all():
                raise ValueError("nonpositive baseline on common support")
            if not ((merged.y00 - merged.baseline_tDM_ha).abs() <=
                    1e-11 * merged.baseline_tDM_ha.abs().clip(lower=1)).all():
                raise ValueError("y00 differs from baseline")

            for country, group in merged.groupby("country", sort=True):
                source = value_rows[(country, summary["regime"])]
                value_raw = source["common_response_value_proxy_thousand_constant_2014_2016_USD"]
                production = math.fsum(group.production_mt.tolist())
                if value_raw is None:
                    missing_production += production
                    continue
                value = float(value_raw) * scalar
                denom = production
                record = {"country": country, "regime": summary["regime"],
                          "covered_value_thousand_USD2005": value}
                for corner in CORNERS:
                    vals = group[corner] / group.y00
                    record[corner] = math.fsum((group.production_mt * vals).tolist()) / denom
                    bad = group[corner] <= 0
                    if bad.any():
                        bad_prod = math.fsum(group.loc[bad, "production_mt"].tolist())
                        negative[corner]["cell_count"] += int(bad.sum())
                        negative[corner]["production_mt"] += bad_prod
                        negative[corner]["covered_value_proxy_thousand_USD2005"] += value * bad_prod / denom
                aggregate_rows.append(record)

        physical_cases[case4] = {
            "rows": aggregate_rows,
            "negative_corners": negative,
            "missing_value_proxy_production_mt_not_dollars": missing_production,
        }

    results = []
    for case4 in sorted(physical_cases):
        state = physical_cases[case4]
        rows = state["rows"]
        total_value = math.fsum(r["covered_value_thousand_USD2005"] for r in rows)
        for elasticity_id, es, ed, central in ELASTICITIES:
            for mapping in MAPPINGS:
                power = 1.0 if mapping == "horizontal_output" else 1.0 + es
                supply = {}
                inadmissible = []
                for corner in CORNERS:
                    bad = [r for r in rows if not math.isfinite(r[corner]) or r[corner] <= 0]
                    if bad:
                        inadmissible.extend({"corner": corner, "country": r["country"],
                                             "regime": r["regime"], "aggregate_multiplier": r[corner]}
                                            for r in bad)
                        supply[corner] = None
                    else:
                        supply[corner] = math.fsum(
                            r["covered_value_thousand_USD2005"] / total_value * r[corner] ** power
                            for r in rows
                        )
                benefits = {}
                for corner in CORNERS:
                    if supply[corner] is None or not math.isfinite(supply[corner]) or supply[corner] <= 0:
                        benefits[corner] = None
                    else:
                        benefits[corner] = paired_surplus(
                            Market(es, ed, total_value, "thousand_USD2005"),
                            0.0, math.log(supply[corner])
                        )["total_surplus_change"]
                mechanically_admissible = not inadmissible and all(v is not None for v in benefits.values())
                precip_damage = temp_damage = joint_damage = closure = None
                if mechanically_admissible:
                    precip_benefit = 0.5 * ((benefits["y01"] - benefits["y00"]) +
                                            (benefits["y11"] - benefits["y10"]))
                    temp_benefit = 0.5 * ((benefits["y10"] - benefits["y00"]) +
                                          (benefits["y11"] - benefits["y01"]))
                    joint_benefit = benefits["y11"] - benefits["y00"]
                    precip_damage, temp_damage, joint_damage = (-precip_benefit, -temp_benefit, -joint_benefit)
                    closure = precip_damage + temp_damage - joint_damage

                key = case4 + (elasticity_id, mapping)
                prior_row = prior_cases[key]
                prior_damage = prior_row["global_market_damage_thousand_USD2005"]
                joint_difference = (joint_damage - prior_damage
                                    if joint_damage is not None and prior_damage is not None else None)
                results.append({
                    "crop_model": case4[0], "climate_model": case4[1],
                    "scenario": case4[2], "calendar": case4[3],
                    "adaptation": "fixed", "market_geography": "global",
                    "elasticity_id": elasticity_id, "supply_elasticity": es,
                    "demand_elasticity_magnitude": ed, "central_elasticity": central,
                    "yield_to_supply_mapping": mapping,
                    "valued_common_support_thousand_USD2005": total_value,
                    "missing_value_proxy_production_mt_not_dollars": state["missing_value_proxy_production_mt_not_dollars"],
                    "country_regime_count": len(rows),
                    "corner_supply_multipliers": supply,
                    "corner_total_surplus_benefit_thousand_USD2005": benefits,
                    "precipitation_shapley_damage_thousand_USD2005": precip_damage,
                    "temperature_shapley_damage_thousand_USD2005": temp_damage,
                    "joint_damage_thousand_USD2005": joint_damage,
                    "shapley_closure_error_thousand_USD2005": closure,
                    "prior_joint_global_damage_thousand_USD2005": prior_damage,
                    "joint_damage_minus_prior_thousand_USD2005": joint_difference,
                    "negative_cell_corners": state["negative_corners"],
                    "nonpositive_country_regime_corner_count": len(inadmissible),
                    "nonpositive_country_regime_corners": inadmissible,
                    "mechanically_admissible": mechanically_admissible,
                    "structural_damage_interpretation_authorized": False,
                })

    unique_ledgers = sorted({x["path"]: x for x in ledger_bindings}.values(), key=lambda x: x["path"])
    output = {
        "status": "four_corner_structural_welfare_attribution_complete",
        "case_count": len(results),
        "physical_case_count": len(physical_cases),
        "cases": results,
        "empirical_damage_authorized": False,
        "agriculture_replacement_authorized": False,
        "give_export_authorized": False,
        "scc_authorized": False,
        "limitations": [
            "two-driver Shapley attribution of structural crop-model output rather than empirical causal effect",
            "global maize market and covered common-support value only",
            "period-mean climate scenario contrast rather than annual emissions pulse",
            "negative crop-model cell corners retained and substantive interpretation disabled",
            "fixed management only; trend and upper adaptation not calibrated",
        ],
        "source_bindings": {
            "physical_result_sha256": digest(PHYSICAL),
            "country_cell_production_sha256": digest(CELLS),
            "baseline_value_ledger_sha256": digest(BASELINE),
            "prior_global_market_result_sha256": digest(PRIOR_GLOBAL),
            "price_registry_sha256": digest(PRICE),
            "market_code_sha256": digest(ROOT / "src/constant_elasticity_market.py"),
            "protocol_sha256": digest(PROTOCOL),
            "builder_sha256": digest(Path(__file__)),
            "physical_ledgers": unique_ledgers,
        },
    }
    if len(results) != 96:
        raise ValueError(f"expected 96 economic cases, found {len(results)}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
