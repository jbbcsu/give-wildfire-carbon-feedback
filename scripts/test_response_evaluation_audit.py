#!/usr/bin/env python3
"""Synthetic failure-mode tests for response-evaluation audit validation."""
from __future__ import annotations

import copy
import sys
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "scripts"))
from validate_response_evaluation_audit import (  # noqa: E402
    HOLDOUTS,
    STATUS,
    load_spec,
    validate_audit,
)


models, digest = load_spec(PROJECT / "config" / "response_evaluation_spec.toml")
crops = ["mai", "soy"]
results: list[dict[str, object]] = []
for crop_index, crop in enumerate(crops):
    for model_index, model in enumerate(models):
        for holdout in HOLDOUTS:
            benchmark = 0.3 + crop_index * 0.01
            rmse = benchmark - 0.01 + model_index * 0.001
            entry: dict[str, object] = {
                "crop": crop,
                "model": model,
                "holdout": holdout,
                "test_rows": 20,
                "rmse": rmse,
                "mae": rmse * 0.8,
                "r_squared": 0.1,
                "correlation": 0.2,
                "zero_change_rmse": benchmark,
                "rmse_improvement_vs_zero": benchmark - rmse,
            }
            if holdout == "spatial_block":
                entry["folds"] = [
                    {"fold": 0, "train_rows": 20, "test_rows": 10, "matrix_rank": 4, "condition_number": 2.0},
                    {"fold": 1, "train_rows": 20, "test_rows": 10, "matrix_rank": 4, "condition_number": 2.5},
                ]
            else:
                entry.update(train_rows=40, matrix_rank=4, condition_number=2.0)
            results.append(entry)

valid = {
    "status": STATUS,
    "spec_sha256": digest,
    "models": models,
    "crops": crops,
    "n_level_rows": 200,
    "n_observed_level_rows": 120,
    "n_consecutive_pairs": 80,
    "results": results,
}
summary = validate_audit(valid, models, digest, crops)
assert summary["n_consecutive_pairs"] == 80
assert len(summary["comparisons"]) == len(crops) * len(HOLDOUTS)
assert all(row["all_models_beat_zero"] for row in summary["comparisons"])
assert all(row["best_model_descriptive_only"] == models[0] for row in summary["comparisons"])

for mutator, expected in (
    (lambda audit: audit.update(spec_sha256="bad"), "frozen response"),
    (lambda audit: audit["results"].pop(), "Incomplete result product"),
    (lambda audit: audit["results"][0].update(zero_change_rmse=0.7), "benchmark differs"),
    (lambda audit: audit["results"][0].update(rmse_improvement_vs_zero=0.0), "arithmetic fails"),
    (lambda audit: audit["results"][0]["folds"][0].update(test_rows=9), "do not reconcile"),
):
    broken = copy.deepcopy(valid)
    mutator(broken)
    try:
        validate_audit(broken, models, digest, crops)
        raise AssertionError("invalid audit should fail")
    except ValueError as error:
        assert expected in str(error)

try:
    validate_audit(valid, models, digest, ["mai"])
    raise AssertionError("partial crop coverage should fail")
except ValueError as error:
    assert "crop coverage" in str(error)

print("response-evaluation audit-validator synthetic tests passed")
