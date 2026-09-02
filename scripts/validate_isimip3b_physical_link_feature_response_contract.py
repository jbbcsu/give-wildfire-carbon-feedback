#!/usr/bin/env python3
"""Fail-closed validator for the physical-link feature-response preregistration."""
from __future__ import annotations

import argparse
import hashlib
import json
import tomllib
from pathlib import Path

from validate_isimip3b_structural_feature_response_contract import CONTINUOUS_TERMS, ESMS, FEATURES, SCENARIOS


POSITIVE = ["precip_mm", "wet_days_n", "cdd_max_days", "rx1day_mm", "rx5day_mm"]
BOUNDED = ["precipitation_timing_centroid", "precipitation_concentration_hhi"]
COMPOSITION = ["stage1_precip_share", "stage2_precip_share", "stage3_precip_share"]


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
    require(config.get("schema") == "isimip3b_physical_link_feature_response_contract_v1", "contract schema changed")
    require(config.get("primary_climate_route") == "direct_isimip3b_daily_feature_response", "primary route changed")
    require(config.get("fallback_climate_route") == "mesmer_m_tp_plus_published_daily_generator", "fallback route changed")
    require(config.get("scenario_categorical_effect") is False, "scenario categorical shortcut is forbidden")
    for gate in ("production_promoted", "response_estimation_authorized", "damage_or_scc_authorized"):
        require(config.get(gate) is False, f"closed gate changed: {gate}")
    require(config.get("required_feature_families") == FEATURES, "feature-family order changed")
    require(config.get("required_esm_ids") == ESMS, "ESM set changed")
    require(config.get("required_scenarios") == SCENARIOS, "scenario set changed")

    training_path = root / str(config.get("training_artifact"))
    require(sha256(training_path) == config.get("training_artifact_sha256"), "training artifact hash changed")
    expected_roles = ["complete_bounded_early_mid_end_training", "actual_give_fair_common_random_number_support", "bounded_multicrop_calendar_support"]
    sources = config.get("source_receipts", [])
    require([source.get("role") for source in sources] == expected_roles, "source receipt roles changed")
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
    require(basis.get("gmst_change_requires_same_realization_previous_year") is True, "GMST identity gate changed")
    require(basis.get("cross_block_gmst_differences_forbidden") is True, "cross-block GMST differences are forbidden")
    require(basis.get("unseen_esm_deviations_in_whole_esm_holdout") == "zero_global_backbone_only", "whole-ESM rule changed")

    links = config.get("response_links", {})
    require(links.get("identity_features") == ["tmean_c"], "identity link set changed")
    require(links.get("positive_log_features") == POSITIVE, "positive-log feature set changed")
    require(0 < float(links.get("positive_log_floor", 0)) <= 1e-4, "positive-log floor is invalid")
    require(links.get("bounded_logit_features") == BOUNDED, "bounded-logit feature set changed")
    require(0 < float(links.get("bounded_logit_epsilon", 0)) <= 1e-4, "bounded-logit epsilon is invalid")
    require(links.get("composition_features") == COMPOSITION, "composition feature set changed")
    require(links.get("composition_link") == "centered_log_ratio", "composition link changed")
    require(0 < float(links.get("composition_zero_replacement", 0)) <= 1e-4, "composition zero replacement is invalid")
    require(links.get("all_zero_composition_rule") == "uniform_three_part_before_zero_replacement", "all-zero composition rule changed")
    require(links.get("composition_lambda_shared_across_parts") is True, "composition lambda must be shared")
    require(links.get("inverse_predictions_scored_on_original_physical_scale") is True, "original-scale scoring is required")

    regularization = config.get("regularization", {})
    require(regularization.get("method") == "ridge", "regularization method changed")
    require(regularization.get("lambda_grid") == [0.001, 0.01, 0.1, 1.0, 10.0, 100.0], "lambda grid changed")
    require(regularization.get("outer_holdouts_excluded_from_lambda_selection") is True, "outer holdout leaked into selection")
    require(regularization.get("probability_weights_assigned_to_esms") is False, "ESMs cannot be probability draws")
    require(regularization.get("lambda_selected_separately_by_feature_family_except_shared_composition") is True, "lambda grouping changed")
    require(regularization.get("lambda_shared_across_grid_cells_within_feature_family") is True, "cell-specific lambdas are forbidden")

    validation = config.get("validation", {})
    require(validation.get("outer_holdouts") == ["whole_esm", "whole_scenario"], "outer holdouts changed")
    required = (
        "required_common_random_numbers", "required_same_realization_gmst", "required_baseline_and_pulse_support_flags",
        "required_zero_pulse_identity", "required_pre_divergence_identity", "required_direct_centered_agreement",
        "required_multicrop_reporting", "required_rainfed_irrigated_calendar_reporting", "required_original_scale_scoring",
        "required_nonnegative_positive_features", "required_unit_interval_bounded_features", "required_stage_composition_sum_one",
    )
    for gate in required:
        require(validation.get(gate) is True, f"validation gate changed: {gate}")
    require(validation.get("required_decreasing_positive_pulse_scales") >= 3, "three decreasing pulse scales are required")
    require(validation.get("benchmark") == "training_fold_cell_feature_mean_on_original_scale", "benchmark changed")

    promotion = config.get("promotion", {})
    require(float(promotion.get("maximum_outer_holdout_rmse_ratio_to_cell_mean", 2)) <= 1.0, "maximum criterion weakened")
    require(float(promotion.get("median_outer_holdout_rmse_ratio_to_cell_mean", 2)) <= 0.995, "median criterion weakened")
    for gate in ("every_feature_family_must_pass_both_holdout_types", "actual_fair_baseline_and_pulse_must_be_within_support", "zero_pulse_and_pre_divergence_must_be_exact", "decreasing_pulse_convergence_must_pass", "human_review_required"):
        require(promotion.get(gate) is True, f"promotion gate changed: {gate}")

    return {
        "schema": "isimip3b_physical_link_feature_response_contract_validation_v1",
        "status": "validated_preregistered_candidate_not_fitted_or_promoted",
        "config": {"path": config_path.resolve().relative_to(root.resolve()).as_posix(), "sha256": sha256(config_path)},
        "implementation": {"path": Path(__file__).resolve().relative_to(root.resolve()).as_posix(), "sha256": sha256(Path(__file__))},
        "source_receipts": checked_sources,
        "training_artifact": {"path": config["training_artifact"], "sha256": config["training_artifact_sha256"]},
        "links": {"identity": ["tmean_c"], "positive_log": POSITIVE, "bounded_logit": BOUNDED, "composition": COMPOSITION},
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
    print("ISIMIP3b physical-link feature-response contract passed")


if __name__ == "__main__":
    main()
