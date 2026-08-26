#!/usr/bin/env python3
"""Fail closed when a diagnostic response subset is mistaken for production.

This validator does not select a model or a threshold.  It checks that the
not-yet-frozen production design registry retains every owner-approved feature
comparison, keeps competing drought representations separate, and labels the
existing frozen predictive specification as an incomplete, SCC-ineligible
diagnostic subset.
"""
from __future__ import annotations

import argparse
import json
import tomllib
from pathlib import Path
from typing import Any


STATUS = "validated_response_scope_boundary_not_production_authorization"
REQUIRED_FEATURE_REQUIREMENTS = {
    "seasonal_precipitation_quantity",
    "stage_precipitation_quantity",
    "normalized_stage_distribution_and_timing",
    "wet_day_frequency",
    "wet_day_intensity",
    "consecutive_dry_days",
    "rx1day_wet_extreme",
    "rx5day_wet_extreme",
    "mean_temperature",
    "heat_extremes",
    "temperature_precipitation_interactions",
}
REQUIRED_WATER_STRESS_FAMILIES = {
    "direct_precipitation_pattern",
    "climatic_water_balance",
    "soil_moisture",
}
EXPECTED_FROZEN_DIAGNOSTIC_GAPS = {
    "normalized_stage_distribution_and_timing",
    "wet_day_frequency",
    "wet_day_intensity",
    "rx5day_wet_extreme",
    "heat_extremes",
}
VALID_DIAGNOSTIC_COVERAGE = {"covered", "partial", "omitted"}
EXPECTED_REAL_PANEL_STATUS = (
    "maize_soy_1982_1989_and_2012_2016_mirca2000_direct_diagnostics_passed_"
    "historical_1982_1989_and_2012_2016_scpdsi_candidate_data_passed_but_"
    "unfitted_other_panels_pending"
)


def load_toml(path: Path) -> dict[str, Any]:
    return tomllib.loads(path.read_text(encoding="utf-8"))


def _unique_records(records: Any, name: str) -> dict[str, dict[str, Any]]:
    if not isinstance(records, list) or not records:
        raise ValueError(f"{name} must be a nonempty array of tables")
    indexed: dict[str, dict[str, Any]] = {}
    for record in records:
        if not isinstance(record, dict):
            raise ValueError(f"{name} entries must be tables")
        identifier = record.get("id")
        if not isinstance(identifier, str) or not identifier:
            raise ValueError(f"{name} entries require a nonempty id")
        if identifier in indexed:
            raise ValueError(f"{name} has duplicate id {identifier!r}")
        indexed[identifier] = record
    return indexed


def _nonempty_string_list(value: Any, name: str) -> list[str]:
    if (
        not isinstance(value, list)
        or not value
        or any(not isinstance(item, str) or not item.strip() for item in value)
        or len(value) != len(set(value))
    ):
        raise ValueError(f"{name} must be a nonempty unique string list")
    return value


def _diagnostic_features(spec: dict[str, Any]) -> tuple[list[str], set[str]]:
    models = spec.get("models")
    if not isinstance(models, dict) or not models:
        raise ValueError("Diagnostic specification must declare models")
    names: list[str] = []
    features: set[str] = set()
    for model, entry in models.items():
        if not isinstance(model, str) or not isinstance(entry, dict):
            raise ValueError("Diagnostic model declarations are invalid")
        values = _nonempty_string_list(entry.get("features"), f"diagnostic model {model} features")
        names.append(model)
        features.update(values)
    return names, features


