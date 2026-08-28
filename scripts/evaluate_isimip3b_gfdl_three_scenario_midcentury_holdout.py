#!/usr/bin/env python3
"""Join three GFDL midcentury SSP feature blocks and audit whole-scenario support."""

from __future__ import annotations

import argparse
import json
import tomllib
from pathlib import Path

import numpy as np
import pandas as pd

import evaluate_isimip3b_gfdl_scenario_holdout_smoke as scenario_helpers
from evaluate_isimip3b_five_esm_holdout_smoke import (
    CELL_KEYS,
    FEATURES,
    KEYS,
    SEASON_FEATURES,
    _checked_keys,
    _display_path,
    _path,
    _timing_features,
    _validate_physical,
    sha256,
)


CONFIG_SCHEMA = "isimip3b_gfdl_three_scenario_midcentury_holdout_config_v1"
CONFIG_ROLE = "outcome_blind_joined_three_scenario_midcentury_feature_holdout_and_support_audit_not_emulator_damage_or_scc"
EXPECTED_SCENARIOS = {"ssp126", "ssp370", "ssp585"}


def validate_config(config: dict) -> None:
    if config.get("schema") != CONFIG_SCHEMA or config.get("role") != CONFIG_ROLE:
        raise ValueError("midcentury scenario-holdout config identity changed")
    selection = config["selection"]
    if set(map(str, selection["expected_scenarios"])) != EXPECTED_SCENARIOS:
        raise ValueError("expected scenario set changed")
    if list(map(str, selection["expected_feature_families"])) != FEATURES:
        raise ValueError("expected feature-family order changed")
    if int(selection["year_start"]) != 2042 or int(selection["year_end"]) != 2049:
        raise ValueError("registered midcentury harvest-year block changed")
    cells = config.get("cells", [])
    if len(cells) != 3 or {str(cell["scenario"]) for cell in cells} != EXPECTED_SCENARIOS:
        raise ValueError("config lacks the exact three-scenario cells")
    limits = config.get("limitations", {})
    required = {
        "complete_three_scenario_midcentury_matrix": True,
        "whole_scenario_holdouts": True,
        "whole_esm_holdouts": False,
        "fair_baseline_pulse_feature_support": False,
        "paired_baseline_pulse_paths": False,
        "response_estimation_authorized": False,
        "damage_or_scc_authorized": False,
    }
    if any(limits.get(key) is not value for key, value in required.items()):
        raise ValueError("midcentury limitations changed")


