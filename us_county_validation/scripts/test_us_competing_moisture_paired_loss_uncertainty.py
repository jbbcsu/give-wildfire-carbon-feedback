#!/usr/bin/env python3
"""Synthetic and hand-checkable tests for the U.S. paired-loss sensitivity."""
from __future__ import annotations

import json
import sys
import tempfile
from copy import deepcopy
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd


PROJECT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT / "us_county_validation" / "scripts"))
from build_us_competing_moisture_inputs import KEYS, load_protocol  # noqa: E402
from evaluate_us_competing_moisture import model_specs  # noqa: E402
from evaluate_us_competing_moisture_paired_loss_uncertainty import (  # noqa: E402
    EXPECTED_MODELS,
    _assert_mutually_exclusive_families,
    _reject_sensitive_payload,
    _verify_artifact_hashes,
    load_sensitivity_config,
    require_shared_test_support,
    summarize_county_cluster_losses,
    summarize_fixed_fit_point_losses,
)


def expect_failure(action: Callable[[], object], text: str) -> None:
    try:
        action()
    except (AssertionError, FileNotFoundError, ValueError) as error:
        assert text.lower() in str(error).lower(), str(error)
    else:
        raise AssertionError(f"expected failure containing {text!r}")


config_path = (
    PROJECT
    / "us_county_validation"
    / "us_competing_moisture_paired_loss_uncertainty_v1.toml"
)
config = load_sensitivity_config(config_path)
assert config["bootstrap_replicates"] == 5000
assert config["minimum_occupied_counties_per_report"] == 30
assert config["training_refit_within_bootstrap"] is False
assert config["promotion_rule_revision_authorized"] is False
assert config["post_hoc_support_sensitivity_authorized"] is True
assert config["post_hoc_bootstrap_authorized"] is False
assert config["post_hoc_model_selection_authorized"] is False
assert len(config["comparisons"]) == 4
assert len(config["base_artifacts"]) == 17
hash_tamper = deepcopy(config)
hash_tamper["base_artifacts"][0]["sha256"] = "0" * 64
expect_failure(lambda: _verify_artifact_hashes(hash_tamper), "differs")

with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    template = config_path.read_text(encoding="utf-8")
    bad = root / "bad.toml"
    bad.write_text(
        template.replace("bootstrap_replicates = 5000", "bootstrap_replicates = 4999"),
        encoding="utf-8",
    )
    expect_failure(lambda: load_sensitivity_config(bad), "bootstrap_replicates")
    bad.write_text(
        template.replace(
            "family_stacking_authorized = false",
            "family_stacking_authorized = true",
        ),
        encoding="utf-8",
    )
    expect_failure(lambda: load_sensitivity_config(bad), "false gate")
    bad.write_text(
        template.replace(
            "post_hoc_fixed_county_window_end = 2018",
            "post_hoc_fixed_county_window_end = 2017",
        ),
        encoding="utf-8",
    )
    expect_failure(lambda: load_sensitivity_config(bad), "post_hoc_fixed_county_window_end")
    bad.write_text(
        template.replace(
            'candidate_model_id = "direct_quantity"',
            'candidate_model_id = "pdsi_season_mean"',
            1,
        ),
        encoding="utf-8",
    )
    expect_failure(lambda: load_sensitivity_config(bad), "comparisons")
    bad.write_text(
        template.replace(
            'path = "us_county_validation/us_competing_moisture_predictive_v1.toml"',
            'path = "/tmp/us_competing_moisture_predictive_v1.toml"',
            1,
        ),
        encoding="utf-8",
    )
    expect_failure(lambda: load_sensitivity_config(bad), "project-relative")


protocol = load_protocol(
    PROJECT / "us_county_validation" / "us_competing_moisture_predictive_v1.toml"
)
specs = model_specs(protocol)
_assert_mutually_exclusive_families(specs, protocol)
stacked = {model: list(columns) for model, columns in specs.items()}
stacked["pdsi_stage_sensitivity"].append("d_precip_mm")
expect_failure(
    lambda: _assert_mutually_exclusive_families(stacked, protocol),
    "stacks",
)


support = pd.DataFrame(
    {
        "county_geoid": [f"{index:05d}" for index in range(30)],
        "outcome_crop": ["corn_grain"] * 30,
        "harvest_year": [2000] * 30,
        "irrigation_practice": ["irrigated"] * 30,
    }
)
shared = {model: support.copy() for model in EXPECTED_MODELS}
support_hash = require_shared_test_support(shared)
assert len(support_hash) == 64
tampered = {model: frame.copy() for model, frame in shared.items()}
tampered["pdsi_season_mean"].loc[0, "harvest_year"] = 2001
expect_failure(lambda: require_shared_test_support(tampered), "exact ordered test support")


