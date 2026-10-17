#!/usr/bin/env python3
"""Validate labor inside its exact GIVE target and publish an integration receipt."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import validate_paired_module_preflight as preflight


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_SECTORS = {"agriculture", "cromar_mortality", "energy", "labor", "slr"}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def bound_json(root: Path, spec: dict, label: str) -> tuple[Path, dict]:
    require(set(spec) == {"path", "sha256"}, f"unexpected {label} binding")
    path = root / spec["path"]
    require(path.is_file(), f"missing {label}: {spec['path']}")
    require(sha256(path) == spec["sha256"], f"{label} hash mismatch")
    return path, json.loads(path.read_text())


def build_integration(root: Path, config_path: Path) -> dict:
    config = json.loads(config_path.read_text())
    require(config.get("schema") == "labor_give_integration_contract/v1", "wrong contract schema")
    target = config["target_model"]
    require(target["id"] == "moore_2026_updated_agriculture_give", "wrong target model")
    require(set(target["active_partial_sectors"]) == EXPECTED_SECTORS, "target sector support differs")
    require(target["preexisting_labor_in_original_give"] is False, "original GIVE overlap gate is not closed")
    validation = config["validation"]
    require(validation["require_full_target_total_from_same_receipt"] is True, "same-receipt target total required")
    require(validation["allow_mean_decomposition"] is True, "mean decomposition must be enabled")
    for gate in ("allow_cross_function_quantile_pooling", "allow_no_labor_quantiles_from_summary_subtraction", "allow_drawwise_addition_without_joint_draws", "allow_precipitation_agriculture_stacking"):
        require(validation[gate] is False, f"hard gate must remain false: {gate}")
    require(config["structural_weights"] == {"ISO": 0.5, "LANCET": 0.5}, "structural weights differ")

    preflight_path, _ = bound_json(root, target["preflight_contract"], "preflight contract")
    source_validation = preflight.validate_contract(root, preflight_path)
    require(source_validation["gates"]["paired_replacement_addition_source_graph_verified"], "source graph not verified")
    require(source_validation["gates"]["case_specific_inputs_and_receipts_verified"], "source cases not verified")

    tolerance = float(validation["component_mean_additivity_absolute_tolerance"])
    require(tolerance <= 1e-9, "additivity tolerance is too loose")
    cases = {}
    for case in ("ISO", "LANCET"):
        _, receipt = bound_json(root, config["receipts"][case], f"{case} receipt")
        require(receipt["labor_function"] == case, f"{case} label differs")
        for field, expected in config["invariants"].items():
            require(receipt.get(field) == expected, f"{case} invariant differs: {field}")
        summary = receipt["summary"]
        require(set(summary) == EXPECTED_SECTORS | {"total"}, f"{case} sector support differs")
        component_means = {sector: float(summary[sector]["expected_scc_2020usd_per_tco2"]) for sector in EXPECTED_SECTORS}
        target_total = float(summary["total"]["expected_scc_2020usd_per_tco2"])
        residual = sum(component_means.values()) - target_total
        require(math.isclose(residual, 0.0, rel_tol=0, abs_tol=tolerance), f"{case} target is not component-additive")
        labor_mean = component_means["labor"]
        nonlabor_component_sum = sum(value for sector, value in component_means.items() if sector != "labor")
        no_labor_mean = target_total - labor_mean
        require(math.isclose(nonlabor_component_sum, no_labor_mean, rel_tol=0, abs_tol=tolerance), f"{case} nonlabor components fail")
        require(no_labor_mean + labor_mean == target_total, f"{case} labor bridge fails")
        cases[case] = {
            "weight": config["structural_weights"][case],
            "target_without_labor_mean_2020usd_per_tco2": no_labor_mean,
            "additive_labor_mean_2020usd_per_tco2": labor_mean,
            "target_with_labor_mean_2020usd_per_tco2": target_total,
            "mean_additivity_residual_2020usd_per_tco2": residual,
            "nonlabor_component_sum_residual_2020usd_per_tco2": nonlabor_component_sum - no_labor_mean,
            "labor_uncertainty_within_case": {"q05": float(summary["labor"]["q05"]), "median": float(summary["labor"]["median"]), "q95": float(summary["labor"]["q95"]), "monte_carlo_se_of_mean": float(summary["labor"]["se_expected_scc"])},
            "full_target_uncertainty_within_case": {"q05": float(summary["total"]["q05"]), "median": float(summary["total"]["median"]), "q95": float(summary["total"]["q95"]), "monte_carlo_se_of_mean": float(summary["total"]["se_expected_scc"])},
        }

    def weighted(field: str) -> float:
        return sum(row["weight"] * row[field] for row in cases.values())

    structural = {
        "target_without_labor_mean_2020usd_per_tco2": weighted("target_without_labor_mean_2020usd_per_tco2"),
        "additive_labor_mean_2020usd_per_tco2": weighted("additive_labor_mean_2020usd_per_tco2"),
        "target_with_labor_mean_2020usd_per_tco2": weighted("target_with_labor_mean_2020usd_per_tco2"),
        "pooled_uncertainty_interval": None,
        "pooled_standard_error": None,
    }
    structural["mean_additivity_residual_2020usd_per_tco2"] = structural["target_without_labor_mean_2020usd_per_tco2"] + structural["additive_labor_mean_2020usd_per_tco2"] - structural["target_with_labor_mean_2020usd_per_tco2"]
    require(abs(structural["mean_additivity_residual_2020usd_per_tco2"]) <= tolerance, "structural mean bridge fails")

    return {
        "schema": "labor_give_integration_receipt/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "complete_mean_integration_with_case_specific_uncertainty",
        "target_model": target["id"],
        "invariants": config["invariants"],
        "cases": cases,
        "equal_weight_structural_result": structural,
        "validation": {"source_graph_verified": True, "original_give_labor_overlap_absent": True, "same_run_component_and_total_means_used": True, "component_mean_additivity_tolerance": tolerance, "case_specific_uncertainty_retained": True, "cross_function_uncertainty_pooled": False, "precipitation_agriculture_stacking_allowed": False},
        "claim_boundary": "Finished expected-value integration in the published updated-agriculture GIVE target. Within-case labor and full-target uncertainty are reported from each same-run receipt; no cross-function distribution or no-labor interval is inferred.",
        "config": {"path": str(config_path.relative_to(root)), "sha256": sha256(config_path)},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "config/labor_give_integration_v1.json")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), "fresh output required")
    result = build_integration(ROOT, args.config.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": result["status"], "equal_weight_structural_result": result["equal_weight_structural_result"]}, indent=2))


if __name__ == "__main__":
    main()
