#!/usr/bin/env python3
"""Validate the saved aggregate moisture/Tmax sensitivity without refitting."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any


PROJECT = Path(__file__).resolve().parents[2]
FROZEN_ARTIFACT_SHA256 = "49aa943d48dddfb2f5e6b946525127d50fe695783e6272d580bddccedf1524dd"
ARTIFACT = PROJECT / "data/provenance/us_moisture_tmax_sensitivity_verified_20260905.json"
INDEPENDENT_AUDIT = PROJECT / "data/provenance/us_competing_moisture_independent_audit_20260826.json"
SENSITIVITY_CODE = PROJECT / "us_county_validation/scripts/evaluate_moisture_tmax_sensitivity.py"
EVALUATOR_CODE = PROJECT / "us_county_validation/scripts/evaluate_us_competing_moisture.py"
SENSITIVITY_PROTOCOL = PROJECT / "us_county_validation/US_MOISTURE_TMAX_PROTOCOL_20260905.md"
MODEL_PROTOCOL = PROJECT / "us_county_validation/us_competing_moisture_predictive_v1.toml"
AUDIT_PROTOCOL = PROJECT / "us_county_validation/US_MOISTURE_TMAX_ARTIFACT_AUDIT_PROTOCOL_20260906.md"

MODELS = (
    "controls_only",
    "direct_quantity",
    "direct_quantity_distribution",
    "pdsi_season_mean",
    "pdsi_stage_sensitivity",
)
GEOGRAPHIC_GROUPS = {
    ("corn_grain", "irrigated"): ("CO", "KS", "ND", "NE", "SD"),
    ("corn_grain", "non_irrigated"): ("CO", "KS", "ND", "NE", "SD"),
    ("soybeans", "irrigated"): ("AR", "KS", "NE"),
    ("soybeans", "non_irrigated"): ("AR", "KS", "NE"),
}
ADDED_CONTROLS = [
    "stage1_tmax_mean_c", "stage2_tmax_mean_c", "stage3_tmax_mean_c",
    "stage1_tmax_mean_c_squared", "stage2_tmax_mean_c_squared",
    "stage3_tmax_mean_c_squared",
]
TOP_FIELDS = {
    "schema", "input_sha256", "audit_receipt_sha256", "code_sha256",
    "evaluator_sha256", "protocol_sha256", "added_level_controls",
    "causal_or_scc_result", "results",
}
RESULT_FIELDS = {
    "status", "protocol_id", "estimand",
    "models_are_mutually_exclusive_moisture_representations",
    "development_leave_state_out_used_for_distribution_selection",
    "distribution_selection_requires_predeclared_material_improvement_floor",
    "terminal_temporal_holdout_used_for_selection",
    "train_test_first_difference_level_endpoints_purged", "train_only_scaling",
    "wheat_included", "metrics", "comparison_summaries",
    "coefficients_in_output", "row_predictions_in_output", "predictive_fit_executed",
    "causal_effect_estimated", "damage_calculated", "scc_calculated",
    "required_disclaimer", "exploratory_sensitivity_not_new_registered_validation",
}
METRIC_FIELDS = {
    "crop", "irrigation_practice", "split", "split_id", "model",
    "feature_count_excluding_year_terms", "train_rows_before_endpoint_purge",
    "train_rows_purged_shared_level_endpoint", "first_difference_level_endpoints_disjoint",
    "rmse", "mae", "r2_oos", "correlation", "train_rows", "test_rows",
    "design_columns_including_intercept", "design_rank",
    "zero_variance_columns_dropped_train_only", "svd_relative_tolerance",
    "minimum_relative_training_scale", "minimum_absolute_training_scale",
    "linear_solver", "smallest_retained_to_largest_singular_value_ratio",
}
SUMMARY_FIELDS = {
    "crop", "irrigation_practice",
    "direct_distribution_selected_on_development_leave_state_out",
    "direct_distribution_rmse_improvement_each_eligible_state",
    "direct_distribution_required_material_rmse_floor_each_eligible_state",
    "direct_distribution_rmse_excess_over_material_floor_each_eligible_state",
    "direct_distribution_minimum_absolute_rmse_improvement",
    "direct_distribution_minimum_relative_rmse_improvement",
    "direct_distribution_mean_leave_state_out_rmse_improvement",
    "direct_distribution_terminal_rmse_improvement_not_used_for_selection",
    "direct_distribution_extreme_rmse_improvement_not_used_for_selection",
    "direct_quantity_minus_pdsi_season_rmse_by_eligible_state",
    "direct_quantity_minus_pdsi_season_terminal_rmse", "rmse_difference_sign",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def finite_number(value: Any, name: str) -> float:
    require(isinstance(value, (int, float)) and not isinstance(value, bool), f"{name} is not numeric")
    number = float(value)
    require(math.isfinite(number), f"{name} is not finite")
    return number


def expected_metric_keys() -> set[tuple[str, str, str, str, str]]:
    keys: set[tuple[str, str, str, str, str]] = set()
    for (crop, practice), groups in GEOGRAPHIC_GROUPS.items():
        splits = [("development_leave_state_out", group) for group in groups]
        splits += [("terminal_temporal_same_counties", "terminal"),
                   ("development_precipitation_extreme", "tails")]
        for split, split_id in splits:
            for model in MODELS:
                keys.add((crop, practice, split, split_id, model))
    return keys


def close(actual: float, expected: float, label: str, errors: list[float]) -> None:
    error = abs(actual - expected)
    errors.append(error)
    require(error <= 1e-12, f"{label} does not reconcile")


def validate_data(artifact: dict[str, Any], root: Path = PROJECT) -> dict[str, Any]:
    require(set(artifact) == TOP_FIELDS, "artifact top-level fields changed")
    require(artifact["schema"] == "us_moisture_tmax_sensitivity_v1", "artifact schema changed")
    require(artifact["added_level_controls"] == ADDED_CONTROLS, "added Tmax controls changed")
    require(artifact["causal_or_scc_result"] is False, "artifact causal/SCC gate changed")

    source_paths = {
        "code_sha256": root / SENSITIVITY_CODE.relative_to(PROJECT),
        "evaluator_sha256": root / EVALUATOR_CODE.relative_to(PROJECT),
        "protocol_sha256": root / SENSITIVITY_PROTOCOL.relative_to(PROJECT),
    }
    for field, path in source_paths.items():
        require(artifact[field] == sha256(path), f"{field} does not match the tracked source")
    audit_path = root / INDEPENDENT_AUDIT.relative_to(PROJECT)
    require(artifact["audit_receipt_sha256"] == sha256(audit_path), "independent audit hash changed")
    ledger = json.loads(audit_path.read_text(encoding="utf-8"))["hash_audit"]["sha256"]
    input_hashes = artifact["input_sha256"]
    require(set(input_hashes) == {"common", "direct_input", "pdsi_input", "direct_raw", "protocol"},
            "input hash fields changed")
    for name, digest in input_hashes.items():
        require(digest == ledger[name], f"{name} hash differs from independent audit ledger")
    require(input_hashes["protocol"] == sha256(root / MODEL_PROTOCOL.relative_to(PROJECT)),
            "registered model protocol hash changed")
    require(artifact["evaluator_sha256"] == ledger["registered_evaluator"],
            "evaluator differs from independent audit ledger")

    require(set(artifact["results"]) == {"baseline", "additional_stage_tmax"},
            "sensitivity labels changed")
    expected_keys = expected_metric_keys()
    require(len(expected_keys) == 120, "internal expected support error")
    indexes: dict[str, dict[tuple[str, str, str, str, str], dict[str, Any]]] = {}
    max_errors: list[float] = []
    promotion_states: dict[str, dict[str, bool]] = {}
    terminal_table: dict[str, dict[str, dict[str, float]]] = {}

    semantic = {
        "status": "aggregate_noncausal_predictive_diagnostic_complete",
        "protocol_id": "us_corn_soy_competing_moisture_predictive_v1",
        "estimand": "out-of-sample prediction of consecutive-year change in log county yield",
        "models_are_mutually_exclusive_moisture_representations": True,
        "development_leave_state_out_used_for_distribution_selection": True,
        "distribution_selection_requires_predeclared_material_improvement_floor": True,
        "terminal_temporal_holdout_used_for_selection": False,
        "train_test_first_difference_level_endpoints_purged": True,
        "train_only_scaling": True,
        "wheat_included": False,
        "coefficients_in_output": False,
        "row_predictions_in_output": False,
        "predictive_fit_executed": True,
        "causal_effect_estimated": False,
        "damage_calculated": False,
        "scc_calculated": False,
        "required_disclaimer": "Predictive validation is not a causal climate-yield estimate and cannot be used as a damage function or SCC input.",
        "exploratory_sensitivity_not_new_registered_validation": True,
    }

    for label, result in artifact["results"].items():
        require(set(result) == RESULT_FIELDS, f"{label} result fields changed")
        for field, expected in semantic.items():
            require(result[field] == expected, f"{label} semantic gate changed: {field}")
        metrics = result["metrics"]
        require(isinstance(metrics, list) and len(metrics) == 120, f"{label} metric row count changed")
        index: dict[tuple[str, str, str, str, str], dict[str, Any]] = {}
        samples: dict[tuple[str, str, str, str], tuple[int, int, int, int]] = {}
        for row in metrics:
            require(set(row) == METRIC_FIELDS, f"{label} metric fields changed")
            key = tuple(str(row[field]) for field in ("crop", "irrigation_practice", "split", "split_id", "model"))
            require(key not in index, f"{label} duplicate metric key")
            index[key] = row
            for field in ("rmse", "mae", "r2_oos", "correlation",
                          "smallest_retained_to_largest_singular_value_ratio"):
                finite_number(row[field], f"{label} {key} {field}")
            for field in ("feature_count_excluding_year_terms", "train_rows_before_endpoint_purge",
                          "train_rows_purged_shared_level_endpoint", "train_rows", "test_rows",
                          "design_columns_including_intercept", "design_rank",
                          "zero_variance_columns_dropped_train_only"):
                require(isinstance(row[field], int) and not isinstance(row[field], bool),
                        f"{label} {key} {field} is not an integer")
            require(row["train_rows"] > 0 and row["test_rows"] > 0, f"{label} {key} has empty support")
            require(row["first_difference_level_endpoints_disjoint"] is True,
                    f"{label} {key} endpoint-disjoint gate changed")
            require(row["design_rank"] == row["design_columns_including_intercept"],
                    f"{label} {key} retained design is not full rank")
            require(row["design_columns_including_intercept"]
                    == row["feature_count_excluding_year_terms"] + 3 - row["zero_variance_columns_dropped_train_only"],
                    f"{label} {key} design-column accounting changed")
            require(row["train_rows_before_endpoint_purge"] - row["train_rows_purged_shared_level_endpoint"]
                    == row["train_rows"], f"{label} {key} endpoint-purge accounting changed")
            require(row["linear_solver"] == "numpy_lstsq_with_registered_relative_svd_cutoff",
                    f"{label} {key} solver changed")
            require(row["svd_relative_tolerance"] == 1e-10
                    and row["minimum_relative_training_scale"] == 1e-8
                    and row["minimum_absolute_training_scale"] == 1e-10,
                    f"{label} {key} numerical safeguards changed")
            sample_key = key[:4]
            sample = tuple(row[field] for field in (
                "train_rows_before_endpoint_purge", "train_rows_purged_shared_level_endpoint",
                "train_rows", "test_rows"))
            require(sample_key not in samples or samples[sample_key] == sample,
                    f"{label} model sample counts differ within a scored split")
            samples[sample_key] = sample
        require(set(index) == expected_keys, f"{label} metric support changed")
        indexes[label] = index

        summaries = result["comparison_summaries"]
        require(isinstance(summaries, list) and len(summaries) == 4, f"{label} summary count changed")
        summary_index: dict[tuple[str, str], dict[str, Any]] = {}
        for summary in summaries:
            require(set(summary) == SUMMARY_FIELDS, f"{label} summary fields changed")
            cp = (str(summary["crop"]), str(summary["irrigation_practice"]))
            require(cp in GEOGRAPHIC_GROUPS and cp not in summary_index, f"{label} summary support changed")
            summary_index[cp] = summary
            states = GEOGRAPHIC_GROUPS[cp]
            minimum_absolute = 0.0001
            minimum_relative = 0.01
            require(summary["direct_distribution_minimum_absolute_rmse_improvement"] == minimum_absolute
                    and summary["direct_distribution_minimum_relative_rmse_improvement"] == minimum_relative,
                    f"{label} promotion thresholds changed")
            improvements: dict[str, float] = {}
            floors: dict[str, float] = {}
            excess: dict[str, float] = {}
            for state in states:
                prefix = (*cp, "development_leave_state_out", state)
                quantity = finite_number(index[(*prefix, "direct_quantity")]["rmse"], "quantity RMSE")
                distribution = finite_number(index[(*prefix, "direct_quantity_distribution")]["rmse"], "distribution RMSE")
                improvement = quantity - distribution
                floor = max(minimum_absolute, minimum_relative * quantity)
                improvements[state], floors[state], excess[state] = improvement, floor, improvement - floor
            for field, expected_map in (
                ("direct_distribution_rmse_improvement_each_eligible_state", improvements),
                ("direct_distribution_required_material_rmse_floor_each_eligible_state", floors),
                ("direct_distribution_rmse_excess_over_material_floor_each_eligible_state", excess),
            ):
                actual_map = summary[field]
                require(set(actual_map) == set(states), f"{label} {cp} {field} support changed")
                for state in states:
                    close(finite_number(actual_map[state], field), expected_map[state], field, max_errors)
            selected = all(value >= 0 for value in excess.values())
            require(summary["direct_distribution_selected_on_development_leave_state_out"] is selected,
                    f"{label} {cp} promotion decision changed")
            close(finite_number(summary["direct_distribution_mean_leave_state_out_rmse_improvement"], "mean improvement"),
                  math.fsum(improvements.values()) / len(improvements), "mean geographic improvement", max_errors)

            def rmse_difference(split: str, split_id: str, left: str, right: str) -> float:
                prefix = (*cp, split, split_id)
                return finite_number(index[(*prefix, left)]["rmse"], left) - finite_number(index[(*prefix, right)]["rmse"], right)

            close(finite_number(summary["direct_distribution_terminal_rmse_improvement_not_used_for_selection"], "terminal improvement"),
                  rmse_difference("terminal_temporal_same_counties", "terminal", "direct_quantity", "direct_quantity_distribution"),
                  "terminal improvement", max_errors)
            close(finite_number(summary["direct_distribution_extreme_rmse_improvement_not_used_for_selection"], "tail improvement"),
                  rmse_difference("development_precipitation_extreme", "tails", "direct_quantity", "direct_quantity_distribution"),
                  "tail improvement", max_errors)
            actual_pdsi = summary["direct_quantity_minus_pdsi_season_rmse_by_eligible_state"]
            require(set(actual_pdsi) == set(states), f"{label} {cp} PDSI comparison support changed")
            for state in states:
                close(finite_number(actual_pdsi[state], "PDSI comparison"),
                      rmse_difference("development_leave_state_out", state, "direct_quantity", "pdsi_season_mean"),
                      "state PDSI comparison", max_errors)
            close(finite_number(summary["direct_quantity_minus_pdsi_season_terminal_rmse"], "terminal PDSI comparison"),
                  rmse_difference("terminal_temporal_same_counties", "terminal", "direct_quantity", "pdsi_season_mean"),
                  "terminal PDSI comparison", max_errors)
            require(summary["rmse_difference_sign"] == "positive means the second named model has lower RMSE",
                    f"{label} comparison sign convention changed")
        require(set(summary_index) == set(GEOGRAPHIC_GROUPS), f"{label} summary keys changed")
        promotion_states[label] = {
            f"{crop}/{practice}": bool(summary_index[(crop, practice)]["direct_distribution_selected_on_development_leave_state_out"])
            for crop, practice in GEOGRAPHIC_GROUPS
        }
        terminal_table[label] = {}
        for crop in ("corn_grain", "soybeans"):
            terminal_table[label][crop] = {
                model: finite_number(index[(crop, "non_irrigated", "terminal_temporal_same_counties", "terminal", model)]["rmse"], "terminal RMSE")
                for model in MODELS
            }

    require(set(indexes["baseline"]) == set(indexes["additional_stage_tmax"]),
            "baseline and richer-Tmax scored support differs")
    for key in expected_keys:
        before = indexes["baseline"][key]["feature_count_excluding_year_terms"]
        after = indexes["additional_stage_tmax"][key]["feature_count_excluding_year_terms"]
        require(after == before + 6, f"{key} does not add exactly six Tmax controls")

    require(promotion_states["baseline"] == {
        "corn_grain/irrigated": False, "corn_grain/non_irrigated": False,
        "soybeans/irrigated": True, "soybeans/non_irrigated": True,
    }, "baseline qualitative promotion result changed")
    require(not any(promotion_states["additional_stage_tmax"].values()),
            "richer-Tmax qualitative promotion result changed")
    soy_summary = next(item for item in artifact["results"]["additional_stage_tmax"]["comparison_summaries"]
                       if item["crop"] == "soybeans" and item["irrigation_practice"] == "non_irrigated")
    soy_improvements = soy_summary["direct_distribution_rmse_improvement_each_eligible_state"]
    soy_excess = soy_summary["direct_distribution_rmse_excess_over_material_floor_each_eligible_state"]
    require(all(soy_improvements[state] > 0 for state in ("AR", "KS", "NE")),
            "richer-Tmax non-irrigated soybean improvement sign changed")
    require({state for state, value in soy_excess.items() if value < 0} == {"NE"},
            "richer-Tmax non-irrigated soybean materiality pattern changed")

    return {
        "schema": "us_moisture_tmax_artifact_audit_v1",
        "status": "passed_saved_aggregate_artifact_and_claim_reconciliation",
        "inputs": {
            "verified_artifact_sha256": FROZEN_ARTIFACT_SHA256,
            "independent_audit_sha256": artifact["audit_receipt_sha256"],
            "sensitivity_code_sha256": artifact["code_sha256"],
            "evaluator_sha256": artifact["evaluator_sha256"],
            "sensitivity_protocol_sha256": artifact["protocol_sha256"],
            "model_protocol_sha256": input_hashes["protocol"],
        },
        "metric_rows_per_specification": 120,
        "metric_rows_total": 240,
        "comparison_summaries_total": 8,
        "scored_support_identical": True,
        "all_retained_designs_full_rank": True,
        "all_first_difference_endpoints_disjoint": True,
        "maximum_absolute_summary_reconciliation_error": max(max_errors, default=0.0),
        "promotion_states": promotion_states,
        "richer_tmax_non_irrigated_soybean_improvements": soy_improvements,
        "richer_tmax_non_irrigated_soybean_excess_over_floor": soy_excess,
        "terminal_non_irrigated_rmse": terminal_table,
        "raw_or_interim_data_read": False,
        "model_refit": False,
        "coefficients_or_row_predictions_emitted": False,
        "causal_effect_estimated": False,
        "damage_calculated": False,
        "welfare_calculated": False,
        "scc_calculated": False,
        "interpretation": "Internal aggregate-artifact and written-claim audit only; not an independent empirical replication.",
    }


def validate_path(path: Path, root: Path = PROJECT) -> dict[str, Any]:
    require(sha256(path) == FROZEN_ARTIFACT_SHA256, "verified artifact content hash changed")
    return validate_data(json.loads(path.read_text(encoding="utf-8")), root)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact", type=Path, default=ARTIFACT)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    require(not args.out.exists(), "audit output already exists")
    result = validate_path(args.artifact)
    result["audit_protocol_sha256"] = sha256(AUDIT_PROTOCOL)
    result["audit_code_sha256"] = sha256(Path(__file__))
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print("moisture/Tmax aggregate artifact audit passed: 240 metrics, 8 summaries")


if __name__ == "__main__":
    main()
