#!/usr/bin/env python3
"""Synthetic integrity tests for the paired-loss uncertainty sensitivity."""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd


PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "scripts"))
from evaluate_direct_scpdsi_paired_loss_uncertainty import (  # noqa: E402
    _cluster_codes,
    load_sensitivity_config,
    summarize_fixed_oof_losses,
)


def expect_failure(action: Callable[[], object], text: str) -> None:
    try:
        action()
    except (ValueError, FileNotFoundError, AssertionError) as error:
        assert text.lower() in str(error).lower(), str(error)
    else:
        raise AssertionError(f"Expected failure containing {text!r}")


template_path = PROJECT / "config" / "direct_scpdsi_paired_loss_uncertainty_v1.toml"
config = load_sensitivity_config(template_path)
assert config["bootstrap_replicates"] == 5000
assert config["training_reestimated_within_bootstrap"] is False
assert len(config["comparisons"]) == 7

with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    template = template_path.read_text(encoding="utf-8")
    bad = root / "bad.toml"
    bad.write_text(template.replace("bootstrap_replicates = 5000", "bootstrap_replicates = 4999"))
    expect_failure(lambda: load_sensitivity_config(bad), "bootstrap_replicates")
    bad.write_text(
        template.replace(
            "training_reestimated_within_bootstrap = false",
            "training_reestimated_within_bootstrap = true",
        )
    )
    expect_failure(lambda: load_sensitivity_config(bad), "training_reestimated")
    bad.write_text(template.replace("candidate_model_id = \"direct_quantity\"", "candidate_model_id = \"scpdsi_mean\"", 1))
    expect_failure(lambda: load_sensitivity_config(bad), "comparisons")


coordinates = pd.DataFrame(
    {
        "lat": [-89.9, -81.0, -80.0, -80.0],
        "lon_360": [0.1, 9.9, 10.0, 359.9],
    }
)
codes = _cluster_codes(coordinates, 10, 10)
assert codes[0] == codes[1]
assert codes[1] != codes[2]
assert codes[2] != codes[3]
expect_failure(
    lambda: _cluster_codes(pd.DataFrame({"lat": [90.0], "lon_360": [0.0]}), 10, 10),
    "outside",
)


# A hand-checkable paired case: controls err by one everywhere, direct is exact,
# and scPDSI mean duplicates controls. Sixty rows occupy thirty equal clusters.
n = 60
observed = np.linspace(-1.0, 1.0, n)
controls = observed + 1.0
direct = observed.copy()
scores = {
    "controls_only": controls,
    "direct_quantity": direct,
    "scpdsi_mean": controls.copy(),
    "scpdsi_seasonal_summary": observed + 0.5,
    "scpdsi_stage_means": observed - 0.25,
}
clusters = np.repeat(np.arange(30), 2)
comparisons = config["comparisons"]
summary, diagnostics = summarize_fixed_oof_losses(
    observed,
    scores,
    clusters,
    comparisons,
    bootstrap_replicates=250,
    random_seed=123,
    interval_probabilities=[0.025, 0.975],
    minimum_clusters=30,
    maximum_cluster_pair_share=0.10,
)
summary_again, diagnostics_again = summarize_fixed_oof_losses(
    observed,
    scores,
    clusters,
    comparisons,
    bootstrap_replicates=250,
    random_seed=123,
    interval_probabilities=[0.025, 0.975],
    minimum_clusters=30,
    maximum_cluster_pair_share=0.10,
)
assert summary == summary_again and diagnostics == diagnostics_again
assert diagnostics["pair_count"] == 60
assert diagnostics["occupied_cluster_count"] == 30
assert np.isclose(diagnostics["effective_cluster_count_inverse_herfindahl"], 30.0)
by_id = {row["comparison_id"]: row for row in summary}
direct_row = by_id["direct_quantity_minus_controls"]
assert np.isclose(direct_row["candidate_oof_rmse"], 0.0)
assert np.isclose(direct_row["reference_oof_rmse"], 1.0)
assert np.isclose(direct_row["rmse_difference"], -1.0)
assert np.isclose(direct_row["mae_difference"], -1.0)
assert np.isclose(direct_row["rmse_interval"]["lower"], -1.0)
assert np.isclose(direct_row["rmse_interval"]["upper"], -1.0)
same_row = by_id["scpdsi_mean_minus_controls"]
assert same_row["rmse_difference"] == 0.0
assert same_row["mae_difference"] == 0.0
assert same_row["rmse_interval"] == {"lower": 0.0, "upper": 0.0}
assert same_row["mae_interval"] == {"lower": 0.0, "upper": 0.0}
rendered = json.dumps(summary)
for forbidden in ("coefficient", "prediction", "row_loss", "bootstrap_draw", "p_value", "significant"):
    assert forbidden not in rendered


expect_failure(
    lambda: summarize_fixed_oof_losses(
        observed,
        scores,
        np.zeros(n, dtype=int),
        comparisons,
        bootstrap_replicates=100,
        random_seed=1,
        interval_probabilities=[0.025, 0.975],
        minimum_clusters=30,
        maximum_cluster_pair_share=0.10,
    ),
    "cluster count",
)
dominant_clusters = np.concatenate([np.zeros(31, dtype=int), np.arange(1, 30)])
expect_failure(
    lambda: summarize_fixed_oof_losses(
        observed,
        scores,
        dominant_clusters,
        comparisons,
        bootstrap_replicates=100,
        random_seed=1,
        interval_probabilities=[0.025, 0.975],
        minimum_clusters=30,
        maximum_cluster_pair_share=0.10,
    ),
    "maximum pair share",
)
bad_scores = {name: values.copy() for name, values in scores.items()}
bad_scores["direct_quantity"][0] = np.nan
expect_failure(
    lambda: summarize_fixed_oof_losses(
        observed,
        bad_scores,
        clusters,
        comparisons,
        bootstrap_replicates=100,
        random_seed=1,
        interval_probabilities=[0.025, 0.975],
        minimum_clusters=30,
        maximum_cluster_pair_share=0.10,
    ),
    "nonfinite",
)

print("paired-loss uncertainty sensitivity synthetic tests passed")
