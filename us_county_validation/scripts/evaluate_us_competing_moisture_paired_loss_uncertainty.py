#!/usr/bin/env python3
"""Conditional paired county-bootstrap loss sensitivity for the U.S. diagnostic.

The registered point-estimate fits are reconstructed in memory on exactly the
same endpoint-purged splits.  Only aggregate loss differences, percentile
intervals, support hashes, and cluster diagnostics are serialized.  Fitted
parameters, row predictions, row losses, and bootstrap draws are discarded.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import tomllib
import warnings
from pathlib import Path, PurePosixPath
from typing import Any, Iterator

import numpy as np
import pandas as pd

from build_us_competing_moisture_inputs import (
    EXPECTED_MODEL_BLOCKS,
    KEYS,
    load_protocol,
    sha256,
)
from evaluate_us_competing_moisture import (
    fit_predictive_ols,
    load_validated_inputs,
    model_specs,
    purge_shared_first_difference_endpoints,
    regression_metrics,
)
from validate_us_competing_moisture import validate_candidate


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONTRACT_ID = "us_competing_moisture_paired_loss_uncertainty_v1"
BASE_PROTOCOL_ID = "us_corn_soy_competing_moisture_predictive_v1"
EXPECTED_MODELS = tuple(EXPECTED_MODEL_BLOCKS)
EXPECTED_COMPARISONS = [
    ("direct_quantity_minus_controls", "direct_quantity", "controls_only"),
    (
        "direct_quantity_distribution_minus_direct_quantity",
        "direct_quantity_distribution",
        "direct_quantity",
    ),
    (
        "pdsi_season_mean_minus_direct_quantity",
        "pdsi_season_mean",
        "direct_quantity",
    ),
    (
        "pdsi_stage_sensitivity_minus_direct_quantity",
        "pdsi_stage_sensitivity",
        "direct_quantity",
    ),
]
STATE_COMPARISON_ID = "direct_quantity_distribution_minus_direct_quantity"
EXPECTED_ARTIFACT_IDS = (
    "protocol",
    "registered_builder",
    "registered_evaluator",
    "registered_validator",
    "common_input",
    "direct_input",
    "pdsi_input",
    "input_audit",
    "direct_weather",
    "direct_validation",
    "pdsi_join",
    "pdsi_validation",
    "calendar",
    "calendar_validation",
    "base_result",
    "base_validation",
    "independent_audit_receipt",
)
FALSE_GATES = (
    "family_stacking_authorized",
    "coefficient_export_authorized",
    "row_prediction_export_authorized",
    "row_loss_export_authorized",
    "bootstrap_draw_export_authorized",
    "refit_uncertainty_authorized",
    "model_selection_uncertainty_authorized",
    "population_uncertainty_authorized",
    "causal_uncertainty_authorized",
    "damage_uncertainty_authorized",
    "scc_uncertainty_authorized",
    "promotion_rule_revision_authorized",
    "post_hoc_bootstrap_authorized",
    "post_hoc_model_selection_authorized",
)


def _walk(value: Any, prefix: str = "") -> Iterator[tuple[str, Any]]:
    if isinstance(value, dict):
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            yield path, child
            yield from _walk(child, path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _walk(child, f"{prefix}[{index}]")


def _reject_sensitive_payload(value: Any) -> None:
    """Reject accidental serialization of protected fit- or row-level values."""
    allowed = {
        "coefficients_emitted",
        "row_predictions_emitted",
        "row_losses_emitted",
        "bootstrap_draws_emitted",
        *FALSE_GATES,
    }
    for path, child in _walk(value):
        leaf = path.rsplit(".", 1)[-1].split("[", 1)[0].lower()
        if leaf not in allowed and any(
            token in leaf
            for token in ("coefficient", "row_prediction", "row_score", "row_loss", "bootstrap_draw")
        ):
            raise ValueError(f"protected fit or row payload field is forbidden: {path}")
        if isinstance(child, float) and not np.isfinite(child):
            raise ValueError(f"nonfinite output value at {path}")


def _relative_artifact_path(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("base artifact path must be a nonempty string")
    if Path(value).is_absolute() or PurePosixPath(value).is_absolute():
        raise ValueError("base artifact paths must be project-relative")
    parts = PurePosixPath(value).parts
    if ".." in parts or "." in parts or value != PurePosixPath(value).as_posix():
        raise ValueError("base artifact paths must be normalized project-relative paths")
    return value


def load_sensitivity_config(config_path: Path) -> dict[str, Any]:
    try:
        config = tomllib.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise ValueError(f"cannot read sensitivity config {config_path}") from error
    expected_fields = {
        "schema_version",
        "contract_id",
        "description",
        "base_protocol_id",
        "score_basis",
        "development_pooling",
        "resampling_scheme",
        "resampling_unit",
        "bootstrap_replicates",
        "random_seed",
        "seed_derivation",
        "interval_probabilities",
        "minimum_occupied_counties_per_report",
        "maximum_county_test_row_share",
        "state_specific_scope",
        "observation_weighting",
        "training_refit_within_bootstrap",
        "model_selection_rule",
        "post_hoc_support_sensitivity_authorized",
        "post_hoc_excluded_terminal_endpoint_years",
        "post_hoc_fixed_county_window_start",
        "post_hoc_fixed_county_window_end",
        "post_hoc_fixed_county_inclusion_rule",
        "post_hoc_loss_metrics",
        "predictive_fit_authorized",
        *FALSE_GATES,
        "comparisons",
        "base_artifacts",
    }
    if set(config) != expected_fields:
        raise ValueError(
            "sensitivity config schema differs: "
            f"missing={sorted(expected_fields - set(config))}, "
            f"extra={sorted(set(config) - expected_fields)}"
        )
    locked = {
        "schema_version": 1,
        "contract_id": CONTRACT_ID,
        "base_protocol_id": BASE_PROTOCOL_ID,
        "score_basis": (
            "registered_endpoint_purged_fits_recomputed_in_memory_on_identical_test_support"
        ),
        "development_pooling": (
            "pool_each_eligible_leave_state_out_test_row_once_using_its_state_holdout_fit"
        ),
        "resampling_scheme": "paired_fixed_fit_county_cluster_bootstrap",
        "resampling_unit": (
            "whole_county_across_all_relevant_test_rows_within_crop_practice_report_scope"
        ),
        "bootstrap_replicates": 5000,
        "random_seed": 20260826,
        "seed_derivation": (
            "base_seed_plus_zero_based_report_index_in_locked_crop_practice_scope_state_order"
        ),
        "interval_probabilities": [0.025, 0.975],
        "minimum_occupied_counties_per_report": 30,
        "maximum_county_test_row_share": 0.10,
        "state_specific_scope": (
            "development_leave_state_out_distribution_vs_quantity_only_when_at_least_30_test_counties"
        ),
        "observation_weighting": "equal_test_row_weighting_with_counties_resampled_uniformly",
        "training_refit_within_bootstrap": False,
        "model_selection_rule": (
            "none_sensitivity_does_not_revise_or_reapply_the_frozen_distribution_promotion_rule"
        ),
        "post_hoc_support_sensitivity_authorized": True,
        "post_hoc_excluded_terminal_endpoint_years": [2019],
        "post_hoc_fixed_county_window_start": 2012,
        "post_hoc_fixed_county_window_end": 2018,
        "post_hoc_fixed_county_inclusion_rule": (
            "county_has_one_terminal_test_row_in_every_endpoint_year_2012_2018_without_using_outcome_values"
        ),
        "post_hoc_loss_metrics": ["rmse_difference", "mae_difference"],
        "predictive_fit_authorized": True,
    }
    for field, expected in locked.items():
        if config.get(field) != expected:
            raise ValueError(f"sensitivity config {field} differs from its locked value")
    for gate in FALSE_GATES:
        if config.get(gate) is not False:
            raise ValueError(f"sensitivity config false gate {gate} must be exactly false")

    observed_comparisons = [
        (
            item.get("id"),
            item.get("candidate_model_id"),
            item.get("reference_model_id"),
        )
        for item in config["comparisons"]
        if isinstance(item, dict)
    ]
    if len(observed_comparisons) != len(config["comparisons"]):
        raise ValueError("every sensitivity comparison must be a table")
    if observed_comparisons != EXPECTED_COMPARISONS or any(
        set(item) != {"id", "candidate_model_id", "reference_model_id"}
        for item in config["comparisons"]
    ):
        raise ValueError("registered paired comparisons differ")

    artifacts = config["base_artifacts"]
    if not isinstance(artifacts, list) or any(not isinstance(item, dict) for item in artifacts):
        raise ValueError("base_artifacts must be an ordered array of tables")
    if [item.get("id") for item in artifacts] != list(EXPECTED_ARTIFACT_IDS):
        raise ValueError("hash-bound base artifact registry differs")
    for item in artifacts:
        if set(item) != {"id", "path", "sha256"}:
            raise ValueError(f"base artifact schema differs for {item.get('id')}")
        _relative_artifact_path(item["path"])
        if not isinstance(item["sha256"], str) or not re.fullmatch(
            r"[0-9a-f]{64}", item["sha256"]
        ):
            raise ValueError(f"base artifact SHA-256 is malformed for {item['id']}")
    return config


def _artifact_registry(config: dict[str, Any]) -> dict[str, dict[str, str]]:
    return {str(item["id"]): dict(item) for item in config["base_artifacts"]}


def _artifact_paths(config: dict[str, Any]) -> dict[str, Path]:
    return {
        identifier: PROJECT_ROOT / item["path"]
        for identifier, item in _artifact_registry(config).items()
    }


def _verify_artifact_hashes(config: dict[str, Any]) -> dict[str, Path]:
    registry = _artifact_registry(config)
    paths = _artifact_paths(config)
    for identifier in EXPECTED_ARTIFACT_IDS:
        path = paths[identifier]
        if not path.is_file():
            raise FileNotFoundError(f"required hash-bound base artifact is missing: {identifier}")
        actual = sha256(path)
        if actual != registry[identifier]["sha256"]:
            raise ValueError(f"hash-bound base artifact differs: {identifier}")
    return paths


def _load_hash_bound_base(
    config: dict[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, Any], dict[str, Any]]:
    """Verify and exactly revalidate the independently audited base diagnostic."""
    paths = _verify_artifact_hashes(config)
    registry = _artifact_registry(config)
    independent = json.loads(paths["independent_audit_receipt"].read_text(encoding="utf-8"))
    if independent.get("status") != "CLEAR_independent_noncausal_predictive_audit":
        raise ValueError("independent base audit status is not CLEAR")
    if independent.get("independent_of_registered_builder_evaluator_validator") is not True:
        raise ValueError("base audit does not assert implementation independence")
    if independent.get("discrepancies") != []:
        raise ValueError("independent base audit records discrepancies")
    audit_hashes = independent.get("hash_audit", {}).get("sha256", {})
    if audit_hashes.get("results") != registry["base_result"]["sha256"]:
        raise ValueError("independent audit result hash differs from the sensitivity binding")
    if audit_hashes.get("validation") != registry["base_validation"]["sha256"]:
        raise ValueError("independent audit validation hash differs from the sensitivity binding")
    if independent.get("promotion_gate_comparison", {}).get(
        "terminal_and_extreme_not_used_for_selection"
    ) is not True:
        raise ValueError("independent audit does not preserve the selection boundary")

    stored_result = json.loads(paths["base_result"].read_text(encoding="utf-8"))
    stored_validation = json.loads(paths["base_validation"].read_text(encoding="utf-8"))
    if stored_result.get("status") != "aggregate_noncausal_predictive_diagnostic_complete":
        raise ValueError("base point-estimate result status differs")
    for field in (
        "models_are_mutually_exclusive_moisture_representations",
        "train_test_first_difference_level_endpoints_purged",
        "train_only_scaling",
    ):
        if stored_result.get(field) is not True:
            raise ValueError(f"base point-estimate gate is false: {field}")
    for field in (
        "coefficients_in_output",
        "row_predictions_in_output",
        "causal_effect_estimated",
        "damage_calculated",
        "scc_calculated",
        "terminal_temporal_holdout_used_for_selection",
    ):
        if stored_result.get(field) is not False:
            raise ValueError(f"base point-estimate false gate differs: {field}")

    declared = {identifier: Path(registry[identifier]["path"]) for identifier in registry}
    previous_directory = Path.cwd()
    try:
        os.chdir(PROJECT_ROOT)
        recomputed_validation = validate_candidate(
            declared["common_input"].parent,
            declared["input_audit"],
            declared["direct_weather"],
            declared["direct_validation"],
            declared["pdsi_join"],
            declared["pdsi_validation"],
            declared["calendar"],
            declared["calendar_validation"],
            declared["base_result"],
            paths["protocol"],
        )
    finally:
        os.chdir(previous_directory)
    if recomputed_validation != stored_validation:
        raise ValueError("stored base validation differs from exact current recomputation")

    protocol = load_protocol(paths["protocol"])
    if protocol.get("protocol_id") != BASE_PROTOCOL_ID:
        raise ValueError("base protocol identity differs")
    common, direct, pdsi, _ = load_validated_inputs(
        paths["common_input"].parent,
        paths["input_audit"],
        protocol,
        paths["protocol"],
        paths["direct_weather"],
        paths["direct_validation"],
        paths["pdsi_join"],
        paths["pdsi_validation"],
        paths["calendar"],
        paths["calendar_validation"],
    )
    return common, direct, pdsi, protocol, stored_result


def _assert_mutually_exclusive_families(
    specs: dict[str, list[str]], protocol: dict[str, Any]
) -> None:
    if tuple(specs) != EXPECTED_MODELS:
        raise ValueError("model registry differs from the five stable registered models")
    features = protocol["features"]
    direct = {
        f"d_{name}"
        for name in [
            *map(str, features["direct_quantity"]),
            *map(str, features["direct_distribution_extension"]),
        ]
    }
    pdsi = {
        f"d_{name}"
        for name in [
            *map(str, features["pdsi_primary"]),
            *map(str, features["pdsi_stage_sensitivity"]),
        ]
    }
    if direct & pdsi:
        raise ValueError("direct and PDSI feature registries overlap")
    for model, columns in specs.items():
        selected = set(columns)
        if selected & direct and selected & pdsi:
            raise ValueError(f"model {model} stacks direct precipitation and PDSI families")


def _fit_scores_with_registered_solver(
    frame: pd.DataFrame,
    columns: list[str],
    train: np.ndarray,
    test: np.ndarray,
    svd_relative_tolerance: float,
    minimum_relative_scale: float,
    minimum_absolute_scale: float,
) -> tuple[dict[str, Any], np.ndarray]:
    """Mirror the hash-bound registered solver and return held-out scores in memory."""
    if train.dtype != bool or test.dtype != bool or train.shape != test.shape:
        raise ValueError("train/test masks must be aligned boolean arrays")
    if np.any(train & test) or not train.any() or not test.any():
        raise ValueError("train/test rows overlap or one side is empty")
    year = frame.harvest_year.to_numpy(dtype=float)
    year_scale = float(year[train].std(ddof=0))
    if not np.isfinite(year_scale) or year_scale <= 0:
        raise ValueError("training years do not vary")
    year_standardized = (year - float(year[train].mean())) / year_scale
    raw = frame[columns].to_numpy(dtype=float)
    raw = np.column_stack([raw, year_standardized, np.square(year_standardized)])
    if not np.isfinite(raw).all():
        raise ValueError("predictor matrix contains missing/nonfinite values")
    mean = raw[train].mean(axis=0)
    scale = raw[train].std(axis=0, ddof=0)
    if minimum_relative_scale <= 0 or minimum_absolute_scale <= 0:
        raise ValueError("training-scale floors must be positive")
    magnitude = np.max(np.abs(raw[train]), axis=0)
    scale_floor = np.maximum(minimum_absolute_scale, minimum_relative_scale * magnitude)
    retain = np.isfinite(scale) & (scale > scale_floor)
    if not retain.any():
        raise ValueError("all candidate predictors are constant in training")
    design = (raw[:, retain] - mean[retain]) / scale[retain]
    design = np.column_stack([np.ones(len(frame)), design])
    outcome = frame.delta_log_yield.to_numpy(dtype=float)
    if not np.isfinite(outcome).all():
        raise ValueError("outcome contains missing/nonfinite values")
    if not 0 < svd_relative_tolerance < 1:
        raise ValueError("SVD relative tolerance must lie strictly between zero and one")
    training_design = design[train]
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", RuntimeWarning)
            coefficients, _, rank, singular = np.linalg.lstsq(
                training_design,
                outcome[train],
                rcond=svd_relative_tolerance,
            )
    except (np.linalg.LinAlgError, RuntimeWarning, FloatingPointError) as error:
        raise ValueError("numerically invalid least-squares fit") from error
    rank = int(rank)
    if (
        rank <= 0
        or singular.ndim != 1
        or not np.isfinite(singular).all()
        or len(singular) == 0
        or singular[0] <= 0
    ):
        raise ValueError("least-squares solver returned an invalid training rank")
    if not np.isfinite(coefficients).all():
        raise ValueError("OLS fit produced nonfinite coefficients")
    prediction = np.einsum("ij,j->i", design[test], coefficients, optimize=False)
    if not np.isfinite(prediction).all():
        raise ValueError("OLS fit produced nonfinite coefficients or predictions")
    metrics = regression_metrics(outcome[test], prediction, float(outcome[train].mean()))
    metrics.update(
        {
            "train_rows": int(train.sum()),
            "test_rows": int(test.sum()),
            "design_columns_including_intercept": int(design.shape[1]),
            "design_rank": rank,
            "zero_variance_columns_dropped_train_only": int((~retain).sum()),
            "svd_relative_tolerance": float(svd_relative_tolerance),
            "minimum_relative_training_scale": float(minimum_relative_scale),
            "minimum_absolute_training_scale": float(minimum_absolute_scale),
            "linear_solver": "numpy_lstsq_with_registered_relative_svd_cutoff",
            "smallest_retained_to_largest_singular_value_ratio": float(
                singular[rank - 1] / singular[0]
            ),
        }
    )
    # ``coefficients`` and full-design values are deliberately allowed to die
    # here.  The caller receives only aggregate metrics and held-out scores.
    return metrics, prediction


def _key_index(frame: pd.DataFrame) -> pd.MultiIndex:
    return pd.MultiIndex.from_frame(frame[KEYS], names=KEYS)


def require_shared_test_support(support_by_model: dict[str, pd.DataFrame]) -> str:
    """Require exact ordered row support for every model and return only its hash."""
    if tuple(support_by_model) != EXPECTED_MODELS:
        raise ValueError("shared-test-support model registry differs")
    reference: pd.MultiIndex | None = None
    reference_frame: pd.DataFrame | None = None
    for model in EXPECTED_MODELS:
        frame = support_by_model[model]
        if set(KEYS) - set(frame) or frame.empty or frame.duplicated(KEYS).any():
            raise ValueError(f"shared test support for {model} is empty, malformed, or duplicated")
        index = _key_index(frame)
        if reference is None:
            reference, reference_frame = index, frame
        elif not index.equals(reference):
            raise ValueError("models do not share exact ordered test support")
    assert reference_frame is not None
    return test_support_sha256(reference_frame)


def test_support_sha256(frame: pd.DataFrame) -> str:
    """Hash a sorted key set without serializing its member rows."""
    if set(KEYS) - set(frame) or frame.empty or frame.duplicated(KEYS).any():
        raise ValueError("test support is empty, malformed, or duplicated")
    selected = frame[KEYS].copy()
    selected["county_geoid"] = selected.county_geoid.astype(str)
    selected["outcome_crop"] = selected.outcome_crop.astype(str)
    selected["irrigation_practice"] = selected.irrigation_practice.astype(str)
    selected["harvest_year"] = pd.to_numeric(
        selected.harvest_year, errors="raise"
    ).astype("int64")
    selected = selected.sort_values(KEYS, kind="mergesort")
    digest = hashlib.sha256()
    for row in selected.itertuples(index=False, name=None):
        fields = [str(row[0]), str(row[1]), str(int(row[2])), str(row[3])]
        if any("\t" in field or "\n" in field for field in fields):
            raise ValueError("test support keys contain forbidden separators")
        digest.update(("\t".join(fields) + "\n").encode("utf-8"))
    return digest.hexdigest()


def _endpoint_record(
    stratum: pd.DataFrame,
    test: np.ndarray,
    scores_by_model: dict[str, np.ndarray],
    split: str,
    split_id: str,
) -> dict[str, Any]:
    support = stratum.loc[test, KEYS + ["state"]].reset_index(drop=True)
    support_by_model = {model: support[KEYS].copy() for model in EXPECTED_MODELS}
    support_hash = require_shared_test_support(support_by_model)
    observed = stratum.loc[test, "delta_log_yield"].to_numpy(dtype=float)
    if not np.isfinite(observed).all():
        raise ValueError("test outcome contains nonfinite values")
    if set(scores_by_model) != set(EXPECTED_MODELS):
        raise ValueError("endpoint score registry differs")
    for model, values in scores_by_model.items():
        if values.shape != observed.shape or not np.isfinite(values).all():
            raise ValueError(f"endpoint scores for {model} are nonfinite or misaligned")
    return {
        "split": split,
        "split_id": split_id,
        "support": support,
        "test_support_sha256": support_hash,
        "observed": observed,
        "scores": scores_by_model,
    }


def _combine_development_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    if not records or any(record["split"] != "development_leave_state_out" for record in records):
        raise ValueError("development OOF pool lacks leave-state-out records")
    support = pd.concat([record["support"] for record in records], ignore_index=True)
    if support.duplicated(KEYS).any():
        raise ValueError("a development test row is scored in more than one state holdout")
    county_state_counts = support.groupby("county_geoid", observed=True).state.nunique()
    if county_state_counts.gt(1).any():
        raise ValueError("a pooled development county crosses state groups")
    observed = np.concatenate([record["observed"] for record in records])
    scores = {
        model: np.concatenate([record["scores"][model] for record in records])
        for model in EXPECTED_MODELS
    }
    if len(support) != len(observed) or any(len(values) != len(observed) for values in scores.values()):
        raise ValueError("pooled development OOF support is misaligned")
    return {
        "split": "development_leave_state_out",
        "split_id": "eligible_states_pooled",
        "support": support,
        "test_support_sha256": test_support_sha256(support),
        "observed": observed,
        "scores": scores,
    }


def _recompute_endpoint_scores(
    common: pd.DataFrame,
    direct: pd.DataFrame,
    pdsi: pd.DataFrame,
    protocol: dict[str, Any],
    base_result: dict[str, Any],
) -> tuple[dict[tuple[str, str], dict[str, Any]], int]:
    specs = model_specs(protocol)
    _assert_mutually_exclusive_families(specs, protocol)
    combined = common.merge(
        direct[KEYS + [column for column in direct if column.startswith("d_")]],
        on=KEYS,
        how="left",
        validate="one_to_one",
    ).merge(
        pdsi[KEYS + [column for column in pdsi if column.startswith("d_")]],
        on=KEYS,
        how="left",
        validate="one_to_one",
    )
    required = sorted(set(column for columns in specs.values() for column in columns))
    if combined[required + ["delta_log_yield"]].isna().any().any():
        raise ValueError("combined common support contains missing analysis values")
    numeric = combined[required + ["delta_log_yield"]].to_numpy(dtype=float)
    if not np.isfinite(numeric).all():
        raise ValueError("combined common support contains nonfinite analysis values")

    registered_rows: dict[tuple[str, str, str, str, str], dict[str, Any]] = {}
    for row in base_result.get("metrics", []):
        key = (
            str(row.get("crop")),
            str(row.get("irrigation_practice")),
            str(row.get("split")),
            str(row.get("split_id")),
            str(row.get("model")),
        )
        if key in registered_rows:
            raise ValueError("base point-estimate result duplicates a metric identity")
        registered_rows[key] = row
    if len(registered_rows) != 120:
        raise ValueError("base point-estimate result does not contain 120 metric rows")

    validation = protocol["validation"]
    minimum_test = int(validation["minimum_test_rows"])
    minimum_groups = int(validation["minimum_geographic_groups_per_crop_practice"])
    svd_tolerance = float(validation["svd_relative_tolerance"])
    relative_scale = float(validation["minimum_relative_training_scale"])
    absolute_scale = float(validation["minimum_absolute_training_scale"])
    all_endpoints: dict[tuple[str, str], dict[str, Any]] = {}
    metric_rows_recomputed = 0
    observed_strata: list[tuple[str, str]] = []

    for (crop_value, practice_value), stratum in combined.groupby(
        ["outcome_crop", "irrigation_practice"], observed=True, sort=True
    ):
        crop, practice = str(crop_value), str(practice_value)
        observed_strata.append((crop, practice))
        stratum = stratum.reset_index(drop=True)
        temporal = stratum.is_temporal_holdout.to_numpy(dtype=bool)
        extreme = stratum.is_precipitation_extreme.to_numpy(dtype=bool)
        geographic = stratum.geographic_group.astype(str)
        counts = geographic.loc[~temporal].value_counts().sort_index()
        states = list(map(str, counts.loc[counts.ge(minimum_test)].index))
        if len(states) < minimum_groups:
            raise ValueError(f"{crop}/{practice} lacks enough eligible state holdouts")
        split_masks: list[tuple[str, str, np.ndarray, np.ndarray]] = []
        for state in states:
            test = (~temporal) & geographic.eq(state).to_numpy(dtype=bool)
            train = (~temporal) & ~geographic.eq(state).to_numpy(dtype=bool)
            split_masks.append(("development_leave_state_out", state, train, test))
        development_counties = set(stratum.loc[~temporal, "county_geoid"].astype(str))
        terminal_test = temporal & stratum.county_geoid.astype(str).isin(
            development_counties
        ).to_numpy(dtype=bool)
        split_masks.append(
            ("terminal_temporal_same_counties", "terminal", ~temporal, terminal_test)
        )
        split_masks.append(
            (
                "development_precipitation_extreme",
                "tails",
                (~temporal) & ~extreme,
                (~temporal) & extreme,
            )
        )

        development_records: list[dict[str, Any]] = []
        terminal_record: dict[str, Any] | None = None
        extreme_record: dict[str, Any] | None = None
        state_records: dict[str, dict[str, Any]] = {}
        for split, split_id, train, test in split_masks:
            if int(test.sum()) < minimum_test:
                raise ValueError(f"{crop}/{practice}/{split}/{split_id} fails minimum test rows")
            train_rows_before = int(train.sum())
            purged_train, purged_rows = purge_shared_first_difference_endpoints(
                stratum, train, test
            )
            if not purged_train.any():
                raise ValueError(f"{crop}/{practice}/{split}/{split_id} has no training rows")
            train_keys = set(
                stratum.loc[purged_train, KEYS].itertuples(index=False, name=None)
            )
            test_keys = set(stratum.loc[test, KEYS].itertuples(index=False, name=None))
            if train_keys & test_keys:
                raise ValueError("endpoint-purged train and test row keys overlap")
            scores: dict[str, np.ndarray] = {}
            for model in EXPECTED_MODELS:
                columns = specs[model]
                registered_metrics = fit_predictive_ols(
                    stratum,
                    columns,
                    purged_train,
                    test,
                    svd_tolerance,
                    relative_scale,
                    absolute_scale,
                )
                internal_metrics, prediction = _fit_scores_with_registered_solver(
                    stratum,
                    columns,
                    purged_train,
                    test,
                    svd_tolerance,
                    relative_scale,
                    absolute_scale,
                )
                if internal_metrics != registered_metrics:
                    raise ValueError("in-memory score reconstruction differs from registered solver")
                recomputed_row = {
                    "crop": crop,
                    "irrigation_practice": practice,
                    "split": split,
                    "split_id": split_id,
                    "model": model,
                    "feature_count_excluding_year_terms": len(columns),
                    "train_rows_before_endpoint_purge": train_rows_before,
                    "train_rows_purged_shared_level_endpoint": purged_rows,
                    "first_difference_level_endpoints_disjoint": True,
                    **registered_metrics,
                }
                key = (crop, practice, split, split_id, model)
                if key not in registered_rows or recomputed_row != registered_rows[key]:
                    raise ValueError(f"recomputed registered metric differs for {key}")
                scores[model] = prediction
                metric_rows_recomputed += 1
            record = _endpoint_record(stratum, test, scores, split, split_id)
            if split == "development_leave_state_out":
                development_records.append(record)
                state_records[split_id] = record
            elif split == "terminal_temporal_same_counties":
                terminal_record = record
            elif split == "development_precipitation_extreme":
                extreme_record = record
        if terminal_record is None or extreme_record is None:
            raise AssertionError("terminal or extreme endpoint reconstruction is absent")
        all_endpoints[(crop, practice)] = {
            "development_pooled": _combine_development_records(development_records),
            "terminal": terminal_record,
            "extreme": extreme_record,
            "states": state_records,
        }

    expected_strata = [
        (crop, practice)
        for crop in map(str, protocol["sample"]["crops"])
        for practice in map(str, protocol["sample"]["irrigation_practices"])
    ]
    if observed_strata != expected_strata:
        raise ValueError("crop/practice stratum order or support differs from the protocol")
    if metric_rows_recomputed != len(registered_rows):
        raise ValueError("not every registered point-estimate metric was recomputed")
    return all_endpoints, metric_rows_recomputed


def summarize_county_cluster_losses(
    observed: np.ndarray,
    scores_by_model: dict[str, np.ndarray],
    county_ids: np.ndarray,
    comparisons: list[dict[str, str]],
    bootstrap_replicates: int,
    random_seed: int,
    interval_probabilities: list[float],
    minimum_counties: int,
    maximum_county_test_row_share: float,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Summarize fixed-fit paired losses while keeping all county rows together."""
    observed = np.asarray(observed, dtype=float)
    counties = np.asarray(county_ids).astype(str)
    if observed.ndim != 1 or counties.shape != observed.shape or not np.isfinite(observed).all():
        raise ValueError("observed outcomes and county clusters must be finite aligned vectors")
    if len(observed) == 0 or any(not county or county.lower() == "nan" for county in counties):
        raise ValueError("county clusters contain missing identities")
    if set(scores_by_model) != set(EXPECTED_MODELS):
        raise ValueError("score registry differs from the five stable registered models")
    for model, scores in scores_by_model.items():
        values = np.asarray(scores, dtype=float)
        if values.shape != observed.shape or not np.isfinite(values).all():
            raise ValueError(f"scores for {model} are nonfinite or lack shared test support")
    if bootstrap_replicates <= 0:
        raise ValueError("bootstrap replicate count must be positive")
    if len(interval_probabilities) != 2 or not (
        0 < interval_probabilities[0] < interval_probabilities[1] < 1
    ):
        raise ValueError("interval probabilities must be ordered interior quantiles")
    if minimum_counties <= 1:
        raise ValueError("minimum county cluster count must exceed one")
    if not 0 < maximum_county_test_row_share < 1:
        raise ValueError("maximum county test-row share must lie between zero and one")

    unique_counties, inverse = np.unique(counties, return_inverse=True)
    county_count = len(unique_counties)
    if county_count < minimum_counties:
        raise ValueError("occupied county cluster count is below the prespecified minimum")
    county_n = np.bincount(inverse, minlength=county_count).astype(np.int64)
    row_count = int(county_n.sum())
    shares = county_n / row_count
    maximum_share = float(shares.max())
    if maximum_share > maximum_county_test_row_share:
        raise ValueError("a county cluster exceeds the prespecified maximum test-row share")
    effective_count = float(1.0 / np.dot(shares, shares))

    squared: dict[str, np.ndarray] = {}
    absolute: dict[str, np.ndarray] = {}
    for model, scores in scores_by_model.items():
        residual = observed - np.asarray(scores, dtype=float)
        squared[model] = np.bincount(
            inverse, weights=np.square(residual), minlength=county_count
        )
        absolute[model] = np.bincount(
            inverse, weights=np.abs(residual), minlength=county_count
        )
    if any(not np.isfinite(values).all() for values in [*squared.values(), *absolute.values()]):
        raise ValueError("cluster loss aggregates contain nonfinite values")

    rng = np.random.default_rng(random_seed)
    draw_counts = rng.multinomial(
        county_count,
        np.full(county_count, 1.0 / county_count),
        size=bootstrap_replicates,
    )
    draw_rows = np.sum(draw_counts * county_n[None, :], axis=1)
    if (draw_rows <= 0).any() or not np.isfinite(draw_rows).all():
        raise ValueError("a county bootstrap replicate has invalid support")

    lower_probability, upper_probability = interval_probabilities
    summaries: list[dict[str, Any]] = []
    for comparison in comparisons:
        if set(comparison) != {"id", "candidate_model_id", "reference_model_id"}:
            raise ValueError("comparison schema differs")
        candidate = comparison["candidate_model_id"]
        reference = comparison["reference_model_id"]
        if candidate not in scores_by_model or reference not in scores_by_model:
            raise ValueError("comparison names an unregistered model")
        candidate_sse, reference_sse = squared[candidate], squared[reference]
        candidate_sae, reference_sae = absolute[candidate], absolute[reference]
        candidate_rmse = float(np.sqrt(candidate_sse.sum() / row_count))
        reference_rmse = float(np.sqrt(reference_sse.sum() / row_count))
        candidate_mae = float(candidate_sae.sum() / row_count)
        reference_mae = float(reference_sae.sum() / row_count)
        candidate_sse_draws = np.sum(draw_counts * candidate_sse[None, :], axis=1)
        reference_sse_draws = np.sum(draw_counts * reference_sse[None, :], axis=1)
        candidate_sae_draws = np.sum(draw_counts * candidate_sae[None, :], axis=1)
        reference_sae_draws = np.sum(draw_counts * reference_sae[None, :], axis=1)
        rmse_draws = np.sqrt(candidate_sse_draws / draw_rows) - np.sqrt(
            reference_sse_draws / draw_rows
        )
        mae_draws = candidate_sae_draws / draw_rows - reference_sae_draws / draw_rows
        if not np.isfinite(rmse_draws).all() or not np.isfinite(mae_draws).all():
            raise ValueError("paired bootstrap loss differences contain nonfinite values")
        rmse_interval = np.quantile(
            rmse_draws, [lower_probability, upper_probability], method="linear"
        )
        mae_interval = np.quantile(
            mae_draws, [lower_probability, upper_probability], method="linear"
        )
        summaries.append(
            {
                "comparison_id": comparison["id"],
                "candidate_model_id": candidate,
                "reference_model_id": reference,
                "sign_convention": (
                    "candidate_minus_reference_negative_favors_candidate_on_loss"
                ),
                "test_row_count": row_count,
                "candidate_rmse": candidate_rmse,
                "reference_rmse": reference_rmse,
                "rmse_difference": candidate_rmse - reference_rmse,
                "rmse_interval": {
                    "lower": float(rmse_interval[0]),
                    "upper": float(rmse_interval[1]),
                },
                "candidate_mae": candidate_mae,
                "reference_mae": reference_mae,
                "mae_difference": candidate_mae - reference_mae,
                "mae_interval": {
                    "lower": float(mae_interval[0]),
                    "upper": float(mae_interval[1]),
                },
            }
        )
    diagnostics = {
        "test_row_count": row_count,
        "occupied_county_count": county_count,
        "effective_county_count_inverse_herfindahl": effective_count,
        "maximum_county_test_row_share": maximum_share,
        "minimum_county_test_row_count": int(county_n.min()),
        "median_county_test_row_count": float(np.median(county_n)),
        "maximum_county_test_row_count": int(county_n.max()),
    }
    return summaries, diagnostics


