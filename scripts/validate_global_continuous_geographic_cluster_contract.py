#!/usr/bin/env python3
"""Validate the frozen geographic/source-cluster benchmark contract."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import tomllib


SCHEMA = "global_continuous_geographic_cluster_contract_v1"
ROLE = "exploratory_geographic_validation_and_source_cluster_uncertainty_only"
MODELS = ["controls_only", "quantity", "quantity_distribution", "scpdsi_mean", "scpdsi_stages"]
CONTRASTS = [
    "quantity_minus_controls_only", "quantity_distribution_minus_quantity",
    "scpdsi_mean_minus_quantity", "scpdsi_stages_minus_quantity",
]


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
    require(config.get("role") == ROLE, "contract role changed")
    for prefix in ("parent_result", "parent_protocol", "parent_implementation"):
        path = root / str(config.get(f"{prefix}_path", ""))
        require(path.is_file(), f"{prefix} path missing")
        require(config.get(f"{prefix}_sha256") == sha256(path), f"{prefix} hash changed")
    protocol = root / str(config.get("protocol_path", ""))
    require(protocol.is_file(), "protocol path missing")

    support = config.get("support", {})
    require(support.get("key_fields") == ["crop", "lat", "lon_360", "harvest_year"], "support keys changed")
    require(support.get("families") == ["direct", "heat", "scpdsi"], "families changed")
    for gate in ("exact_inner_join", "positive_identical_outcomes_required", "finite_registered_features_required", "consecutive_year_differences_only"):
        require(support.get(gate) is True, f"support gate changed: {gate}")
    require(support.get("train_end_years") == [1983, 2010], "training years changed")
    require(support.get("excluded_end_year") == 2011, "endpoint purge changed")
    require(support.get("test_end_years") == [2012, 2016], "test years changed")

    folds = config.get("geographic_folds", {})
    require(folds.get("count") == 5, "fold count changed")
    require(folds.get("latitude_block_degrees") == 10 and folds.get("longitude_block_degrees") == 10, "block size changed")
    require(folds.get("assignment") == "(37*floor((lat+90)/10)+17*floor(lon_360/10)+20260907)%5", "fold assignment changed")
    require(folds.get("outcome_blind") is True and folds.get("held_out_blocks_absent_from_training") is True, "geographic separation gate changed")
    require(folds.get("minimum_blocks_per_fold") == 2 and folds.get("minimum_blocks_per_crop") == 10, "minimum block support changed")

    models = config.get("models", {})
    require(models.get("ordered_names") == MODELS, "model set changed")
    require(models.get("moisture_families_mutually_exclusive") is True, "moisture-family gate changed")
    require(models.get("condition_number_maximum") == 1.0e10, "condition gate changed")
    require(models.get("coefficient_export_forbidden") is True and models.get("row_prediction_export_forbidden") is True, "output suppression changed")

    uncertainty = config.get("uncertainty", {})
    require(uncertainty.get("cluster") == "crop_specific_10_degree_latitude_longitude_source_block", "cluster definition changed")
    require(uncertainty.get("resampling") == "paired_within_fold_cluster_bootstrap", "resampling changed")
    require(uncertainty.get("replicates") == 5000 and uncertainty.get("seed") == 20260907, "bootstrap lock changed")
    require(uncertainty.get("generator") == "numpy.random.Generator(PCG64)", "random generator changed")
    require(uncertainty.get("quantiles") == [0.025, 0.5, 0.975], "quantiles changed")
    require(uncertainty.get("contrasts") == CONTRASTS, "contrasts changed")
    for gate in ("retain_all_pairs_within_selected_cluster", "conditional_on_fixed_fits", "significance_claim_forbidden"):
        require(uncertainty.get(gate) is True, f"uncertainty gate changed: {gate}")

    resources = config.get("resources", {})
    require(resources.get("batch_rows") == 8192, "batch size changed")
    require(resources.get("sampled_peak_resident_memory_bytes_maximum") == 1024**3, "memory ceiling changed")
    require(resources.get("result_bytes_maximum") == 1024**2, "result ceiling changed")
    for gate in ("existing_derived_inputs_only", "download_forbidden", "raw_rehydration_forbidden", "one_parquet_file_at_a_time", "large_climate_computation_forbidden"):
        require(resources.get(gate) is True, f"resource gate changed: {gate}")

    decision = config.get("decision", {})
    for gate in ("coefficient_export_authorized", "model_promotion_authorized", "causal_response_authorized", "future_projection_authorized", "fair_run_authorized", "damage_or_welfare_authorized", "scc_authorized"):
        require(decision.get(gate) is False, f"closed gate changed: {gate}")
    require(decision.get("all_results_remain_exploratory") is True, "exploratory status changed")

    inputs = config.get("inputs", [])
    require(len(inputs) == 6, "input count changed")
    expected = {(crop, family) for crop in ("maize", "soy") for family in ("direct", "heat", "scpdsi")}
    actual = {(item.get("crop"), item.get("family")) for item in inputs}
    require(actual == expected, "input matrix changed")
    for item in inputs:
        path = root / str(item.get("receipt_path", ""))
        require(path.is_file(), "input receipt missing")
        require(item.get("receipt_sha256") == sha256(path), "input receipt hash changed")

    return {
        "schema": "global_continuous_geographic_cluster_preregistration_v1",
        "status": "geographic_and_source_cluster_audit_preregistered_not_evaluated",
        "config_sha256": sha256(config_path),
        "protocol_sha256": sha256(protocol),
        "validator_sha256": sha256(Path(__file__)),
        "input_receipts": 6,
        "fold_count": 5,
        "bootstrap_replicates": 5000,
        "coefficient_export_authorized": False,
        "model_promotion_authorized": False,
        "damage_or_scc_authorized": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = validate(args.config.resolve(), args.root.resolve())
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("global continuous geographic/source-cluster contract passed")


if __name__ == "__main__":
    main()
