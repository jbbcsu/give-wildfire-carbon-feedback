#!/usr/bin/env python3
"""Audit pooled versus ESM-conditional dependence sample sufficiency.

This evaluator reads three checksum-bound JSON receipts only. It does not read
derived Parquet or global daily inputs and does not fit a dependence model.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import platform
import resource
import tomllib

from validate_isimip3b_rimex_dependence_pool_decision_contract import validate as validate_contract


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def observed_rss_bytes() -> int:
    raw = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    return raw if platform.system() == "Darwin" else raw * 1024


def summarize(
    identities: list[tuple[str, str]],
    config: dict[str, object],
    represented_stability_passed: bool,
    mri_instability_resolved: bool,
    esm_stability: dict[str, bool | None],
) -> dict[str, object]:
    matrix = config["matrix"]
    decision = config["decision"]
    esms = list(matrix["expected_esms"])
    scenarios = list(matrix["expected_scenarios"])
    templates_per_cell = int(matrix["templates_per_dataset_cell"])
    minimum = int(decision["minimum_distinct_training_templates_per_permitted_pool"])
    require(len(identities) == len(set(identities)), "duplicate completed dataset cell")
    require(all(esm in esms and scenario in scenarios for esm, scenario in identities), "unexpected matrix identity")
    completed = set(identities)
    expected = {(esm, scenario) for esm in esms for scenario in scenarios}
    require(len(completed) * templates_per_cell == int(matrix["completed_templates_required"]), "completed template count changed")

    pooled_current = len(completed) * templates_per_cell
    pooled_complete = len(expected) * templates_per_cell
    balanced_complete = completed == expected
    pooled_count_passed = pooled_current >= minimum
    stability_resolved = represented_stability_passed and mri_instability_resolved
    pooled_permitted = balanced_complete and pooled_count_passed and stability_resolved
    pooled = {
        "pool_type": "pooled_across_esms",
        "current_templates": pooled_current,
        "complete_design_templates": pooled_complete,
        "minimum_templates": minimum,
        "current_template_count_gate_passed": pooled_count_passed,
        "complete_balanced_matrix_gate_passed": balanced_complete,
        "adverse_stability_gate_resolved": stability_resolved,
        "permitted_for_dependence_fit": pooled_permitted,
    }

    conditional_rows = []
    complete_conditional_templates = len(scenarios) * templates_per_cell
    for esm in esms:
        observed_scenarios = sorted(scenario for item_esm, scenario in completed if item_esm == esm)
        current_templates = len(observed_scenarios) * templates_per_cell
        scenario_complete = observed_scenarios == scenarios
        count_passed = current_templates >= minimum
        existing_stability = esm_stability.get(esm)
        esm_stability_resolved = bool(existing_stability) and (
            mri_instability_resolved if esm == decision["locked_adverse_esm"] else True
        )
        conditional_rows.append({
            "esm": esm,
            "current_scenarios": observed_scenarios,
            "current_templates": current_templates,
            "complete_design_templates": complete_conditional_templates,
            "minimum_templates": minimum,
            "template_shortfall_from_complete_design": max(0, minimum - complete_conditional_templates),
            "all_expected_scenarios_present": scenario_complete,
            "current_template_count_gate_passed": count_passed,
            "complete_design_can_meet_minimum": complete_conditional_templates >= minimum,
            "existing_esm_holdout_stability_gate_passed": existing_stability,
            "stability_evidence_gate_resolved": esm_stability_resolved,
            "permitted_for_dependence_fit": scenario_complete and count_passed and esm_stability_resolved,
        })

    require(len(conditional_rows) == int(config["outputs"]["esm_conditional_rows_required"]), "ESM-conditional output count changed")
    permitted = int(pooled_permitted) + sum(bool(row["permitted_for_dependence_fit"]) for row in conditional_rows)
    return {
        "pooled_pool": pooled,
        "esm_conditional_pools": conditional_rows,
        "permitted_pool_count": permitted,
        "decision": "no_pool_permitted_for_dependence_fit" if permitted == 0 else "one_or_more_pools_passed_locked_gates",
        "esm_conditional_structurally_sufficient_under_frozen_design": complete_conditional_templates >= minimum,
        "minimum_additional_distinct_templates_needed_per_complete_esm_pool": max(0, minimum - complete_conditional_templates),
        "missing_dataset_cells": [
            {"esm": esm, "scenario": scenario} for esm, scenario in sorted(expected - completed)
        ],
    }


def evaluate(config_path: Path, root: Path) -> dict[str, object]:
    preregistration = validate_contract(config_path, root)
    config = tomllib.loads(config_path.read_text(encoding="utf-8"))
    sources = {source["role"]: root / source["path"] for source in config["source_receipts"]}
    inventory = json.loads(sources["completed_contiguous_template_inventory"].read_text(encoding="utf-8"))
    stability = json.loads(sources["locked_adverse_dependence_stability_audit"].read_text(encoding="utf-8"))
    mri = json.loads(sources["locked_mri_failure_decomposition"].read_text(encoding="utf-8"))

    require(inventory.get("schema") == "isimip3b_rimex_contiguous_completed_matrix_audit_v1", "inventory schema changed")
    require(inventory.get("completed_templates") == config["matrix"]["completed_templates_required"], "inventory template count changed")
    require(inventory.get("balanced_five_esm_three_scenario_matrix_complete") is False, "current matrix completeness changed")
    require(stability.get("all_represented_holdouts_passed") is False, "locked adverse stability result changed")
    require(stability.get("real_joint_fit_authorized") is False, "locked stability fit gate changed")
    require(mri.get("scenario_imbalance_sufficient_to_explain_locked_failure") is False, "MRI decomposition result changed")
    require(abs(float(mri["scenario_matched_primary"]["absolute_difference"]) - float(config["decision"]["locked_scenario_matched_difference"])) < 1e-12, "MRI matched failure value changed")
    require(float(mri["locked_gate"]) == float(config["decision"]["locked_maximum_difference_gate"]), "MRI locked gate changed")

    identities = [(str(cell["esm"]), str(cell["scenario"])) for cell in inventory["cells"]]
    esm_stability = {
        str(row["holdout"]): bool(row["passed_preregistered_stability_tolerances"])
        for row in stability["holdouts"]
        if row["holdout_type"] == "esm"
    }
    summary = summarize(identities, config, False, False, esm_stability)
    configured_missing = sorted(config["limitations"]["missing_cells"])
    observed_missing = sorted(f"{row['esm']}/{row['scenario']}" for row in summary["missing_dataset_cells"])
    require(observed_missing == configured_missing, "missing-cell list changed")
    maximum_rss = observed_rss_bytes()
    require(maximum_rss < int(config["resources"]["maximum_peak_resident_memory_bytes"]), "peak RSS exceeded 2 GiB")
    rss_reporting_quantum = 64 * 1024**2
    rounded_rss = ((maximum_rss + rss_reporting_quantum - 1) // rss_reporting_quantum) * rss_reporting_quantum

    return {
        "schema": "isimip3b_rimex_dependence_pool_decision_audit_v1",
        "status": summary["decision"],
        "preregistration": {
            "path": "data/provenance/isimip3b_rimex_dependence_pool_decision_preregistration_20260904.json",
            "sha256": sha256(root / "data/provenance/isimip3b_rimex_dependence_pool_decision_preregistration_20260904.json"),
            "config_sha256": preregistration["config_sha256"],
        },
        "implementation_sha256": sha256(Path(__file__)),
        "receipt_json_files_read": 3,
        "derived_parquet_files_read": 0,
        "global_daily_files_read": 0,
        "peak_rss_observed_rounded_up_to_64_mib_bytes": rounded_rss,
        "peak_rss_gate_bytes": int(config["resources"]["maximum_peak_resident_memory_bytes"]),
        "peak_rss_gate_passed": True,
        **summary,
        "dependence_fit_authorized": False,
        "fair_feature_response_authorized": False,
        "response_estimation_authorized": False,
        "damage_or_scc_authorized": False,
        "interpretation": "No-fit receipt-level decision audit. The incomplete pooled matrix and unresolved MRI stability failure block pooling; every complete ESM-conditional pool has only 24 templates under the frozen design, 27 below the locked 51-template minimum.",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = evaluate(args.config, args.root.resolve())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"dependence pool decision: {result['status']}; peak_rss_bytes={observed_rss_bytes()}")


if __name__ == "__main__":
    main()
