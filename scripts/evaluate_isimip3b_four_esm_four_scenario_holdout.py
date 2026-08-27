#!/usr/bin/env python3
"""Joint bounded four-ESM/four-scenario feature holdout audit."""
from __future__ import annotations

import argparse
import json
import tomllib
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

import evaluate_isimip3b_five_esm_holdout_smoke as esm_helpers
import evaluate_isimip3b_gfdl_scenario_holdout_smoke as scenario_helpers
import validate_paired_feature_emulator as training_helpers
from evaluate_isimip3b_five_esm_holdout_smoke import (
    CELL_KEYS, FEATURES, KEYS, _display_path, _path, evaluate_leave_one_esm_out, sha256,
)
from evaluate_isimip3b_gfdl_scenario_holdout_smoke import evaluate_leave_one_scenario_out
from evaluate_isimip3b_two_esm_four_scenario_holdout import read_source_audit, summarize
from validate_paired_feature_emulator import validate_training_design


CONFIG_SCHEMA = "isimip3b_bounded_four_esm_four_scenario_holdout_config_v1"
CONFIG_ROLE = "outcome_blind_joint_whole_esm_and_whole_scenario_engineering_smoke_not_complete_emulator_damage_or_scc_input"
EXPECTED_ESMS = {"GFDL-ESM4", "IPSL-CM6A-LR", "MPI-ESM1-2-HR", "mri-esm2-0"}
EXPECTED_SCENARIOS = {"historical", "ssp126", "ssp370", "ssp585"}