def assemble(config_path: Path) -> tuple[pd.DataFrame, dict[str, object]]:
    config = tomllib.loads(config_path.read_text(encoding="utf-8"))
    validate_config(config)
    root = config_path.parent.parent
    selection = config["selection"]
    esm_id = str(selection["esm_id"])
    member_id = str(selection["member_id"])
    year_start = int(selection["year_start"])
    year_end = int(selection["year_end"])
    reference_keys: pd.DataFrame | None = None
    frames: list[pd.DataFrame] = []
    receipts: list[dict[str, object]] = []
    for cell in config["cells"]:
        scenario = str(cell["scenario"])
        season_path = _path(root, str(cell["season_path"]))
        stage_path = _path(root, str(cell["stage_path"]))
        gmst_path = _path(root, str(cell["gmst_path"]))
        for path in (season_path, stage_path, gmst_path):
            if not path.is_file():
                raise ValueError(f"{scenario} input is missing: {path}")
        season = _checked_keys(
            pd.read_parquet(season_path).loc[lambda frame: frame.harvest_year.between(year_start, year_end)].copy(),
            f"{scenario} season",
        )
        if missing := set(SEASON_FEATURES) - set(season):
            raise ValueError(f"{scenario} season lacks {sorted(missing)}")
        stages = pd.read_parquet(stage_path)
        stages = stages.loc[stages.harvest_year.between(year_start, year_end)].copy()
        timing = _timing_features(season, stages, scenario)
        wide = season[KEYS + SEASON_FEATURES].merge(timing, on=KEYS, validate="one_to_one")
        _validate_physical(wide, scenario)
        keys = wide[KEYS].sort_values(KEYS).reset_index(drop=True)
        if reference_keys is None:
            reference_keys = keys
        elif not keys.equals(reference_keys):
            raise ValueError("scenario feature cells do not have identical keys")
        gmst = pd.read_parquet(gmst_path)
        required_gmst = {"esm_id", "member_id", "scenario", "gmst_source_id", "year", "gmst_value_k"}
        if missing := required_gmst - set(gmst):
            raise ValueError(f"{scenario} GMST lacks {sorted(missing)}")
        gmst = gmst.loc[gmst.year.between(year_start, year_end)].copy()
        if gmst.duplicated("year").any() or set(gmst.year) != set(range(year_start, year_end + 1)):
            raise ValueError(f"{scenario} GMST year coverage changed")
        observed_esms = set(gmst.esm_id.astype(str))
        if {value.lower() for value in observed_esms} != {esm_id.lower()} or set(gmst.member_id.astype(str)) != {member_id}:
            raise ValueError(f"{scenario} GMST realization changed")
        if set(gmst.scenario.astype(str)) != {scenario}:
            raise ValueError(f"{scenario} GMST scenario changed")
        if (gmst.gmst_source_id.astype(str).str.strip() == "").any() or not pd.to_numeric(
            gmst.gmst_value_k, errors="coerce"
        ).between(150, 350).all():
            raise ValueError(f"{scenario} GMST values/source IDs are invalid")
        wide["esm_id"], wide["member_id"], wide["scenario"] = esm_id, member_id, scenario
        wide = wide.merge(
            gmst[["year", "gmst_source_id", "gmst_value_k"]],
            left_on="harvest_year", right_on="year", validate="many_to_one",
        ).drop(columns="year")
        wide["gmst_esm_id"], wide["gmst_member_id"] = esm_id, member_id
        long = wide.melt(
            id_vars=KEYS + ["esm_id", "member_id", "scenario", "gmst_source_id", "gmst_value_k", "gmst_esm_id", "gmst_member_id"],
            value_vars=FEATURES, var_name="feature_family", value_name="feature_value",
        )
        long["year"] = long.harvest_year
        frames.append(long)
        receipts.append({
            "scenario": scenario,
            "observed_gmst_esm_ids": sorted(observed_esms),
            "canonical_esm_id": esm_id,
            "season_path": _display_path(season_path, root), "season_sha256": sha256(season_path),
            "stage_path": _display_path(stage_path, root), "stage_sha256": sha256(stage_path),
            "gmst_path": _display_path(gmst_path, root), "gmst_sha256": sha256(gmst_path),
        })
    training = pd.concat(frames, ignore_index=True)
    duplicate_keys = ["scenario", "feature_family", *KEYS]
    if training.duplicated(duplicate_keys).any():
        raise ValueError("joined scenario product contains duplicate keys")
    if set(training.scenario.astype(str)) != EXPECTED_SCENARIOS or set(training.feature_family.astype(str)) != set(FEATURES):
        raise ValueError("joined scenario/feature product is incomplete")
    if not np.isfinite(training[["feature_value", "gmst_value_k"]].to_numpy(float)).all():
        raise ValueError("joined scenario product has nonfinite values")
    if not (training.esm_id == training.gmst_esm_id).all() or not (training.member_id == training.gmst_member_id).all():
        raise ValueError("features and GMST do not use the same realization")
    return training, {
        "config_path": _display_path(config_path, root),
        "config_sha256": sha256(config_path),
        "esm_id": esm_id,
        "member_id": member_id,
        "year_start": year_start,
        "year_end": year_end,
        "inputs": receipts,
    }