def _subset_endpoint(
    endpoint: dict[str, Any], mask: np.ndarray, split_id: str
) -> dict[str, Any]:
    mask = np.asarray(mask)
    support = endpoint["support"]
    if mask.dtype != bool or mask.shape != (len(support),) or not mask.any():
        raise ValueError("post hoc endpoint subset mask is empty or misaligned")
    subset_support = support.loc[mask].reset_index(drop=True)
    observed = np.asarray(endpoint["observed"], dtype=float)[mask]
    scores = {
        model: np.asarray(endpoint["scores"][model], dtype=float)[mask]
        for model in EXPECTED_MODELS
    }
    if not np.isfinite(observed).all() or any(
        not np.isfinite(values).all() for values in scores.values()
    ):
        raise ValueError("post hoc support subset contains nonfinite outcomes or scores")
    return {
        "split": endpoint["split"],
        "split_id": split_id,
        "support": subset_support,
        "test_support_sha256": test_support_sha256(subset_support),
        "observed": observed,
        "scores": scores,
    }


def summarize_fixed_fit_point_losses(
    observed: np.ndarray,
    scores_by_model: dict[str, np.ndarray],
    comparisons: list[dict[str, str]],
) -> list[dict[str, Any]]:
    """Return aggregate point loss contrasts only; no resampling or inference."""
    observed = np.asarray(observed, dtype=float)
    if observed.ndim != 1 or len(observed) == 0 or not np.isfinite(observed).all():
        raise ValueError("post hoc outcomes must be a nonempty finite vector")
    if set(scores_by_model) != set(EXPECTED_MODELS):
        raise ValueError("post hoc score registry differs from the registered models")
    squared: dict[str, float] = {}
    absolute: dict[str, float] = {}
    for model, scores in scores_by_model.items():
        values = np.asarray(scores, dtype=float)
        if values.shape != observed.shape or not np.isfinite(values).all():
            raise ValueError(f"post hoc scores for {model} are nonfinite or misaligned")
        residual = observed - values
        squared[model] = float(np.mean(np.square(residual)))
        absolute[model] = float(np.mean(np.abs(residual)))
    rows: list[dict[str, Any]] = []
    for comparison in comparisons:
        candidate, reference = (
            comparison["candidate_model_id"],
            comparison["reference_model_id"],
        )
        candidate_rmse, reference_rmse = (
            float(np.sqrt(squared[candidate])),
            float(np.sqrt(squared[reference])),
        )
        candidate_mae, reference_mae = absolute[candidate], absolute[reference]
        values = [candidate_rmse, reference_rmse, candidate_mae, reference_mae]
        if not np.isfinite(values).all():
            raise ValueError("post hoc point loss contains a nonfinite value")
        rows.append(
            {
                "comparison_id": comparison["id"],
                "candidate_model_id": candidate,
                "reference_model_id": reference,
                "sign_convention": (
                    "candidate_minus_reference_negative_favors_candidate_on_loss"
                ),
                "test_row_count": int(len(observed)),
                "candidate_rmse": candidate_rmse,
                "reference_rmse": reference_rmse,
                "rmse_difference": candidate_rmse - reference_rmse,
                "candidate_mae": candidate_mae,
                "reference_mae": reference_mae,
                "mae_difference": candidate_mae - reference_mae,
            }
        )
    return rows


