#!/usr/bin/env python3
"""Recompute four-corner welfare on one fixed all-case positive support."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path
import sys
import tomllib

import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.constant_elasticity_market import Market, paired_surplus  # noqa: E402

PHYSICAL = ROOT / "data/interim/epic_caraib_global_comparison_20260908/result.json"
CELLS = ROOT / "data/interim/epic_caraib_geography_20260908/country_cell_production.parquet"
AREA = ROOT / "data/interim/epic_caraib_global_comparison_20260908/common_area_support.parquet"
BASELINE = ROOT / "data/interim/welfare_baseline_ledger_20260914_v2/result.json"
COVERAGE = ROOT / "data/interim/fixed_positive_crop_support_20260919/result.json"
FULL = ROOT / "data/interim/four_corner_welfare_attribution_20260919/result.json"
PRICE = ROOT / "config/price_basis_registry.toml"
PROTOCOL = ROOT / "FIXED_POSITIVE_WELFARE_SENSITIVITY_PROTOCOL_20260919.md"
DEFAULT_OUTPUT = ROOT / "data/interim/fixed_positive_welfare_sensitivity_20260919/result.json"
CORNERS = ("y00", "y10", "y01", "y11")
ELASTICITIES = (("hultgren_pair_008_002", .08, .02, False),
                ("hultgren_pair_010_004", .10, .04, True),
                ("hultgren_pair_050_006", .50, .06, False))


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    physical = json.loads(PHYSICAL.read_text())
    baseline = json.loads(BASELINE.read_text())
    coverage = json.loads(COVERAGE.read_text())
    full = json.loads(FULL.read_text())
    with PRICE.open("rb") as f:
        scalar = float(tomllib.load(f)["central_scalar"])

    area = pq.read_table(AREA).to_pandas()
    area = area.loc[area.common_response, ["latitude", "longitude", "regime", "area_ha"]]
    mask = area[["latitude", "longitude", "regime"]].copy()
    mask["retain"] = True
    ledger_bindings = []
    for summary in physical["summaries"]:
        path = ROOT / summary["ledger_path"]
        if digest(path) != summary["ledger_sha256"]:
            raise ValueError("physical ledger hash mismatch")
        ledger_bindings.append({"path": summary["ledger_path"], "sha256": summary["ledger_sha256"]})
        frame = pq.read_table(path, columns=["latitude", "longitude", *CORNERS]).to_pandas()
        idx = mask.index[mask.regime == summary["regime"]]
        joined = mask.loc[idx, ["latitude", "longitude"]].merge(
            frame, on=["latitude", "longitude"], how="left", validate="one_to_one", sort=False
        )
        good = joined[list(CORNERS)].map(math.isfinite).all(axis=1) & (joined[list(CORNERS)] > 0).all(axis=1)
        mask.loc[idx, "retain"] &= good.to_numpy()
    mask = mask.merge(area, on=["latitude", "longitude", "regime"], validate="one_to_one")

    cells = pq.read_table(CELLS).to_pandas()
    cells = cells.loc[cells.common_response & (cells.production_mt > 0),
                      ["country", "latitude", "longitude", "regime", "production_mt"]]
    cells = cells.merge(mask[["latitude", "longitude", "regime", "retain"]],
                        on=["latitude", "longitude", "regime"], validate="many_to_one")
    original_den = cells.groupby(["country", "regime"]).production_mt.sum().to_dict()
    retained = cells.loc[cells.retain].copy()
    retained_den = retained.groupby(["country", "regime"]).production_mt.sum().to_dict()
    value_rows = {(r["country"], r["regime"]): r for r in baseline["country_regime_rows"]}

    full_cases = {(r["crop_model"], r["climate_model"], r["scenario"], r["calendar"],
                   r["elasticity_id"], r["yield_to_supply_mapping"]): r for r in full["cases"]}
    grouped = defaultdict(list)
    for row in physical["summaries"]:
        grouped[(row["crop_model"], row["climate_model"], row["scenario"], row["calendar"])].append(row)
    physical_states = {}
    for case4, summaries in grouped.items():
        rows = []
        missing_prod = 0.0
        for summary in summaries:
            ledger = pq.read_table(ROOT / summary["ledger_path"],
                                   columns=["latitude", "longitude", *CORNERS]).to_pandas()
            joined = retained.loc[retained.regime == summary["regime"]].merge(
                ledger, on=["latitude", "longitude"], validate="many_to_one")
            for country, group in joined.groupby("country", sort=True):
                key = (country, summary["regime"])
                source = value_rows[key]
                raw = source["common_response_value_proxy_thousand_constant_2014_2016_USD"]
                retained_prod = math.fsum(group.production_mt.tolist())
                if raw is None:
                    missing_prod += retained_prod
                    continue
                value = float(raw) * scalar * retained_prod / original_den[key]
                record = {"country": country, "regime": summary["regime"], "value": value}
                for corner in CORNERS:
                    record[corner] = math.fsum(
                        (group.production_mt * group[corner] / group.y00).tolist()
                    ) / retained_prod
                    if not math.isfinite(record[corner]) or record[corner] <= 0:
                        raise ValueError("fixed-positive country/regime aggregate is not positive")
                rows.append(record)
        physical_states[case4] = {"rows": rows, "missing_production": missing_prod}

    results = []
    for case4, state in sorted(physical_states.items()):
        rows = state["rows"]
        total = math.fsum(r["value"] for r in rows)
        for elasticity_id, es, ed, central in ELASTICITIES:
            for mapping in ("horizontal_output", "fixed_input_cost"):
                power = 1.0 if mapping == "horizontal_output" else 1.0 + es
                supply = {corner: math.fsum(r["value"] / total * r[corner]**power for r in rows)
                          for corner in CORNERS}
                benefits = {corner: paired_surplus(Market(es, ed, total, "thousand_USD2005"),
                                                   0.0, math.log(supply[corner]))["total_surplus_change"]
                            for corner in CORNERS}
                precip = -0.5*((benefits["y01"]-benefits["y00"]) +
                               (benefits["y11"]-benefits["y10"]))
                temp = -0.5*((benefits["y10"]-benefits["y00"]) +
                             (benefits["y11"]-benefits["y01"]))
                joint = -(benefits["y11"]-benefits["y00"])
                closure = precip + temp - joint
                key = case4 + (elasticity_id, mapping)
                prior = full_cases[key]
                results.append({
                    "crop_model": case4[0], "climate_model": case4[1],
                    "scenario": case4[2], "calendar": case4[3],
                    "adaptation": "fixed", "market_geography": "global",
                    "support": "fixed_both_model_all_case_positive_partial",
                    "elasticity_id": elasticity_id, "supply_elasticity": es,
                    "demand_elasticity_magnitude": ed, "central_elasticity": central,
                    "yield_to_supply_mapping": mapping,
                    "valued_retained_support_thousand_USD2005": total,
                    "missing_value_proxy_retained_production_mt_not_dollars": state["missing_production"],
                    "country_regime_count": len(rows),
                    "corner_supply_multipliers": supply,
                    "precipitation_shapley_damage_thousand_USD2005": precip,
                    "temperature_shapley_damage_thousand_USD2005": temp,
                    "joint_damage_thousand_USD2005": joint,
                    "shapley_closure_error_thousand_USD2005": closure,
                    "full_support_precipitation_damage_thousand_USD2005": prior["precipitation_shapley_damage_thousand_USD2005"],
                    "full_support_temperature_damage_thousand_USD2005": prior["temperature_shapley_damage_thousand_USD2005"],
                    "full_support_joint_damage_thousand_USD2005": prior["joint_damage_thousand_USD2005"],
                    "restricted_minus_full_precipitation_damage_thousand_USD2005": (
                        precip-prior["precipitation_shapley_damage_thousand_USD2005"]
                        if prior["precipitation_shapley_damage_thousand_USD2005"] is not None else None),
                    "restricted_minus_full_temperature_damage_thousand_USD2005": (
                        temp-prior["temperature_shapley_damage_thousand_USD2005"]
                        if prior["temperature_shapley_damage_thousand_USD2005"] is not None else None),
                    "restricted_minus_full_joint_damage_thousand_USD2005": (
                        joint-prior["joint_damage_thousand_USD2005"]
                        if prior["joint_damage_thousand_USD2005"] is not None else None),
                    "mechanically_admissible": True,
                    "partial_support_only": True,
                    "structural_damage_interpretation_authorized": False,
                })

    coverage_all = next(r for r in coverage["summaries"]
                        if r["mask"] == "both_models_positive" and r["regime"] == "all")
    if not math.isclose(results[0]["valued_retained_support_thousand_USD2005"],
                        coverage_all["retained_covered_value_thousand_USD2005"], rel_tol=2e-12):
        raise ValueError("retained value does not reconcile to coverage audit")
    output = {
        "status": "fixed_positive_partial_support_welfare_sensitivity_complete",
        "case_count": len(results), "physical_case_count": len(physical_states),
        "coverage": coverage_all, "cases": results,
        "crop_model_repaired": False, "partial_support_only": True,
        "empirical_damage_authorized": False, "agriculture_replacement_authorized": False,
        "give_export_authorized": False, "scc_authorized": False,
        "source_bindings": {
            "physical_result_sha256": digest(PHYSICAL),
            "country_cell_production_sha256": digest(CELLS),
            "common_area_support_sha256": digest(AREA),
            "baseline_value_ledger_sha256": digest(BASELINE),
            "fixed_support_audit_sha256": digest(COVERAGE),
            "full_support_attribution_sha256": digest(FULL),
            "price_registry_sha256": digest(PRICE),
            "market_code_sha256": digest(ROOT / "src/constant_elasticity_market.py"),
            "protocol_sha256": digest(PROTOCOL), "builder_sha256": digest(Path(__file__)),
            "physical_ledgers": sorted({x["path"]: x for x in ledger_bindings}.values(), key=lambda x:x["path"]),
        },
    }
    if len(results) != 96:
        raise ValueError("expected 96 cases")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
