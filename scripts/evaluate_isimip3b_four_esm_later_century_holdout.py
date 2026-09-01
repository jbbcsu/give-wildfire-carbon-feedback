#!/usr/bin/env python3
"""Evaluate registered four-ESM later-century whole-ESM holdouts."""

from __future__ import annotations

import argparse
import json
import tomllib
from pathlib import Path

import numpy as np
import pandas as pd

from evaluate_isimip3b_five_esm_holdout_smoke import CELL_KEYS, FEATURES, evaluate_leave_one_esm_out, sha256


EXPECTED_ESMS = {"GFDL-ESM4", "IPSL-CM6A-LR", "MPI-ESM1-2-HR", "MRI-ESM2-0"}
EXPECTED_SCENARIOS = {"ssp126", "ssp370", "ssp585"}
CONFIG_SCHEMA = "isimip3b_four_esm_later_century_holdout_config_v1"
CONFIG_ROLE = "outcome_blind_four_esm_three_scenario_whole_esm_holdout_and_support_not_complete_emulator_damage_or_scc"
PERIODS = {"midcentury": (2042, 2049), "endcentury": (2092, 2099)}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def validate_config(config: dict) -> None:
    require(config.get("schema") == CONFIG_SCHEMA and config.get("role") == CONFIG_ROLE, "four-ESM config identity changed")
    selection = config.get("selection", {})
    period = str(selection.get("period", ""))
    require(period in PERIODS, "later-century period changed")
    require((int(selection.get("year_start", -1)), int(selection.get("year_end", -1))) == PERIODS[period], "harvest-year block changed")
    require(set(map(str, selection.get("expected_esm_ids", []))) == EXPECTED_ESMS, "ESM set changed")
    require(set(map(str, selection.get("expected_scenarios", []))) == EXPECTED_SCENARIOS, "scenario set changed")
    require(list(map(str, selection.get("expected_feature_families", []))) == FEATURES, "feature-family order changed")
    products = config.get("training_products", [])
    require(len(products) == 4 and {str(row.get("esm_id")) for row in products} == EXPECTED_ESMS, "training products are incomplete")
    limits = config.get("limitations", {})
    required = {
        "complete_five_esm_matrix": False,
        "whole_esm_holdouts": True,
        "whole_scenario_holdouts": True,
        "fair_baseline_pulse_feature_support": False,
        "response_estimation_authorized": False,
        "damage_or_scc_authorized": False,
    }
    require(all(limits.get(key) is value for key, value in required.items()), "four-ESM limitations changed")


def project_path(root: Path, value: str) -> Path:
    path = Path(value)
    require(not path.is_absolute() and ".." not in path.parts, "input path must be project-relative")
    return root / path


def assemble(config_path: Path) -> tuple[pd.DataFrame, dict]:
    config = tomllib.loads(config_path.read_text(encoding="utf-8"))
    validate_config(config)
    root = config_path.parent.parent
    frames: list[pd.DataFrame] = []
    receipts: list[dict[str, object]] = []
    for product in config["training_products"]:
        esm = str(product["esm_id"])
        member = str(product["member_id"])
        path = project_path(root, str(product["path"]))
        audit_path = project_path(root, str(product["source_audit"]))
        require(path.is_file() and audit_path.is_file(), f"{esm} source product is missing")
        actual_hash = sha256(path)
        require(actual_hash == str(product["sha256"]), f"{esm} training hash changed")
        source_audit = json.loads(audit_path.read_text(encoding="utf-8"))
        require(source_audit.get("whole_scenario_holdout") is True, f"{esm} source scenario gate is absent")
        require(source_audit.get("response_estimation_authorized") is False and source_audit.get("damage_or_scc_authorized") is False, f"{esm} source audit opened a forbidden gate")
        require(source_audit.get("outputs", {}).get("training_sha256") == actual_hash, f"{esm} source receipt does not bind training")
        frame = pd.read_parquet(path)
        require(set(frame.esm_id.astype(str).str.upper()) == {esm.upper()}, f"{esm} feature identity changed")
        require(set(frame.member_id.astype(str)) == {member}, f"{esm} member changed")
        require(set(frame.scenario.astype(str)) == EXPECTED_SCENARIOS, f"{esm} scenario coverage changed")
        require(set(frame.feature_family.astype(str)) == set(FEATURES), f"{esm} feature coverage changed")
        frames.append(frame)
        receipts.append({"esm_id": esm, "member_id": member, "path": str(product["path"]), "sha256": actual_hash, "source_audit": str(product["source_audit"]), "source_audit_sha256": sha256(audit_path)})
    training = pd.concat(frames, ignore_index=True)
    keys = ["esm_id", "member_id", "scenario", "feature_family", "harvest_year", *CELL_KEYS]
    require(not training.duplicated(keys).any(), "duplicate ESM/scenario/feature/cell-year keys")
    require(np.isfinite(training[["feature_value", "gmst_value_k"]].to_numpy(float)).all(), "training values are nonfinite")
    require((training.esm_id.astype(str).str.upper() == training.gmst_esm_id.astype(str).str.upper()).all(), "feature/GMST ESM identity differs")
    return training, {"config_path": str(config_path.relative_to(root)), "config_sha256": sha256(config_path), "inputs": receipts, "period": config["selection"]["period"]}


