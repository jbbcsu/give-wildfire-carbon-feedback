#!/usr/bin/env python3
"""Hash-locked recomputation validator for the multicrop distribution diagnostic."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

from evaluate_multicrop_rainfed_distribution_diagnostic import (
    CONTRACT_ID,
    HOLDOUTS,
    STATUS,
    assert_coefficients_suppressed,
    run_diagnostic,
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


def validate(report_path: Path) -> dict[str, Any]:
    reported = json.loads(report_path.read_text(encoding="utf-8"))
    recomputed = run_diagnostic()
    assert reported["status"] == STATUS
    assert reported["diagnostic_contract_id"] == CONTRACT_ID
    assert reported["crops"] == ["mai", "ri1", "ri2", "soy", "swh", "wwh"]
    assert reported["holdouts"] == list(HOLDOUTS)
    assert len(reported["models"]) == 7
    assert len(reported["results"]) == 6 * 7 * 3
    assert reported["coefficients_suppressed"] is True
    for gate in (
        "causal_interpretation_authorized",
        "production_model_selection_authorized",
        "response_draw_export_authorized",
        "scc_use_authorized",
    ):
        assert reported[gate] is False
    assert reported["runtime"]["maximum_worker_rss_bytes"] <= 512 * 1024 * 1024
    assert recomputed["runtime"]["maximum_worker_rss_bytes"] <= 512 * 1024 * 1024
    for row in reported["results"]:
        if row["holdout"] == "spatial_block":
            assert len(row["folds"]) == 5
            assert all(fold["endpoint_overlap_count"] == 0 for fold in row["folds"])
        else:
            assert row["endpoint_overlap_count"] == 0
    assert_coefficients_suppressed(reported)
    reported_core = {key: value for key, value in reported.items() if key != "runtime"}
    recomputed_core = {key: value for key, value in recomputed.items() if key != "runtime"}
    _equal(reported_core, recomputed_core)
    return {
        "status": "validated",
        "report": str(report_path),
        "hash_locked_full_recomputation_matches": True,
        "crop_count": 6,
        "model_count": 7,
        "holdout_count": 3,
        "result_count": 126,
        "maximum_reported_worker_rss_bytes": reported["runtime"]["maximum_worker_rss_bytes"],
        "maximum_recomputed_worker_rss_bytes": recomputed["runtime"]["maximum_worker_rss_bytes"],
        "memory_cap_bytes": 512 * 1024 * 1024,
        "all_nonspatial_endpoint_overlap_counts_zero": True,
        "coefficients_suppressed": True,
        "all_claim_gates_closed": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("report", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    summary = validate(args.report)
    payload = json.dumps(summary, indent=2, sort_keys=True) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(payload, encoding="utf-8")
    print(payload, end="")


if __name__ == "__main__":
    main()
