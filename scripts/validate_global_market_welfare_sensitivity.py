#!/usr/bin/env python3
"""Independent audit of the global-market structural welfare sensitivity."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path
import tomllib

ROOT = Path(__file__).resolve().parents[1]
RESPONSE = ROOT / "data/interim/epic_caraib_geography_20260908/result.json"
BASELINE = ROOT / "data/interim/welfare_baseline_ledger_20260914_v2/result.json"
COUNTRY = ROOT / "data/interim/structural_welfare_benchmark_v2_20260919/result.json"
PRICE = ROOT / "config/price_basis_registry.toml"
PROTOCOL = ROOT / "GLOBAL_MARKET_WELFARE_SENSITIVITY_PROTOCOL_20260919.md"
BUILDER = ROOT / "scripts/build_global_market_welfare_sensitivity.py"
RESULT = ROOT / "data/interim/global_market_welfare_sensitivity_20260919/result.json"
DEFAULT_OUTPUT = ROOT / "data/interim/global_market_welfare_sensitivity_validation_20260919/result.json"


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def close(a, b, label, checks):
    if a is None or b is None:
        if a is not b:
            raise AssertionError(f"{label}: {a!r} != {b!r}")
    elif not math.isclose(float(a), float(b), rel_tol=2e-12, abs_tol=1e-7):
        raise AssertionError(f"{label}: {a!r} != {b!r}")
    checks.append(label)


def damage(value, es, ed, shift):
    z = -(1.0 - ed) * shift / (es + ed)
    ratio = math.expm1(z) / z if z else 1.0
    return -value * shift / (1.0 + es) * ratio


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    physical = json.loads(RESPONSE.read_text())
    baseline = json.loads(BASELINE.read_text())
    country = json.loads(COUNTRY.read_text())
    result = json.loads(RESULT.read_text())
    with PRICE.open("rb") as f:
        scalar = float(tomllib.load(f)["central_scalar"])
    checks = []

    expected_bindings = {
        "physical_response_sha256": digest(RESPONSE),
        "baseline_value_ledger_sha256": digest(BASELINE),
        "country_market_result_sha256": digest(COUNTRY),
        "price_registry_sha256": digest(PRICE),
        "market_code_sha256": digest(ROOT / "src/constant_elasticity_market.py"),
        "protocol_sha256": digest(PROTOCOL),
        "builder_sha256": digest(BUILDER),
    }
    if result["source_bindings"] != expected_bindings:
        raise AssertionError("source binding mismatch")
    checks.append("source_bindings")
    if result["case_count"] != 96 or len(result["cases"]) != 96:
        raise AssertionError("case count mismatch")
    checks.append("case_count")
    for flag in ("empirical_damage_authorized", "agriculture_replacement_authorized",
                 "give_export_authorized", "scc_authorized"):
        if result[flag] is not False:
            raise AssertionError(f"{flag} must be false")
        checks.append(flag)

    values = {(r["country"], r["regime"]): r for r in baseline["country_regime_rows"]}
    grouped = defaultdict(list)
    for row in physical["summaries"]:
        grouped[(row["crop_model"], row["climate_model"], row["scenario"], row["calendar"])].append(row)
    country_cases = {
        (r["crop_model"], r["climate_model"], r["scenario"], r["calendar"],
         r["elasticity_id"], r["yield_to_supply_mapping"]): r
        for r in country["cases"]
    }
    outputs = {
        (r["crop_model"], r["climate_model"], r["scenario"], r["calendar"],
         r["elasticity_id"], r["yield_to_supply_mapping"]): r
        for r in result["cases"]
    }
    if len(outputs) != 96:
        raise AssertionError("duplicate output case")

    for case4, rows in grouped.items():
        for elasticity_id, es, ed in (
            ("hultgren_pair_008_002", 0.08, 0.02),
            ("hultgren_pair_010_004", 0.10, 0.04),
            ("hultgren_pair_050_006", 0.50, 0.06),
        ):
            for mapping in ("horizontal_output", "fixed_input_cost"):
                key = case4 + (elasticity_id, mapping)
                out = outputs[key]
                parts = []
                missing = 0.0
                invalid = []
                for row in rows:
                    source = values[(row["country"], row["regime"])]
                    raw = source["common_response_value_proxy_thousand_constant_2014_2016_USD"]
                    if raw is None:
                        missing += float(row["common_production_mt"])
                        continue
                    value = float(raw) * scalar
                    mult = 1.0 + float(row["effects"]["joint"]["conditional_country_percent"]) / 100.0
                    parts.append((row["country"], row["regime"], value, mult))
                    if not math.isfinite(mult) or mult <= 0:
                        invalid.append((row["country"], row["regime"]))
                total = sum(x[2] for x in parts)
                minimum = min(x[3] for x in parts)
                min_row = next(x for x in parts if x[3] == minimum)
                admissible = not invalid
                supply = global_damage = None
                if admissible:
                    power = 1.0 if mapping == "horizontal_output" else 1.0 + es
                    supply = sum(value / total * mult**power for _, _, value, mult in parts)
                    global_damage = damage(total, es, ed, math.log(supply))
                country_damage = float(country_cases[key]["valid_subset_damage_thousand_USD2005"])
                close(out["valued_common_support_thousand_USD2005"], total, f"{key}:value", checks)
                close(out["missing_value_proxy_production_mt_not_dollars"], missing,
                      f"{key}:missing", checks)
                close(out["minimum_regime_productivity_multiplier"], minimum, f"{key}:min", checks)
                close(out["global_market_supply_multiplier"], supply, f"{key}:supply", checks)
                close(out["global_market_damage_thousand_USD2005"], global_damage,
                      f"{key}:global_damage", checks)
                close(out["country_market_valid_subset_damage_thousand_USD2005"], country_damage,
                      f"{key}:country_damage", checks)
                difference = global_damage - country_damage if global_damage is not None else None
                ratio = global_damage / country_damage if global_damage is not None and country_damage else None
                close(out["global_minus_country_damage_thousand_USD2005"], difference,
                      f"{key}:difference", checks)
                close(out["global_to_country_damage_ratio"], ratio, f"{key}:ratio", checks)
                exact = {
                    "invalid_response_count": len(invalid),
                    "global_market_log_admissible": admissible,
                    "minimum_regime_productivity_identity": {"country": min_row[0], "regime": min_row[1]},
                    "structural_damage_interpretation_authorized": False,
                }
                for name, expected in exact.items():
                    if out[name] != expected:
                        raise AssertionError(f"{key}:{name}: {out[name]!r} != {expected!r}")
                    checks.append(f"{key}:{name}")

    # Synthetic aggregation: offsetting equal-value supply multipliers are
    # combined before equilibrium, not summed as two market welfare changes.
    a, b = 0.8, 1.2
    supply = 0.5 * a + 0.5 * b
    close(damage(100.0, 0.1, 0.04, math.log(supply)), 0.0, "synthetic_offset", checks)
    separate = damage(50.0, 0.1, 0.04, math.log(a)) + damage(50.0, 0.1, 0.04, math.log(b))
    if math.isclose(separate, 0.0, abs_tol=1e-9):
        raise AssertionError("separate nonlinear markets should not cancel exactly")
    checks.append("synthetic_geography_noncommutation")

    audit = {
        "status": "passed",
        "check_count": len(checks),
        "case_count": len(outputs),
        "admissible_case_count": sum(r["global_market_log_admissible"] for r in result["cases"]),
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