def evaluate_support(training: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for holdout in sorted(EXPECTED_ESMS):
        train = training.loc[training.esm_id.astype(str).str.upper() != holdout.upper()]
        test = training.loc[training.esm_id.astype(str).str.upper() == holdout.upper()]
        for family in FEATURES:
            group_keys = ["scenario", *CELL_KEYS]
            bounds = train.loc[train.feature_family == family].groupby(group_keys, observed=True).feature_value.agg(support_min="min", support_max="max").reset_index()
            score = test.loc[test.feature_family == family].merge(bounds, on=group_keys, validate="many_to_one")
            require(len(score) == len(test.loc[test.feature_family == family]), "held-out ESM lacks exact cell support")
            below = score.feature_value < score.support_min
            above = score.feature_value > score.support_max
            rows.append({"holdout_id": holdout, "feature_family": family, "n_test": len(score), "below_support": int(below.sum()), "within_support": int((~below & ~above).sum()), "above_support": int(above.sum()), "outside_support": int((below | above).sum())})
    output = pd.DataFrame(rows)
    require(len(output) == 4 * len(FEATURES), "whole-ESM support product is incomplete")
    output["outside_support_share"] = output.outside_support / output.n_test
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--training-out", type=Path, required=True)
    parser.add_argument("--holdouts-out", type=Path, required=True)
    parser.add_argument("--support-out", type=Path, required=True)
    parser.add_argument("--audit-out", type=Path, required=True)
    args = parser.parse_args()
    config_path = args.config.resolve()
    training, metadata = assemble(config_path)
    holdouts = evaluate_leave_one_esm_out(training)
    support = evaluate_support(training)
    for path in (args.training_out, args.holdouts_out, args.support_out, args.audit_out):
        path.parent.mkdir(parents=True, exist_ok=True)
    training.to_parquet(args.training_out, index=False)
    holdouts.to_csv(args.holdouts_out, index=False)
    support.to_csv(args.support_out, index=False)
    ratios = holdouts.rmse / holdouts.benchmark_rmse
    audit = {
        "schema": "isimip3b_four_esm_later_century_holdout_audit_v1",
        "role": CONFIG_ROLE,
        "result": "passed_four_of_five_esm_engineering_holdout_and_support_only",
        **metadata,
        "implementation": {"path": str(Path(__file__).resolve().relative_to(config_path.parent.parent)), "sha256": sha256(Path(__file__).resolve())},
        "training_rows": len(training),
        "esm_ids": sorted(EXPECTED_ESMS),
        "scenarios": sorted(EXPECTED_SCENARIOS),
        "comparison_count": len(holdouts),
        "gmst_model_better_than_cell_mean_count": int((holdouts.rmse < holdouts.benchmark_rmse).sum()),
        "median_rmse_ratio_to_cell_mean": float(ratios.median()),
        "maximum_rmse_ratio_to_cell_mean": float(ratios.max()),
        "held_out_feature_values": int(support.n_test.sum()),
        "held_out_feature_values_outside_three_esm_support": int(support.outside_support.sum()),
        "held_out_feature_values_outside_three_esm_support_share": float(support.outside_support.sum() / support.n_test.sum()),
        "outputs": {"training_sha256": sha256(args.training_out), "holdouts_sha256": sha256(args.holdouts_out), "support_sha256": sha256(args.support_out)},
        "complete_five_esm_matrix": False,
        "whole_esm_holdout": True,
        "whole_scenario_holdout": True,
        "fair_baseline_pulse_feature_support": False,
        "response_estimation_authorized": False,
        "damage_or_scc_authorized": False,
        "limitation": "Four of five frozen ESMs, one crop/regime, and two latitude rows; UKESM and FAIR feature-path support remain absent.",
    }
    args.audit_out.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"four-ESM {metadata['period']} audit passed: {len(training)} rows, improved {audit['gmst_model_better_than_cell_mean_count']}/{len(holdouts)}, outside {audit['held_out_feature_values_outside_three_esm_support']}/{audit['held_out_feature_values']}")


if __name__ == "__main__":
    main()
