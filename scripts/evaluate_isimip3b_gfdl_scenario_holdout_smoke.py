#!/usr/bin/env python3
"""Bounded whole-scenario holdout smoke for one GFDL ISIMIP3b slice."""
from __future__ import annotations

import argparse
import json
import tomllib
from pathlib import Path

import numpy as np
import pandas as pd

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
from validate_paired_feature_emulator import validate_training_design


SCENARIOS = {"historical", "ssp126", "ssp370", "ssp585"}


def assemble_training(config_path: Path) -> tuple[pd.DataFrame, dict[str, object]]:
    config = tomllib.loads(config_path.read_text(encoding="utf-8"))
    root = config_path.parent.parent
    selection = config["selection"]
    esm_id, member_id = str(selection["esm_id"]), str(selection["member_id"])
    cells = config.get("cells", [])
    if len(cells) != 4 or {str(cell["scenario"]) for cell in cells} != SCENARIOS:
        raise ValueError("scenario config must contain historical plus the three frozen SSPs")
    reference_keys: pd.DataFrame | None = None
    frames: list[pd.DataFrame] = []
    receipts = []
    for cell in cells:
        scenario = str(cell["scenario"])
        year_start, year_end = int(cell["year_start"]), int(cell["year_end"])
        season_path = _path(root, str(cell["season_path"]))
        stage_path = _path(root, str(cell["stage_path"]))
        gmst_path = _path(root, str(cell["gmst_path"]))
        for path in (season_path, stage_path, gmst_path):
            if not path.is_file():
                raise ValueError(f"{scenario} input is missing: {path}")
        season = pd.read_parquet(season_path)
        season = _checked_keys(
            season.loc[season["harvest_year"].between(year_start, year_end)].copy(),
            f"{scenario} season",
        )
        if missing := set(SEASON_FEATURES) - set(season.columns):
            raise ValueError(f"{scenario} season missing features: {sorted(missing)}")
        stages = pd.read_parquet(stage_path)
        stages = stages.loc[stages["harvest_year"].between(year_start, year_end)].copy()
        timing = _timing_features(season, stages, scenario)
        wide = season[KEYS + SEASON_FEATURES].merge(timing, on=KEYS, validate="one_to_one")
        _validate_physical(wide, scenario)
        spatial_keys = wide[CELL_KEYS].drop_duplicates().sort_values(CELL_KEYS).reset_index(drop=True)
        if reference_keys is None:
            reference_keys = spatial_keys
        elif not spatial_keys.equals(reference_keys):
            raise ValueError("scenario feature cells do not have identical spatial support")
        gmst = pd.read_parquet(gmst_path)
        required = {"esm_id", "member_id", "scenario", "gmst_source_id", "year", "gmst_value_k"}
        if missing := required - set(gmst.columns):
            raise ValueError(f"{scenario} GMST missing columns: {sorted(missing)}")
        gmst = gmst.loc[gmst["year"].between(year_start, year_end)].copy()
        if gmst.duplicated("year").any() or set(gmst["year"]) != set(range(year_start, year_end + 1)):
            raise ValueError(f"{scenario} GMST does not contain the exact smoke years")
        if set(gmst["esm_id"].astype(str)) != {esm_id} or set(gmst["member_id"].astype(str)) != {member_id}:
            raise ValueError(f"{scenario} GMST realization identity mismatch")
        if set(gmst["scenario"].astype(str)) != {scenario}:
            raise ValueError(f"{scenario} GMST scenario identity mismatch")
        if not pd.to_numeric(gmst["gmst_value_k"], errors="coerce").between(150, 350).all():
            raise ValueError(f"{scenario} GMST is outside physical Kelvin bounds")
        wide["esm_id"], wide["member_id"], wide["scenario"] = esm_id, member_id, scenario
        wide = wide.merge(
            gmst[["year", "gmst_source_id", "gmst_value_k"]],
            left_on="harvest_year", right_on="year", validate="many_to_one",
        ).drop(columns="year")
        wide["gmst_esm_id"], wide["gmst_member_id"] = esm_id, member_id
        long = wide.melt(
            id_vars=KEYS + [
                "esm_id", "member_id", "scenario", "gmst_source_id", "gmst_value_k",
                "gmst_esm_id", "gmst_member_id",
            ],
            value_vars=FEATURES,
            var_name="feature_family",
            value_name="feature_value",
        )
        long["year"] = long["harvest_year"]
        frames.append(long)
        receipts.append({
            "scenario": scenario,
            "year_start": year_start,
            "year_end": year_end,
            "season_path": _display_path(season_path, root), "season_sha256": sha256(season_path),
            "stage_path": _display_path(stage_path, root), "stage_sha256": sha256(stage_path),
            "gmst_path": _display_path(gmst_path, root), "gmst_sha256": sha256(gmst_path),
        })
    training = pd.concat(frames, ignore_index=True)
    if training.duplicated(["scenario", "feature_family", *KEYS]).any():
        raise ValueError("scenario training has duplicate feature keys")
    if set(training["feature_family"]) != set(FEATURES) or set(training["scenario"]) != SCENARIOS:
        raise ValueError("scenario training product is incomplete")
    if not (training["esm_id"] == training["gmst_esm_id"]).all() or not (
        training["member_id"] == training["gmst_member_id"]
    ).all():
        raise ValueError("scenario features and GMST use different realizations")
    validate_training_design(training)
    return training, {
        "config_path": _display_path(config_path, root),
        "config_sha256": sha256(config_path),
        "esm_id": esm_id,
        "member_id": member_id,
        "year_start": int(training["year"].min()),
        "year_end": int(training["year"].max()),
        "inputs": receipts,
    }


