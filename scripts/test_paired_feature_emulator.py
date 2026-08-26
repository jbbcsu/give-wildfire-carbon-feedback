#!/usr/bin/env python3
"""Synthetic whole-holdout and marginal-pairing emulator tests."""
from __future__ import annotations

import copy

import pandas as pd

from validate_paired_feature_emulator import (
    SCENARIOS,
    validate_holdouts,
    validate_pairs,
    validate_training_design,
)


ESMS = {"esm-a": "r1", "esm-b": "r2"}
FAMILIES = {"precip_total", "dry_spell"}


def training() -> pd.DataFrame:
    rows = []
    for esm, member in ESMS.items():
        for scenario in SCENARIOS:
            for family in FAMILIES:
                rows.append(
                    {
                        "esm_id": esm,
                        "member_id": member,
                        "scenario": scenario,
                        "year": 2000,
                        "gmst_source_id": f"cmip6-{esm}-{member}",
                        "gmst_esm_id": esm,
                        "gmst_member_id": member,
                        "feature_family": family,
                        "feature_value": 10.0,
                    }
                )
    return pd.DataFrame(rows)


def holdouts() -> pd.DataFrame:
    rows = []
    for split_type, identifiers in (("esm", ESMS), ("scenario", SCENARIOS)):
        for identifier in identifiers:
            for family in FAMILIES:
                rows.append(
                    {
                        "split_type": split_type,
                        "holdout_id": identifier,
                        "feature_family": family,
                        "holdout_excluded": True,
                        "n_test": 12,
                        "rmse": 1.0,
                        "mae": 0.8,
                    }
                )
    return pd.DataFrame(rows)


def pairs() -> pd.DataFrame:
    rows = []
    for year in (2019, 2020):
        for family in FAMILIES:
            for pulse_scale in (0.0, 1.0, 0.5, 0.25):
                baseline = 10.0
                difference = 0.0 if year < 2020 else pulse_scale * (2.0 + 0.01 * pulse_scale)
                rows.append(
                    {
                        "draw_id": "draw-1",
                        "esm_id": "esm-a",
                        "member_id": "r1",
                        "year": year,
                        "first_divergence_year": 2020,
                        "feature_family": family,
                        "pulse_scale": pulse_scale,
                        "baseline_residual_id": "esm-a-r1-year-block-7",
                        "pulse_residual_id": "esm-a-r1-year-block-7",
                        "baseline_feature": baseline,
                        "pulse_feature": baseline + difference,
                        "support_min": 0.0,
                        "support_max": 20.0,
                        "baseline_support": "within",
                        "pulse_support": "within",
                        "direct_difference": difference,
                        "centered_difference": difference,
                    }
                )
    return pd.DataFrame(rows)


def expect_failure(function, *args, message: str) -> None:
    try:
        function(*args)
    except ValueError as error:
        assert message in str(error), error
    else:
        raise AssertionError(f"Expected failure containing {message!r}")


train = training()
members, families = validate_training_design(train)
assert members == ESMS
assert families == FAMILIES
validate_holdouts(holdouts(), set(members), families)
validate_pairs(pairs(), members)

case = train.copy()
case.loc[0, "gmst_member_id"] = "different"
expect_failure(validate_training_design, case, message="same realization")

case = holdouts()
case = case[~((case["split_type"] == "scenario") & (case["holdout_id"] == "ssp585"))]
expect_failure(validate_holdouts, case, set(members), families, message="exact ESM/scenario")

case = pairs()
case.loc[1, "pulse_residual_id"] = "independent-weather"
expect_failure(validate_pairs, case, members, message="common residual")

case = pairs()
case.loc[(case["year"] == 2019) & (case["pulse_scale"] == 1.0), "pulse_feature"] += 1.0
case.loc[(case["year"] == 2019) & (case["pulse_scale"] == 1.0), "direct_difference"] += 1.0
case.loc[(case["year"] == 2019) & (case["pulse_scale"] == 1.0), "centered_difference"] += 1.0
expect_failure(validate_pairs, case, members, message="pre-divergence")

case = pairs()
mask = (case["year"] == 2020) & (case["feature_family"] == "dry_spell") & (case["pulse_scale"] == 0.25)
case.loc[mask, "direct_difference"] = 0.4
case.loc[mask, "pulse_feature"] = 10.4
case.loc[mask, "centered_difference"] = 0.4
expect_failure(validate_pairs, case, members, message="does not converge")

case = pairs()
case.loc[case.index[0], "baseline_support"] = "above"
expect_failure(validate_pairs, case, members, message="support flags")

print("paired climate-feature emulator synthetic tests passed")
