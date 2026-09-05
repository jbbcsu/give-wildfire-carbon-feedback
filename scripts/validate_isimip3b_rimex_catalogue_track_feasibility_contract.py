#!/usr/bin/env python3
"""Validate the no-fit official-catalogue track-feasibility contract."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import tomllib


SCHEMA = "isimip3b_rimex_catalogue_track_feasibility_contract_v1"
SCENARIOS = ["ssp126", "ssp370", "ssp585"]
VARIABLES = ["pr", "tas"]
CENTERS = [2025, 2046, 2067, 2088]
STARTS = [2015, 2036, 2057, 2078]
ENDS = [2035, 2056, 2077, 2098]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate(config_path: Path, root: Path) -> dict[str, object]:
    config = tomllib.loads(config_path.read_text(encoding="utf-8"))
    require(config.get("schema") == SCHEMA, "contract schema changed")
    require(config.get("role") == "outcome_blind_no_fit_official_catalogue_metadata_only_track_screen", "role changed")
    require(config.get("primary_climate_route") == "direct_isimip3b_daily_feature_response", "primary route changed")
    require(config.get("fallback_climate_route") == "mesmer_m_tp_plus_published_daily_generator", "fallback route changed")
    for gate in (
        "candidate_ensemble_selection_authorized",
        "acquisition_authorized",
        "dependence_fit_authorized",
        "fair_feature_response_authorized",
        "response_estimation_authorized",
        "damage_or_scc_authorized",
    ):
        require(config.get(gate) is False, f"closed gate changed: {gate}")

    source = config.get("source", {})
    require(source.get("catalogue_api") == "https://data.isimip.org/api/v1/datasets/", "catalogue API changed")
    expected_source = {
        "simulation_round": "ISIMIP3b",
        "product": "InputData",
        "region": "global",
        "time_step": "daily",
        "bias_adjustment": "w5e5",
        "dataset_version": "20210512",
        "rights": "CC0 1.0",
        "resource_doi": "10.48364/ISIMIP.842396.1",
    }
    require(all(source.get(key) == value for key, value in expected_source.items()), "source identity changed")
    require(source.get("query_must_not_filter_climate_forcing") is True, "forcing discovery gate changed")
    require(source.get("query_must_not_filter_ensemble_member") is True, "member discovery gate changed")

    screen = config.get("screen", {})
    require(screen.get("scenarios") == SCENARIOS, "scenario set changed")
    require(screen.get("variables") == VARIABLES, "variable set changed")
    require(screen.get("window_centers") == CENTERS, "window centers changed")
    require(screen.get("window_starts") == STARTS, "window starts changed")
    require(screen.get("window_ends") == ENDS, "window ends changed")
    for center, start, end in zip(CENTERS, STARTS, ENDS, strict=True):
        require(end - start + 1 == 21 and center - start == 10 and end - center == 10, "window geometry changed")
    require(all(STARTS[index] > ENDS[index - 1] for index in range(1, len(STARTS))), "windows overlap")
    require(screen.get("minimum_esm_member_tracks") == 7, "minimum track count changed")
    require(screen.get("minimum_esm_families") == 4, "minimum family count changed")
    require(screen.get("maximum_members_per_esm_family") == 2, "family cap changed")
    for gate in (
        "same_esm_member_required_across_all_scenarios_variables_and_windows",
        "balanced_catalogue_matrix_required",
        "public_unrestricted_cc0_required",
        "complete_daily_coverage_required",
        "exact_file_bytes_and_sha512_required",
        "report_all_eligible_tracks_without_selecting_final_ensemble",
        "report_unique_required_source_files_and_catalogue_bytes",
    ):
        require(screen.get(gate) is True, f"screen gate changed: {gate}")

    decision = config.get("decision", {})
    require(decision.get("if_fewer_than_seven_tracks") == "catalogue_track_gate_failed_no_acquisition_or_fit", "failure decision changed")
    require(decision.get("if_seven_or_more_tracks") == "metadata_feasible_only_storage_and_scientific_gates_still_required", "pass decision changed")
    for gate in (
        "strictly_exceed_51_templates_after_whole_member_family_scenario_holdouts_required",
        "member_independence_must_be_established_separately",
        "adverse_mri_stability_must_be_resolved_separately",
        "storage_retention_review_required_before_acquisition",
        "no_outcome_columns",
    ):
        require(decision.get(gate) is True, f"decision gate changed: {gate}")

    resources = config.get("resources", {})
    require(resources.get("maximum_peak_resident_memory_bytes") == 2 * 1024**3, "memory ceiling changed")
    require(resources.get("minimum_free_disk_bytes_before_any_future_acquisition") == 150 * 1024**3, "disk floor changed")
    for gate in ("large_downloads_forbidden", "raw_rehydration_forbidden", "global_daily_inputs_forbidden", "derived_parquet_inputs_forbidden", "metadata_payloads_only"):
        require(resources.get(gate) is True, f"resource gate changed: {gate}")

    limitations = config.get("limitations", {})
    for gate in ("final_ensemble_not_selected", "member_independence_not_established", "adverse_mri_stability_unresolved", "storage_plan_not_authorized"):
        require(limitations.get(gate) is True, f"limitation changed: {gate}")

    sources = []
    for source_receipt in config.get("source_receipts", []):
        path = root / source_receipt["path"]
        observed = sha256(path)
        require(observed == source_receipt["sha256"], f"source receipt hash changed: {source_receipt['path']}")
        sources.append({**source_receipt, "sha256": observed})
    require(len(sources) == 2, "source receipt count changed")

    return {
        "schema": "isimip3b_rimex_catalogue_track_feasibility_preregistration_v1",
        "status": "validated_before_official_catalogue_metadata_query",
        "config_sha256": sha256(config_path),
        "implementation_sha256": sha256(Path(__file__)),
        "sources": sources,
        "minimum_esm_member_tracks": 7,
        "scenarios": SCENARIOS,
        "variables": VARIABLES,
        "window_starts": STARTS,
        "window_ends": ENDS,
        "final_ensemble_selection_authorized": False,
        "acquisition_authorized": False,
        "dependence_fit_authorized": False,
        "fair_feature_response_authorized": False,
        "damage_or_scc_authorized": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = validate(args.config, args.root.resolve())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("ISIMIP3b catalogue track-feasibility preregistration passed")


if __name__ == "__main__":
    main()
