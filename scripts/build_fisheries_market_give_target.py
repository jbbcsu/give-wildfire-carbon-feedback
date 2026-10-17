#!/usr/bin/env python3
"""Build a fail-closed GIVE target record from the Blue-SCC market benchmark.

Only the pulse denominator and price-level basis are mechanically harmonized.
The output remains non-additive because discounting, socioeconomic draws, and
welfare semantics cannot be harmonized from terminal SCC summaries.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
from pathlib import Path
from typing import Any


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_tree(root: Path, expected_commit: str | None, files: dict[str, str], label: str) -> None:
    if expected_commit:
        commit = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"], check=True,
            text=True, capture_output=True,
        ).stdout.strip()
        require(commit == expected_commit, f"{label} commit changed")
    for relative, digest in files.items():
        path = root / relative
        require(path.is_file() and not path.is_symlink(), f"{label} source absent or symlinked: {relative}")
        require(sha256(path) == digest, f"{label} source hash changed: {relative}")


def require_tokens(path: Path, tokens: list[str]) -> None:
    text = path.read_text(encoding="utf-8")
    missing = [token for token in tokens if token not in text]
    require(not missing, f"{path.name} method evidence changed: {missing}")


def harmonize(config: dict[str, Any], benchmark: dict[str, Any]) -> dict[str, Any]:
    source = config["source_conventions"]
    target = config["give_target_conventions"]
    require(source["pulse_year"] == target["pulse_year"] == 2020, "pulse years do not match")
    require(source["output_unit"] == target["output_unit"] == "2020_USD_per_tCO2", "SCC output units do not match")
    target_pulse_tco2 = target["pulse_size_gtc"] * 1e9 * target["carbon_to_co2_ratio"]
    require(target_pulse_tco2 > 0 and source["pulse_size_tco2"] > 0, "pulse sizes must be positive")
    # Both source and target divide the response by physical tCO2.  Pulse-size
    # differences therefore require no scalar conversion, conditional on local
    # linearity; the source release contains no pulse-convergence experiment.
    pulse_unit_factor = 1.0
    currency_factor = (
        target["deflator_2005_numerator"] / target["deflator_2005_denominator"]
    ) / (
        source["deflator_2005_numerator"] / source["deflator_2005_denominator"]
    )
    result = benchmark["result"]
    market = result["published_monte_carlo_usd_per_tco2"]["market"]
    baseline = result["published_deterministic_baseline_usd_per_tco2"]["market"]
    scenarios = {
        "published_mc_p05": market["p05"] * currency_factor,
        "published_mc_median": market["median"] * currency_factor,
        "published_mc_p95": market["p95"] * currency_factor,
        "published_deterministic": baseline * currency_factor,
    }
    require(all(math.isfinite(value) and value >= 0 for value in scenarios.values()), "harmonized benchmark is invalid")
    discount_match = (
        math.isclose(source["deterministic_prtp"], target["prtp"], abs_tol=1e-15)
        and math.isclose(source["deterministic_eta"], target["eta"], abs_tol=1e-15)
    )
    target_inside_mc_support = (
        source["mc_prtp_min"] <= target["prtp"] <= source["mc_prtp_max"]
        and source["mc_eta_min"] <= target["eta"] <= source["mc_eta_max"]
    )
    welfare_match = config["accounting_boundary"]["source_measure"] == config["accounting_boundary"]["required_give_measure"]
    reason_codes = []
    if not discount_match:
        reason_codes.append("discount_parameters_not_matched")
    if not target_inside_mc_support:
        reason_codes.append("give_discount_target_outside_joint_mc_support")
    if not welfare_match:
        reason_codes.append("profit_output_multiplier_is_not_direct_consumer_plus_producer_surplus")
    reason_codes += [
        "terminal_scc_has_no_annual_damage_path",
        "source_pulse_linearity_not_tested",
        "source_draws_not_coupled_to_give_climate_or_socioeconomic_draws",
        "source_repository_has_no_explicit_root_license",
    ]
    return {
        "harmonization": {
            "source_pulse_year": source["pulse_year"],
            "give_pulse_year": target["pulse_year"],
            "source_pulse_tco2": source["pulse_size_tco2"],
            "give_pulse_tco2": target_pulse_tco2,
            "per_tco2_unit_factor": pulse_unit_factor,
            "source_to_give_price_basis_factor": currency_factor,
            "pulse_year_match": True,
            "per_tco2_unit_match": True,
            "discount_parameters_match": discount_match,
            "give_discount_target_inside_source_mc_support": target_inside_mc_support,
            "welfare_measure_match": welfare_match,
        },
        "market_external_sensitivity_2020_usd_per_tco2": scenarios,
        "target_interface": {
            "component": "fisheries_market_only",
            "value_role": "external_terminal_scc_sensitivity",
            "additive_eligible": False,
            "annual_damage_path_available": False,
            "draw_coupling_available": False,
            "reason_codes": reason_codes,
        },
        "nutrition_nonmarket": {
            "role": "nonadditive_literature_bound",
            "included_in_market_sensitivity": False,
            "overlap_status": "unresolved_with_give_mortality",
        },
    }


def build(config_path: Path, benchmark_path: Path, blue_root: Path, rice_root: Path, give_root: Path) -> dict[str, Any]:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    require(config.get("contract_id") == "fisheries_market_give_target_v1", "wrong contract")
    receipt = config["source_benchmark_receipt"]
    require(sha256(benchmark_path) == receipt["sha256"], "benchmark receipt hash changed")
    benchmark = json.loads(benchmark_path.read_text(encoding="utf-8"))
    require(benchmark.get("status") == "passed_published_external_benchmark_only", "benchmark gate did not pass")
    sources = config["source_code"]
    verify_tree(blue_root, sources["blue_scc_commit"], sources["blue_scc_files"], "Blue-SCC")
    verify_tree(rice_root, sources["rice50x_commit"], sources["rice50x_files"], "RICE50x")
    verify_tree(give_root, None, sources["give_files"], "GIVE")
    require_tokens(blue_root / "Code/SCC/utils.py", [
        "/ 1e6  # divide by 1e6 because pulse is one million tons",
        "conv2005toyear = 113.647 / 87.504",
        "scc = -scc",
    ])
    require_tokens(blue_root / "Code/SCC/make_mc_bat_files.py", [
        "'prstp': [0.01, 0.02]", "'elasmu': [1.1, 1.6]",
        "--elasmu=1.24 --prstp=0.02",
    ])
    require_tokens(rice_root / "modules/mod_emission_pulse.gms", [
        "$setglobal emission_pulse 1 #unit is MtCO2eq", "# Pulse in 2020!",
    ])
    require_tokens(give_root / "src/price_level_inflator.jl", [
        "const pricelevel_2005_to_2020 = 113.648 / 87.504",
    ])
    require_tokens(give_root / "src/discount_rates.jl", [
        "prtp = exp(0.001972641) - 1, eta = 1.244458999",
    ])
    require_tokens(give_root / "src/compute_scc.jl", [
        "year = 2020", "pulse_size = 1e-4",
    ])
    require_tokens(give_root / "packages/MimiGIVE/src/scc.jl", [
        "scc_gas_molecular_conversions = Dict(:CO2 => 12/44",
        "scc_gas_pulse_size_conversions = Dict(:CO2 => 1e9",
    ])
    return {
        "schema": "fisheries_market_give_target_audit_v1",
        "status": "passed_mechanical_harmonization_nonadditive",
        "contract_id": config["contract_id"],
        "result": harmonize(config, benchmark),
        "source_rows_copied": False,
        "give_model_modified": False,
        "give_scc_calculated": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=Path("config/fisheries_market_give_target_v1.json"))
    parser.add_argument("--benchmark", type=Path, default=Path("data/provenance/blue_scc_fisheries_mc_benchmark_20261017.json"))
    parser.add_argument("--blue-scc-root", required=True, type=Path)
    parser.add_argument("--rice50x-root", required=True, type=Path)
    parser.add_argument("--give-root", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    payload = build(*(path.resolve() for path in [args.config, args.benchmark, args.blue_scc_root, args.rice50x_root, args.give_root]))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload["result"], sort_keys=True))


if __name__ == "__main__":
    main()

