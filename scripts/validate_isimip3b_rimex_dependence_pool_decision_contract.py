#!/usr/bin/env python3
"""Validate the no-fit pooled-versus-ESM-conditional decision contract."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import tomllib


SCHEMA = "isimip3b_rimex_dependence_pool_decision_contract_v1"
ESMS = ["GFDL-ESM4", "IPSL-CM6A-LR", "MPI-ESM1-2-HR", "MRI-ESM2-0", "UKESM1-0-LL"]
SCENARIOS = ["ssp126", "ssp370", "ssp585"]
YEARS = list(range(2042, 2050))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate(config_path: Path, root: Path) -> dict[str, object]:
    config = tomllib.loads(config_path.read_text(encoding="utf-8"))
    require(config.get("schema") == SCHEMA, "contract schema changed")
    require(config.get("role", "").startswith("outcome_blind_no_fit_"), "no-fit outcome-blind role changed")
    for gate in ("dependence_fit_authorized", "fair_feature_response_authorized", "response_estimation_authorized", "damage_or_scc_authorized"):
        require(config.get(gate) is False, f"closed gate changed: {gate}")

    matrix = config.get("matrix", {})
    require(matrix.get("expected_esms") == ESMS, "expected ESM set changed")
    require(matrix.get("expected_scenarios") == SCENARIOS, "expected scenario set changed")
    require(matrix.get("center_years") == YEARS, "center-year design changed")
    require(matrix.get("templates_per_dataset_cell") == 8, "templates per dataset cell changed")
    require(matrix.get("expected_dataset_cells") == 15, "expected dataset-cell count changed")
    require(matrix.get("expected_balanced_templates") == 120, "balanced template count changed")
    require(matrix.get("completed_templates_required") == 88, "completed template count changed")
    require(matrix.get("balanced_five_esm_three_scenario_matrix_required") is True, "balanced-matrix gate changed")

    decision = config.get("decision", {})
    require(decision.get("candidate_pool_types") == ["pooled_across_esms", "esm_conditional"], "candidate pool types changed")
    require(decision.get("minimum_distinct_training_templates_per_permitted_pool") == 51, "minimum template gate changed")
    for gate in ("pool_must_cover_all_expected_scenarios", "pooled_pool_must_cover_all_expected_esms", "esm_conditional_pool_must_cover_exactly_one_expected_esm", "adverse_stability_gate_must_be_resolved_before_fit", "no_fit_if_any_gate_fails", "no_outcome_columns"):
        require(decision.get(gate) is True, f"decision gate changed: {gate}")
    require(decision.get("locked_adverse_esm") == "MRI-ESM2-0", "adverse ESM changed")
    require(decision.get("locked_adverse_coordinate_pair") == "wet_logit|rx1_given_rx5_logit", "adverse coordinate pair changed")
    require(decision.get("locked_maximum_difference_gate") == 0.15, "locked stability gate changed")
    require(abs(float(decision.get("locked_scenario_matched_difference", 0)) - 0.17365415357199204) < 1e-15, "locked matched failure changed")

    outputs = config.get("outputs", {})
    require(outputs.get("pooled_row_required") is True, "pooled output removed")
    require(outputs.get("esm_conditional_rows_required") == 5, "ESM-conditional output count changed")
    for gate in ("report_current_and_complete_design_template_counts", "report_template_shortfall", "report_structural_feasibility_under_frozen_eight_center_year_design", "report_missing_dataset_cells"):
        require(outputs.get(gate) is True, f"output gate changed: {gate}")

    resources = config.get("resources", {})
    require(resources.get("maximum_peak_resident_memory_bytes") == 2 * 1024**3, "memory ceiling changed")
    for gate in ("large_downloads_forbidden", "raw_rehydration_forbidden", "global_daily_inputs_forbidden", "derived_parquet_inputs_forbidden", "receipt_json_inputs_only"):
        require(resources.get(gate) is True, f"resource gate changed: {gate}")

    sources = []
    for source in config.get("source_receipts", []):
        path = root / source["path"]
        observed = sha256(path)
        require(observed == source["sha256"], f"source receipt hash changed: {source['path']}")
        sources.append({**source, "sha256": observed})
    require(len(sources) == 3, "source receipt count changed")

    return {
        "schema": "isimip3b_rimex_dependence_pool_decision_preregistration_v1",
        "status": "validated_before_pool_decision_audit",
        "config_sha256": sha256(config_path),
        "implementation_sha256": sha256(Path(__file__)),
        "sources": sources,
        "minimum_distinct_training_templates_per_permitted_pool": 51,
        "dependence_fit_authorized": False,
        "fair_feature_response_authorized": False,
        "damage_or_scc_authorized": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = validate(args.config, args.root)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("dependence pool decision preregistration passed")


if __name__ == "__main__":
    main()
