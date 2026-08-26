#!/usr/bin/env python3
"""Fail-closed validation for the SPEI design contract; performs no fitting."""
from __future__ import annotations

import argparse
import tomllib
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONTRACT = PROJECT_ROOT / "config/spei_competitor_v1.toml"
FALSE_GATES = (
    "index_construction_authorized",
    "predictive_diagnostic_fit_authorized",
    "coefficient_export_authorized",
    "causal_interpretation_authorized",
    "damage_calculation_authorized",
    "future_projection_authorized",
    "scc_authorized",
    "selection_by_scc_authorized",
)


def _section(contract: dict[str, Any], name: str) -> dict[str, Any]:
    value = contract.get(name)
    if not isinstance(value, dict):
        raise ValueError(f"SPEI contract lacks [{name}]")
    return value


def _exact_false(section: dict[str, Any], key: str, label: str) -> None:
    if section.get(key) is not False:
        raise ValueError(f"{label}.{key} must be exactly false")


def _exact_true(section: dict[str, Any], key: str, label: str) -> None:
    if section.get(key) is not True:
        raise ValueError(f"{label}.{key} must be exactly true")


def _resolve(project_root: Path, value: Any, label: str) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a nonblank path")
    path = Path(value)
    resolved = path if path.is_absolute() else project_root / path
    if not resolved.exists():
        raise ValueError(f"{label} does not exist: {resolved}")
    return resolved


def _declared_relative(project_root: Path, value: Any, label: str) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a nonblank path")
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"{label} must remain project-relative")
    return project_root / path


