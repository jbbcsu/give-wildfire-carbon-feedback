#!/usr/bin/env python3
"""Fail-closed gates for climate-feature emulator holdouts and paired paths.

This validates model design and paired numerical behavior.  Passing it does
not validate an agricultural response, welfare calculation, or SCC.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


SCENARIOS = {"historical", "ssp126", "ssp370", "ssp585"}


def _require(frame: pd.DataFrame, columns: set[str], label: str) -> None:
    missing = sorted(columns - set(frame.columns))
    if missing:
        raise ValueError(f"{label} missing columns: {missing}")
    if frame.empty:
        raise ValueError(f"{label} is empty")


def validate_training_design(training: pd.DataFrame) -> tuple[dict[str, str], set[str]]:
    _require(
        training,
        {
            "esm_id",
            "member_id",
            "scenario",
            "year",
            "gmst_source_id",
            "gmst_esm_id",
            "gmst_member_id",
            "feature_family",
            "feature_value",
        },
        "training",
    )
    if training[list({"year", "feature_value"})].isna().any().any():
        raise ValueError("training has missing year or feature value")
    if not np.isfinite(training["feature_value"].to_numpy(dtype=float)).all():
        raise ValueError("training feature values must be finite")
    if (training["gmst_source_id"].astype(str).str.strip() == "").any():
        raise ValueError("training GMST source IDs must be explicit")
    if not (training["esm_id"].astype(str) == training["gmst_esm_id"].astype(str)).all():
        raise ValueError("training features and GMST must use the same ESM")
    if not (training["member_id"].astype(str) == training["gmst_member_id"].astype(str)).all():
        raise ValueError("training features and GMST must use the same realization")
    if set(training["scenario"].astype(str)) != SCENARIOS:
        raise ValueError("training must cover historical, SSP1-2.6, SSP3-7.0, and SSP5-8.5")

    member_counts = training.groupby("esm_id")["member_id"].nunique()
    if (member_counts != 1).any():
        raise ValueError("each ESM must retain exactly one primary realization")
    members = training.groupby("esm_id")["member_id"].first().astype(str).to_dict()
    families = set(training["feature_family"].astype(str))
    expected = {(esm, scenario, family) for esm in members for scenario in SCENARIOS for family in families}
    observed = set(
        training[["esm_id", "scenario", "feature_family"]]
        .astype(str)
        .drop_duplicates()
        .itertuples(index=False, name=None)
    )
    if observed != expected:
        raise ValueError("training lacks the complete ESM/scenario/feature-family product")
    return members, families


def validate_holdouts(holdouts: pd.DataFrame, esms: set[str], families: set[str]) -> None:
    _require(
        holdouts,
        {"split_type", "holdout_id", "feature_family", "holdout_excluded", "n_test", "rmse", "mae"},
        "holdouts",
    )
    if set(holdouts["split_type"].astype(str)) != {"esm", "scenario"}:
        raise ValueError("holdouts must include whole-ESM and whole-scenario splits")
    if not holdouts["holdout_excluded"].map(lambda value: str(value).lower() == "true").all():
        raise ValueError("every holdout row must certify exclusion from fitting")
    numeric = holdouts[["n_test", "rmse", "mae"]].apply(pd.to_numeric, errors="coerce")
    if numeric.isna().any().any() or not np.isfinite(numeric.to_numpy()).all():
        raise ValueError("holdout counts and metrics must be finite")
    if (numeric["n_test"] <= 0).any() or (numeric[["rmse", "mae"]] < 0).any().any():
        raise ValueError("holdout counts must be positive and errors nonnegative")
    expected = {
        *(('esm', holdout, family) for holdout in esms for family in families),
        *(('scenario', holdout, family) for holdout in SCENARIOS for family in families),
    }
    if holdouts.duplicated(["split_type", "holdout_id", "feature_family"]).any():
        raise ValueError("holdout audit has duplicate split/holdout/feature rows")
    observed = set(
        holdouts[["split_type", "holdout_id", "feature_family"]]
        .astype(str)
        .itertuples(index=False, name=None)
    )
    if observed != expected:
        raise ValueError("holdout audit lacks the exact ESM/scenario/feature-family product")


def _support(value: float, lower: float, upper: float) -> str:
    if value < lower:
        return "below"
    if value > upper:
        return "above"
    return "within"


def validate_pairs(pairs: pd.DataFrame, members: dict[str, str], *, convergence_rtol: float = 0.05) -> None:
    required = {
        "draw_id",
        "esm_id",
        "member_id",
        "year",
        "first_divergence_year",
        "feature_family",
        "pulse_scale",
        "baseline_residual_id",
        "pulse_residual_id",
        "baseline_feature",
        "pulse_feature",
        "support_min",
        "support_max",
        "baseline_support",
        "pulse_support",
        "direct_difference",
        "centered_difference",
    }
    _require(pairs, required, "pairs")
    numeric_columns = [
        "year",
        "first_divergence_year",
        "pulse_scale",
        "baseline_feature",
        "pulse_feature",
        "support_min",
        "support_max",
        "direct_difference",
        "centered_difference",
    ]
    numeric = pairs[numeric_columns].apply(pd.to_numeric, errors="coerce")
    if numeric.isna().any().any() or not np.isfinite(numeric.to_numpy()).all():
        raise ValueError("paired numeric fields must be finite")
    if (numeric["pulse_scale"] < 0).any() or (numeric["support_min"] > numeric["support_max"]).any():
        raise ValueError("pulse scales and support bounds are invalid")
    expected_members = pairs["esm_id"].astype(str).map(members)
    if expected_members.isna().any() or not (expected_members == pairs["member_id"].astype(str)).all():
        raise ValueError("paired paths must use a selected ESM realization")
    if not (pairs["baseline_residual_id"].astype(str) == pairs["pulse_residual_id"].astype(str)).all():
        raise ValueError("baseline and pulse must use common residual innovations")
    if not np.allclose(
        numeric["direct_difference"], numeric["pulse_feature"] - numeric["baseline_feature"], rtol=0, atol=1e-12
    ):
        raise ValueError("direct differences do not reconcile to feature levels")
    for side in ("baseline", "pulse"):
        expected = [
            _support(value, lower, upper)
            for value, lower, upper in zip(
                numeric[f"{side}_feature"], numeric["support_min"], numeric["support_max"]
            )
        ]
        if expected != pairs[f"{side}_support"].astype(str).tolist():
            raise ValueError(f"{side} support flags are incorrect")

    prediv = numeric["year"] < numeric["first_divergence_year"]
    zero = numeric["pulse_scale"] == 0
    identity = prediv | zero
    if not np.allclose(numeric.loc[identity, "direct_difference"], 0, rtol=0, atol=1e-12):
        raise ValueError("zero-pulse and pre-divergence paths must be identical")
    if not np.allclose(numeric.loc[zero, "centered_difference"], 0, rtol=0, atol=1e-12):
        raise ValueError("zero-pulse centered differences must be zero")
    if not zero.any():
        raise ValueError("paired audit requires an all-years zero-pulse control")

    group_columns = ["draw_id", "esm_id", "member_id", "year", "feature_family"]
    for key, indices in pairs.groupby(group_columns, sort=False).groups.items():
        block = pairs.loc[indices].copy()
        if (pd.to_numeric(block["pulse_scale"]) == 0).sum() != 1:
            raise ValueError(f"{key}: requires exactly one zero-pulse row")
        positive = block[pd.to_numeric(block["pulse_scale"]) > 0].copy()
        if positive.empty:
            continue
        if len(positive) < 3:
            raise ValueError(f"{key}: need at least three decreasing positive pulse sizes")
        positive["pulse_scale"] = pd.to_numeric(positive["pulse_scale"])
        positive["direct_difference"] = pd.to_numeric(positive["direct_difference"])
        positive["centered_difference"] = pd.to_numeric(positive["centered_difference"])
        positive = positive.sort_values("pulse_scale", ascending=False)
        if positive["pulse_scale"].duplicated().any():
            raise ValueError(f"{key}: pulse sizes must be distinct")
        centered_error = np.abs(positive["direct_difference"] - positive["centered_difference"])
        centered_limit = 1e-12 + convergence_rtol * np.maximum(
            np.abs(positive["direct_difference"]), np.abs(positive["centered_difference"])
        )
        if (centered_error > centered_limit).any():
            raise ValueError(f"{key}: direct and centered marginal calculations disagree")
        slopes = (positive["direct_difference"] / positive["pulse_scale"]).to_numpy()
        changes = np.abs(np.diff(slopes))
        if len(changes) > 1 and changes[-1] > changes[-2] + 1e-12:
            raise ValueError(f"{key}: normalized marginal signal does not converge as pulse shrinks")
        scale = max(abs(slopes[-1]), abs(slopes[-2]), 1e-12)
        if abs(slopes[-1] - slopes[-2]) > convergence_rtol * scale + 1e-12:
            raise ValueError(f"{key}: smallest-pulse marginal signals do not agree")


def read_table(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".parquet":
        return pd.read_parquet(path)
    return pd.read_csv(path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("training", type=Path)
    parser.add_argument("holdouts", type=Path)
    parser.add_argument("pairs", type=Path)
    args = parser.parse_args()
    members, families = validate_training_design(read_table(args.training))
    validate_holdouts(read_table(args.holdouts), set(members), families)
    validate_pairs(read_table(args.pairs), members)
    print("paired climate-feature emulator gates passed")


if __name__ == "__main__":
    main()
