#!/usr/bin/env python3
"""Independent fail-closed audit of the four-ESM joint holdout outputs."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from evaluate_isimip3b_five_esm_holdout_smoke import FEATURES, KEYS
from evaluate_isimip3b_four_esm_four_scenario_holdout import (
    CONFIG_ROLE, EXPECTED_ESMS, EXPECTED_SCENARIOS,
)
from evaluate_isimip3b_two_esm_four_scenario_holdout import summarize
from validate_isimip3b_two_esm_four_scenario_holdout import (
    require, require_summary_equal, sha256, validate_holdout_product,
)


ROOT = Path(__file__).resolve().parents[1]


def project_path(value: str) -> Path:
    path = Path(value)
    require(not path.is_absolute() and ".." not in path.parts, "audit path must be project-relative")
    result = (ROOT / path).resolve()
    result.relative_to(ROOT.resolve())
    return result


def validate(audit_path: Path, training_path: Path, esm_path: Path, scenario_path: Path) -> dict[str, object]:
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    require(audit.get("schema") == "isimip3b_bounded_four_esm_four_scenario_holdout_v1", "four-ESM audit schema changed")
    require(audit.get("role") == CONFIG_ROLE and audit.get("result") == "passed", "four-ESM audit role/result changed")
    for gate in (
        "complete_five_esm_matrix", "complete_historical_future_temporal_coverage",
        "paired_baseline_pulse_paths", "support_flags", "damage_or_scc_authorized",
    ):
        require(audit.get(gate) is False, f"four-ESM audit unexpectedly opens {gate}")
    require(audit.get("whole_esm_holdout") is True and audit.get("whole_scenario_holdout") is True, "four-ESM holdout gates are not explicit")
    require(set(audit.get("esm_ids", [])) == EXPECTED_ESMS, "four-ESM audit ESM set changed")
    require(set(audit.get("scenarios", [])) == EXPECTED_SCENARIOS, "four-ESM audit scenario set changed")

    implementation = audit.get("implementation", {})
    receipts = [{"path": implementation.get("path"), "sha256": implementation.get("sha256")}, *implementation.get("dependencies", [])]
    require(len(receipts) == 4, "four-ESM implementation receipts are incomplete")
    for receipt in receipts:
        path = project_path(str(receipt.get("path", "")))
        require(path.is_file() and sha256(path) == receipt.get("sha256"), f"four-ESM code hash changed: {path}")
    config = audit.get("config", {})
    config_path = project_path(str(config.get("path", "")))
    require(config_path.is_file() and sha256(config_path) == config.get("sha256"), "four-ESM config hash changed")
    require(len(audit.get("inputs", [])) == 4, "four-ESM input receipts are incomplete")
    for receipt in audit["inputs"]:
        source = project_path(str(receipt["source_audit"]))
        source_training = project_path(str(receipt["path"]))
        require(sha256(source) == receipt["source_audit_sha256"], "four-ESM source-audit hash changed")
        require(sha256(source_training) == receipt["sha256"], "four-ESM source-training hash changed")

    require(sha256(training_path) == audit["training_output"]["sha256"], "four-ESM training artifact hash changed")
    require(sha256(esm_path) == audit["esm_holdouts_output"]["sha256"], "four-ESM ESM holdout artifact hash changed")
    require(sha256(scenario_path) == audit["scenario_holdouts_output"]["sha256"], "four-ESM scenario holdout artifact hash changed")
    training = pd.read_parquet(training_path)
    duplicate_keys = ["esm_id", "member_id", "scenario", "feature_family", *KEYS]
    require(len(training) == int(audit["training_rows"]), "four-ESM training row count changed")
    require(not training.duplicated(duplicate_keys).any(), "four-ESM training keys duplicate")
    require(set(training["esm_id"].astype(str)) == EXPECTED_ESMS, "four-ESM training ESM set changed")
    require(set(training["scenario"].astype(str)) == EXPECTED_SCENARIOS, "four-ESM training scenario set changed")
    require(set(training["feature_family"].astype(str)) == set(FEATURES), "four-ESM training features changed")
    require((training["esm_id"].astype(str) == training["gmst_esm_id"].astype(str)).all(), "four-ESM GMST ESM identity changed")
    require((training["member_id"].astype(str) == training["gmst_member_id"].astype(str)).all(), "four-ESM GMST member identity changed")

    esm, scenario = pd.read_csv(esm_path), pd.read_csv(scenario_path)
    validate_holdout_product(esm, split_type="esm", expected_holdouts=EXPECTED_ESMS)
    validate_holdout_product(scenario, split_type="scenario", expected_holdouts=EXPECTED_SCENARIOS)
    require_summary_equal(summarize(esm, scenario), audit["summary"])
    return {
        "result": "passed", "training_rows": len(training),
        "whole_esm_holdouts": len(esm), "whole_scenario_holdouts": len(scenario),
        "production_emulator_authorized": False, "damage_or_scc_authorized": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--training", type=Path, required=True)
    parser.add_argument("--esm-holdouts", type=Path, required=True)
    parser.add_argument("--scenario-holdouts", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(validate(
        args.audit.resolve(), args.training.resolve(), args.esm_holdouts.resolve(), args.scenario_holdouts.resolve()
    ), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
