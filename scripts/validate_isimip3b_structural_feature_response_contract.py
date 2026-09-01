#!/usr/bin/env python3
"""Fail-closed validator for the pathway-aware feature-response preregistration."""
from __future__ import annotations

import argparse
import hashlib
import json
import tomllib
from pathlib import Path


FEATURES = ["tmean_c", "precip_mm", "wet_days_n", "cdd_max_days", "rx1day_mm", "rx5day_mm", "stage1_precip_share", "stage2_precip_share", "stage3_precip_share", "precipitation_timing_centroid", "precipitation_concentration_hhi"]
ESMS = ["GFDL-ESM4", "IPSL-CM6A-LR", "MPI-ESM1-2-HR", "MRI-ESM2-0", "UKESM1-0-LL"]
SCENARIOS = ["historical", "ssp126", "ssp370", "ssp585"]
CONTINUOUS_TERMS = ["same_realization_gmst_anomaly_k", "same_realization_gmst_one_year_change_k", "years_since_2020", "gmst_anomaly_squared", "gmst_anomaly_x_one_year_change", "gmst_anomaly_x_years_since_2020"]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def validate(config_path: Path, root: Path) -> dict[str, object]:
    config = tomllib.loads(config_path.read_text(encoding="utf-8"))
    require(config.get("schema") == "isimip3b_structural_feature_response_contract_v1", "contract schema changed")
    require(config.get("primary_climate_route") == "direct_isimip3b_daily_feature_response", "primary route changed")
    require(config.get("fallback_climate_route") == "mesmer_m_tp_plus_published_daily_generator", "fallback route changed")
    require(config.get("scenario_categorical_effect") is False, "scenario categorical shortcut is forbidden")
    for gate in ("production_promoted", "response_estimation_authorized", "damage_or_scc_authorized"):
        require(config.get(gate) is False, f"closed gate changed: {gate}")
    require(config.get("required_feature_families") == FEATURES, "feature-family order changed")
    require(config.get("required_esm_ids") == ESMS, "ESM set changed")
    require(config.get("required_scenarios") == SCENARIOS, "scenario set changed")

    sources = config.get("source_receipts", [])
    require([source.get("role") for source in sources] == [
        "complete_bounded_early_mid_end_training",
        "actual_give_fair_common_random_number_support",
        "bounded_multicrop_calendar_support",
    ], "source receipt roles changed")
    checked_sources = []
    for source in sources:
        path = root / str(source["path"])
        observed = sha256(path)
        require(observed == source.get("sha256"), f"source receipt hash changed: {path}")
        checked_sources.append({"role": source["role"], "path": source["path"], "sha256": observed})

    basis = config.get("predictor_basis", {})
    require(basis.get("continuous_terms") == CONTINUOUS_TERMS, "continuous pathway basis changed")
    require(basis.get("scenario_identity_as_predictor") is False, "scenario identity cannot enter the predictor basis")
    require(basis.get("standardize_within_training_fold_only") is True, "fold-local standardization is required")
    require(basis.get("gmst_change_requires_same_realization_previous_year") is True, "GMST change identity gate changed")
    require(basis.get("cross_block_gmst_differences_forbidden") is True, "cross-block GMST differences are forbidden")
    require(basis.get("unseen_esm_deviations_in_whole_esm_holdout") == "zero_global_backbone_only", "whole-ESM prediction rule changed")

    regularization = config.get("regularization", {})
    require(regularization.get("method") == "ridge", "regularization method changed")
    require(regularization.get("lambda_grid") == [0.001, 0.01, 0.1, 1.0, 10.0, 100.0], "lambda grid changed")
    require(regularization.get("outer_holdouts_excluded_from_lambda_selection") is True, "outer holdout leaked into selection")
    require(regularization.get("probability_weights_assigned_to_esms") is False, "ESMs cannot be treated as probability draws")

    validation = config.get("validation", {})
    require(validation.get("outer_holdouts") == ["whole_esm", "whole_scenario"], "outer holdouts changed")
    for gate in ("required_common_random_numbers", "required_same_realization_gmst", "required_baseline_and_pulse_support_flags", "required_zero_pulse_identity", "required_pre_divergence_identity", "required_direct_centered_agreement", "required_multicrop_reporting", "required_rainfed_irrigated_calendar_reporting"):
        require(validation.get(gate) is True, f"validation gate changed: {gate}")
    require(validation.get("required_decreasing_positive_pulse_scales") >= 3, "at least three decreasing pulse scales are required")

    promotion = config.get("promotion", {})
    require(float(promotion.get("maximum_outer_holdout_rmse_ratio_to_cell_mean", 2)) <= 1.0, "maximum holdout criterion weakened")
    require(float(promotion.get("median_outer_holdout_rmse_ratio_to_cell_mean", 2)) <= 0.995, "median holdout criterion weakened")
    for gate in ("every_feature_family_must_pass_both_holdout_types", "actual_fair_baseline_and_pulse_must_be_within_support", "zero_pulse_and_pre_divergence_must_be_exact", "decreasing_pulse_convergence_must_pass", "human_review_required"):
        require(promotion.get(gate) is True, f"promotion gate changed: {gate}")
    limitations = config.get("limitations", {})
    require(all(limitations.get(gate) is True for gate in ("no_causal_yield_response", "no_irrigation_treatment_effect", "no_probability_interpretation", "no_post_2100_daily_support", "no_damage_or_scc_input")), "limitations changed")

    return {
        "schema": "isimip3b_structural_feature_response_contract_validation_v1",
        "status": "validated_preregistered_candidate_not_fitted_or_promoted",
        "config": {"path": config_path.resolve().relative_to(root.resolve()).as_posix(), "sha256": sha256(config_path)},
        "implementation": {"path": Path(__file__).resolve().relative_to(root.resolve()).as_posix(), "sha256": sha256(Path(__file__))},
        "source_receipts": checked_sources,
        "candidate": {"method": "ridge", "continuous_terms": CONTINUOUS_TERMS, "esm_partial_pooling": True, "scenario_categorical_effect": False},
        "whole_esm_holdout_required": True,
        "whole_scenario_holdout_required": True,
        "actual_fair_common_random_number_validation_required": True,
        "production_promoted": False,
        "response_estimation_authorized": False,
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
    print("ISIMIP3b structural feature-response contract passed")


if __name__ == "__main__":
    main()
