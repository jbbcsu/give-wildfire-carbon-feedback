#!/usr/bin/env python3
"""Validate the corrected compatible-template distinctness contract."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import tomllib


SCHEMA = "isimip3b_rimex_template_compatibility_distinctness_contract_v2"
ESMS = ["GFDL-ESM4", "IPSL-CM6A-LR", "MPI-ESM1-2-HR", "MRI-ESM2-0", "UKESM1-0-LL"]
SCENARIOS = ["ssp126", "ssp370", "ssp585"]
CROPS = ["mai", "soy", "ri1", "ri2", "swh", "wwh"]
REGIMES = ["noirr", "firr"]


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
    require(config.get("role") == "outcome_blind_no_fit_receipt_only_compatible_template_distinctness_gate", "contract role changed")
    require(config.get("supersedes_withdrawn_contract") == "config/isimip3b_rimex_temporal_distinctness_v1.toml", "withdrawal link changed")
    for gate in ("dependence_fit_authorized", "fair_feature_response_authorized", "response_estimation_authorized", "damage_or_scc_authorized"):
        require(config.get(gate) is False, f"closed gate changed: {gate}")

    target = config.get("target_template", {})
    require(target.get("unit") == "centered_21yr_linked_multicrop_regime_physical_field", "target template unit changed")
    require(target.get("centered_window_years") == 21 and target.get("window_year_radius") == 10, "window geometry changed")
    require(target.get("required_center_years") == list(range(2042, 2050)), "center years changed")
    require(target.get("required_crops") == CROPS, "crop coverage changed")
    require(target.get("required_calendar_regimes") == REGIMES, "calendar coverage changed")
    require(target.get("same_esm_member_scenario_windows_must_be_pairwise_nonoverlapping") is True, "nonoverlap gate changed")

    matrix = config.get("matrix", {})
    require(matrix.get("expected_esms") == ESMS and matrix.get("expected_scenarios") == SCENARIOS, "matrix identity changed")
    require(matrix.get("current_compatible_dataset_cells") == 11, "current cell count changed")
    require(matrix.get("current_nominal_compatible_templates") == 88, "current nominal count changed")
    require(matrix.get("complete_design_dataset_cells") == 15, "complete cell count changed")
    require(matrix.get("complete_design_nominal_templates") == 120, "complete nominal count changed")

    decision = config.get("decision", {})
    require(decision.get("minimum_distinct_training_templates_per_permitted_pool") == 51, "minimum template gate changed")
    for gate in ("incompatible_candidate_receipts_contribute_zero_templates", "pairwise_nonoverlap_is_only_an_upper_bound_not_independence_evidence", "whole_esm_holdout_training_count_required", "whole_scenario_holdout_training_count_required", "no_fit_if_any_gate_fails", "no_outcome_columns"):
        require(decision.get(gate) is True, f"decision gate changed: {gate}")

    resources = config.get("resources", {})
    require(resources.get("maximum_peak_resident_memory_bytes") == 2 * 1024**3, "memory ceiling changed")
    for gate in ("large_downloads_forbidden", "raw_rehydration_forbidden", "global_daily_inputs_forbidden", "derived_parquet_inputs_forbidden", "receipt_json_inputs_only"):
        require(resources.get(gate) is True, f"resource gate changed: {gate}")

    sources = {}
    for record in config.get("source_receipts", []):
        path = root / str(record["path"])
        require(sha256(path) == str(record["sha256"]), f"source receipt hash changed: {path}")
        sources[str(record["role"])] = json.loads(path.read_text(encoding="utf-8"))
    require(set(sources) == {"compatible_centered_multicrop_regime_inventory", "locked_pool_decision"}, "source receipt roles changed")
    inventory = sources["compatible_centered_multicrop_regime_inventory"]
    require(inventory.get("schema") == "isimip3b_rimex_contiguous_completed_matrix_audit_v1", "compatible inventory schema changed")
    require(inventory.get("completed_dataset_cells") == 11 and inventory.get("completed_templates") == 88, "compatible inventory counts changed")
    require(inventory.get("balanced_five_esm_three_scenario_matrix_complete") is False, "compatible matrix completeness changed")
    for cell in inventory.get("cells", []):
        nested_path = root / str(cell["audit"])
        require(sha256(nested_path) == str(cell["audit_sha256"]), f"nested compatible audit hash changed: {nested_path}")
        nested = json.loads(nested_path.read_text(encoding="utf-8"))
        require(nested.get("schema") == "isimip3b_rimex_contiguous_multicrop_regime_audit_v1", "nested compatible schema changed")
        ids = sorted(str(row["id"]) for row in nested.get("cells", []))
        require(ids == sorted(f"{crop}_{regime}" for crop in CROPS for regime in REGIMES), "nested crop/regime coverage changed")
        require(all(row["row_counts"]["center_gmst"] == 8 for row in nested["cells"]), "nested center-year count changed")
        require(all("centered_gmst_21yr.parquet" in row["inputs"]["center_gmst"]["path"] for row in nested["cells"]), "nested centered-window evidence changed")

    incompatible = {}
    for record in config.get("incompatible_candidate_receipts", []):
        path = root / str(record["path"])
        require(sha256(path) == str(record["sha256"]), f"candidate receipt hash changed: {path}")
        incompatible[str(record["period"])] = json.loads(path.read_text(encoding="utf-8"))
    require(len(incompatible) == 4, "incompatible candidate receipt count changed")
    require(incompatible["historical_and_early_future"].get("schema") == "isimip3b_bounded_five_esm_four_scenario_holdout_v1", "early candidate schema changed")
    for period in ("midcentury", "endcentury"):
        require(incompatible[period].get("schema") == "isimip3b_five_esm_later_century_holdout_audit_v1", f"{period} candidate schema changed")
        require(incompatible[period].get("period") == period, f"{period} candidate label changed")
    combined = incompatible["combined_period_inventory"]
    require(combined.get("schema") == "isimip3b_expanded_fair_training_audit_v1", "combined candidate schema changed")
    require(combined.get("limitation") == "One crop/regime and two latitude rows; joins climate-feature support only.", "candidate limitation changed")

    return {
        "schema": "isimip3b_rimex_template_compatibility_distinctness_preregistration_v2",
        "status": "validated_before_corrected_compatibility_distinctness_audit",
        "config_sha256": sha256(config_path),
        "implementation_sha256": sha256(Path(__file__)),
        "top_level_receipts_read": 6,
        "nested_compatible_receipts_read": 11,
        "minimum_distinct_training_templates": 51,
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
    result = validate(args.config, args.root.resolve())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("corrected template compatibility/distinctness preregistration passed")


if __name__ == "__main__":
    main()