def evaluate_support(training: pd.DataFrame) -> pd.DataFrame:
    observed = set(
        training[["scenario", "feature_family"]]
        .astype(str)
        .drop_duplicates()
        .itertuples(index=False, name=None)
    )
    expected = {(scenario, family) for scenario in EXPECTED_SCENARIOS for family in FEATURES}
    group_sizes = training.groupby(["scenario", "feature_family"], observed=True).size()
    if observed != expected or group_sizes.nunique() != 1:
        raise ValueError("support input lacks equal complete scenario/feature coverage")
    rows: list[dict[str, object]] = []
    for holdout in sorted(EXPECTED_SCENARIOS):
        train = training.loc[training.scenario != holdout]
        test = training.loc[training.scenario == holdout]
        for family in FEATURES:
            bounds = train.loc[train.feature_family == family].groupby(CELL_KEYS, observed=True).agg(
                support_min=("feature_value", "min"), support_max=("feature_value", "max")
            ).reset_index()
            score = test.loc[test.feature_family == family].merge(bounds, on=CELL_KEYS, how="left", validate="many_to_one")
            if score[["support_min", "support_max"]].isna().any().any() or (score.support_min > score.support_max).any():
                raise ValueError(f"{holdout}/{family} support bounds are missing or invalid")
            values = score.feature_value.to_numpy(float)
            lower = score.support_min.to_numpy(float)
            upper = score.support_max.to_numpy(float)
            states = np.where(values < lower, "below", np.where(values > upper, "above", "within"))
            counts = pd.Series(states).value_counts().to_dict()
            rows.append({
                "holdout_id": holdout,
                "feature_family": family,
                "n_test": len(score),
                "below_support": int(counts.get("below", 0)),
                "within_support": int(counts.get("within", 0)),
                "above_support": int(counts.get("above", 0)),
                "outside_support": int(counts.get("below", 0) + counts.get("above", 0)),
            })
    result = pd.DataFrame(rows)
    if len(result) != 3 * len(FEATURES) or result.duplicated(["holdout_id", "feature_family"]).any():
        raise ValueError("support audit lacks the exact scenario/feature product")
    if not (result.below_support + result.within_support + result.above_support == result.n_test).all():
        raise ValueError("support counts do not reconcile")
    result["outside_support_share"] = result.outside_support / result.n_test
    return result


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
    scenario_helpers.SCENARIOS = EXPECTED_SCENARIOS
    holdouts = scenario_helpers.evaluate_leave_one_scenario_out(training)
    support = evaluate_support(training)
    for path in (args.training_out, args.holdouts_out, args.support_out, args.audit_out):
        path.parent.mkdir(parents=True, exist_ok=True)
    training.to_parquet(args.training_out, index=False)
    holdouts.to_csv(args.holdouts_out, index=False)
    support.to_csv(args.support_out, index=False)
    ratios = holdouts.rmse / holdouts.benchmark_rmse
    improved = holdouts.rmse < holdouts.benchmark_rmse
    audit = {
        "schema": "isimip3b_gfdl_three_scenario_midcentury_holdout_audit_v1",
        "role": CONFIG_ROLE,
        "result": "passed_engineering_holdout_and_support_only",
        **metadata,
        "training_rows": len(training),
        "holdout_rows": len(holdouts),
        "support_summary_rows": len(support),
        "feature_families": FEATURES,
        "gmst_model_better_than_cell_mean_count": int(improved.sum()),
        "comparison_count": len(holdouts),
        "median_rmse_ratio_to_cell_mean": float(ratios.median()),
        "maximum_rmse_ratio_to_cell_mean": float(ratios.max()),
        "held_out_feature_values": int(support.n_test.sum()),
        "held_out_feature_values_outside_two_scenario_support": int(support.outside_support.sum()),
        "held_out_feature_values_outside_two_scenario_support_share": float(support.outside_support.sum() / support.n_test.sum()),
        "scenario_summaries": {
            scenario: {
                "comparisons": int(len(block)),
                "gmst_model_better_count": int((block.rmse < block.benchmark_rmse).sum()),
                "median_rmse_ratio_to_cell_mean": float((block.rmse / block.benchmark_rmse).median()),
                "maximum_rmse_ratio_to_cell_mean": float((block.rmse / block.benchmark_rmse).max()),
                "outside_support_values": int(support.loc[support.holdout_id == scenario, "outside_support"].sum()),
                "outside_support_share": float(
                    support.loc[support.holdout_id == scenario, "outside_support"].sum()
                    / support.loc[support.holdout_id == scenario, "n_test"].sum()
                ),
            }
            for scenario, block in holdouts.groupby("holdout_id", sort=True)
        },
        "implementation": {
            "path": _display_path(Path(__file__).resolve(), config_path.parent.parent),
            "sha256": sha256(Path(__file__).resolve()),
        },
        "outputs": {
            "training_sha256": sha256(args.training_out),
            "holdouts_sha256": sha256(args.holdouts_out),
            "support_sha256": sha256(args.support_out),
        },
        "whole_scenario_holdout": True,
        "whole_esm_holdout": False,
        "fair_baseline_pulse_feature_support": False,
        "paired_baseline_pulse_paths": False,
        "response_estimation_authorized": False,
        "damage_or_scc_authorized": False,
        "limitation": "Support flags apply to held-out climate-scenario feature values only, not FAIR baseline/pulse evaluation or an agricultural response.",
    }
    args.audit_out.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        f"GFDL three-scenario midcentury audit passed: {len(training)} rows, "
        f"GMST model improved {int(improved.sum())}/{len(holdouts)}, "
        f"outside support {int(support.outside_support.sum())}/{int(support.n_test.sum())}"
    )


if __name__ == "__main__":
    main()
