#!/usr/bin/env python3
"""Deterministic recomputation validator for the geographic paired-loss audit."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

from evaluate_multicrop_rainfed_distribution_geographic_audit import (
    CONFIG_DEFAULT,
    STATUS,
    load_config,
    run_audit,
)


def _equal(left: Any, right: Any, path: str = "root") -> None:
    if isinstance(left, dict) and isinstance(right, dict):
        if set(left) != set(right):
            raise AssertionError(f"Key mismatch at {path}")
        for key in left:
            _equal(left[key], right[key], f"{path}.{key}")
        return
    if isinstance(left, list) and isinstance(right, list):
        if len(left) != len(right):
            raise AssertionError(f"Length mismatch at {path}")
        for index, (a, b) in enumerate(zip(left, right)):
            _equal(a, b, f"{path}[{index}]")
        return
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        if not math.isclose(float(left), float(right), rel_tol=1e-11, abs_tol=1e-12):
            raise AssertionError(f"Numeric mismatch at {path}: {left} != {right}")
        return
    if left != right:
        raise AssertionError(f"Mismatch at {path}: {left!r} != {right!r}")


def _independent_holm(values: list[float]) -> list[float]:
    ranked = sorted(enumerate(values), key=lambda item: (item[1], item[0]))
    output = [0.0] * len(values)
    previous = 0.0
    for rank, (index, value) in enumerate(ranked):
        previous = max(previous, min(1.0, value * (len(values) - rank)))
        output[index] = previous
    return output


def validate(report_path: Path, config_path: Path = CONFIG_DEFAULT) -> dict[str, Any]:
    config, config_hash = load_config(config_path)
    reported = json.loads(report_path.read_text(encoding="utf-8"))
    recomputed = run_audit(config_path)
    assert reported["status"] == STATUS
    assert reported["config_sha256"] == config_hash
    assert reported["comparison_count"] == 30 == len(reported["results"])
    assert reported["runtime"]["maximum_worker_rss_bytes"] <= 512 * 1024 * 1024
    assert recomputed["runtime"]["maximum_worker_rss_bytes"] <= 512 * 1024 * 1024
    for gate in (
        "causal_interpretation_authorized",
        "economic_winner_loser_interpretation_authorized",
        "production_model_selection_authorized",
        "response_draw_export_authorized",
        "damage_calculation_authorized",
        "scc_use_authorized",
    ):
        assert reported[gate] is False
    assert reported["row_predictions_exported"] is False
    assert reported["bootstrap_draws_exported"] is False
    raw = [row["two_sided_bootstrap_tail_probability"] for row in reported["results"]]
    adjusted = _independent_holm(raw)
    alpha = float(config["uncertainty"]["familywise_alpha"])
    supported = []
    for row, expected in zip(reported["results"], adjusted):
        assert math.isclose(row["holm_adjusted_tail_probability_30_tests"], expected, abs_tol=1e-15)
        assert len(row["spatial_fold_differences"]) == 5
        assert {part["fold"] for part in row["spatial_fold_differences"]} == set(range(5))
        gate = (
            row["paired_cluster_bootstrap_rmse_difference_quantiles"]["p97_5"] < 0
            and expected <= alpha
            and all(part["candidate_has_lower_rmse"] for part in row["spatial_fold_differences"])
            and row["cluster_share_with_lower_candidate_mean_squared_loss"] > 0.5
        )
        assert row["passes_prespecified_descriptive_predictive_support_gate"] is gate
        if gate:
            supported.append({"crop": row["crop"], "candidate_model": row["candidate_model"]})
    assert supported == reported["comparisons_passing_descriptive_predictive_support_gate"]
    reported_core = {key: value for key, value in reported.items() if key != "runtime"}
    recomputed_core = {key: value for key, value in recomputed.items() if key != "runtime"}
    _equal(reported_core, recomputed_core)
    return {
        "status": "validated",
        "report": str(report_path),
        "deterministic_full_recomputation_matches": True,
        "independent_holm_check_matches": True,
        "comparison_count": 30,
        "descriptive_support_gate_pass_count": len(supported),
        "maximum_reported_worker_rss_bytes": reported["runtime"]["maximum_worker_rss_bytes"],
        "maximum_recomputed_worker_rss_bytes": recomputed["runtime"]["maximum_worker_rss_bytes"],
        "all_causal_economic_production_damage_scc_gates_closed": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("report", type=Path)
    parser.add_argument("--config", type=Path, default=CONFIG_DEFAULT)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    summary = validate(args.report, args.config)
    payload = json.dumps(summary, indent=2, sort_keys=True) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(payload, encoding="utf-8")
    print(payload, end="")


if __name__ == "__main__":
    main()
