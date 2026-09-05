#!/usr/bin/env python3
"""Audit compatibility before counting nonoverlapping dependence templates."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import platform
import resource
import tomllib

from validate_isimip3b_rimex_template_compatibility_distinctness_contract import validate as validate_contract


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


def summarize(inventory: dict[str, object], config: dict[str, object]) -> dict[str, object]:
    target = config["target_template"]
    matrix = config["matrix"]
    decision = config["decision"]
    esms = list(matrix["expected_esms"])
    scenarios = list(matrix["expected_scenarios"])
    centers = list(target["required_center_years"])
    selected = maximum_nonoverlapping_centers(centers, int(target["window_year_radius"]))
    require(selected == [2042], "current centered-window nonoverlap result changed")
    identities = {(str(row["esm"]), str(row["scenario"])) for row in inventory["cells"]}
    expected = {(esm, scenario) for esm in esms for scenario in scenarios}
    require(len(identities) == int(matrix["current_compatible_dataset_cells"]), "current compatible cell count changed")

    current_upper = len(identities) * len(selected)
    complete_upper = len(expected) * len(selected)
    esm_holdouts = {
        esm: len({identity for identity in identities if identity[0] != esm}) * len(selected)
        for esm in esms
    }
    scenario_holdouts = {
        scenario: len({identity for identity in identities if identity[1] != scenario}) * len(selected)
        for scenario in scenarios
    }
    minimum = int(decision["minimum_distinct_training_templates_per_permitted_pool"])
    require(current_upper == 11, "current compatible upper bound changed")
    require(complete_upper == 15, "complete compatible upper bound changed")
    return {
        "compatible_inventory": {
            "current_dataset_cells": len(identities),
            "nominal_centered_templates": len(identities) * len(centers),
            "maximum_pairwise_nonoverlapping_templates": current_upper,
            "complete_design_dataset_cells": len(expected),
            "complete_design_nominal_centered_templates": len(expected) * len(centers),
            "complete_design_maximum_pairwise_nonoverlapping_templates": complete_upper,
            "selected_center_year_per_track": selected,
        },
        "incompatible_candidate_products": {
            "receipt_count": len(config["incompatible_candidate_receipts"]),
            "combined_rows": 2376990,
            "nominal_exact_year_labels": 315,
            "compatible_centered_multicrop_regime_templates_contributed": 0,
            "reason": "annual one_crop_regime_two_latitude holdout rows are not registered as centered_21yr linked multicrop_regime dependence templates",
        },
        "current_whole_esm_holdout_nonoverlap_upper_bounds": esm_holdouts,
        "current_whole_scenario_holdout_nonoverlap_upper_bounds": scenario_holdouts,
        "complete_design_whole_esm_holdout_nonoverlap_upper_bound": (len(esms) - 1) * len(scenarios) * len(selected),
        "complete_design_whole_scenario_holdout_nonoverlap_upper_bound": len(esms) * (len(scenarios) - 1) * len(selected),
        "minimum_distinct_training_templates": minimum,
        "current_upper_bound_shortfall": minimum - current_upper,
        "complete_design_upper_bound_shortfall": minimum - complete_upper,
        "current_upper_bound_gate_passed": current_upper >= minimum,
        "complete_design_upper_bound_gate_passed": complete_upper >= minimum,
        "decision": "no_compatible_pool_meets_locked_distinct_template_minimum",
    }


def evaluate(config_path: Path, root: Path) -> dict[str, object]:
    preregistration = validate_contract(config_path, root)
    config = tomllib.loads(config_path.read_text(encoding="utf-8"))
    inventory_path = root / "data/provenance/isimip3b_rimex_contiguous_completed_matrix_audit_20260903.json"
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    summary = summarize(inventory, config)
    maximum_rss = observed_rss_bytes()
    ceiling = int(config["resources"]["maximum_peak_resident_memory_bytes"])
    require(maximum_rss < ceiling, "peak RSS exceeded 2 GiB")
    quantum = 64 * 1024**2
    rounded_rss = ((maximum_rss + quantum - 1) // quantum) * quantum
    require(not summary["current_upper_bound_gate_passed"], "current distinctness gate unexpectedly passed")
    require(not summary["complete_design_upper_bound_gate_passed"], "complete-design distinctness gate unexpectedly passed")
    return {
        "schema": "isimip3b_rimex_template_compatibility_distinctness_audit_v2",
        "status": summary["decision"],
        "supersedes_withdrawn_v1_audit": "data/provenance/isimip3b_rimex_temporal_distinctness_audit_20260904.json",
        "preregistration": {
            "path": "data/provenance/isimip3b_rimex_template_compatibility_distinctness_preregistration_v2_20260904.json",
            "sha256": sha256(root / "data/provenance/isimip3b_rimex_template_compatibility_distinctness_preregistration_v2_20260904.json"),
            "config_sha256": preregistration["config_sha256"],
        },
        "implementation_sha256": sha256(Path(__file__)),
        "top_level_receipt_json_files_read": preregistration["top_level_receipts_read"],
        "nested_compatible_receipt_json_files_read": preregistration["nested_compatible_receipts_read"],
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
            "Only the 88 nominal centered multicrop/regime RIME-X templates are compatible with the registered "
            "dependence unit. Their eight 21-year windows overlap within every ESM-member-scenario track, leaving "
            "at most one pairwise-nonoverlapping window per completed dataset cell: 11 now and 15 after matrix "
            "completion, versus the locked minimum of 51. The 2,376,990 legacy early/mid/end holdout rows contribute "
            "zero compatible templates because they are not registered as centered 21-year linked multicrop/regime fields."
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
    print(f"corrected compatibility/distinctness decision: {result['status']}; current_upper_bound={result['compatible_inventory']['maximum_pairwise_nonoverlapping_templates']}")


if __name__ == "__main__":
    main()