def validate_contract(
    contract: dict[str, Any],
    project_root: Path = PROJECT_ROOT,
    *,
    require_local_inputs: bool = False,
) -> None:
    if contract.get("schema_version") != 1 or contract.get("contract_id") != "spei_competitor_v1":
        raise ValueError("unexpected SPEI schema or contract identity")
    if contract.get("status") != (
        "source_and_method_locked_bounded_engineering_pipeline_implemented_gates_closed"
    ):
        raise ValueError("SPEI implementation status drifted")
    if contract.get("reference_date") != "2026-08-26":
        raise ValueError("SPEI source decision date drifted")
    for gate in FALSE_GATES:
        _exact_false(contract, gate, "root")

    decision = _section(contract, "source_decision")
    if decision.get("primary_route") != "compute_from_source_consistent_daily_weather":
        raise ValueError("published or mixed-source SPEI cannot be the primary route")
    if decision.get("large_download_required_for_primary") is not False:
        raise ValueError("primary route unexpectedly depends on a large download")
    for key in ("published_noaa_role", "published_speibase_role"):
        role = str(decision.get(key, ""))
        if "retrospective" not in role or "not_terminal_score" not in role:
            raise ValueError(f"{key} must remain outside terminal scoring")
    _resolve(project_root, decision.get("source_decision_provenance"), "source decision provenance")

    method = _section(contract, "method")
    expected_method = {
        "pet_method": "hargreaves_samani_1985_daily",
        "distribution": "log_logistic_three_parameter",
        "fit_method": "unbiased_probability_weighted_moments",
        "accumulation_kernel": "rectangular_right_aligned_including_current_month",
        "fit_scope": "separately_by_native_grid_cell_and_calendar_month_for_each_scale",
    }
    for key, expected in expected_method.items():
        if method.get(key) != expected:
            raise ValueError(f"method.{key} differs from the locked design")
    if method.get("accumulation_scales_months") != [1, 3, 6]:
        raise ValueError("SPEI scales must be exactly 1, 3, and 6 months")
    if method.get("tmean_definition") != "arithmetic_mean_of_daily_tmin_and_tmax_not_source_tavg_or_tas":
        raise ValueError("Hargreaves Tmean definition drifted")
    if method.get("standardization") != "inverse_standard_normal_cdf_of_fitted_log_logistic_cdf_negative_is_dry":
        raise ValueError("SPEI sign or standardization rule drifted")
    if method.get("cdf_probability_clip_epsilon") != 1e-12:
        raise ValueError("SPEI numerical tail clip drifted")
    _exact_true(method, "tail_clip_audit_required", "method")
    _exact_true(method, "scales_reported_separately", "method")
    _exact_false(method, "scales_selected_by_outcome", "method")
    _exact_false(method, "scales_stacked", "method")
    _exact_false(method, "irrigation_in_index", "method")
    if "max(0, 0.0023 * 0.408" not in str(method.get("pet_equation", "")):
        raise ValueError("Hargreaves equation/units are not explicitly locked")

    calibration = _section(contract, "calibration")
    start, end = calibration.get("start_year"), calibration.get("end_year")
    holdout, warmup = calibration.get("terminal_holdout_start_year"), calibration.get("warmup_source_start_year")
    if (start, end, holdout, warmup) != (1982, 2011, 2012, 1981):
        raise ValueError("calibration, warm-up, or terminal holdout boundary drifted")
    if end - start + 1 != calibration.get("minimum_years_per_calendar_month"):
        raise ValueError("calibration does not provide exactly the locked 30 years")
    if not (warmup <= start - 1 and end < holdout):
        raise ValueError("SPEI calibration overlaps holdout or lacks maximum-scale warm-up")
    _exact_false(calibration, "post_holdout_climate_in_calibration_allowed", "calibration")
    _exact_false(calibration, "outcomes_in_calibration_allowed", "calibration")

    features = _section(contract, "features")
    if features.get("temporal_availability_role") != "retrospective_crop_season_exposure_not_an_operational_within_season_forecast":
        raise ValueError("monthly SPEI temporal-availability role drifted")
    if "complete calendar month" not in str(features.get("boundary_month_caveat", "")):
        raise ValueError("partial boundary-month limitation is not disclosed")

    expected_panels = {
        "us_county": {
            "weather_source_id": "nclimgrid_daily_v1_0_0_20220829",
            "required_variables": ["prcp", "tavg", "tmax", "tmin"],
            "level_key": "level_keys",
            "level_values": ["county_geoid", "outcome_crop", "harvest_year", "irrigation_practice"],
            "family_values": ["direct_precipitation", "pdsi", "spei_1", "spei_3", "spei_6"],
        },
        "global": {
            "weather_source_id": "isimip3a_gswp3_w5e5_obsclim_v1_3",
            "required_variables": ["pr", "tas", "tasmax", "tasmin"],
            "level_key": "level_keys_after_allocation",
            "level_values": ["harvest_year", "lat", "lon_360", "crop"],
            "family_values": ["direct_precipitation", "scpdsi", "spei_1", "spei_3", "spei_6"],
        },
    }
    for name, expected in expected_panels.items():
        panel = _section(contract, name)
        if panel.get("weather_source_id") != expected["weather_source_id"]:
            raise ValueError(f"{name} weather source drifted")
        if panel.get("required_variables") != expected["required_variables"]:
            raise ValueError(f"{name} required PET/weather variables drifted")
        if panel.get(expected["level_key"]) != expected["level_values"]:
            raise ValueError(f"{name} exact comparison keys drifted")
        if panel.get("comparison_families") != expected["family_values"]:
            raise ValueError(f"{name} master common-support families drifted")
        if panel.get("source_year_start") != 1981 or panel.get("terminal_holdout_start_year") != 2012:
            raise ValueError(f"{name} source or holdout boundary drifted")
        weather_root = _declared_relative(project_root, panel.get("weather_root"), f"{name} weather root")
        if require_local_inputs and not weather_root.is_dir():
            raise ValueError(f"{name} weather root does not exist: {weather_root}")
        provenance_key = "weather_provenance_smoke" if name == "us_county" else "weather_provenance"
        _resolve(project_root, panel.get(provenance_key), f"{name} weather provenance")
    global_panel = _section(contract, "global")
    if global_panel.get("preplant90_global_year_start") != 1983:
        raise ValueError("global preplant90 boundary must remain 1983 without pre-1981 weather")
    if global_panel.get("source_start_month") != "1981-01":
        raise ValueError("global monthly source boundary drifted")
    coverage_rule = str(global_panel.get("antecedent_coverage_rule", ""))
    if "earliest required water-balance month" not in coverage_rule or "every family" not in coverage_rule:
        raise ValueError("global algorithmic antecedent-coverage rule drifted")
    _exact_true(global_panel, "preconstruction_coverage_receipt_required", "global")
    _exact_true(global_panel, "preconstruction_coverage_receipt_hash_required", "global")
    if global_panel.get("terminal_ranking_eligible_families") != [
        "direct_precipitation", "spei_1", "spei_3", "spei_6"
    ]:
        raise ValueError("retrospectively calibrated scPDSI entered terminal ranking")
    if global_panel.get("scpdsi_temporal_role") != (
        "retrospective_context_only_full_record_calibration_not_eligible_for_terminal_promotion"
    ):
        raise ValueError("global scPDSI retrospective role drifted")

    support = _section(contract, "common_support")
    if support.get("mode") != "one_master_inner_intersection_across_every_reported_moisture_family_and_scale":
        raise ValueError("common support is not the locked master intersection")
    for key in (
        "outcomes_equal_exactly",
        "calendar_lineage_equal_exactly",
        "allocation_weights_equal_exactly",
        "common_temperature_and_heat_controls_equal_exactly",
        "split_labels_equal_exactly",
        "test_key_hashes_equal_exactly",
        "first_difference_endpoint_purging_required",
        "support_loss_audit_required",
    ):
        _exact_true(support, key, "common_support")
    _exact_false(support, "family_specific_imputation_allowed", "common_support")

    exclusion = _section(contract, "mutual_exclusivity")
    if exclusion.get("maximum_moisture_families_per_model") != 1:
        raise ValueError("models may contain exactly one moisture family at most")
    if exclusion.get("maximum_spei_scales_per_model") != 1:
        raise ValueError("models may contain exactly one SPEI scale at most")
    for key in (
        "direct_precipitation_in_spei_model",
        "pdsi_or_scpdsi_in_spei_model",
        "raw_pet_in_any_outcome_model",
        "family_effects_may_be_summed",
    ):
        _exact_false(exclusion, key, "mutual_exclusivity")
    _exact_true(
        exclusion,
        "common_temperature_and_heat_controls_allowed_in_every_model",
        "mutual_exclusivity",
    )

    bounded = _section(contract, "bounded_construction")
    expected_bounded = {
        "status": "engineering_verification_only_not_production_index_authorization",
        "runner": "scripts/build_spei_grid_chunk.py",
        "maximum_native_grid_cells_per_invocation": 64,
        "nclimgrid_checkpoint": "one_calendar_year",
        "global_checkpoint": "one_calendar_year_within_each_decadal_source_file",
        "source_start_date": "1981-01-01",
        "source_end_date": "2019-12-31",
        "expected_daily_steps": 14244,
        "expected_monthly_steps": 468,
        "environment_mismatch_rule": "fail_closed_and_require_a_fresh_output_root",
        "numerical_environment_fields": [
            "python_implementation",
            "python_version",
            "python_cache_tag",
            "platform_system",
            "platform_release",
            "platform_machine",
            "byteorder",
            "numpy",
            "pandas",
            "xarray",
            "h5py",
            "hdf5",
            "h5netcdf",
        ],
        "required_receipts": [
            "contract_receipt.json",
            "source_receipt.json",
            "output_receipt.json",
        ],
        "output_format": "netcdf4_h5netcdf",
        "output_role": "bounded_native_grid_engineering_diagnostic_only",
    }
    for key, expected in expected_bounded.items():
        if bounded.get(key) != expected:
            raise ValueError(f"bounded_construction.{key} differs from the locked pipeline")
    for key in (
        "source_sha512_recomputation_required",
        "source_file_set_exactness_required",
        "source_daily_calendar_exactness_required",
        "source_variable_units_exactness_required",
        "source_coordinate_alignment_required",
        "numerical_environment_in_run_signature_required",
        "numerical_environment_in_checkpoint_identity_required",
        "require_at_least_one_fully_fitted_cell",
    ):
        _exact_true(bounded, key, "bounded_construction")
    for key in ("full_grid_invocation_allowed", "outcome_input_allowed", "imputation_allowed"):
        _exact_false(bounded, key, "bounded_construction")
    _resolve(project_root, bounded.get("runner"), "bounded SPEI runner")

def load_contract(path: Path) -> dict[str, Any]:
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise ValueError(f"cannot read SPEI contract {path}") from error


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", default=str(DEFAULT_CONTRACT))
    parser.add_argument(
        "--require-local-inputs",
        action="store_true",
        help="also require the ignored local daily-weather roots to be present",
    )
    args = parser.parse_args()
    contract = load_contract(Path(args.contract))
    validate_contract(contract, require_local_inputs=args.require_local_inputs)
    print(
        "SPEI design contract valid; production_construction=false; "
        "bounded_engineering=true; predictive_fit=false; "
        f"local_inputs_checked={str(args.require_local_inputs).lower()}"
    )


if __name__ == "__main__":
    main()
