#!/usr/bin/env python3
"""Independent audit of the four-corner structural welfare attribution."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path
import tomllib

import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
PHYSICAL = ROOT / "data/interim/epic_caraib_global_comparison_20260908/result.json"
CELLS = ROOT / "data/interim/epic_caraib_geography_20260908/country_cell_production.parquet"
BASELINE = ROOT / "data/interim/welfare_baseline_ledger_20260914_v2/result.json"
PRIOR_GLOBAL = ROOT / "data/interim/global_market_welfare_sensitivity_20260919/result.json"
PRICE = ROOT / "config/price_basis_registry.toml"
PROTOCOL = ROOT / "FOUR_CORNER_WELFARE_ATTRIBUTION_PROTOCOL_20260919.md"
BUILDER = ROOT / "scripts/build_four_corner_welfare_attribution.py"
RESULT = ROOT / "data/interim/four_corner_welfare_attribution_20260919/result.json"
DEFAULT_OUTPUT = ROOT / "data/interim/four_corner_welfare_attribution_validation_20260919/result.json"
CORNERS = ("y00", "y10", "y01", "y11")


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def close(a, b, label, checks, rel=3e-12, abs_=1e-6):
    if a is None or b is None:
        if a is not b:
            raise AssertionError(f"{label}: {a!r} != {b!r}")
    elif not math.isclose(float(a), float(b), rel_tol=rel, abs_tol=abs_):
        raise AssertionError(f"{label}: {a!r} != {b!r}")
    checks.append(label)


def benefit(value, es, ed, supply):
    shift = math.log(supply)
    z = -(1.0 - ed) * shift / (es + ed)
    ratio = math.expm1(z) / z if z else 1.0
    return value * shift / (1.0 + es) * ratio


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    physical = json.loads(PHYSICAL.read_text())
    baseline = json.loads(BASELINE.read_text())
    prior = json.loads(PRIOR_GLOBAL.read_text())
    result = json.loads(RESULT.read_text())
    with PRICE.open("rb") as f:
        scalar = float(tomllib.load(f)["central_scalar"])
    checks = []

    ledger_bindings = sorted(
        {r["ledger_path"]: {"path": r["ledger_path"], "sha256": r["ledger_sha256"]}
         for r in physical["summaries"]}.values(), key=lambda x: x["path"]
    )
    expected_bindings = {
        "physical_result_sha256": digest(PHYSICAL),
        "country_cell_production_sha256": digest(CELLS),
        "baseline_value_ledger_sha256": digest(BASELINE),
        "prior_global_market_result_sha256": digest(PRIOR_GLOBAL),
        "price_registry_sha256": digest(PRICE),
        "market_code_sha256": digest(ROOT / "src/constant_elasticity_market.py"),
        "protocol_sha256": digest(PROTOCOL),
        "builder_sha256": digest(BUILDER),
        "physical_ledgers": ledger_bindings,
    }
    if result["source_bindings"] != expected_bindings:
        raise AssertionError("source bindings differ")
    checks.append("source_bindings")
    if result["case_count"] != 96 or len(result["cases"]) != 96:
        raise AssertionError("case count differs")
    checks.append("case_count")
    for flag in ("empirical_damage_authorized", "agriculture_replacement_authorized",
                 "give_export_authorized", "scc_authorized"):
        if result[flag] is not False:
            raise AssertionError(f"{flag} must remain false")
        checks.append(flag)

    cell = pq.read_table(CELLS).to_pandas()
    cell = cell.loc[cell.common_response & (cell.production_mt > 0),
                    ["country", "regime", "latitude", "longitude", "production_mt"]]
    values = {(r["country"], r["regime"]): r for r in baseline["country_regime_rows"]}
    grouped = defaultdict(list)
    for row in physical["summaries"]:
        grouped[(row["crop_model"], row["climate_model"], row["scenario"], row["calendar"])].append(row)
    prior_cases = {
        (r["crop_model"], r["climate_model"], r["scenario"], r["calendar"],
         r["elasticity_id"], r["yield_to_supply_mapping"]): r
        for r in prior["cases"]
    }
    outputs = {
        (r["crop_model"], r["climate_model"], r["scenario"], r["calendar"],
         r["elasticity_id"], r["yield_to_supply_mapping"]): r
        for r in result["cases"]
    }
    if len(outputs) != 96:
        raise AssertionError("duplicate output cases")

    states = {}
    for case4, summaries in grouped.items():
        rows = []
        missing = 0.0
        negative = {c: {"cell_count": 0, "production_mt": 0.0,
                        "covered_value_proxy_thousand_USD2005": 0.0} for c in CORNERS}
        for summary in summaries:
            source = cell.loc[cell.regime == summary["regime"]]
            ledger = pq.read_table(ROOT / summary["ledger_path"],
                                   columns=["latitude", "longitude", "baseline_tDM_ha",
                                            "y00", "y10", "y01", "y11"]).to_pandas()
            joined = source.merge(ledger, on=["latitude", "longitude"], how="left", validate="many_to_one")
            for country, group in joined.groupby("country", sort=True):
                value_source = values[(country, summary["regime"])][
                    "common_response_value_proxy_thousand_constant_2014_2016_USD"]
                production = math.fsum(group.production_mt.tolist())
                if value_source is None:
                    missing += production
                    continue
                value = float(value_source) * scalar
                record = {"country": country, "regime": summary["regime"], "value": value}
                for corner in CORNERS:
                    record[corner] = math.fsum(
                        (group.production_mt * group[corner] / group.y00).tolist()
                    ) / production
                    bad = group[corner] <= 0
                    if bad.any():
                        bad_prod = math.fsum(group.loc[bad, "production_mt"].tolist())
                        negative[corner]["cell_count"] += int(bad.sum())
                        negative[corner]["production_mt"] += bad_prod
                        negative[corner]["covered_value_proxy_thousand_USD2005"] += value * bad_prod / production
                rows.append(record)
        states[case4] = (rows, missing, negative)

    for case4, (rows, missing, negative) in states.items():
        total = math.fsum(r["value"] for r in rows)
        for elasticity_id, es, ed in (
            ("hultgren_pair_008_002", 0.08, 0.02),
            ("hultgren_pair_010_004", 0.10, 0.04),
            ("hultgren_pair_050_006", 0.50, 0.06),
        ):
            for mapping in ("horizontal_output", "fixed_input_cost"):
                key = case4 + (elasticity_id, mapping)
                out = outputs[key]
                power = 1.0 if mapping == "horizontal_output" else 1.0 + es
                supply, benefits, invalid = {}, {}, []
                for corner in CORNERS:
                    bad = [r for r in rows if not math.isfinite(r[corner]) or r[corner] <= 0]
                    if bad:
                        invalid.extend((corner, r["country"], r["regime"]) for r in bad)
                        supply[corner] = benefits[corner] = None
                    else:
                        supply[corner] = math.fsum(r["value"] / total * r[corner] ** power for r in rows)
                        benefits[corner] = benefit(total, es, ed, supply[corner])
                admissible = not invalid
                p = t = j = closure = None
                if admissible:
                    p = -0.5 * ((benefits["y01"] - benefits["y00"]) +
                                (benefits["y11"] - benefits["y10"]))
                    t = -0.5 * ((benefits["y10"] - benefits["y00"]) +
                                (benefits["y11"] - benefits["y01"]))
                    j = -(benefits["y11"] - benefits["y00"])
                    closure = p + t - j
                prior_damage = prior_cases[key]["global_market_damage_thousand_USD2005"]
                comparisons = (
                    ("valued_common_support_thousand_USD2005", total),
                    ("missing_value_proxy_production_mt_not_dollars", missing),
                    ("precipitation_shapley_damage_thousand_USD2005", p),
                    ("temperature_shapley_damage_thousand_USD2005", t),
                    ("joint_damage_thousand_USD2005", j),
                    ("shapley_closure_error_thousand_USD2005", closure),
                    ("prior_joint_global_damage_thousand_USD2005", prior_damage),
                    ("joint_damage_minus_prior_thousand_USD2005",
                     j - prior_damage if j is not None and prior_damage is not None else None),
                )
                for name, expected in comparisons:
                    close(out[name], expected, f"{key}:{name}", checks)
                for corner in CORNERS:
                    close(out["corner_supply_multipliers"][corner], supply[corner],
                          f"{key}:{corner}:supply", checks)
                    close(out["corner_total_surplus_benefit_thousand_USD2005"][corner], benefits[corner],
                          f"{key}:{corner}:benefit", checks)
                    for field in ("cell_count", "production_mt", "covered_value_proxy_thousand_USD2005"):
                        close(out["negative_cell_corners"][corner][field], negative[corner][field],
                              f"{key}:{corner}:{field}", checks)
                exact = {
                    "country_regime_count": len(rows),
                    "nonpositive_country_regime_corner_count": len(invalid),
                    "mechanically_admissible": admissible,
                    "structural_damage_interpretation_authorized": False,
                }
                for name, expected in exact.items():
                    if out[name] != expected:
                        raise AssertionError(f"{key}:{name}: {out[name]!r} != {expected!r}")
                    checks.append(f"{key}:{name}")

    # A synthetic additive benefit surface must assign each driver its own arm.
    b00, b10, b01, b11 = 0.0, -3.0, 2.0, -1.0
    p = 0.5 * ((b01 - b00) + (b11 - b10))
    t = 0.5 * ((b10 - b00) + (b11 - b01))
    close(p, 2.0, "synthetic_precipitation", checks)
    close(t, -3.0, "synthetic_temperature", checks)
    close(p + t, b11 - b00, "synthetic_closure", checks)

    audit = {
        "status": "passed",
        "check_count": len(checks),
        "case_count": len(outputs),
        "mechanically_admissible_case_count": sum(r["mechanically_admissible"] for r in result["cases"]),
        "validated_result_sha256": digest(RESULT),
        "validator_sha256": digest(Path(__file__)),
        "source_bindings": expected_bindings,
        "structural_damage_interpretation_authorized": False,
        "give_export_authorized": False,
        "scc_authorized": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
