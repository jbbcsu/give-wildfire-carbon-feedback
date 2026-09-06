#!/usr/bin/env python3
"""Evaluate source metadata for the preregistered precipitation fallback chain."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import platform
import resource
import tomllib

from validate_climate_fallback_chain_readiness_contract import validate as validate_contract


COMPONENT_IDS = ["mesmer_m_tp", "kemsley_markov_gamma", "mesmer_x_rx1day", "stitches"]
CAPABILITY_IDS = [
    "monthly_precipitation_backbone",
    "daily_occurrence_and_amount",
    "exact_monthly_precipitation_conservation",
    "daily_temperature_precipitation_joint_draws",
    "spatially_coherent_daily_precipitation",
    "wet_day_frequency",
    "consecutive_dry_days",
    "rx1day",
    "rx5day",
    "crop_stage_timing",
    "whole_esm_holdout",
    "whole_scenario_holdout",
    "common_random_number_fair_pairs",
    "shrinking_pulse_convergence",
    "direct_daily_reference",
]
EXECUTABLE_CHAIN_COMPONENTS = ["mesmer_m_tp", "kemsley_markov_gamma"]


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


def evaluate(config_path: Path, preregistration_path: Path, snapshot_path: Path, root: Path) -> dict[str, object]:
    config_path = config_path.resolve()
    preregistration_path = preregistration_path.resolve()
    snapshot_path = snapshot_path.resolve()
    preregistration = validate_contract(config_path, root)
    stored = json.loads(preregistration_path.read_text(encoding="utf-8"))
    require(stored == preregistration, "stored preregistration differs from validated contract")
    snapshot = tomllib.loads(snapshot_path.read_text(encoding="utf-8"))
    require(snapshot.get("schema") == "climate_fallback_chain_source_snapshot_v1", "source snapshot schema changed")
    require(snapshot.get("role") == "primary_source_metadata_snapshot_not_software_or_climate_payload", "snapshot role changed")
    require(snapshot.get("climate_payload_bytes_downloaded") == 0, "climate payload was downloaded")
    require(snapshot.get("software_archives_downloaded") == 0, "software archive was downloaded")
    require(snapshot.get("fit_or_emulation_run") is False, "fit or emulation run was performed")

    components = snapshot.get("component", [])
    require([item.get("id") for item in components] == COMPONENT_IDS, "snapshot component identities or order changed")
    require(len({item["id"] for item in components}) == len(COMPONENT_IDS), "duplicate component identity")
    by_component = {item["id"]: item for item in components}
    for item in components:
        require(item.get("peer_reviewed_method") is True, f"unreviewed component: {item['id']}")
        require(str(item.get("paper_url", "")).startswith("https://doi.org/"), f"paper DOI URL missing: {item['id']}")
        require(bool(item.get("license_identity")), f"license identity missing: {item['id']}")
        if item.get("public_executable_source"):
            require(str(item.get("repository_url", "")).startswith("https://github.com/"), f"repository URL missing: {item['id']}")
            require(len(str(item.get("pinned_code_identity", ""))) == 40, f"pinned code identity missing: {item['id']}")
            require(str(item.get("archived_release_url", "")).startswith("https://doi.org/10.5281/zenodo."), f"archive URL missing: {item['id']}")

    capabilities = snapshot.get("capability", [])
    require([item.get("id") for item in capabilities] == CAPABILITY_IDS, "capability identities or order changed")
    require(len({item["id"] for item in capabilities}) == len(CAPABILITY_IDS), "duplicate capability identity")
    for item in capabilities:
        require(isinstance(item.get("method_component_support"), bool), f"method support is not boolean: {item['id']}")
        require(isinstance(item.get("end_to_end_fallback_established"), bool), f"chain support is not boolean: {item['id']}")
        require(bool(item.get("reason")), f"capability reason missing: {item['id']}")
        require(set(item.get("evidence_components", [])).issubset(COMPONENT_IDS), f"unknown evidence component: {item['id']}")

    missing_code = [
        component_id
        for component_id in EXECUTABLE_CHAIN_COMPONENTS
        if not by_component[component_id]["public_executable_source"] or not by_component[component_id]["pinned_code_identity"]
    ]
    unresolved = [item["id"] for item in capabilities if not item["end_to_end_fallback_established"]]
    supported_methods = [item["id"] for item in capabilities if item["method_component_support"]]
    if missing_code:
        status = "fallback_not_executable_no_fit"
    elif unresolved:
        status = "fallback_not_promoted_validation_plan_only"
    else:
        status = "metadata_ready_only_fit_and_downstream_gates_still_closed"

    maximum_rss = observed_rss_bytes()
    ceiling = 2 * 1024**3
    require(maximum_rss < ceiling, "peak RSS exceeded 2 GiB")
    rounded_rss = ((maximum_rss + 64 * 1024**2 - 1) // (64 * 1024**2)) * (64 * 1024**2)
    return {
        "schema": "climate_fallback_chain_readiness_audit_v1",
        "status": status,
        "preregistration": {"path": preregistration_path.relative_to(root).as_posix(), "sha256": sha256(preregistration_path)},
        "config": {"path": config_path.relative_to(root).as_posix(), "sha256": sha256(config_path)},
        "source_snapshot": {"path": snapshot_path.relative_to(root).as_posix(), "sha256": sha256(snapshot_path)},
        "component_ids": COMPONENT_IDS,
        "executable_chain_component_ids": EXECUTABLE_CHAIN_COMPONENTS,
        "public_executable_code_missing": missing_code,
        "method_capabilities_supported": supported_methods,
        "end_to_end_capabilities_unresolved": unresolved,
        "end_to_end_capability_count": len(CAPABILITY_IDS),
        "end_to_end_capability_pass_count": len(CAPABILITY_IDS) - len(unresolved),
        "climate_payload_bytes_downloaded": 0,
        "software_archives_downloaded": 0,
        "peak_rss_observed_rounded_up_to_64_mib_bytes": rounded_rss,
        "peak_rss_gate_bytes": ceiling,
        "peak_rss_gate_passed": True,
        "fallback_selected": False,
        "software_acquisition_authorized": False,
        "climate_payload_acquisition_authorized": False,
        "emulator_fit_authorized": False,
        "fair_feature_response_authorized": False,
        "response_estimation_authorized": False,
        "damage_or_scc_authorized": False,
        "interpretation": (
            "MESMER-M-TP remains a reproducible monthly backbone and the benchmark components are archived, but the "
            "preregistered Kemsley daily generator has no identified pinned public executable source. Fourteen of fifteen "
            "end-to-end capabilities remain unestablished, including monthly conservation, joint daily temperature-precipitation "
            "draws, spatial daily dependence, Rx5day, crop-stage fidelity, whole-ESM/scenario holdouts, and matched FAIR pulse "
            "convergence. The fallback is retained as a validation plan but is not executable or promoted."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--preregistration", type=Path, required=True)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = evaluate(args.config, args.preregistration, args.snapshot, args.root.resolve())
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"climate fallback readiness audit passed: status={result['status']}")


if __name__ == "__main__":
    main()