def evaluate_leave_one_scenario_out(training: pd.DataFrame) -> pd.DataFrame:
    if set(training["scenario"].astype(str)) != SCENARIOS:
        raise ValueError("scenario scoring input lacks the exact frozen future-scenario set")
    rows = []
    for holdout in sorted(SCENARIOS):
        train = training.loc[training["scenario"] != holdout].copy()
        test = training.loc[training["scenario"] == holdout].copy()
        for family in FEATURES:
            fit = train.loc[train["feature_family"] == family].copy()
            score = test.loc[test["feature_family"] == family].copy()
            means = fit.groupby(CELL_KEYS, observed=True).agg(
                train_cell_feature_mean=("feature_value", "mean"),
                train_cell_gmst_mean=("gmst_value_k", "mean"),
                train_cell_rows=("feature_value", "size"),
            ).reset_index()
            fit = fit.merge(means, on=CELL_KEYS, validate="many_to_one")
            dx = fit["gmst_value_k"].to_numpy(float) - fit["train_cell_gmst_mean"].to_numpy(float)
            dy = fit["feature_value"].to_numpy(float) - fit["train_cell_feature_mean"].to_numpy(float)
            denominator = float(np.sum(dx * dx))
            if not np.isfinite(denominator) or denominator <= 0:
                raise ValueError(f"{holdout}/{family}: training GMST variation is degenerate")
            slope = float(np.sum(dx * dy) / denominator)
            score = score.merge(means, on=CELL_KEYS, how="left", validate="many_to_one")
            if score[["train_cell_feature_mean", "train_cell_gmst_mean"]].isna().any().any():
                raise ValueError(f"{holdout}/{family}: test cells lack training support")
            truth = score["feature_value"].to_numpy(float)
            benchmark = score["train_cell_feature_mean"].to_numpy(float)
            prediction = benchmark + slope * (
                score["gmst_value_k"].to_numpy(float) - score["train_cell_gmst_mean"].to_numpy(float)
            )
            residual, benchmark_residual = prediction - truth, benchmark - truth
            rows.append({
                "split_type": "scenario", "holdout_id": holdout,
                "feature_family": family, "holdout_excluded": True,
                "model": "training_cell_mean_plus_common_within_cell_gmst_slope",
                "benchmark": "training_cell_mean", "n_train": len(fit), "n_test": len(score),
                "n_cells": len(means), "gmst_slope_per_k": slope,
                "rmse": float(np.sqrt(np.mean(residual**2))),
                "mae": float(np.mean(np.abs(residual))),
                "benchmark_rmse": float(np.sqrt(np.mean(benchmark_residual**2))),
                "benchmark_mae": float(np.mean(np.abs(benchmark_residual))),
            })
    result = pd.DataFrame(rows)
    if len(result) != len(SCENARIOS) * len(FEATURES) or result.duplicated(
        ["holdout_id", "feature_family"]
    ).any():
        raise ValueError("scenario holdout audit lacks the exact scenario/feature product")
    if not np.isfinite(result.select_dtypes(include=["number"]).to_numpy()).all():
        raise ValueError("scenario holdout metrics must be finite")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--training-out", type=Path, required=True)
    parser.add_argument("--holdouts-out", type=Path, required=True)
    parser.add_argument("--audit-out", type=Path, required=True)
    args = parser.parse_args()
    training, metadata = assemble_training(args.config.resolve())
    holdouts = evaluate_leave_one_scenario_out(training)
    for path in (args.training_out, args.holdouts_out, args.audit_out):
        path.parent.mkdir(parents=True, exist_ok=True)
    training.to_parquet(args.training_out, index=False)
    holdouts.to_csv(args.holdouts_out, index=False)
    ratios = holdouts["rmse"] / holdouts["benchmark_rmse"]
    improved = holdouts["rmse"] < holdouts["benchmark_rmse"]
    audit = {
        "schema": "isimip3b_bounded_gfdl_scenario_holdout_smoke_v1",
        "role": "historical_plus_three_ssp_scenario_engineering_smoke_not_complete_emulator_damage_or_scc_input",
        **metadata,
        "implementation": {
            "path": _display_path(Path(__file__).resolve(), args.config.resolve().parent.parent),
            "sha256": sha256(Path(__file__).resolve()),
        },
        "training_rows": len(training), "holdout_rows": len(holdouts),
        "feature_families": FEATURES,
        "gmst_model_better_than_cell_mean_count": int(improved.sum()),
        "comparison_count": len(holdouts),
        "median_rmse_ratio_to_cell_mean": float(ratios.median()),
        "maximum_rmse_ratio_to_cell_mean": float(ratios.max()),
        "scenario_summaries": {
            scenario: {
                "comparisons": int(len(block)),
                "gmst_model_better_count": int((block["rmse"] < block["benchmark_rmse"]).sum()),
                "median_rmse_ratio_to_cell_mean": float((block["rmse"] / block["benchmark_rmse"]).median()),
                "maximum_rmse_ratio_to_cell_mean": float((block["rmse"] / block["benchmark_rmse"]).max()),
            }
            for scenario, block in holdouts.groupby("holdout_id", sort=True)
        },
        "training_output": {"artifact_name": args.training_out.name, "sha256": sha256(args.training_out)},
        "holdouts_output": {"artifact_name": args.holdouts_out.name, "sha256": sha256(args.holdouts_out)},
        "limitations": [
            "Only seven nonoverlapping harvest years, one ESM/member, one crop/regime, and two latitude rows are evaluated.",
            "The exact four-scenario training-design gate passes, but this is not the complete historical/future temporal or five-ESM product.",
            "No paired baseline/pulse path, support rule, yield response, damage, welfare, or SCC value is produced.",
        ],
        "result": "passed",
    }
    args.audit_out.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        f"bounded GFDL scenario holdout smoke passed: {len(training)} training rows, "
        f"{len(holdouts)} holdouts, GMST model improved {int(improved.sum())}/{len(holdouts)}"
    )


if __name__ == "__main__":
    main()
