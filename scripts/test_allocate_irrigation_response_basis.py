#!/usr/bin/env python3
"""Synthetic order-of-operations tests for aggregate irrigation exposure."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd


PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "scripts"))
SPEC = importlib.util.spec_from_file_location(
    "allocate_irrigation_response_basis",
    PROJECT / "scripts/allocate_irrigation_response_basis.py",
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
from evaluate_crop_response_models import prepare_levels  # noqa: E402


panel = pd.DataFrame(
    [
        [2000, 10.25, 20.25, "mai", "noirr", True, 2.0, 10.0, 100.0, 8.0, 30.0],
        [2000, 10.25, 20.25, "mai", "firr", True, 2.0, 30.0, 20.0, 2.0, 10.0],
    ],
    columns=[
        "harvest_year",
        "lat",
        "lon_360",
        "crop",
        "irrigation",
        "yield_observed",
        "yield_t_ha",
        "tmean_c",
        "precip_mm",
        "cdd_max_days",
        "rx1day_mm",
    ],
)
weights = pd.DataFrame(
    [
        [10.25, 20.25, "mai", "noirr", 0.75],
        [10.25, 20.25, "mai", "firr", 0.25],
    ],
    columns=["lat", "lon_360", "crop", "irrigation", "area_share"],
)
weights["weight_source_id"] = "synthetic-independent-area-v1"
weights["weight_vintage"] = "baseline-2000"
weights["source_role"] = "independent_fixed_baseline_crop_area_share"
weights["production_eligible"] = True
weights["season_specific_share"] = True

output, audit = MODULE.allocate_registered_basis(
    panel, weights, ["noirr", "firr"], ["seasonal"]
)
assert len(output) == 1
row = output.iloc[0]

# Linear temperature commutes, but nonlinear precipitation and the interaction
# must be formed inside each regime before weighting.
expected_temperature = 0.75 * 10.0 + 0.25 * 30.0
expected_log_precip = 0.75 * np.log1p(100.0) + 0.25 * np.log1p(20.0)
expected_interaction = (
    0.75 * 10.0 * np.log1p(100.0) + 0.25 * 30.0 * np.log1p(20.0)
)
invalid_log_after_average = np.log1p(0.75 * 100.0 + 0.25 * 20.0)
invalid_interaction_after_average = expected_temperature * expected_log_precip
invalid_interaction_from_averaged_weather = (
    expected_temperature * invalid_log_after_average
)

assert np.isclose(row.tmean_c, expected_temperature)
assert np.isclose(row.log1p_precip_mm, expected_log_precip)
assert np.isclose(row.tmean_x_log1p_precip, expected_interaction)
assert not np.isclose(row.log1p_precip_mm, invalid_log_after_average)
assert not np.isclose(row.tmean_x_log1p_precip, invalid_interaction_after_average)
assert not np.isclose(
    row.tmean_x_log1p_precip, invalid_interaction_from_averaged_weather
)
assert "precip_mm" not in output.columns
assert row.response_basis_contract_id == MODULE.CONTRACT_ID
assert row.basis_allocation_order == MODULE.BASIS_ORDER
assert not bool(row.nonlinear_post_allocation_transform_authorized)
assert audit["basis_allocation_order"] == MODULE.BASIS_ORDER
assert audit["primitive_precipitation_emitted"] is False
assert audit["estimand"] == "aggregate_log_yield_reduced_form_design_only"
assert audit["legacy_diagnostic_evaluator_compatible"] is False
assert audit["explicit_prebuilt_diagnostic_mode_compatible"] is True
assert audit["diagnostic_fit_authorized"] is True
assert audit["production_feature_basis_complete"] is False
assert audit["production_fit_authorized"] is False
assert audit["scc_authorized"] is False

try:
    prepare_levels(output, {"seasonal_joint": ["log1p_precip_mm"]})
    raise AssertionError("design-only prebuilt basis should fail in legacy evaluator")
except ValueError as exc:
    assert "explicit" in str(exc), str(exc)

legacy_area_weighted = output.drop(columns="response_basis_contract_id")
try:
    prepare_levels(
        legacy_area_weighted, {"seasonal_joint": ["log1p_precip_mm"]}
    )
    raise AssertionError("legacy area-weighted panel should fail before transforms")
except ValueError as exc:
    assert "Area-weighted irrigation panels are forbidden" in str(exc), str(exc)


def expect_basis_failure(candidate: pd.DataFrame, message: str) -> None:
    try:
        MODULE.build_regime_basis(candidate, ["seasonal"])
    except ValueError as exc:
        assert message in str(exc), str(exc)
    else:
        raise AssertionError(f"Expected failure containing {message!r}")


pretransformed = panel.copy()
pretransformed["log1p_precip_mm"] = np.log1p(pretransformed.precip_mm)
expect_basis_failure(pretransformed, "already exist")

negative_precip = panel.copy()
negative_precip.loc[0, "precip_mm"] = -1.0
expect_basis_failure(negative_precip, "must be nonnegative")

nonfinite_weather = panel.copy()
nonfinite_weather.loc[0, "tmean_c"] = np.inf
expect_basis_failure(nonfinite_weather, "must be finite")


def expect_allocation_failure(candidate: pd.DataFrame, message: str) -> None:
    try:
        MODULE.allocate_registered_basis(
            panel, candidate, ["noirr", "firr"], ["seasonal"]
        )
    except ValueError as exc:
        assert message in str(exc), str(exc)
    else:
        raise AssertionError(f"Expected failure containing {message!r}")


ineligible = weights.copy()
ineligible["production_eligible"] = False
expect_allocation_failure(ineligible, "not production-eligible")

nonseasonal = weights.copy()
nonseasonal["season_specific_share"] = False
expect_allocation_failure(nonseasonal, "not season-specific")

missing_gate = weights.drop(columns="season_specific_share")
expect_allocation_failure(missing_gate, "missing required fields")

print("aggregate irrigation response-basis synthetic tests passed")
