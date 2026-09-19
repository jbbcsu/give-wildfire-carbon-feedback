#!/usr/bin/env python3
"""Independent source-to-result audit of the structural welfare benchmark."""
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
PRICE = ROOT / "config/price_basis_registry.toml"
MARKET_CODE = ROOT / "src/constant_elasticity_market.py"
PROTOCOL = ROOT / "STRUCTURAL_WELFARE_BENCHMARK_PROTOCOL_20260919.md"
BUILDER = ROOT / "scripts/build_structural_welfare_benchmark.py"
RESULT = ROOT / "data/interim/structural_welfare_benchmark_v2_20260919/result.json"
DEFAULT_OUTPUT = ROOT / "data/interim/structural_welfare_benchmark_validation_20260919/result.json"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def close(a: float | None, b: float | None, label: str, checks: list[str]) -> None:
    if a is None or b is None:
        if a is not b:
            raise AssertionError(f"{label}: {a!r} != {b!r}")
    elif not math.isclose(float(a), float(b), rel_tol=2e-12, abs_tol=1e-7):
        raise AssertionError(f"{label}: {a!r} != {b!r}")
    checks.append(label)


def exprel(x: float) -> float:
    return math.expm1(x) / x if x else 1.0


def independent_damage(value: float, es: float, ed: float, supply_shift: float) -> float:
    # At baseline shift zero, paired total surplus is V*h/(1+es)*exprel(z).
    z = -(1.0 - ed) * supply_shift / (es + ed)
    benefit = value * supply_shift / (1.0 + es) * exprel(z)
    return -benefit


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    physical = json.loads(RESPONSE.read_text())
    baseline = json.loads(BASELINE.read_text())
    result = json.loads(RESULT.read_text())
    with PRICE.open("rb") as f:
        price = tomllib.load(f)
    scalar = float(price["central_scalar"])
    checks: list[str] = []

    expected_bindings = {
        "physical_response_sha256": sha256(RESPONSE),
        "baseline_value_ledger_sha256": sha256(BASELINE),
        "price_registry_sha256": sha256(PRICE),
        "market_code_sha256": sha256(MARKET_CODE),
        "protocol_sha256": sha256(PROTOCOL),
        "builder_sha256": sha256(BUILDER),
    }
    if result["source_bindings"] != expected_bindings:
        raise AssertionError("source binding mismatch")
    checks.append("source_bindings")
    for flag in ("empirical_damage_authorized", "agriculture_replacement_authorized",
                 "give_export_authorized", "scc_authorized"):
        if result.get(flag) is not False:
            raise AssertionError(f"{flag} must be false")
        checks.append(flag)
    if result["case_count"] != 96 or len(result["cases"]) != 96:
        raise AssertionError("expected 96 result cases")
    checks.append("case_count")

    values = {(r["country"], r["regime"]): r for r in baseline["country_regime_rows"]}
    grouped: dict[tuple[str, str, str, str], list[dict]] = defaultdict(list)
    for row in physical["summaries"]:
        grouped[(row["crop_model"], row["climate_model"], row["scenario"], row["calendar"])].append(row)
    output_cases = {}
    for row in result["cases"]:
        key = (row["crop_model"], row["climate_model"], row["scenario"], row["calendar"],
               row["elasticity_id"], row["yield_to_supply_mapping"])
        if key in output_cases:
            raise AssertionError(f"duplicate case {key}")
        output_cases[key] = row

    for case4, rows in grouped.items():
        by_country: dict[str, list[dict]] = defaultdict(list)
        for row in rows:
            by_country[row["country"]].append(row)
        for elasticity_id, es, ed in (
            ("hultgren_pair_008_002", 0.08, 0.02),
            ("hultgren_pair_010_004", 0.10, 0.04),
            ("hultgren_pair_050_006", 0.50, 0.06),
        ):
            for mapping in ("horizontal_output", "fixed_input_cost"):
                key = case4 + (elasticity_id, mapping)
                out = output_cases[key]
                damage = value_total = invalid_value = missing_prod = 0.0
                invalid = missing = valued_n = 0
                changes = []
                min_supply = None
                min_country = None
                for country, country_rows in sorted(by_country.items()):
                    parts = []
                    country_missing = False
                    production = 0.0
                    for row in country_rows:
                        production += float(row["common_production_mt"])
                        ledger = values[(country, row["regime"])]
                        raw_value = ledger["common_response_value_proxy_thousand_constant_2014_2016_USD"]
                        if raw_value is None:
                            country_missing = True
                            continue
                        parts.append((float(raw_value) * scalar,
                                      1.0 + float(row["effects"]["joint"]["conditional_country_percent"]) / 100.0))
                    if country_missing or not parts:
                        missing += 1
                        missing_prod += production
                        continue
                    country_value = sum(v for v, _ in parts)
                    if any(not math.isfinite(a) or a <= 0 for _, a in parts):
                        invalid += 1
                        invalid_value += country_value
                        continue
                    power = 1.0 if mapping == "horizontal_output" else 1.0 + es
                    supply = sum((v / country_value) * a**power for v, a in parts)
                    shift = math.log(supply)
                    country_damage = independent_damage(country_value, es, ed, shift)
                    damage += country_damage
                    value_total += country_value
                    valued_n += 1
                    changes.append((country, country_damage))
                    if min_supply is None or supply < min_supply:
                        min_supply, min_country = supply, country

                absolute_sum = sum(abs(v) for _, v in changes)
                largest_country, largest_damage = max(changes, key=lambda x: abs(x[1]), default=(None, None))
                close(out["valid_subset_damage_thousand_USD2005"], damage, f"{key}:damage", checks)
                close(out["valid_subset_total_surplus_change_thousand_USD2005"], -damage,
                      f"{key}:surplus", checks)
                close(out["valued_common_support_thousand_USD2005"], value_total, f"{key}:value", checks)
                close(out["invalid_response_common_support_thousand_USD2005"], invalid_value,
                      f"{key}:invalid_value", checks)
                close(out["missing_value_proxy_production_mt_not_dollars"], missing_prod,
                      f"{key}:missing_production", checks)
                close(out["minimum_market_supply_multiplier"], min_supply, f"{key}:minimum_supply", checks)
                close(out["largest_absolute_country_damage_thousand_USD2005"], largest_damage,
                      f"{key}:largest_damage", checks)
                expected_share = abs(largest_damage) / absolute_sum if absolute_sum else None
                close(out["largest_absolute_country_share_of_absolute_changes"], expected_share,
                      f"{key}:concentration", checks)
                for name, expected in (
                    ("valued_country_count", valued_n),
                    ("missing_value_country_count", missing),
                    ("invalid_response_country_count", invalid),
                    ("all_valued_country_responses_log_admissible", invalid == 0),
                    ("minimum_market_supply_multiplier_country", min_country),
                    ("largest_absolute_country_damage_country", largest_country),
                    ("structural_damage_interpretation_authorized", False),
                ):
                    if out[name] != expected:
                        raise AssertionError(f"{key}:{name}: {out[name]!r} != {expected!r}")
                    checks.append(f"{key}:{name}")

    # Independent synthetic direction, identity and mapping checks.
    close(independent_damage(100.0, 0.1, 0.04, 0.0), 0.0, "synthetic_zero", checks)
    if independent_damage(100.0, 0.1, 0.04, math.log(1.1)) >= 0:
        raise AssertionError("positive productivity must be a benefit")
    checks.append("synthetic_positive_productivity")
    if independent_damage(100.0, 0.1, 0.04, 1.1 * math.log(0.9)) <= independent_damage(
        100.0, 0.1, 0.04, math.log(0.9)
    ):
        raise AssertionError("fixed-input mapping must amplify a negative shock")
    checks.append("synthetic_mapping_order")

    audit = {
        "status": "passed",
        "check_count": len(checks),
        "case_count": len(output_cases),
        "maximum_reported_damage_thousand_USD2005": max(
            c["valid_subset_damage_thousand_USD2005"] for c in result["cases"]
        ),
        "minimum_reported_market_supply_multiplier": min(
            c["minimum_market_supply_multiplier"] for c in result["cases"]
            if c["minimum_market_supply_multiplier"] is not None
        ),
        "structural_damage_interpretation_authorized": False,
        "give_export_authorized": False,
        "scc_authorized": False,
        "validated_result_sha256": sha256(RESULT),
        "validator_sha256": sha256(Path(__file__)),
        "source_bindings": expected_bindings,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
