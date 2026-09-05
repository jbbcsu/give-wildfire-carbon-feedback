#!/usr/bin/env python3
"""Evaluate metadata-only structural feasibility for compatible RIME-X expansion."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import platform
import resource
import tomllib

from validate_isimip3b_rimex_compatible_expansion_feasibility_contract import validate as validate_contract


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


def summarize(
    member_tracks: int,
    scenarios: int,
    windows: int,
    maximum_members_per_family: int,
    minimum: int,
) -> dict[str, object]:
    require(member_tracks > maximum_members_per_family >= 1, "invalid family concentration design")
    require(scenarios >= 2 and windows >= 1, "invalid scenario/window design")
    total = member_tracks * scenarios * windows
    member_holdout = (member_tracks - 1) * scenarios * windows
    scenario_holdout = member_tracks * (scenarios - 1) * windows
    family_holdout = (member_tracks - maximum_members_per_family) * scenarios * windows
    six_tracks = member_tracks - 1
    six_track_scenario_holdout = six_tracks * (scenarios - 1) * windows
    six_track_family_holdout = (six_tracks - maximum_members_per_family) * scenarios * windows
    return {
        "design": {
            "esm_member_tracks": member_tracks,
            "esm_families_at_least": (member_tracks + maximum_members_per_family - 1) // maximum_members_per_family,
            "maximum_members_per_esm_family": maximum_members_per_family,
            "largest_esm_family_member_share": maximum_members_per_family / member_tracks,
            "scenarios": scenarios,
            "pairwise_nonoverlapping_windows_per_track": windows,
            "total_compatible_templates": total,
        },
        "holdout_training_templates": {
            "whole_esm_member": member_holdout,
            "worst_case_whole_esm_family": family_holdout,
            "whole_scenario": scenario_holdout,
        },
        "holdout_gates_strictly_exceed_minimum": {
            "whole_esm_member": member_holdout > minimum,
            "worst_case_whole_esm_family": family_holdout > minimum,
            "whole_scenario": scenario_holdout > minimum,
        },
        "six_track_minimality_check": {
            "whole_scenario_training_templates": six_track_scenario_holdout,
            "worst_case_whole_esm_family_training_templates": six_track_family_holdout,
            "whole_scenario_strict_gate_passed": six_track_scenario_holdout > minimum,
            "worst_case_whole_esm_family_strict_gate_passed": six_track_family_holdout > minimum,
        },
        "minimum_distinct_training_templates_per_holdout": minimum,
    }


def evaluate(config_path: Path, root: Path) -> dict[str, object]:
    preregistration = validate_contract(config_path, root)
    config = tomllib.loads(config_path.read_text(encoding="utf-8"))
    sources = {source["role"]: root / source["path"] for source in config["source_receipts"]}
    corrected = json.loads(sources["corrected_compatible_template_distinctness_audit"].read_text(encoding="utf-8"))
    prior_matrix = json.loads(sources["prior_official_catalogue_matrix_metadata"].read_text(encoding="utf-8"))
    require(corrected.get("status") == "no_compatible_pool_meets_locked_distinct_template_minimum", "corrected distinctness result changed")
    require(corrected.get("minimum_distinct_training_templates") == 51, "locked distinctness minimum changed")
    require(corrected.get("global_daily_files_read") == 0, "corrected audit input scope changed")
    require(prior_matrix.get("status") == "passed_exact_metadata_matrix_not_content_feature_or_holdout_validation", "prior metadata status changed")
    require(prior_matrix.get("all_public_unrestricted_cc0") is True, "prior source-rights gate changed")
    require(prior_matrix.get("new_files_acquired") is False, "prior acquisition status changed")

    design = config["minimal_design"]
    decision = config["decision"]
    summary = summarize(
        int(design["minimum_esm_member_tracks"]),
        len(design["scenarios"]),
        int(design["pairwise_nonoverlapping_windows_per_track"]),
        int(design["maximum_members_per_esm_family"]),
        int(decision["minimum_distinct_training_templates_per_holdout"]),
    )
    require(summary["design"]["esm_families_at_least"] >= int(design["minimum_esm_families"]), "minimum ESM-family count failed")
    require(all(summary["holdout_gates_strictly_exceed_minimum"].values()), "seven-track structural gate failed")
    minimality = summary["six_track_minimality_check"]
    require(minimality["whole_scenario_training_templates"] == 48, "six-track scenario count changed")
    require(minimality["worst_case_whole_esm_family_training_templates"] == 48, "six-track family count changed")
    require(not minimality["whole_scenario_strict_gate_passed"], "six-track scenario design unexpectedly passed")
    require(not minimality["worst_case_whole_esm_family_strict_gate_passed"], "six-track family design unexpectedly passed")

    maximum_rss = observed_rss_bytes()
    ceiling = int(config["resources"]["maximum_peak_resident_memory_bytes"])
    require(maximum_rss < ceiling, "peak RSS exceeded 2 GiB")
    quantum = 64 * 1024**2
    rounded_rss = ((maximum_rss + quantum - 1) // quantum) * quantum
    return {
        "schema": "isimip3b_rimex_compatible_expansion_feasibility_audit_v1",
        "status": "structurally_feasible_but_selection_catalogue_and_storage_unverified",
        "preregistration": {
            "path": "data/provenance/isimip3b_rimex_compatible_expansion_feasibility_preregistration_20260905.json",
            "sha256": sha256(root / "data/provenance/isimip3b_rimex_compatible_expansion_feasibility_preregistration_20260905.json"),
            "config_sha256": preregistration["config_sha256"],
        },
        "implementation_sha256": sha256(Path(__file__)),
        "receipt_json_files_read": 2,
        "derived_parquet_files_read": 0,
        "global_daily_files_read": 0,
        "peak_rss_observed_rounded_up_to_64_mib_bytes": rounded_rss,
        "peak_rss_gate_bytes": ceiling,
        "peak_rss_gate_passed": True,
        **summary,
        "candidate_esm_members_selected": False,
        "official_catalogue_availability_verified": False,
        "dataset_bytes_estimated": False,
        "storage_plan_authorized": False,
        "member_independence_established": False,
        "adverse_mri_stability_resolved": False,
        "dependence_fit_authorized": False,
        "acquisition_authorized": False,
        "fair_feature_response_authorized": False,
        "response_estimation_authorized": False,
        "damage_or_scc_authorized": False,
        "interpretation": (
            "A balanced seven-member, three-scenario design with four pairwise-nonoverlapping 21-year windows "
            "contains 84 compatible templates. Whole-member, worst-case whole-ESM-family, and whole-scenario "
            "holdouts retain 72, 60, and 56 templates, each strictly above 51. Six members retain only 48 after "
            "the limiting family or scenario holdout, proving seven is the minimum under the locked four-window "
            "and two-members-per-family constraints. This is arithmetic feasibility only: no members, catalogue "
            "files, byte volume, storage plan, independence evidence, fit, response, damage, or SCC are authorized."
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
    print(
        "compatible expansion feasibility: "
        f"{result['status']}; total={result['design']['total_compatible_templates']}"
    )


if __name__ == "__main__":
    main()