def assemble(config_path: Path) -> tuple[pd.DataFrame, dict[str, Any]]:
    config = tomllib.loads(config_path.read_text(encoding="utf-8"))
    root = config_path.parent.parent
    if config.get("schema") != CONFIG_SCHEMA or config.get("role") != CONFIG_ROLE:
        raise ValueError("four-ESM joint holdout contract identity changed")
    limits = config.get("limitations", {})
    for gate in (
        "complete_five_esm_matrix", "complete_historical_future_temporal_coverage",
        "paired_baseline_pulse_paths", "support_flags", "damage_or_scc_authorized",
    ):
        if limits.get(gate) is not False:
            raise ValueError(f"four-ESM joint holdout unexpectedly opens {gate}")
    products = config.get("training_products", [])
    if len(products) != len(EXPECTED_ESMS) or {str(row.get("esm_id")) for row in products} != EXPECTED_ESMS:
        raise ValueError("joint holdout lacks the exact declared ESM products")

    frames: list[pd.DataFrame] = []
    receipts: list[dict[str, Any]] = []
    for product in products:
        esm_id, member_id = str(product["esm_id"]), str(product["member_id"])
        path = _path(root, str(product["path"]))
        source_audit_path = _path(root, str(product["source_audit"]))
        actual_sha256 = sha256(path)
        if actual_sha256 != str(product["sha256"]):
            raise ValueError(f"{esm_id} training product hash changed")
        read_source_audit(source_audit_path, esm_id, actual_sha256)
        frame = pd.read_parquet(path)
        required = set(KEYS) | {
            "esm_id", "member_id", "scenario", "feature_family", "feature_value", "year",
            "gmst_source_id", "gmst_value_k", "gmst_esm_id", "gmst_member_id",
        }
        if missing := required - set(frame.columns):
            raise ValueError(f"{esm_id} training product lacks columns: {sorted(missing)}")
        if set(frame["esm_id"].astype(str)) != {esm_id} or set(frame["member_id"].astype(str)) != {member_id}:
            raise ValueError(f"{esm_id} training realization identity changed")
        if set(frame["scenario"].astype(str)) != EXPECTED_SCENARIOS:
            raise ValueError(f"{esm_id} scenario set changed")
        if set(frame["feature_family"].astype(str)) != set(FEATURES):
            raise ValueError(f"{esm_id} feature-family set changed")
        numeric = frame[["feature_value", "gmst_value_k"]].apply(pd.to_numeric, errors="coerce")
        if numeric.isna().any().any() or not np.isfinite(numeric.to_numpy()).all():
            raise ValueError(f"{esm_id} training values are nonfinite")
        frames.append(frame)
        receipts.append({
            "esm_id": esm_id, "member_id": member_id,
            "path": _display_path(path, root), "sha256": actual_sha256,
            "source_audit": _display_path(source_audit_path, root),
            "source_audit_sha256": sha256(source_audit_path), "rows": int(len(frame)),
        })

    combined = pd.concat(frames, ignore_index=True)
    duplicate_keys = ["esm_id", "member_id", "scenario", "feature_family", *KEYS]
    if combined.duplicated(duplicate_keys).any():
        raise ValueError("joint holdout training product has duplicate keys")
    if set(combined["esm_id"].astype(str)) != EXPECTED_ESMS or set(combined["scenario"].astype(str)) != EXPECTED_SCENARIOS:
        raise ValueError("joint holdout ESM/scenario set changed")
    if not (combined["esm_id"].astype(str) == combined["gmst_esm_id"].astype(str)).all():
        raise ValueError("joint features and GMST use different ESMs")
    if not (combined["member_id"].astype(str) == combined["gmst_member_id"].astype(str)).all():
        raise ValueError("joint features and GMST use different members")
    spatial = [
        block[CELL_KEYS].drop_duplicates().sort_values(CELL_KEYS).reset_index(drop=True)
        for _, block in combined.groupby("esm_id", sort=True)
    ]
    if any(not spatial[0].equals(block) for block in spatial[1:]):
        raise ValueError("joint ESM products do not share exact spatial support")
    validate_training_design(combined)
    return combined, {
        "config": {"path": _display_path(config_path, root), "sha256": sha256(config_path)},
        "inputs": receipts,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--training-out", type=Path, required=True)
    parser.add_argument("--esm-holdouts-out", type=Path, required=True)
    parser.add_argument("--scenario-holdouts-out", type=Path, required=True)
    parser.add_argument("--audit-out", type=Path, required=True)
    args = parser.parse_args()
    config_path = args.config.resolve()
    training, metadata = assemble(config_path)
    esm_holdouts = evaluate_leave_one_esm_out(training)
    scenario_holdouts = evaluate_leave_one_scenario_out(training)
    for path in (args.training_out, args.esm_holdouts_out, args.scenario_holdouts_out, args.audit_out):
        path.parent.mkdir(parents=True, exist_ok=True)
    training.to_parquet(args.training_out, index=False)
    esm_holdouts.to_csv(args.esm_holdouts_out, index=False)
    scenario_holdouts.to_csv(args.scenario_holdouts_out, index=False)
    root, implementation = config_path.parent.parent, Path(__file__).resolve()
    audit = {
        "schema": "isimip3b_bounded_four_esm_four_scenario_holdout_v1", "role": CONFIG_ROLE,
        **metadata,
        "implementation": {
            "path": _display_path(implementation, root), "sha256": sha256(implementation),
            "dependencies": [
                {"path": _display_path(Path(esm_helpers.__file__).resolve(), root), "sha256": sha256(Path(esm_helpers.__file__).resolve())},
                {"path": _display_path(Path(scenario_helpers.__file__).resolve(), root), "sha256": sha256(Path(scenario_helpers.__file__).resolve())},
                {"path": _display_path(Path(training_helpers.__file__).resolve(), root), "sha256": sha256(Path(training_helpers.__file__).resolve())},
            ],
        },
        "training_rows": int(len(training)), "esm_ids": sorted(EXPECTED_ESMS),
        "scenarios": sorted(EXPECTED_SCENARIOS), "feature_families": FEATURES,
        "summary": summarize(esm_holdouts, scenario_holdouts),
        "training_output": {"artifact_name": args.training_out.name, "sha256": sha256(args.training_out)},
        "esm_holdouts_output": {"artifact_name": args.esm_holdouts_out.name, "sha256": sha256(args.esm_holdouts_out)},
        "scenario_holdouts_output": {"artifact_name": args.scenario_holdouts_out.name, "sha256": sha256(args.scenario_holdouts_out)},
        "whole_esm_holdout": True, "whole_scenario_holdout": True,
        "complete_five_esm_matrix": False, "complete_historical_future_temporal_coverage": False,
        "paired_baseline_pulse_paths": False, "support_flags": False, "damage_or_scc_authorized": False,
        "limitations": [
            "Four of the five frozen ESM realizations have the exact four-scenario bounded product.",
            "Only seven nonoverlapping years, one crop/regime, and two latitude rows are evaluated.",
            "No common-random-number baseline/pulse pair, production support rule, yield response, damage, or SCC value is produced.",
        ],
        "result": "passed",
    }
    args.audit_out.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        f"joint four-ESM/four-scenario holdout passed: {len(training)} rows, "
        f"ESM improvements {audit['summary']['esm']['gmst_model_better_count']}/{len(esm_holdouts)}, "
        f"scenario improvements {audit['summary']['scenario']['gmst_model_better_count']}/{len(scenario_holdouts)}"
    )


if __name__ == "__main__":
    main()