def _project_relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT).as_posix()
    except ValueError as error:
        raise ValueError("sensitivity config must be inside the project tree") from error


def evaluate_sensitivity(config_path: Path) -> dict[str, Any]:
    config = load_sensitivity_config(config_path)
    common, direct, pdsi, protocol, base_result = _load_hash_bound_base(config)
    endpoints, metric_rows_recomputed = _recompute_endpoint_scores(
        common, direct, pdsi, protocol, base_result
    )
    comparisons = list(config["comparisons"])
    state_comparison = [
        comparison for comparison in comparisons if comparison["id"] == STATE_COMPARISON_ID
    ]
    if len(state_comparison) != 1:
        raise AssertionError("state-specific comparison registry differs")

    reports: list[tuple[str, str, str, str, dict[str, Any], list[dict[str, str]]]] = []
    omissions: list[dict[str, Any]] = []
    for crop in map(str, protocol["sample"]["crops"]):
        for practice in map(str, protocol["sample"]["irrigation_practices"]):
            stratum = endpoints[(crop, practice)]
            reports.extend(
                [
                    (
                        crop,
                        practice,
                        "pooled_development_oof",
                        "eligible_states_pooled",
                        stratum["development_pooled"],
                        comparisons,
                    ),
                    (
                        crop,
                        practice,
                        "terminal_temporal_same_counties",
                        "terminal",
                        stratum["terminal"],
                        comparisons,
                    ),
                    (
                        crop,
                        practice,
                        "development_precipitation_extreme",
                        "tails",
                        stratum["extreme"],
                        comparisons,
                    ),
                ]
            )
            for state, endpoint in sorted(stratum["states"].items()):
                county_count = int(endpoint["support"].county_geoid.astype(str).nunique())
                if county_count < config["minimum_occupied_counties_per_report"]:
                    omissions.append(
                        {
                            "crop": crop,
                            "irrigation_practice": practice,
                            "report_scope": "state_specific_development_oof",
                            "state": state,
                            "test_row_count": int(len(endpoint["support"])),
                            "occupied_county_count": county_count,
                            "minimum_required_counties": config[
                                "minimum_occupied_counties_per_report"
                            ],
                            "reason": "below_locked_minimum_occupied_counties_not_reported",
                        }
                    )
                    continue
                reports.append(
                    (
                        crop,
                        practice,
                        "state_specific_development_oof",
                        state,
                        endpoint,
                        state_comparison,
                    )
                )

    aggregate_rows: list[dict[str, Any]] = []
    diagnostics_rows: list[dict[str, Any]] = []
    for report_index, (crop, practice, scope, split_id, endpoint, selected) in enumerate(reports):
        seed = int(config["random_seed"] + report_index)
        support = endpoint["support"]
        summaries, diagnostics = summarize_county_cluster_losses(
            endpoint["observed"],
            endpoint["scores"],
            support.county_geoid.astype(str).to_numpy(),
            selected,
            config["bootstrap_replicates"],
            seed,
            config["interval_probabilities"],
            config["minimum_occupied_counties_per_report"],
            config["maximum_county_test_row_share"],
        )
        report_id = f"{crop}|{practice}|{scope}|{split_id}"
        states = sorted(set(support.state.astype(str)))
        diagnostic = {
            "report_id": report_id,
            "crop": crop,
            "irrigation_practice": practice,
            "report_scope": scope,
            "split_id": split_id,
            "source_states": states,
            "source_state_count": len(states),
            "test_support_sha256": endpoint["test_support_sha256"],
            "bootstrap_seed": seed,
            **diagnostics,
        }
        diagnostics_rows.append(diagnostic)
        aggregate_rows.extend(
            {
                "report_id": report_id,
                "crop": crop,
                "irrigation_practice": practice,
                "report_scope": scope,
                "split_id": split_id,
                "test_support_sha256": endpoint["test_support_sha256"],
                **summary,
            }
            for summary in summaries
        )

    primary_terminal = {
        (row["crop"], row["irrigation_practice"], row["comparison_id"]): row
        for row in aggregate_rows
        if row["report_scope"] == "terminal_temporal_same_counties"
    }
    post_hoc_rows: list[dict[str, Any]] = []
    post_hoc_diagnostics: list[dict[str, Any]] = []
    fixed_counties_by_crop: dict[str, set[str]] = {}
    excluded_years = set(map(int, config["post_hoc_excluded_terminal_endpoint_years"]))
    window_start = int(config["post_hoc_fixed_county_window_start"])
    window_end = int(config["post_hoc_fixed_county_window_end"])
    required_window_years = set(range(window_start, window_end + 1))
    for crop in map(str, protocol["sample"]["crops"]):
        for practice in map(str, protocol["sample"]["irrigation_practices"]):
            terminal = endpoints[(crop, practice)]["terminal"]
            support = terminal["support"]
            years = pd.to_numeric(support.harvest_year, errors="raise").astype("int64")
            without_excluded = ~years.isin(excluded_years).to_numpy(dtype=bool)
            excluded_endpoint = _subset_endpoint(
                terminal, without_excluded, "terminal_excluding_2019_endpoint"
            )

            in_window = years.between(window_start, window_end).to_numpy(dtype=bool)
            window_support = support.loc[in_window, ["county_geoid", "harvest_year"]].copy()
            county_year_sets = window_support.groupby(
                "county_geoid", observed=True
            ).harvest_year.agg(lambda values: set(map(int, values)))
            fixed_counties = set(
                map(str, county_year_sets.loc[county_year_sets.map(lambda x: x == required_window_years)].index)
            )
            if not fixed_counties:
                raise ValueError("post hoc fixed-county terminal window is infeasible")
            prior_fixed = fixed_counties_by_crop.setdefault(crop, fixed_counties)
            if prior_fixed != fixed_counties:
                raise ValueError("post hoc fixed-county support differs across practices")
            fixed_mask = in_window & support.county_geoid.astype(str).isin(
                fixed_counties
            ).to_numpy(dtype=bool)
            fixed_endpoint = _subset_endpoint(
                terminal, fixed_mask, "fixed_counties_complete_2012_2018"
            )
            minimum_test = int(protocol["validation"]["minimum_test_rows"])
            if len(fixed_endpoint["support"]) < minimum_test:
                raise ValueError("post hoc fixed-county window fails the registered test-row floor")

            for scope, endpoint, selection_rule in (
                (
                    "post_hoc_terminal_excluding_2019_endpoint",
                    excluded_endpoint,
                    "exclude_harvest_year_2019_from_terminal_test_without_inspecting_outcomes",
                ),
                (
                    "post_hoc_fixed_counties_complete_2012_2018",
                    fixed_endpoint,
                    config["post_hoc_fixed_county_inclusion_rule"],
                ),
            ):
                point_rows = summarize_fixed_fit_point_losses(
                    endpoint["observed"], endpoint["scores"], comparisons
                )
                counties = endpoint["support"].county_geoid.astype(str)
                county_n = counties.value_counts().to_numpy(dtype=float)
                shares = county_n / county_n.sum()
                years_present = sorted(
                    set(map(int, endpoint["support"].harvest_year.astype(int)))
                )
                post_hoc_diagnostics.append(
                    {
                        "crop": crop,
                        "irrigation_practice": practice,
                        "report_scope": scope,
                        "split_id": endpoint["split_id"],
                        "selection_rule": selection_rule,
                        "selection_uses_outcome_values": False,
                        "endpoint_years": years_present,
                        "test_row_count": int(len(endpoint["support"])),
                        "rows_removed_from_primary_terminal": int(
                            len(terminal["support"]) - len(endpoint["support"])
                        ),
                        "support_identical_to_primary_terminal": bool(
                            endpoint["test_support_sha256"]
                            == terminal["test_support_sha256"]
                        ),
                        "occupied_county_count": int(counties.nunique()),
                        "effective_county_count_inverse_herfindahl": float(
                            1.0 / np.dot(shares, shares)
                        ),
                        "below_locked_bootstrap_minimum_counties": bool(
                            counties.nunique()
                            < config["minimum_occupied_counties_per_report"]
                        ),
                        "paired_interval_reported": False,
                        "test_support_sha256": endpoint["test_support_sha256"],
                    }
                )
                for row in point_rows:
                    primary = primary_terminal[(crop, practice, row["comparison_id"])]
                    rmse_flip = bool(
                        float(primary["rmse_difference"]) * float(row["rmse_difference"]) < 0
                    )
                    mae_flip = bool(
                        float(primary["mae_difference"]) * float(row["mae_difference"]) < 0
                    )
                    post_hoc_rows.append(
                        {
                            "crop": crop,
                            "irrigation_practice": practice,
                            "report_scope": scope,
                            "split_id": endpoint["split_id"],
                            "test_support_sha256": endpoint["test_support_sha256"],
                            "primary_terminal_rmse_difference": primary["rmse_difference"],
                            "rmse_ranking_flip_vs_primary_terminal": rmse_flip,
                            "primary_terminal_mae_difference": primary["mae_difference"],
                            "mae_ranking_flip_vs_primary_terminal": mae_flip,
                            **row,
                        }
                    )
    post_hoc_flip_count = sum(
        int(row["rmse_ranking_flip_vs_primary_terminal"])
        + int(row["mae_ranking_flip_vs_primary_terminal"])
        for row in post_hoc_rows
    )

    registry = _artifact_registry(config)
    result: dict[str, Any] = {
        "schema_version": 1,
        "contract_id": CONTRACT_ID,
        "status": "completed_conditional_paired_predictive_loss_sensitivity",
        "config_file": _project_relative(config_path),
        "config_sha256": sha256(config_path),
        "base_protocol_id": BASE_PROTOCOL_ID,
        "base_artifacts": {
            identifier: {
                "path": registry[identifier]["path"],
                "sha256": registry[identifier]["sha256"],
            }
            for identifier in EXPECTED_ARTIFACT_IDS
        },
        "base_exact_validation_recomputed": True,
        "base_independent_audit_clear": True,
        "registered_point_metric_rows_recomputed": metric_rows_recomputed,
        "all_registered_point_metrics_match": True,
        "registered_solver": "numpy_lstsq_with_registered_relative_svd_cutoff",
        "registered_solver_scores_reconstructed_exactly_in_memory": True,
        "identical_endpoint_purged_splits_recomputed": True,
        "all_models_share_exact_test_support_within_each_fit": True,
        "score_basis": config["score_basis"],
        "development_pooling": config["development_pooling"],
        "resampling_scheme": config["resampling_scheme"],
        "resampling_unit": config["resampling_unit"],
        "bootstrap_replicates": config["bootstrap_replicates"],
        "random_seed": config["random_seed"],
        "seed_derivation": config["seed_derivation"],
        "interval_probabilities": config["interval_probabilities"],
        "minimum_occupied_counties_per_report": config[
            "minimum_occupied_counties_per_report"
        ],
        "maximum_county_test_row_share": config["maximum_county_test_row_share"],
        "state_specific_scope": config["state_specific_scope"],
        "observation_weighting": config["observation_weighting"],
        "training_refit_within_bootstrap": False,
        "frozen_distribution_promotion_rule_revised": False,
        "frozen_distribution_promotion_outcomes_revised": False,
        "model_selection_rule": config["model_selection_rule"],
        "cluster_diagnostics": diagnostics_rows,
        "cluster_diagnostic_count": len(diagnostics_rows),
        "state_specific_omissions": omissions,
        "state_specific_omission_count": len(omissions),
        "comparisons": aggregate_rows,
        "comparison_count": len(aggregate_rows),
        "post_hoc_support_sensitivity_authorized": True,
        "post_hoc_support_sensitivity_role": (
            "support_only_point_metric_checks_requested_after_the_primary_protocol_was_frozen"
        ),
        "post_hoc_support_selection_uses_outcome_values": False,
        "post_hoc_support_sensitivity_changes_primary_protocol": False,
        "post_hoc_support_sensitivity_changes_promotion_decision": False,
        "post_hoc_support_bootstrap_performed": False,
        "post_hoc_support_diagnostics": post_hoc_diagnostics,
        "post_hoc_support_diagnostic_count": len(post_hoc_diagnostics),
        "post_hoc_support_comparisons": post_hoc_rows,
        "post_hoc_support_comparison_count": len(post_hoc_rows),
        "post_hoc_ranking_flip_count_across_metric_comparisons": post_hoc_flip_count,
        "uncertainty_scope": (
            "paired empirical county-resampling variation conditional on the observed test "
            "supports, registered fitted models, and registered endpoint-purged splits"
        ),
        "unsupported_uncertainty": (
            "not refit, training-sample, model-selection, target-population, causal, damage, "
            "welfare, or SCC uncertainty"
        ),
        "dependence_boundary": (
            "all relevant test rows for a county move together within a crop-practice report; "
            "dependence between counties is not modeled"
        ),
        "predictive_fit_authorized": True,
        "families_stacked": False,
        "coefficients_emitted": False,
        "row_predictions_emitted": False,
        "row_losses_emitted": False,
        "bootstrap_draws_emitted": False,
        **{gate: False for gate in FALSE_GATES},
    }
    if metric_rows_recomputed != 120:
        raise AssertionError("all 120 stable registered fits were not reconstructed")
    if len(diagnostics_rows) != 26 or len(aggregate_rows) != 62:
        raise AssertionError("complete pooled and adequate-state report product was not emitted")
    if len(omissions) != 2:
        raise AssertionError("locked state-specific county-support omission count differs")
    if len(post_hoc_diagnostics) != 8 or len(post_hoc_rows) != 32:
        raise AssertionError("complete post hoc support point-metric product was not emitted")
    _reject_sensitive_payload(result)
    return result


def evaluate_file(config_path: Path, result_path: Path) -> dict[str, Any]:
    result = evaluate_sensitivity(config_path)
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(
        json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--result-out", required=True, type=Path)
    arguments = parser.parse_args()
    result = evaluate_file(arguments.config, arguments.result_out)
    print(
        f"wrote {result['comparison_count']} aggregate paired-loss comparisons across "
        f"{result['cluster_diagnostic_count']} county-bootstrap reports; no coefficients, "
        "row predictions, row losses, or draws"
    )


if __name__ == "__main__":
    main()
