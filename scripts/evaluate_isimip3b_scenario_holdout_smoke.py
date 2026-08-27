#!/usr/bin/env python3
"""Run a bounded historical-plus-three-SSP whole-scenario holdout smoke.

This generalizes the earlier GFDL-only engineering audit without changing its
transparent cell-mean-plus-GMST specification. A passing result is not a
production emulator, marginal pulse response, damage function, or SCC input.
"""
from __future__ import annotations

import argparse
import json
import tomllib
from pathlib import Path

import pandas as pd

import evaluate_isimip3b_five_esm_holdout_smoke as esm_helpers
import evaluate_isimip3b_gfdl_scenario_holdout_smoke as scenario_helpers
from evaluate_isimip3b_gfdl_scenario_holdout_smoke import (
    assemble_training,
    evaluate_leave_one_scenario_out,
)
from evaluate_isimip3b_five_esm_holdout_smoke import FEATURES, _display_path, sha256


CONFIG_SCHEMA = "isimip3b_bounded_scenario_holdout_smoke_config_v1"
CONFIG_ROLE = "outcome_blind_historical_plus_three_ssp_engineering_smoke_not_complete_emulator_damage_or_scc_input"


def validate_config(path: Path) -> dict[str, object]:
    config = tomllib.loads(path.read_text(encoding="utf-8"))
    if config.get("schema") != CONFIG_SCHEMA or config.get("role") != CONFIG_ROLE:
        raise ValueError("generic scenario-holdout contract identity changed")
    limits = config.get("limitations", {})
    required = {
        "historical_scenario_present": True,
        "complete_historical_future_temporal_coverage": False,
        "complete_esm_matrix": False,
        "paired_baseline_pulse_paths": False,
        "support_flags": False,
        "damage_or_scc_authorized": False,
    }
    if any(limits.get(key) is not value for key, value in required.items()):
        raise ValueError("generic scenario-holdout limitations changed")
    return config


def summarize_holdouts(holdouts: pd.DataFrame) -> dict[str, object]:
    required = {"holdout_id", "feature_family", "rmse", "benchmark_rmse"}
    if missing := required - set(holdouts.columns):
        raise ValueError(f"scenario holdouts lack summary columns: {sorted(missing)}")
    numeric = holdouts[["rmse", "benchmark_rmse"]].apply(pd.to_numeric, errors="coerce")
    if numeric.isna().any().any() or (numeric < 0).any().any() or (numeric["benchmark_rmse"] == 0).any():
        raise ValueError("scenario holdout errors are invalid")
    ratios = numeric["rmse"] / numeric["benchmark_rmse"]
    improved = numeric["rmse"] < numeric["benchmark_rmse"]
    return {
        "gmst_model_better_than_cell_mean_count": int(improved.sum()),
        "comparison_count": int(len(holdouts)),
        "median_rmse_ratio_to_cell_mean": float(ratios.median()),
        "maximum_rmse_ratio_to_cell_mean": float(ratios.max()),
        "scenario_summaries": {
            str(scenario): {
                "comparisons": int(len(block)),
                "gmst_model_better_count": int((block["rmse"] < block["benchmark_rmse"]).sum()),
                "median_rmse_ratio_to_cell_mean": float((block["rmse"] / block["benchmark_rmse"]).median()),
                "maximum_rmse_ratio_to_cell_mean": float((block["rmse"] / block["benchmark_rmse"]).max()),
            }
            for scenario, block in holdouts.groupby("holdout_id", sort=True)
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--training-out", type=Path, required=True)
    parser.add_argument("--holdouts-out", type=Path, required=True)
    parser.add_argument("--audit-out", type=Path, required=True)
    args = parser.parse_args()
    config_path = args.config.resolve()
    validate_config(config_path)
    training, metadata = assemble_training(config_path)
    holdouts = evaluate_leave_one_scenario_out(training)
    for path in (args.training_out, args.holdouts_out, args.audit_out):
        path.parent.mkdir(parents=True, exist_ok=True)
    training.to_parquet(args.training_out, index=False)
    holdouts.to_csv(args.holdouts_out, index=False)
    root = config_path.parent.parent
    audit = {
        "schema": "isimip3b_bounded_scenario_holdout_smoke_v1",
        "role": CONFIG_ROLE,
        **metadata,
        "implementation": {
            "path": _display_path(Path(__file__).resolve(), root),
            "sha256": sha256(Path(__file__).resolve()),
            "dependencies": [
                {
                    "path": _display_path(Path(scenario_helpers.__file__).resolve(), root),
                    "sha256": sha256(Path(scenario_helpers.__file__).resolve()),
                },
                {
                    "path": _display_path(Path(esm_helpers.__file__).resolve(), root),
                    "sha256": sha256(Path(esm_helpers.__file__).resolve()),
                },
            ],
        },
        "training_rows": len(training),
        "holdout_rows": len(holdouts),
        "feature_families": FEATURES,
        **summarize_holdouts(holdouts),
        "training_output": {"artifact_name": args.training_out.name, "sha256": sha256(args.training_out)},
        "holdouts_output": {"artifact_name": args.holdouts_out.name, "sha256": sha256(args.holdouts_out)},
        "whole_scenario_holdout": True,
        "whole_esm_holdout_in_this_product": False,
        "paired_baseline_pulse_paths": False,
        "support_flags": False,
        "damage_or_scc_authorized": False,
        "limitations": [
            "Only seven nonoverlapping harvest years, one ESM/member, one crop/regime, and two latitude rows are evaluated.",
            "The exact four-scenario training-design gate passes, but complete historical/future temporal and five-ESM coverage remain absent.",
            "No common-random-number baseline/pulse pair, support rule, yield response, damage, welfare, or SCC value is produced.",
        ],
        "result": "passed",
    }
    args.audit_out.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        f"bounded {metadata['esm_id']} scenario holdout smoke passed: "
        f"{len(training)} training rows, {len(holdouts)} holdouts, "
        f"GMST model improved {audit['gmst_model_better_than_cell_mean_count']}/{len(holdouts)}"
    )


if __name__ == "__main__":
    main()
