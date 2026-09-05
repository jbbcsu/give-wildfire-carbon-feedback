#!/usr/bin/env python3
"""Count a permissive upper bound on nonoverlapping climate templates.

The evaluator reads checksum-bound JSON receipts through the preregistration
validator. It never reads Parquet or daily climate data and never fits a model.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import platform
import resource
import tomllib

from validate_isimip3b_rimex_temporal_distinctness_contract import validate as validate_contract


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def observed_rss_bytes() -> int:
    raw = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    return raw if platform.system() == "Darwin" else raw * 1024


def maximum_nonoverlapping_centers(center_years: list[int], radius: int) -> list[int]:
    """Greedy maximum-cardinality selection for equal closed intervals."""
    candidates = sorted(set(int(year) for year in center_years), key=lambda year: (year + radius, year))
    selected = []
    previous_end = None
    for year in candidates:
        start = year - radius
        end = year + radius
        if previous_end is None or start > previous_end:
            selected.append(year)
            previous_end = end
    return selected


def summarize(config: dict[str, object]) -> dict[str, object]:
    matrix = config["matrix"]
    decision = config["distinctness"]
    esms = list(matrix["expected_esms"])
    scenarios = list(matrix["expected_future_scenarios"])
    radius = int(decision["window_year_radius"])
    minimum = int(decision["minimum_distinct_training_templates_per_permitted_pool"])
    future_years = [
        *matrix["early_future_center_years"],
        *matrix["midcentury_center_years"],
        *matrix["endcentury_center_years"],
    ]
    historical_years = list(matrix["historical_center_years"])
    require(len(future_years) == len(set(future_years)), "future center-year periods overlap exactly")
    require(not (set(future_years) & set(historical_years)), "historical and future center-year labels overlap")

    selected_future = maximum_nonoverlapping_centers(future_years, radius)
    selected_historical = maximum_nonoverlapping_centers(historical_years, radius)
    track_rows = []
    for esm in esms:
        for scenario in scenarios:
            track_rows.append({
                "esm": esm,
                "scenario": scenario,
                "nominal_center_year_count": len(future_years),
                "maximum_pairwise_nonoverlapping_center_years": selected_future,
                "maximum_pairwise_nonoverlapping_count": len(selected_future),
            })

    nominal_future = len(esms) * len(scenarios) * len(future_years)
    upper_future = len(track_rows) * len(selected_future)
    nominal_historical = len(esms) * len(historical_years)
    upper_historical = len(esms) * len(selected_historical)
    future_shortfall = max(0, minimum - upper_future)
    augmented_shortfall = max(0, minimum - (upper_future + upper_historical))
    whole_esm_training = (len(esms) - 1) * len(scenarios) * len(selected_future)
    whole_scenario_training = len(esms) * (len(scenarios) - 1) * len(selected_future)
    require(upper_future == 45, "future-only permissive upper bound changed")
    require(upper_future + upper_historical == 50, "historical-augmented permissive upper bound changed")

    return {
        "nominal_exact_label_counts": {
            "future_only": nominal_future,
            "historical": nominal_historical,
            "historical_augmented": nominal_future + nominal_historical,
        },
        "permissive_pairwise_nonoverlap_upper_bounds": {
            "future_only": upper_future,
            "historical": upper_historical,
            "historical_augmented_diagnostic": upper_future + upper_historical,
            "whole_esm_holdout_future_training": whole_esm_training,
            "whole_scenario_holdout_future_training": whole_scenario_training,
        },
        "minimum_distinct_training_templates": minimum,
        "future_only_shortfall": future_shortfall,
        "historical_augmented_diagnostic_shortfall": augmented_shortfall,
        "future_only_upper_bound_gate_passed": upper_future >= minimum,
        "historical_augmented_diagnostic_gate_passed": upper_future + upper_historical >= minimum,
        "whole_esm_holdout_future_training_gate_passed": whole_esm_training >= minimum,
        "whole_scenario_holdout_future_training_gate_passed": whole_scenario_training >= minimum,
        "future_track_count": len(track_rows),
        "future_track_rows": track_rows,
        "historical_track": {
            "nominal_center_year_count_per_esm": len(historical_years),
            "maximum_pairwise_nonoverlapping_center_years": selected_historical,
            "maximum_pairwise_nonoverlapping_count_per_esm": len(selected_historical),
        },
        "decision": "no_pool_meets_locked_distinct_template_minimum",
    }


def evaluate(config_path: Path, root: Path) -> dict[str, object]:
    preregistration = validate_contract(config_path, root)
    config = tomllib.loads(config_path.read_text(encoding="utf-8"))
    summary = summarize(config)
    maximum_rss = observed_rss_bytes()
    ceiling = int(config["resources"]["maximum_peak_resident_memory_bytes"])
    require(maximum_rss < ceiling, "peak RSS exceeded 2 GiB")
    quantum = 64 * 1024**2
    rounded_rss = ((maximum_rss + quantum - 1) // quantum) * quantum
    require(not summary["future_only_upper_bound_gate_passed"], "future-only distinctness gate unexpectedly passed")
    require(not summary["historical_augmented_diagnostic_gate_passed"], "historical diagnostic unexpectedly passed")

    return {
        "schema": "isimip3b_rimex_temporal_distinctness_audit_v1",
        "status": summary["decision"],
        "preregistration": {
            "path": "data/provenance/isimip3b_rimex_temporal_distinctness_preregistration_20260904.json",
            "sha256": sha256(root / "data/provenance/isimip3b_rimex_temporal_distinctness_preregistration_20260904.json"),
            "config_sha256": preregistration["config_sha256"],
        },
        "implementation_sha256": sha256(Path(__file__)),
        "top_level_receipt_json_files_read": preregistration["top_level_receipts_read"],
        "nested_receipt_json_files_read": preregistration["nested_receipts_read"],
        "derived_parquet_files_read": 0,
        "global_daily_files_read": 0,
        "peak_rss_observed_rounded_up_to_64_mib_bytes": rounded_rss,
        "peak_rss_gate_bytes": ceiling,
        "peak_rss_gate_passed": True,
        **summary,
        "dependence_fit_authorized": False,
        "fair_feature_response_authorized": False,
        "response_estimation_authorized": False,
        "damage_or_scc_authorized": False,
        "interpretation": (
            "The complete legacy early/mid/end inventory has 300 nominal future labels, but overlapping "
            "21-year windows yield at most 45 pairwise-nonoverlapping future labels even when different "
            "scenario branches are counted separately. Adding historical raises this permissive diagnostic "
            "upper bound only to 50. Both remain below the locked minimum of 51, and pairwise nonoverlap is "
            "itself only an upper bound rather than evidence of stochastic independence."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = evaluate(args.config, args.root.resolve())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"temporal distinctness decision: {result['status']}; future_upper_bound={result['permissive_pairwise_nonoverlap_upper_bounds']['future_only']}")


if __name__ == "__main__":
    main()
