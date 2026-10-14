#!/usr/bin/env python3
"""Validate the source-faithful Moore labor/agriculture paired-module preflight.

This is intentionally a metadata and source-structure gate. It does not import
Julia, build a model, read model output arrays, or calculate a new SCC.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA = "moore_paired_module_preflight_contract/v1"
RECEIPT_SCHEMA = "labor_ag_sectoral_scc_stage_receipt/v1"
EXPECTED_CASES = {"LANCET": "Lancet", "ISO": "ISO"}
EXPECTED_PARTIALS = {"agriculture", "labor"}
EXPECTED_REMOVALS = {
    "Agriculture",
    "Agriculture_aggregator_pop90",
    "Agriculture_aggregator_gdp90",
    "Agriculture_aggregator_population",
    "Agriculture_aggregator_gdp",
    "AgricultureDamagesDisaggregator",
    "Damages_RegionAggregatorSum",
    "regional_netconsumption",
    "RegionalPerCapitaGDP",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_bound_file(root: Path, spec: dict[str, Any], *, check_size: bool = False) -> Path:
    require(set(spec) == ({"path", "sha256", "bytes"} if check_size else {"path", "sha256"}),
            f"unexpected bound-file fields: {spec.get('path')}")
    path = root / spec["path"]
    require(path.is_file(), f"missing bound file: {spec['path']}")
    require(sha256(path) == spec["sha256"], f"hash mismatch: {spec['path']}")
    if check_size:
        require(path.stat().st_size == spec["bytes"], f"size mismatch: {spec['path']}")
    return path


def require_source_fact(text: str, fragment: str, label: str) -> None:
    require(fragment in text, f"source fact absent: {label}")


def validate_source_graph(contract: dict[str, Any], texts: dict[str, str]) -> dict[str, Any]:
    install = contract["module_installation"]
    require(install["baseline_constructor"] == "MimiGIVE.get_model", "baseline constructor differs")
    require(install["replacement_constructor"] == "get_model", "replacement constructor differs")
    require(set(install["legacy_agriculture_components_removed"]) == EXPECTED_REMOVALS,
            "legacy agriculture removal set differs")
    require(install["replacement_components_added_in_order"] ==
            ["AgricultureShare", "Labor", "Agriculture"], "component installation order differs")
    require(install["aggregator_component_replaced"] == "DamageAggregator",
            "damage aggregator replacement differs")
    require(install["legacy_agriculture_random_variables_removed"] == 48,
            "legacy agriculture RV count differs")
    require(install["updated_agriculture_coefficients_per_country"] == 7,
            "updated agriculture coefficient count differs")
    require(install["labor_gcm_uncertainty_added"] is True, "labor GCM uncertainty must be added")

    get_model = texts["get_model"]
    for component in EXPECTED_REMOVALS:
        require_source_fact(get_model, f":{component}", f"remove {component}")
    require_source_fact(get_model, "Mimi.has_comp(m, c) && delete!(m, c)", "guarded legacy deletion")
    require_source_fact(get_model, "replace!(m, :DamageAggregator => DamageAggregator)",
                        "damage aggregator replacement")
    ordered_fragments = [
        "add_comp!(m, AgricultureShare, :AgricultureShare",
        "add_comp!(m, Labor, :Labor, after = :AgricultureShare",
        "add_comp!(m, Agriculture, :Agriculture, after = :Labor",
    ]
    positions = [get_model.find(fragment) for fragment in ordered_fragments]
    require(all(position >= 0 for position in positions) and positions == sorted(positions),
            "replacement components are absent or out of order")
    require_source_fact(get_model,
                        "connect_param!(m, :DamageAggregator => :damage_ag, :Agriculture => :agcost)",
                        "agriculture damage connection")
    require_source_fact(get_model,
                        "connect_param!(m, :DamageAggregator => :damage_labor, :Labor => :laborcost)",
                        "labor damage connection")
    require_source_fact(get_model,
                        '20260428_Plants_People_results_v4_$(labor_damage_function)_Revision.csv',
                        "case-selected labor input")

    mcs = texts["mcs"]
    require_source_fact(mcs, "for coef in [1,2,3]", "three legacy agriculture coefficients")
    for region in ("USA", "CAN", "WEU", "JPK", "ANZ", "EEU", "FSU", "MDE",
                   "CAM", "LAM", "SAS", "SEA", "CHI", "MAF", "SSA", "SIS"):
        require_source_fact(mcs, f'"{region}"', f"legacy region {region}")
    require_source_fact(mcs, "Mimi.delete_RV!(mcs, rv_name)", "legacy agriculture RV deletion")
    require_source_fact(mcs, "Mimi.add_RV!(mcs, rv_name, Mimi.EmpiricalDistribution(gcm_options))",
                        "labor GCM RV")
    require_source_fact(mcs, "for coef in [1,2,3,4,5,6,7]", "seven updated agriculture coefficients")

    aggregator = texts["damage_aggregator"]
    for flag in ("include_ag", "include_labor"):
        require(flag in install["required_active_flags"], f"missing configured flag: {flag}")
        require_source_fact(aggregator, f"{flag} = Parameter{{Bool}}(default=true)",
                            f"active {flag} default")
    require_source_fact(aggregator, "p.damage_ag[t,:]", "separate agriculture aggregation")
    require_source_fact(aggregator, "p.damage_labor[t,:]", "separate labor aggregation")

    scc = texts["scc"]
    require_source_fact(scc, ":agriculture, :energy, :labor, :slr", "separate partial SCC sectors")
    runner = texts["runner"]
    require_source_fact(runner, 'LABOR_FUNCTION = get(ENV, "LABOR_FUNCTION", "ISO")',
                        "case selected by environment")
    require_source_fact(runner, 'LABOR_FUNCTION in ("ISO", "Lancet")',
                        "case allowlist")
    require_source_fact(runner, "labor_damage_function = LABOR_FUNCTION", "case passed to model")
    require_source_fact(runner, "socioeconomics_source = :RFF", "RFF-SP model construction")
    require_source_fact(runner, "year = 2025", "2025 pulse year")
    require_source_fact(runner, "pulse_size = 1e-4", "pulse size")
    require_source_fact(runner, "compute_sectoral_values = true", "partial sector outputs")
    return {
        "legacy_components_removed": len(EXPECTED_REMOVALS),
        "replacement_components_added": 3,
        "legacy_agriculture_random_variables_removed": 48,
        "updated_agriculture_coefficients_per_country": 7,
        "separate_damage_connections": sorted(EXPECTED_PARTIALS),
    }


def validate_receipt(receipt: dict[str, Any], case: str, invariants: dict[str, Any]) -> dict[str, Any]:
    require(receipt.get("schema") == RECEIPT_SCHEMA, f"{case} receipt schema differs")
    require(receipt.get("labor_function") == case, f"{case} receipt mislabeled")
    for field in ("currency", "discount_rate_label", "draws", "julia_threads", "julia_version",
                  "pulse_year", "seed", "socioeconomics"):
        require(receipt.get(field) == invariants[field], f"{case} invariant differs: {field}")
    summary = receipt.get("summary", {})
    expected = {"agriculture", "cromar_mortality", "energy", "labor", "slr", "total"}
    require(set(summary) == expected, f"{case} receipt sector support differs")
    means = []
    for sector, values in summary.items():
        for field in ("expected_scc_2020usd_per_tco2", "median", "q05", "q95", "se_expected_scc"):
            value = values.get(field)
            require(isinstance(value, (int, float)) and math.isfinite(value),
                    f"{case} non-finite {sector}.{field}")
        require(values["q05"] <= values["median"] <= values["q95"],
                f"{case} quantile order differs: {sector}")
        if sector != "total":
            means.append(float(values["expected_scc_2020usd_per_tco2"]))
    total = float(summary["total"]["expected_scc_2020usd_per_tco2"])
    require(math.isclose(sum(means), total, rel_tol=0, abs_tol=1e-9),
            f"{case} component means do not sum to total")
    # Preserve each case's reported uncertainty; no cross-case statistic is constructed.
    return {
        sector: {field: float(summary[sector][field]) for field in
                 ("expected_scc_2020usd_per_tco2", "q05", "median", "q95")}
        for sector in sorted(EXPECTED_PARTIALS)
    }


def validate_contract(root: Path, contract_path: Path) -> dict[str, Any]:
    contract = json.loads(contract_path.read_text())
    require(contract.get("schema") == SCHEMA, "unexpected contract schema")
    require(contract.get("source_license") == "MIT", "source license differs")
    require(set(contract.get("source_files", {})) ==
            {"runner", "project", "manifest", "get_model", "mcs", "damage_aggregator", "scc"},
            "source-file set differs")
    require(set(contract.get("structural_cases", {})) == set(EXPECTED_CASES),
            "cases must be exactly LANCET and ISO")

    outputs = contract.get("output_contract", {})
    require(set(outputs.get("allowed_partial_sectors", [])) == EXPECTED_PARTIALS,
            "allowed partial-sector set differs")
    require(outputs.get("case_outputs_must_remain_separate") is True,
            "case outputs must remain separate")
    for gate in ("allow_cross_case_quantile_pooling", "allow_equal_weight_quantile_averaging",
                 "allow_agriculture_addition", "allow_precipitation_stacking",
                 "allow_replacement_delta_claim", "allow_combined_give_scc_claim"):
        require(outputs.get(gate) is False, f"hard gate must remain false: {gate}")

    texts = {
        name: validate_bound_file(root, spec).read_text()
        for name, spec in contract["source_files"].items()
    }
    source_graph = validate_source_graph(contract, texts)

    ignored = contract.get("ignored_runtime_inputs", {})
    expected_inputs = {"region_crosswalk", "gcm_dimension", "sector_share", "rff_ypc2017",
                       "updated_agriculture", "labor_lancet", "labor_iso"}
    require(set(ignored) == expected_inputs, "runtime input set differs")
    for spec in ignored.values():
        require(spec["path"].startswith(contract["source_root"] + "/data/"),
                f"runtime input outside source data root: {spec['path']}")
        validate_bound_file(root, spec, check_size=True)
    gitignore = (root / ".gitignore").read_text().splitlines()
    require("vendor/" in gitignore, "vendor raw-data ignore is absent")

    cases: dict[str, Any] = {}
    for case, constructor_value in EXPECTED_CASES.items():
        spec = contract["structural_cases"][case]
        require(set(spec) == {"constructor_value", "labor_input", "receipt"},
                f"unexpected {case} case fields")
        require(spec["constructor_value"] == constructor_value,
                f"{case} constructor value differs")
        require(spec["labor_input"] == f"labor_{case.lower()}", f"{case} labor input differs")
        receipt_path = validate_bound_file(root, spec["receipt"])
        receipt = json.loads(receipt_path.read_text())
        cases[case] = {
            "constructor_value": constructor_value,
            "receipt": spec["receipt"],
            "partial_sector_summary": validate_receipt(
                receipt, case, contract["execution_invariants"]
            ),
        }

    return {
        "schema": "moore_paired_module_preflight_receipt/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "contract": {
            "path": str(contract_path.relative_to(root)),
            "sha256": sha256(contract_path),
        },
        "source_graph": source_graph,
        "ignored_runtime_inputs": {
            "count": len(ignored),
            "bytes": sum(spec["bytes"] for spec in ignored.values()),
            "hashes_valid": True,
            "vendor_ignore_present": True,
        },
        "structural_cases": cases,
        "gates": {
            "paired_replacement_addition_source_graph_verified": True,
            "case_specific_inputs_and_receipts_verified": True,
            "case_outputs_remain_separate": True,
            "cross_case_quantile_pooling_allowed": False,
            "agriculture_addition_allowed": False,
            "precipitation_stacking_allowed": False,
            "replacement_delta_promoted": False,
            "target_give_run_completed": False,
            "combined_give_scc_authorized": False,
        },
        "claim_status": (
            "source-verified paired-module execution preflight only; no new run, replacement delta, "
            "pooled uncertainty, precipitation stacking, or combined GIVE SCC"
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--contract", type=Path,
                        default=Path("config/moore_paired_module_preflight_v1.json"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    contract_path = args.contract if args.contract.is_absolute() else root / args.contract
    result = validate_contract(root, contract_path)
    payload = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        output = args.output if args.output.is_absolute() else root / args.output
        require(not output.exists(), "fresh output path required")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(payload)
    print(payload, end="")


if __name__ == "__main__":
    main()
