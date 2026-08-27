#!/usr/bin/env python3
"""Independent fail-closed audit of the joint ESM/scenario smoke outputs."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from evaluate_isimip3b_five_esm_holdout_smoke import FEATURES, KEYS
from evaluate_isimip3b_two_esm_four_scenario_holdout import (
    CONFIG_ROLE,
    EXPECTED_ESMS,
    EXPECTED_SCENARIOS,
    summarize,
)


ROOT = Path(__file__).resolve().parents[1]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def project_path(value: str) -> Path:
    path = Path(value)
    require(not path.is_absolute() and ".." not in path.parts, "audit path must be project-relative")
    result = (ROOT / path).resolve()
    result.relative_to(ROOT.resolve())
    return result


def require_summary_equal(actual: object, expected: object, *, path: str = "summary") -> None:
    """Compare a CSV-recomputed summary without requiring bit-identical floats."""
    if isinstance(actual, dict) and isinstance(expected, dict):
        require(set(actual) == set(expected), f"{path} keys changed")
        for key in actual:
            require_summary_equal(actual[key], expected[key], path=f"{path}.{key}")
        return
    if isinstance(actual, list) and isinstance(expected, list):
        require(len(actual) == len(expected), f"{path} length changed")
        for index, (actual_value, expected_value) in enumerate(zip(actual, expected, strict=True)):
            require_summary_equal(actual_value, expected_value, path=f"{path}[{index}]")
        return
    if (
        isinstance(actual, (int, float))
        and not isinstance(actual, bool)
        and isinstance(expected, (int, float))
        and not isinstance(expected, bool)
    ):
        require(
            math.isfinite(float(actual))
            and math.isfinite(float(expected))
            and math.isclose(float(actual), float(expected), rel_tol=1e-12, abs_tol=1e-12),
            f"{path} changed",
        )
        return
    require(actual == expected, f"{path} changed")


def validate_holdout_product(
    frame: pd.DataFrame,
    *,
    split_type: str,
    expected_holdouts: set[str],
) -> None:
    required = {
        "split_type", "holdout_id", "feature_family", "holdout_excluded", "n_train", "n_test",
        "n_cells", "gmst_slope_per_k", "rmse", "mae", "benchmark_rmse", "benchmark_mae",
    }
    if missing := required - set(frame.columns):
        raise ValueError(f"{split_type} holdouts lack columns: {sorted(missing)}")
    require(set(frame["split_type"].astype(str)) == {split_type}, f"{split_type} split identity changed")
    require(set(frame["holdout_id"].astype(str)) == expected_holdouts, f"{split_type} holdout set changed")
    require(set(frame["feature_family"].astype(str)) == set(FEATURES), f"{split_type} features changed")
    require(not frame.duplicated(["holdout_id", "feature_family"]).any(), f"{split_type} holdouts duplicate a fold")
    require(len(frame) == len(expected_holdouts) * len(FEATURES), f"{split_type} holdout product is incomplete")
    require(frame["holdout_excluded"].map(lambda value: value is True or str(value).lower() == "true").all(), f"{split_type} holdout was not excluded")
    numeric = frame[[
        "n_train", "n_test", "n_cells", "gmst_slope_per_k", "rmse", "mae",
        "benchmark_rmse", "benchmark_mae",
    ]].apply(pd.to_numeric, errors="coerce")
    require(not numeric.isna().any().any() and bool(np.isfinite(numeric.to_numpy()).all()), f"{split_type} metrics are nonfinite")
    require((numeric[["n_train", "n_test", "n_cells"]] > 0).all().all(), f"{split_type} fold counts are nonpositive")
    require((numeric[["rmse", "mae", "benchmark_rmse", "benchmark_mae"]] >= 0).all().all(), f"{split_type} errors are negative")


def validate(audit_path: Path, training_path: Path, esm_path: Path, scenario_path: Path) -> dict[str, object]:
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    require(audit.get("schema") == "isimip3b_bounded_two_esm_four_scenario_holdout_v1", "joint audit schema changed")
    require(audit.get("role") == CONFIG_ROLE and audit.get("result") == "passed", "joint audit role/result changed")
    for gate in (
        "complete_five_esm_matrix",
        "complete_historical_future_temporal_coverage",
        "paired_baseline_pulse_paths",
        "support_flags",
        "damage_or_scc_authorized",
    ):
        require(audit.get(gate) is False, f"joint audit unexpectedly opens {gate}")
    require(audit.get("whole_esm_holdout") is True and audit.get("whole_scenario_holdout") is True, "joint holdout gates are not explicit")
    require(set(audit.get("esm_ids", [])) == EXPECTED_ESMS, "joint audit ESM set changed")
    require(set(audit.get("scenarios", [])) == EXPECTED_SCENARIOS, "joint audit scenario set changed")

    implementation = audit.get("implementation", {})
    paths = [{"path": implementation.get("path"), "sha256": implementation.get("sha256")}, *implementation.get("dependencies", [])]
    require(len(paths) == 4, "joint audit implementation receipts are incomplete")
    for receipt in paths:
        path = project_path(str(receipt.get("path", "")))
        require(path.is_file() and sha256(path) == receipt.get("sha256"), f"joint code hash changed: {path}")
    config = audit.get("config", {})
    config_path = project_path(str(config.get("path", "")))
    require(config_path.is_file() and sha256(config_path) == config.get("sha256"), "joint config hash changed")
    for receipt in audit.get("inputs", []):
        source = project_path(str(receipt["source_audit"]))
        source_training = project_path(str(receipt["path"]))
        require(sha256(source) == receipt["source_audit_sha256"], "joint source-audit hash changed")
        require(sha256(source_training) == receipt["sha256"], "joint source-training hash changed")

    require(sha256(training_path) == audit["training_output"]["sha256"], "joint training artifact hash changed")
    require(sha256(esm_path) == audit["esm_holdouts_output"]["sha256"], "joint ESM holdout artifact hash changed")
    require(sha256(scenario_path) == audit["scenario_holdouts_output"]["sha256"], "joint scenario holdout artifact hash changed")
    training = pd.read_parquet(training_path)
    duplicate_keys = ["esm_id", "member_id", "scenario", "feature_family", *KEYS]
    require(len(training) == int(audit["training_rows"]), "joint training row count changed")
    require(not training.duplicated(duplicate_keys).any(), "joint training keys duplicate")
    require(set(training["esm_id"].astype(str)) == EXPECTED_ESMS, "joint training ESM set changed")
    require(set(training["scenario"].astype(str)) == EXPECTED_SCENARIOS, "joint training scenario set changed")
    require(set(training["feature_family"].astype(str)) == set(FEATURES), "joint training features changed")
    esm = pd.read_csv(esm_path)
    scenario = pd.read_csv(scenario_path)
    validate_holdout_product(esm, split_type="esm", expected_holdouts=EXPECTED_ESMS)
    validate_holdout_product(scenario, split_type="scenario", expected_holdouts=EXPECTED_SCENARIOS)
    recomputed = summarize(esm, scenario)
    require_summary_equal(recomputed, audit["summary"])
    return {
        "result": "passed",
        "training_rows": len(training),
        "whole_esm_holdouts": len(esm),
        "whole_scenario_holdouts": len(scenario),
        "production_emulator_authorized": False,
        "damage_or_scc_authorized": False,
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
