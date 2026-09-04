#!/usr/bin/env python3
"""Validate the preregistered represented-template dependence diagnostic."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import tomllib


SCHEMA = "isimip3b_rimex_dependence_stability_contract_v1"
COORDINATES = [
    "tmean_c", "log_precip", "wet_logit", "cdd_logit",
    "rx5_share_logit", "rx1_given_rx5_logit", "stage_alr1", "stage_alr2",
]
ESMS = ["GFDL-ESM4", "IPSL-CM6A-LR", "MPI-ESM1-2-HR", "MRI-ESM2-0"]
SCENARIOS = ["ssp126", "ssp370", "ssp585"]


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
    require(config.get("role", "").startswith("outcome_blind_"), "outcome-blind role changed")
    for gate in ("real_joint_fit_authorized", "fair_feature_response_authorized", "response_estimation_authorized", "damage_or_scc_authorized"):
        require(config.get(gate) is False, f"closed gate changed: {gate}")

    sample = config.get("sample", {})
    require(sample.get("completed_templates_required") == 88, "completed-template sample changed")
    require(sample.get("center_years") == list(range(2042, 2050)), "center-year blocks changed")
    require(sample.get("expected_rows_per_template") == 7676, "complete-template row count changed")
    require(sample.get("minimum_training_templates") == 51, "minimum training support changed")
    require(sample.get("represented_whole_esm_holdouts") == ESMS, "represented ESM holdouts changed")
    require(sample.get("represented_whole_scenario_holdouts") == SCENARIOS, "scenario holdouts changed")
    require(sample.get("balanced_five_esm_three_scenario_matrix_required_for_promotion") is True, "balanced-matrix promotion gate weakened")

    method = config.get("method", {})
    require(method.get("linked_coordinates") == COORDINATES, "linked-coordinate basis changed")
    for gate in ("stage_shares_derived_from_centered_stage_precipitation", "one_centered_season_and_stage_file_pair_read_at_a_time", "explicit_center_year_blocks", "whole_esm_holdout_required", "whole_scenario_holdout_required", "held_out_templates_excluded_from_training", "outcome_columns_forbidden", "model_fit_forbidden"):
        require(method.get(gate) is True, f"method safety gate changed: {gate}")
    require(method.get("scenario_identity_as_predictor") is False, "scenario shortcut opened")

    diagnostic = config.get("diagnostic", {})
    require(diagnostic.get("pairwise_coordinate_pairs") == 28, "coordinate-pair count changed")
    require(diagnostic.get("mean_absolute_difference_max") == 0.05, "mean stability tolerance changed")
    require(diagnostic.get("maximum_absolute_difference_max") == 0.15, "maximum stability tolerance changed")
    require(diagnostic.get("strong_pair_absolute_training_median") == 0.20, "strong-pair threshold changed")
    require(diagnostic.get("strong_pair_sign_flips_allowed") == 0, "sign-flip gate changed")
    require(diagnostic.get("every_represented_holdout_must_pass") is True, "holdout gate weakened")
    require(diagnostic.get("diagnostic_pass_does_not_authorize_promotion") is True, "diagnostic was allowed to promote")

    resources = config.get("resources", {})
    require(resources.get("maximum_peak_resident_memory_bytes") == 2 * 1024**3, "memory ceiling changed")
    for gate in ("large_downloads_forbidden", "raw_rehydration_forbidden", "global_daily_inputs_forbidden", "derived_parquet_columns_only"):
        require(resources.get(gate) is True, f"resource gate changed: {gate}")

    sources = []
    for source in config.get("source_receipts", []):
        path = root / source["path"]
        observed = sha256(path)
        require(observed == source["sha256"], f"source receipt hash changed: {source['path']}")
        sources.append({**source, "sha256": observed})
    require(len(sources) == 2, "source receipt count changed")

    return {
        "schema": "isimip3b_rimex_dependence_stability_preregistration_v1",
        "status": "validated_preregistered_before_real_template_diagnostic",
        "config_sha256": sha256(config_path),
        "implementation_sha256": sha256(Path(__file__)),
        "sources": sources,
        "completed_templates_locked": 88,
        "represented_holdouts_locked": len(ESMS) + len(SCENARIOS),
        "real_joint_fit_authorized": False,
        "fair_feature_response_authorized": False,
        "damage_or_scc_authorized": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = validate(args.config, args.root)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("RIME-X represented-template dependence diagnostic preregistration passed")


if __name__ == "__main__":
    main()