# Hand-checkable case: two rows in each of 30 counties.  Every model has a
# constant absolute residual, so every county-bootstrap draw has the same loss
# difference and both percentile endpoints equal the point value.
n = 60
observed = np.linspace(-1.0, 1.0, n)
scores = {
    "controls_only": observed + 1.0,
    "direct_quantity": observed.copy(),
    "direct_quantity_distribution": observed + 0.5,
    "pdsi_season_mean": observed - 0.25,
    "pdsi_stage_sensitivity": observed + 0.75,
}
counties = np.repeat([f"{index:05d}" for index in range(30)], 2)
summaries, diagnostics = summarize_county_cluster_losses(
    observed,
    scores,
    counties,
    config["comparisons"],
    bootstrap_replicates=250,
    random_seed=123,
    interval_probabilities=[0.025, 0.975],
    minimum_counties=30,
    maximum_county_test_row_share=0.10,
)
summaries_again, diagnostics_again = summarize_county_cluster_losses(
    observed,
    scores,
    counties,
    config["comparisons"],
    bootstrap_replicates=250,
    random_seed=123,
    interval_probabilities=[0.025, 0.975],
    minimum_counties=30,
    maximum_county_test_row_share=0.10,
)
assert summaries == summaries_again and diagnostics == diagnostics_again
assert diagnostics["test_row_count"] == 60
assert diagnostics["occupied_county_count"] == 30
assert np.isclose(diagnostics["effective_county_count_inverse_herfindahl"], 30.0)
expected = {
    "direct_quantity_minus_controls": -1.0,
    "direct_quantity_distribution_minus_direct_quantity": 0.5,
    "pdsi_season_mean_minus_direct_quantity": 0.25,
    "pdsi_stage_sensitivity_minus_direct_quantity": 0.75,
}
for row in summaries:
    value = expected[row["comparison_id"]]
    assert np.isclose(row["rmse_difference"], value)
    assert np.isclose(row["mae_difference"], value)
    assert np.isclose(row["rmse_interval"]["lower"], value)
    assert np.isclose(row["rmse_interval"]["upper"], value)
    assert np.isclose(row["mae_interval"]["lower"], value)
    assert np.isclose(row["mae_interval"]["upper"], value)

point_rows = summarize_fixed_fit_point_losses(observed, scores, config["comparisons"])
assert {
    row["comparison_id"]: row["rmse_difference"] for row in point_rows
}.keys() == expected.keys()
for row in point_rows:
    assert np.isclose(row["rmse_difference"], expected[row["comparison_id"]])
    assert np.isclose(row["mae_difference"], expected[row["comparison_id"]])

expect_failure(
    lambda: summarize_county_cluster_losses(
        observed[:58],
        {model: values[:58] for model, values in scores.items()},
        np.repeat([f"{index:05d}" for index in range(29)], 2),
        config["comparisons"],
        100,
        1,
        [0.025, 0.975],
        30,
        0.10,
    ),
    "below the prespecified minimum",
)
dominant_counties = np.concatenate(
    [np.repeat("00000", 31), np.array([f"{index:05d}" for index in range(1, 30)])]
)
expect_failure(
    lambda: summarize_county_cluster_losses(
        observed,
        scores,
        dominant_counties,
        config["comparisons"],
        100,
        1,
        [0.025, 0.975],
        30,
        0.10,
    ),
    "maximum test-row share",
)
bad_scores = {model: values.copy() for model, values in scores.items()}
bad_scores["direct_quantity"][0] = np.nan
expect_failure(
    lambda: summarize_county_cluster_losses(
        observed,
        bad_scores,
        counties,
        config["comparisons"],
        100,
        1,
        [0.025, 0.975],
        30,
        0.10,
    ),
    "nonfinite",
)
expect_failure(lambda: _reject_sensitive_payload({"coefficients": [1.0]}), "forbidden")

serialized = json.dumps(summaries, allow_nan=False)
for forbidden in ("coefficient", "row_prediction", "row_loss", "bootstrap_draw"):
    assert forbidden not in serialized

print("U.S. competing-moisture paired-loss sensitivity synthetic tests passed")
