#!/usr/bin/env python3
"""Synthetic failure-mode tests for response-specification scope boundaries."""
from __future__ import annotations

import copy
import sys
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "scripts"))
from validate_response_spec_boundaries import (  # noqa: E402
    EXPECTED_FROZEN_DIAGNOSTIC_GAPS,
    EXPECTED_REAL_PANEL_STATUS,
    STATUS,
    load_toml,
    validate_boundaries,
)


production = load_toml(PROJECT / "config" / "primary_response_spec.toml")
diagnostic = load_toml(PROJECT / "config" / "response_evaluation_spec.toml")
valid = validate_boundaries(production, diagnostic)
assert valid["status"] == STATUS
assert valid["production_fit_authorized"] is False
assert valid["production_scc_use_authorized"] is False
assert valid["production_requires_purged_temporal_extreme_splits"] is True
assert valid["purged_split_implementation_status"] == "implemented_and_synthetic_tests_pass"
assert valid["real_panel_rerun_status"] == EXPECTED_REAL_PANEL_STATUS
assert valid["primary_model_selection_status"] == "not_frozen"
assert valid["distribution_retention_is_incremental_out_of_sample"] is True
assert valid["pdsi_spei_are_competing_families"] is True
assert set(valid["diagnostic_partial_requirements"] + valid["diagnostic_omitted_requirements"]) == (
    EXPECTED_FROZEN_DIAGNOSTIC_GAPS
)


def must_fail(mutator, expected: str) -> None:
    broken_production = copy.deepcopy(production)
    broken_diagnostic = copy.deepcopy(diagnostic)
    mutator(broken_production, broken_diagnostic)
    try:
        validate_boundaries(broken_production, broken_diagnostic)
        raise AssertionError("invalid response boundary should fail")
    except ValueError as error:
        assert expected in str(error), str(error)


must_fail(
    lambda prod, diag: prod["production_feature_requirements"].__setitem__(
        slice(None),
        [row for row in prod["production_feature_requirements"] if row["id"] != "wet_day_intensity"],
    ),
    "silently dropped required features",
)
must_fail(
    lambda prod, diag: prod.update(fit_authorized=True),
    "fit_authorized must be false",
)
must_fail(
    lambda prod, diag: prod["threshold_registry"].update(production_heat_thresholds_c=[30.0]),
    "must remain empty",
)
must_fail(
    lambda prod, diag: prod["water_stress_comparison"].update(simultaneous_stacking_allowed=True),
    "must not be stacked",
)
must_fail(
    lambda prod, diag: prod["model_hierarchy"].update(
        distribution_retention_rule="always include distribution terms"
    ),
    "robust stable incremental out-of-sample",
)
must_fail(
    lambda prod, diag: prod["model_hierarchy"].update(
        null_and_adverse_result_rule="report only favorable timing results"
    ),
    "report null/worse results",
)
must_fail(
    lambda prod, diag: prod["model_hierarchy"].update(
        drought_family_status="drought is a secondary sensitivity"
    ),
    "serious competing families",
)
must_fail(
    lambda prod, diag: diag["boundary"].update(status="production response"),
    "diagnostic-only status",
)
must_fail(
    lambda prod, diag: diag["holdouts"].update(temporal="final-year split"),
    "must declare its endpoint purge",
)
must_fail(
    lambda prod, diag: prod["integration_boundary"].update(production_eligible=True),
    "must remain production-ineligible",
)
must_fail(
    lambda prod, diag: prod["validation_boundary"].update(
        production_requires_purged_observation_disjoint_temporal_extreme_splits=False
    ),
    "must require purged observation-disjoint",
)
must_fail(
    lambda prod, diag: prod["fixed_effects"].update(outcome_cell="lat_lon_crop_irrigation"),
    "without irrigation",
)

relabeled = copy.deepcopy(production)
row = next(
    item for item in relabeled["production_feature_requirements"]
    if item["id"] == "wet_day_frequency"
)
row["diagnostic_coverage"] = "covered"
row["diagnostic_present_features"] = ["wet_day_frequency"]
row["diagnostic_absent_features"] = []
try:
    validate_boundaries(relabeled, diagnostic)
    raise AssertionError("false diagnostic coverage should fail")
except ValueError as error:
    assert "claims diagnostic features that are absent" in str(error)

print("response-specification scope-boundary synthetic tests passed")
