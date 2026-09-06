#!/usr/bin/env python3
"""Validate the metadata-only precipitation fallback readiness contract."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import tomllib


SCHEMA = "climate_fallback_chain_readiness_contract_v1"
ROLE = "outcome_blind_metadata_only_mesmer_m_tp_daily_generator_readiness_screen"
COMPONENTS = ["mesmer_m_tp", "kemsley_markov_gamma", "mesmer_x_rx1day", "stitches"]


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
    require(config.get("role") == ROLE, "role changed")
    require(config.get("primary_climate_route") == "direct_isimip3b_daily_feature_response", "primary route changed")
    require(
        config.get("fallback_climate_route") == "mesmer_m_tp_plus_kemsley_markov_gamma_daily_generator",
        "fallback route changed",
    )
    for gate in (
        "fallback_selection_authorized",
        "software_acquisition_authorized",
        "climate_payload_acquisition_authorized",
        "emulator_fit_authorized",
        "fair_feature_response_authorized",
        "response_estimation_authorized",
        "damage_or_scc_authorized",
    ):
        require(config.get(gate) is False, f"closed gate changed: {gate}")

    components = config.get("components", {})
    require(list(components) == ["monthly_backbone", "daily_generator", "heavy_rain_benchmark", "sequence_benchmark"], "component roles changed")
    require([components[role].get("id") for role in components] == COMPONENTS, "component identities changed")
    require(components["monthly_backbone"].get("paper_doi") == "10.5194/gmd-17-8283-2024", "monthly backbone DOI changed")
    require(components["daily_generator"].get("paper_doi") == "10.1002/joc.8320", "daily generator DOI changed")
    require(components["heavy_rain_benchmark"].get("paper_doi") == "10.1088/1748-9326/ae5fad", "tail benchmark DOI changed")
    require(components["sequence_benchmark"].get("paper_doi") == "10.5194/esd-13-1557-2022", "sequence benchmark DOI changed")

    screen = config.get("screen", {})
    require(screen.get("component_ids") == COMPONENTS, "screen component identities changed")
    required_screen_gates = (
        "public_source_or_archive_required",
        "license_identity_required",
        "peer_reviewed_method_required",
        "pinned_code_identity_required_for_executable_components",
        "monthly_precipitation_backbone_required",
        "daily_occurrence_and_amount_required",
        "exact_monthly_precipitation_conservation_required",
        "daily_temperature_precipitation_joint_draws_required",
        "spatially_coherent_daily_precipitation_required",
        "wet_day_frequency_required",
        "consecutive_dry_days_required",
        "rx1day_required",
        "rx5day_required",
        "crop_stage_timing_required",
        "whole_esm_holdout_required",
        "whole_scenario_holdout_required",
        "common_random_number_fair_pairs_required",
        "shrinking_pulse_convergence_required",
        "direct_daily_reference_required",
    )
    for gate in required_screen_gates:
        require(screen.get(gate) is True, f"screen gate changed: {gate}")

    decision = config.get("decision", {})
    require(decision.get("if_any_executable_component_lacks_pinned_public_code") == "fallback_not_executable_no_fit", "missing-code decision changed")
    require(decision.get("if_any_end_to_end_capability_is_unestablished") == "fallback_not_promoted_validation_plan_only", "capability decision changed")
    for gate in ("no_component_substitution_after_preregistration", "no_outcome_columns", "no_empirical_coefficients"):
        require(decision.get(gate) is True, f"decision gate changed: {gate}")

    resources = config.get("resources", {})
    require(resources.get("maximum_peak_resident_memory_bytes") == 2 * 1024**3, "memory ceiling changed")
    require(resources.get("minimum_free_disk_bytes_before_any_future_acquisition") == 150 * 1024**3, "disk floor changed")
    for gate in ("metadata_payloads_only", "large_downloads_forbidden", "raw_rehydration_forbidden", "global_daily_inputs_forbidden", "derived_parquet_inputs_forbidden"):
        require(resources.get(gate) is True, f"resource gate changed: {gate}")

    sources = []
    for receipt in config.get("source_receipts", []):
        path = root / receipt["path"]
        observed = sha256(path)
        require(observed == receipt["sha256"], f"source receipt hash changed: {receipt['path']}")
        sources.append({**receipt, "sha256": observed})
    require(len(sources) == 3, "source receipt count changed")

    return {
        "schema": "climate_fallback_chain_readiness_preregistration_v1",
        "status": "validated_before_fallback_source_metadata_snapshot",
        "config_sha256": sha256(config_path),
        "implementation_sha256": sha256(Path(__file__)),
        "sources": sources,
        "component_ids": COMPONENTS,
        "fallback_selection_authorized": False,
        "software_acquisition_authorized": False,
        "climate_payload_acquisition_authorized": False,
        "emulator_fit_authorized": False,
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
    print("climate fallback readiness preregistration passed")


if __name__ == "__main__":
    main()