def validate_boundaries(
    production: dict[str, Any], diagnostic: dict[str, Any]
) -> dict[str, Any]:
    if production.get("specification_kind") != "production causal-model design registry":
        raise ValueError("Production specification kind is missing or unrecognized")
    if production.get("freeze_status") != "not_frozen":
        raise ValueError("Production response must remain explicitly not frozen at this stage")
    for field in ("fit_authorized", "response_draw_export_authorized", "scc_use_authorized"):
        if production.get(field) is not False:
            raise ValueError(f"{field} must be false until the production causal specification is frozen")

    diagnostic_boundary = production.get("diagnostic_boundary", {})
    if diagnostic_boundary.get("frozen_predictive_spec_is_production_eligible") is not False:
        raise ValueError("Frozen predictive diagnostic must be explicitly production-ineligible")
    if "cannot become" not in str(diagnostic_boundary.get("promotion_rule", "")):
        raise ValueError("Diagnostic-to-production promotion rule is not fail-closed")
    source_boundary = diagnostic.get("boundary", {})
    if source_boundary.get("status") != "diagnostic held-out predictive comparison only":
        raise ValueError("Diagnostic source no longer carries its frozen diagnostic-only status")
    source_forbidden = str(source_boundary.get("forbidden", "")).lower()
    if "causal" not in source_forbidden or "scc" not in source_forbidden:
        raise ValueError("Diagnostic source must forbid both causal and SCC interpretation")
    source_holdouts = diagnostic.get("holdouts", {})
    for holdout in ("temporal", "extreme"):
        holdout_rule = str(source_holdouts.get(holdout, "")).lower()
        if "purg" not in holdout_rule or "unpurged" in holdout_rule:
            raise ValueError(f"Diagnostic {holdout} holdout must declare its endpoint purge")
    diagnostic_models, diagnostic_features = _diagnostic_features(diagnostic)

    hierarchy = production.get("model_hierarchy", {})
    if hierarchy.get("primary_selection_status") != "not_frozen":
        raise ValueError("Evidence-led primary model selection must remain not frozen")
    reference = str(hierarchy.get("parsimonious_reference", "")).lower()
    if "temperature" not in reference or "precipitation quantity" not in reference:
        raise ValueError("Model hierarchy must retain the joint seasonal-quantity reference")
    distribution_rule = str(hierarchy.get("distribution_retention_rule", "")).lower()
    if not all(term in distribution_rule for term in ("incremental", "out-of-sample", "robust", "stable")):
        raise ValueError("Distribution terms require robust stable incremental out-of-sample value")
    adverse_rule = str(hierarchy.get("null_and_adverse_result_rule", "")).lower()
    if not all(term in adverse_rule for term in ("null", "worse", "quantity")):
        raise ValueError("Hierarchy must report null/worse results and allow the quantity reference")
    drought_status = str(hierarchy.get("drought_family_status", "")).lower()
    if not all(term in drought_status for term in ("pdsi", "spei", "competing", "outer holdouts")):
        raise ValueError("PDSI/scPDSI and SPEI must remain serious competing families")
    if "replace" not in str(hierarchy.get("nonstacking_rule", "")).lower():
        raise ValueError("Water-stress families must replace rather than mechanically stack")
    if "scc magnitude" not in str(hierarchy.get("selection_target", "")).lower():
        raise ValueError("Model selection must explicitly forbid choosing by SCC magnitude")

    requirements = _unique_records(
        production.get("production_feature_requirements"), "production_feature_requirements"
    )
    missing_requirements = REQUIRED_FEATURE_REQUIREMENTS - set(requirements)
    if missing_requirements:
        raise ValueError(f"Production registry silently dropped required features {sorted(missing_requirements)}")

    coverage: dict[str, str] = {}
    for identifier in sorted(REQUIRED_FEATURE_REQUIREMENTS):
        record = requirements[identifier]
        if record.get("required_for_production_comparison") is not True:
            raise ValueError(f"{identifier} must remain required for a production comparison")
        _nonempty_string_list(record.get("construction_outputs"), f"{identifier}.construction_outputs")
        _nonempty_string_list(record.get("candidate_model_terms"), f"{identifier}.candidate_model_terms")
        _nonempty_string_list(record.get("literature_basis"), f"{identifier}.literature_basis")
        if record.get("model_form_status") != "not_frozen":
            raise ValueError(f"{identifier} model form must remain not frozen pending evidence")
        declared = record.get("diagnostic_coverage")
        if declared not in VALID_DIAGNOSTIC_COVERAGE:
            raise ValueError(f"{identifier} has invalid diagnostic coverage {declared!r}")
        present = record.get("diagnostic_present_features")
        absent = record.get("diagnostic_absent_features")
        if not isinstance(present, list) or not isinstance(absent, list):
            raise ValueError(f"{identifier} diagnostic feature audits must be lists")
        if len(present) != len(set(present)) or len(absent) != len(set(absent)):
            raise ValueError(f"{identifier} diagnostic feature audits contain duplicates")
        unexpected_missing = set(present) - diagnostic_features
        unexpected_present = set(absent) & diagnostic_features
        if unexpected_missing:
            raise ValueError(
                f"{identifier} claims diagnostic features that are absent {sorted(unexpected_missing)}"
            )
        if unexpected_present:
            raise ValueError(
                f"{identifier} claims diagnostic omissions that are present {sorted(unexpected_present)}"
            )
        if declared == "covered" and (not present or absent):
            raise ValueError(f"{identifier} covered declaration must have present and no absent features")
        if declared == "partial" and (not present or not absent):
            raise ValueError(f"{identifier} partial declaration must identify present and absent features")
        if declared == "omitted" and (present or not absent):
            raise ValueError(f"{identifier} omitted declaration must identify only absent features")
        coverage[identifier] = declared

    observed_gaps = {identifier for identifier, value in coverage.items() if value != "covered"}
    if observed_gaps != EXPECTED_FROZEN_DIAGNOSTIC_GAPS:
        raise ValueError(
            "Frozen diagnostic gap set changed; update it only through a new diagnostic version, "
            f"not by relabeling the old one (observed={sorted(observed_gaps)})"
        )

    thresholds = production.get("threshold_registry", {})
    if thresholds.get("status") != "not_frozen":
        raise ValueError("Production threshold registry must remain not frozen")
    for field in (
        "production_wet_day_thresholds_mm",
        "production_heat_thresholds_c",
        "production_drought_thresholds",
    ):
        if thresholds.get(field) != []:
            raise ValueError(f"{field} must remain empty until supported and preregistered")

    water_families = _unique_records(production.get("water_stress_families"), "water_stress_families")
    missing_water = REQUIRED_WATER_STRESS_FAMILIES - set(water_families)
    if missing_water:
        raise ValueError(f"Production registry silently dropped drought families {sorted(missing_water)}")
    for identifier in REQUIRED_WATER_STRESS_FAMILIES:
        family = water_families[identifier]
        _nonempty_string_list(family.get("members"), f"{identifier}.members")
        if family.get("production_use_authorized") is not False:
            raise ValueError(f"{identifier} cannot be production-authorized before comparison")
        if family.get("exclusive_group") != "water_stress_representation":
            raise ValueError(f"{identifier} must remain in the non-stacking water-stress group")
    comparison = production.get("water_stress_comparison", {})
    if set(comparison.get("required_families", [])) != REQUIRED_WATER_STRESS_FAMILIES:
        raise ValueError("Water-stress comparison does not retain every required family")
    if comparison.get("simultaneous_stacking_allowed") is not False:
        raise ValueError("Competing drought families must not be stacked")
    if comparison.get("selection_status") != "not_frozen":
        raise ValueError("Drought-family selection must remain not frozen")

    fixed_effects = production.get("fixed_effects", {})
    if fixed_effects.get("outcome_cell") != "lat_lon_crop_season":
        raise ValueError("Aggregate observed yield requires crop-season cell fixed effects without irrigation")
    if "not an outcome fixed-effect" not in str(fixed_effects.get("irrigation_dimension_rule", "")):
        raise ValueError("Fixed-effect registry must not create an irrigation outcome dimension")
    if fixed_effects.get("first_difference_vs_level_fixed_effects_status") != "not_frozen":
        raise ValueError("First-difference versus level fixed-effects identification remains unresolved")
    _nonempty_string_list(fixed_effects.get("time_shock_candidates"), "fixed_effects.time_shock_candidates")

    validation = production.get("validation_boundary", {})
    if validation.get("production_requires_purged_observation_disjoint_temporal_extreme_splits") is not True:
        raise ValueError("Production promotion must require purged observation-disjoint temporal/extreme splits")
    if validation.get("production_split_implementation_status") != "implemented_and_synthetic_tests_pass":
        raise ValueError("Purged split implementation must retain its reviewed synthetic-test status")
    if validation.get("real_panel_rerun_status") != EXPECTED_REAL_PANEL_STATUS:
        raise ValueError("Real-panel rerun status must preserve the reviewed partial-coverage boundary")
    if "share" not in str(validation.get("legacy_reported_temporal_extreme_split_status", "")).lower():
        raise ValueError("Legacy diagnostic status must disclose shared first-difference endpoints")
    current_split = str(validation.get("current_temporal_extreme_split_status", "")).lower()
    if "purges" not in current_split or "yield endpoint" not in current_split:
        raise ValueError("Current diagnostic must disclose its yield-endpoint purge")
    current_interpretation = str(validation.get("current_temporal_extreme_interpretation", "")).lower()
    if "noncausal" not in current_interpretation or "scc-ineligible" not in current_interpretation:
        raise ValueError("Purged diagnostic must remain noncausal and SCC-ineligible")

    integration = production.get("integration_boundary", {})
    if integration.get("production_eligible") is not False:
        raise ValueError("Current coarse aggregation interface must remain production-ineligible")
    if "plumbing" not in str(integration.get("current_status", "")).lower():
        raise ValueError("Integration boundary must identify the current component as plumbing only")
    if not str(integration.get("required_choice", "")).strip():
        raise ValueError("Production integration representation remains an explicit unresolved choice")

    return {
        "status": STATUS,
        "production_specification_id": production.get("specification_id"),
        "production_freeze_status": production.get("freeze_status"),
        "production_fit_authorized": production.get("fit_authorized"),
        "production_scc_use_authorized": production.get("scc_use_authorized"),
        "n_required_feature_comparisons": len(REQUIRED_FEATURE_REQUIREMENTS),
        "n_water_stress_families": len(REQUIRED_WATER_STRESS_FAMILIES),
        "primary_model_selection_status": hierarchy.get("primary_selection_status"),
        "distribution_retention_is_incremental_out_of_sample": True,
        "pdsi_spei_are_competing_families": True,
        "production_requires_purged_temporal_extreme_splits": True,
        "purged_split_implementation_status": validation.get("production_split_implementation_status"),
        "real_panel_rerun_status": validation.get("real_panel_rerun_status"),
        "diagnostic_models": diagnostic_models,
        "diagnostic_fully_covered_requirements": sorted(
            identifier for identifier, value in coverage.items() if value == "covered"
        ),
        "diagnostic_partial_requirements": sorted(
            identifier for identifier, value in coverage.items() if value == "partial"
        ),
        "diagnostic_omitted_requirements": sorted(
            identifier for identifier, value in coverage.items() if value == "omitted"
        ),
        "warning": (
            "This validates scope labels and omissions only. It does not freeze a causal model, "
            "select thresholds, fit coefficients, authorize response draws, or authorize SCC use."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--production-spec", default="config/primary_response_spec.toml")
    parser.add_argument("--diagnostic-spec", default="config/response_evaluation_spec.toml")
    parser.add_argument("--audit-out")
    args = parser.parse_args()
    audit = validate_boundaries(
        load_toml(Path(args.production_spec)), load_toml(Path(args.diagnostic_spec))
    )
    rendered = json.dumps(audit, indent=2, sort_keys=True) + "\n"
    if args.audit_out:
        output = Path(args.audit_out)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()
