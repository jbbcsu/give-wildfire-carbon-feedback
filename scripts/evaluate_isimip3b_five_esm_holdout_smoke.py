#!/usr/bin/env python3
"""Bounded whole-ESM holdout smoke for direct ISIMIP3b crop features.

This script assembles a provenance-rich long table from a predeclared set of
same-scenario feature cells and evaluates a deliberately simple, transparent
predictor while withholding each ESM in turn.  It is an engineering smoke,
not the complete historical/four-scenario emulator validation and not an
agricultural response, damage, or SCC input.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import tomllib
from pathlib import Path

import numpy as np
import pandas as pd


KEYS = ["harvest_year", "lat", "lon_360", "crop", "irrigation"]
CELL_KEYS = ["lat", "lon_360", "crop", "irrigation"]
SEASON_FEATURES = [
    "tmean_c",
    "precip_mm",
    "wet_days_n",
    "cdd_max_days",
    "rx1day_mm",
    "rx5day_mm",
]
TIMING_FEATURES = [
    "stage1_precip_share",
    "stage2_precip_share",
    "stage3_precip_share",
    "precipitation_timing_centroid",
    "precipitation_concentration_hhi",
]
FEATURES = SEASON_FEATURES + TIMING_FEATURES


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _path(root: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else root / path


def _display_path(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def _checked_keys(frame: pd.DataFrame, label: str) -> pd.DataFrame:
    missing = set(KEYS) - set(frame.columns)
    if missing:
        raise ValueError(f"{label} missing keys: {sorted(missing)}")
    if frame.empty:
        raise ValueError(f"{label} is empty")
    if frame.duplicated(KEYS).any():
        raise ValueError(f"{label} has duplicate keys")
    return frame.sort_values(KEYS).reset_index(drop=True)


def _timing_features(season: pd.DataFrame, stages: pd.DataFrame, label: str) -> pd.DataFrame:
    required = set(KEYS + ["stage_id", "precip_mm"])
    if missing := required - set(stages.columns):
        raise ValueError(f"{label} stages missing columns: {sorted(missing)}")
    if stages.duplicated(KEYS + ["stage_id"]).any():
        raise ValueError(f"{label} stages have duplicate keys")
    observed = stages.groupby(KEYS, observed=True)["stage_id"].agg(lambda x: set(x))
    if not observed.map(lambda x: x == {1, 2, 3}).all():
        raise ValueError(f"{label} must contain exactly stage IDs 1, 2, and 3")
    wide = stages.pivot(index=KEYS, columns="stage_id", values="precip_mm")
    wide.columns = [f"stage{stage}_precip_mm" for stage in wide.columns]
    merged = season[KEYS + ["precip_mm"]].merge(
        wide.reset_index(), on=KEYS, how="left", validate="one_to_one"
    )
    stage_columns = [f"stage{stage}_precip_mm" for stage in (1, 2, 3)]
    values = merged[stage_columns].to_numpy(float)
    totals = merged["precip_mm"].to_numpy(float)
    if not np.isfinite(values).all() or (values < 0).any():
        raise ValueError(f"{label} stage precipitation must be finite and nonnegative")
    if not np.allclose(values.sum(axis=1), totals, rtol=0, atol=1e-3):
        raise ValueError(f"{label} stage precipitation does not reconcile to season totals")
    shares = np.divide(values, totals[:, None], out=np.zeros_like(values), where=totals[:, None] > 0)
    result = merged[KEYS].copy()
    for index in range(3):
        result[f"stage{index + 1}_precip_share"] = shares[:, index]
    # Elementwise reduction avoids spurious floating-point-status warnings
    # emitted by some sandboxed BLAS builds for an otherwise finite matmul.
    result["precipitation_timing_centroid"] = np.sum(
        shares * np.array([1 / 6, 1 / 2, 5 / 6]), axis=1
    )
    result["precipitation_concentration_hhi"] = (shares**2).sum(axis=1)
    return result


def _validate_physical(frame: pd.DataFrame, label: str) -> None:
    numeric = frame[SEASON_FEATURES + TIMING_FEATURES].apply(pd.to_numeric, errors="coerce")
    if numeric.isna().any().any() or not np.isfinite(numeric.to_numpy()).all():
        raise ValueError(f"{label} feature values must be finite")
    nonnegative = ["precip_mm", "wet_days_n", "cdd_max_days", "rx1day_mm", "rx5day_mm"]
    if (numeric[nonnegative] < 0).any().any():
        raise ValueError(f"{label} precipitation/count features must be nonnegative")
    if (numeric["rx1day_mm"] > numeric["rx5day_mm"] + 1e-9).any():
        raise ValueError(f"{label} Rx1day exceeds Rx5day")
    if (numeric["rx5day_mm"] > numeric["precip_mm"] + 1e-3).any():
        raise ValueError(f"{label} Rx5day exceeds seasonal precipitation")
    shares = numeric[[f"stage{i}_precip_share" for i in (1, 2, 3)]]
    if ((shares < 0) | (shares > 1)).any().any():
        raise ValueError(f"{label} stage shares must lie in [0, 1]")
    wet = numeric["precip_mm"] > 0
    if not np.allclose(shares.loc[wet].sum(axis=1), 1, rtol=0, atol=1e-10):
        raise ValueError(f"{label} wet-season stage shares must sum to one")
    if not ((numeric["precipitation_timing_centroid"] >= 0) &
            (numeric["precipitation_timing_centroid"] <= 1)).all():
        raise ValueError(f"{label} timing centroid must lie in [0, 1]")
    if not ((numeric["precipitation_concentration_hhi"] >= 0) &
            (numeric["precipitation_concentration_hhi"] <= 1 + 1e-12)).all():
        raise ValueError(f"{label} timing concentration must lie in [0, 1]")


def assemble_training(config_path: Path) -> tuple[pd.DataFrame, dict[str, object]]:
    config = tomllib.loads(config_path.read_text(encoding="utf-8"))
    root = config_path.parent.parent
    expected_count = int(config["selection"]["expected_esm_count"])
    scenario = str(config["selection"]["scenario"])
    year_start = int(config["selection"]["year_start"])
    year_end = int(config["selection"]["year_end"])
    cells = config.get("cells", [])
    if len(cells) != expected_count or expected_count < 3:
        raise ValueError("config does not contain the declared ESM count")
    identities = [(str(cell["esm_id"]), str(cell["member_id"])) for cell in cells]
    if len(set(identities)) != expected_count:
        raise ValueError("ESM/member identities must be unique")

    reference_keys: pd.DataFrame | None = None
    frames: list[pd.DataFrame] = []
    receipts: list[dict[str, object]] = []
    for cell in cells:
        esm_id = str(cell["esm_id"])
        member_id = str(cell["member_id"])
        label = f"{esm_id}/{member_id}"
        season_path = _path(root, str(cell["season_path"]))
        stage_path = _path(root, str(cell["stage_path"]))
        gmst_path = _path(root, str(cell["gmst_path"]))
        for path in (season_path, stage_path, gmst_path):
            if not path.is_file():
                raise ValueError(f"{label} input is missing: {path}")

        season = pd.read_parquet(season_path)
        season = season.loc[season["harvest_year"].between(year_start, year_end)].copy()
        season = _checked_keys(season, f"{label} season")
        if missing := set(SEASON_FEATURES) - set(season.columns):
            raise ValueError(f"{label} season missing features: {sorted(missing)}")
        stages = pd.read_parquet(stage_path)
        stages = stages.loc[stages["harvest_year"].between(year_start, year_end)].copy()
        timing = _timing_features(season, stages, label)
        wide = season[KEYS + SEASON_FEATURES].merge(
            timing, on=KEYS, how="left", validate="one_to_one"
        )
        _validate_physical(wide, label)
        keys = wide[KEYS]
        if reference_keys is None:
            reference_keys = keys.copy()
        elif not keys.equals(reference_keys):
            raise ValueError("ESM feature cells do not have identical ordered keys")

        gmst = pd.read_parquet(gmst_path)
        required_gmst = {
            "esm_id", "member_id", "scenario", "gmst_source_id", "year", "gmst_value_k"
        }
        if missing := required_gmst - set(gmst.columns):
            raise ValueError(f"{label} GMST missing columns: {sorted(missing)}")
        gmst = gmst.loc[gmst["year"].between(year_start, year_end)].copy()
        if gmst.duplicated(["year"]).any() or set(gmst["year"]) != set(range(year_start, year_end + 1)):
            raise ValueError(f"{label} GMST must contain exactly one row for every smoke year")
        if set(gmst["esm_id"].astype(str)) != {esm_id}:
            raise ValueError(f"{label} GMST ESM identity mismatch")
        if set(gmst["member_id"].astype(str)) != {member_id}:
            raise ValueError(f"{label} GMST member identity mismatch")
        if set(gmst["scenario"].astype(str)) != {scenario}:
            raise ValueError(f"{label} GMST scenario mismatch")
        if (gmst["gmst_source_id"].astype(str).str.strip() == "").any():
            raise ValueError(f"{label} GMST source IDs must be explicit")
        if not pd.to_numeric(gmst["gmst_value_k"], errors="coerce").between(150, 350).all():
            raise ValueError(f"{label} GMST values are outside physical Kelvin bounds")

        wide["esm_id"] = esm_id
        wide["member_id"] = member_id
        wide["scenario"] = scenario
        wide = wide.merge(
            gmst[["year", "gmst_source_id", "gmst_value_k"]],
            left_on="harvest_year",
            right_on="year",
            how="left",
            validate="many_to_one",
        ).drop(columns="year")
        wide["gmst_esm_id"] = esm_id
        wide["gmst_member_id"] = member_id
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
            "esm_id": esm_id,
            "member_id": member_id,
            "season_path": _display_path(season_path, root),
            "season_sha256": sha256(season_path),
            "stage_path": _display_path(stage_path, root),
            "stage_sha256": sha256(stage_path),
            "gmst_path": _display_path(gmst_path, root),
            "gmst_sha256": sha256(gmst_path),
        })

    training = pd.concat(frames, ignore_index=True)
    validate_training(training, expected_count, scenario, year_start, year_end)
    metadata: dict[str, object] = {
        "config_path": _display_path(config_path, root),
        "config_sha256": sha256(config_path),
        "scenario": scenario,
        "year_start": year_start,
        "year_end": year_end,
        "expected_esm_count": expected_count,
        "inputs": receipts,
    }
    return training, metadata


def validate_training(
    training: pd.DataFrame,
    expected_esm_count: int,
    scenario: str,
    year_start: int,
    year_end: int,
) -> None:
    required = set(KEYS + [
        "esm_id", "member_id", "scenario", "gmst_source_id", "gmst_value_k",
        "gmst_esm_id", "gmst_member_id", "feature_family", "feature_value", "year",
    ])
    if missing := required - set(training.columns):
        raise ValueError(f"training missing columns: {sorted(missing)}")
    if training.duplicated(["esm_id", "member_id", "feature_family"] + KEYS).any():
        raise ValueError("training has duplicate ESM/member/feature/cell-year keys")
    if training["esm_id"].nunique() != expected_esm_count:
        raise ValueError("training does not contain the declared ESM count")
    if (training.groupby("esm_id")["member_id"].nunique() != 1).any():
        raise ValueError("each ESM must retain exactly one realization")
    if set(training["scenario"].astype(str)) != {scenario}:
        raise ValueError("training scenario differs from the frozen smoke scenario")
    if set(training["year"].astype(int)) != set(range(year_start, year_end + 1)):
        raise ValueError("training does not contain the exact smoke years")
    if set(training["feature_family"].astype(str)) != set(FEATURES):
        raise ValueError("training feature-family set differs from the frozen smoke set")
    if not (training["esm_id"].astype(str) == training["gmst_esm_id"].astype(str)).all():
        raise ValueError("feature and GMST ESM identities differ")
    if not (training["member_id"].astype(str) == training["gmst_member_id"].astype(str)).all():
        raise ValueError("feature and GMST member identities differ")
    numeric = training[["gmst_value_k", "feature_value"]].apply(pd.to_numeric, errors="coerce")
    if numeric.isna().any().any() or not np.isfinite(numeric.to_numpy()).all():
        raise ValueError("training GMST and feature values must be finite")


def evaluate_leave_one_esm_out(training: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for holdout in sorted(training["esm_id"].astype(str).unique()):
        train = training.loc[training["esm_id"].astype(str) != holdout].copy()
        test = training.loc[training["esm_id"].astype(str) == holdout].copy()
        for family in FEATURES:
            fit = train.loc[train["feature_family"] == family].copy()
            score = test.loc[test["feature_family"] == family].copy()
            means = fit.groupby(CELL_KEYS, observed=True).agg(
                train_cell_feature_mean=("feature_value", "mean"),
                train_cell_gmst_mean=("gmst_value_k", "mean"),
                train_cell_rows=("feature_value", "size"),
            ).reset_index()
            fit = fit.merge(means, on=CELL_KEYS, how="left", validate="many_to_one")
            dx = fit["gmst_value_k"].to_numpy(float) - fit["train_cell_gmst_mean"].to_numpy(float)
            dy = fit["feature_value"].to_numpy(float) - fit["train_cell_feature_mean"].to_numpy(float)
            denominator = float(np.sum(dx * dx))
            if not np.isfinite(denominator) or denominator <= 0:
                raise ValueError(f"{holdout}/{family}: training GMST variation is degenerate")
            slope = float(np.sum(dx * dy) / denominator)
            score = score.merge(means, on=CELL_KEYS, how="left", validate="many_to_one")
            if score[["train_cell_feature_mean", "train_cell_gmst_mean"]].isna().any().any():
                raise ValueError(f"{holdout}/{family}: held-out cells lack training support")
            truth = score["feature_value"].to_numpy(float)
            benchmark = score["train_cell_feature_mean"].to_numpy(float)
            prediction = benchmark + slope * (
                score["gmst_value_k"].to_numpy(float) - score["train_cell_gmst_mean"].to_numpy(float)
            )
            residual = prediction - truth
            benchmark_residual = benchmark - truth
            rows.append({
                "split_type": "esm",
                "holdout_id": holdout,
                "feature_family": family,
                "holdout_excluded": True,
                "model": "training_cell_mean_plus_common_within_cell_gmst_slope",
                "benchmark": "training_cell_mean",
                "n_train": int(len(fit)),
                "n_test": int(len(score)),
                "n_cells": int(len(means)),
                "gmst_slope_per_k": slope,
                "rmse": float(np.sqrt(np.mean(residual**2))),
                "mae": float(np.mean(np.abs(residual))),
                "benchmark_rmse": float(np.sqrt(np.mean(benchmark_residual**2))),
                "benchmark_mae": float(np.mean(np.abs(benchmark_residual))),
            })
    result = pd.DataFrame(rows)
    expected = len(training["esm_id"].unique()) * len(FEATURES)
    if len(result) != expected or result.duplicated(["holdout_id", "feature_family"]).any():
        raise ValueError("holdout audit does not contain the exact ESM/feature product")
    numeric = result[[
        "n_train", "n_test", "n_cells", "gmst_slope_per_k", "rmse", "mae",
        "benchmark_rmse", "benchmark_mae",
    ]].to_numpy(float)
    if not np.isfinite(numeric).all() or (result[["n_train", "n_test", "n_cells"]] <= 0).any().any():
        raise ValueError("holdout diagnostics must be finite with positive counts")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--training-out", type=Path, required=True)
    parser.add_argument("--holdouts-out", type=Path, required=True)
    parser.add_argument("--audit-out", type=Path, required=True)
    args = parser.parse_args()

    training, metadata = assemble_training(args.config.resolve())
    holdouts = evaluate_leave_one_esm_out(training)
    args.training_out.parent.mkdir(parents=True, exist_ok=True)
    args.holdouts_out.parent.mkdir(parents=True, exist_ok=True)
    args.audit_out.parent.mkdir(parents=True, exist_ok=True)
    training.to_parquet(args.training_out, index=False)
    holdouts.to_csv(args.holdouts_out, index=False)
    improvements = holdouts["rmse"] < holdouts["benchmark_rmse"]
    ratios = holdouts["rmse"] / holdouts["benchmark_rmse"]
    feature_summaries = {}
    for family, indices in holdouts.groupby("feature_family", sort=True).groups.items():
        block = holdouts.loc[indices]
        block_ratios = ratios.loc[indices]
        feature_summaries[str(family)] = {
            "comparisons": int(len(block)),
            "gmst_model_better_count": int((block["rmse"] < block["benchmark_rmse"]).sum()),
            "median_rmse_ratio_to_cell_mean": float(block_ratios.median()),
            "maximum_rmse_ratio_to_cell_mean": float(block_ratios.max()),
        }
    esm_summaries = {}
    for esm_id, indices in holdouts.groupby("holdout_id", sort=True).groups.items():
        block = holdouts.loc[indices]
        block_ratios = ratios.loc[indices]
        esm_summaries[str(esm_id)] = {
            "comparisons": int(len(block)),
            "gmst_model_better_count": int((block["rmse"] < block["benchmark_rmse"]).sum()),
            "median_rmse_ratio_to_cell_mean": float(block_ratios.median()),
            "maximum_rmse_ratio_to_cell_mean": float(block_ratios.max()),
        }
    audit = {
        "schema": "isimip3b_bounded_five_esm_holdout_smoke_v1",
        "role": "engineering_smoke_not_complete_emulator_damage_or_scc_input",
        **metadata,
        "implementation": {
            "path": _display_path(Path(__file__).resolve(), args.config.resolve().parent.parent),
            "sha256": sha256(Path(__file__).resolve()),
        },
        "training_rows": int(len(training)),
        "holdout_rows": int(len(holdouts)),
        "feature_families": FEATURES,
        "esm_ids": sorted(training["esm_id"].astype(str).unique()),
        "members": training.groupby("esm_id")["member_id"].first().astype(str).to_dict(),
        "rows_per_esm": training.groupby("esm_id").size().astype(int).to_dict(),
        "model_better_than_cell_mean_count": int(improvements.sum()),
        "comparison_count": int(len(holdouts)),
        "max_finite_rmse": float(holdouts["rmse"].max()),
        "feature_summaries": feature_summaries,
        "esm_summaries": esm_summaries,
        "training_output": {"artifact_name": args.training_out.name, "sha256": sha256(args.training_out)},
        "holdouts_output": {"artifact_name": args.holdouts_out.name, "sha256": sha256(args.holdouts_out)},
        "limitations": [
            "Only one scenario, four harvest years, one crop/regime, and a two-latitude-row engineering slice are evaluated.",
            "This does not satisfy the complete historical plus four-scenario production training gate.",
            "No paired baseline/pulse path, support rule, yield response, damage, welfare, or SCC value is produced.",
        ],
        "result": "passed",
    }
    args.audit_out.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        "bounded five-ESM holdout smoke passed: "
        f"{len(training)} training rows, {len(holdouts)} holdout rows, "
        f"GMST model improved {int(improvements.sum())}/{len(holdouts)} comparisons"
    )


if __name__ == "__main__":
    main()
