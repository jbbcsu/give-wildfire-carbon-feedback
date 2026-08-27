#!/usr/bin/env python3
"""Joint bounded five-ESM/four-scenario feature holdout audit."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import evaluate_isimip3b_five_esm_holdout_smoke as esm_helpers
import evaluate_isimip3b_four_esm_four_scenario_holdout as assembly_helpers
import evaluate_isimip3b_gfdl_scenario_holdout_smoke as scenario_helpers
import validate_paired_feature_emulator as training_helpers
from evaluate_isimip3b_five_esm_holdout_smoke import (
    FEATURES,
    _display_path,
    evaluate_leave_one_esm_out,
    sha256,
)
from evaluate_isimip3b_gfdl_scenario_holdout_smoke import evaluate_leave_one_scenario_out
from evaluate_isimip3b_two_esm_four_scenario_holdout import summarize


CONFIG_SCHEMA = "isimip3b_bounded_five_esm_four_scenario_holdout_config_v1"
CONFIG_ROLE = "outcome_blind_joint_whole_esm_and_whole_scenario_engineering_smoke_not_complete_temporal_emulator_damage_or_scc_input"
EXPECTED_ESMS = {
    "GFDL-ESM4", "IPSL-CM6A-LR", "MPI-ESM1-2-HR", "mri-esm2-0", "UKESM1-0-LL",
}
EXPECTED_SCENARIOS = {"historical", "ssp126", "ssp370", "ssp585"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--training-out", type=Path, required=True)
    parser.add_argument("--esm-holdouts-out", type=Path, required=True)
    parser.add_argument("--scenario-holdouts-out", type=Path, required=True)
    parser.add_argument("--audit-out", type=Path, required=True)
    args = parser.parse_args()

    assembly_helpers.CONFIG_SCHEMA = CONFIG_SCHEMA
    assembly_helpers.CONFIG_ROLE = CONFIG_ROLE
    assembly_helpers.EXPECTED_ESMS = EXPECTED_ESMS
    assembly_helpers.EXPECTED_SCENARIOS = EXPECTED_SCENARIOS
    config_path = args.config.resolve()
    training, metadata = assembly_helpers.assemble(config_path)
    esm_holdouts = evaluate_leave_one_esm_out(training)
    scenario_holdouts = evaluate_leave_one_scenario_out(training)
    for path in (args.training_out, args.esm_holdouts_out, args.scenario_holdouts_out, args.audit_out):
        path.parent.mkdir(parents=True, exist_ok=True)
    training.to_parquet(args.training_out, index=False)
    esm_holdouts.to_csv(args.esm_holdouts_out, index=False)
    scenario_holdouts.to_csv(args.scenario_holdouts_out, index=False)

    root = config_path.parent.parent
    implementation = Path(__file__).resolve()
    audit = {
        "schema": "isimip3b_bounded_five_esm_four_scenario_holdout_v1",
        "role": CONFIG_ROLE,
        **metadata,
        "implementation": {
            "path": _display_path(implementation, root),
            "sha256": sha256(implementation),
            "dependencies": [
                {"path": _display_path(Path(assembly_helpers.__file__).resolve(), root), "sha256": sha256(Path(assembly_helpers.__file__).resolve())},
                {"path": _display_path(Path(esm_helpers.__file__).resolve(), root), "sha256": sha256(Path(esm_helpers.__file__).resolve())},
                {"path": _display_path(Path(scenario_helpers.__file__).resolve(), root), "sha256": sha256(Path(scenario_helpers.__file__).resolve())},
                {"path": _display_path(Path(training_helpers.__file__).resolve(), root), "sha256": sha256(Path(training_helpers.__file__).resolve())},
            ],
        },
        "training_rows": int(len(training)),
        "esm_ids": sorted(EXPECTED_ESMS),
        "scenarios": sorted(EXPECTED_SCENARIOS),
        "feature_families": FEATURES,
        "summary": summarize(esm_holdouts, scenario_holdouts),
        "training_output": {"artifact_name": args.training_out.name, "sha256": sha256(args.training_out)},
        "esm_holdouts_output": {"artifact_name": args.esm_holdouts_out.name, "sha256": sha256(args.esm_holdouts_out)},
        "scenario_holdouts_output": {"artifact_name": args.scenario_holdouts_out.name, "sha256": sha256(args.scenario_holdouts_out)},
        "whole_esm_holdout": True,
        "whole_scenario_holdout": True,
        "complete_bounded_five_esm_four_scenario_matrix": True,
        "complete_five_esm_matrix": False,
        "complete_historical_future_temporal_coverage": False,
        "paired_baseline_pulse_paths": False,
        "support_flags": False,
        "damage_or_scc_authorized": False,
        "limitations": [
            "All five frozen ESM realizations have the exact four-scenario bounded product.",
            "Only seven nonoverlapping years, one crop/regime, and two latitude rows are evaluated.",
            "No common-random-number baseline/pulse pair, production support rule, yield response, damage, or SCC value is produced.",
        ],
        "result": "passed",
    }
    args.audit_out.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        f"joint five-ESM/four-scenario holdout passed: {len(training)} rows, "
        f"ESM improvements {audit['summary']['esm']['gmst_model_better_count']}/{len(esm_holdouts)}, "
        f"scenario improvements {audit['summary']['scenario']['gmst_model_better_count']}/{len(scenario_holdouts)}"
    )


if __name__ == "__main__":
    main()
