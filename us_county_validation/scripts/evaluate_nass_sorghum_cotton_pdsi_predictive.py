#!/usr/bin/env python3
"""Evaluate frozen PDSI-only predictive candidates for sorghum and cotton."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT = Path(__file__).resolve().parents[2]
MODELS = {
    "trend_only": [],
    "season_linear": ["delta_season"],
    "season_quadratic": ["delta_season", "delta_season_squared"],
    "stage_linear": ["delta_stage1", "delta_stage2", "delta_stage3"],
}


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 << 20), b""):
            value.update(block)
    return value.hexdigest()


def project_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("paths must be project-relative")
    result = (PROJECT / path).resolve()
    result.relative_to(PROJECT)
    return result


def build_differences(panel: pd.DataFrame) -> pd.DataFrame:
    required = {
        "crop", "practice", "county_geoid", "state_alpha", "harvest_year", "yield_value",
        "pdsi_season_mean", "pdsi_stage1_mean", "pdsi_stage2_mean", "pdsi_stage3_mean",
    }
    if missing := required - set(panel.columns):
        raise ValueError(f"joined panel lacks {sorted(missing)}")
    rows = []
    levels = {
        "season": "pdsi_season_mean", "stage1": "pdsi_stage1_mean",
        "stage2": "pdsi_stage2_mean", "stage3": "pdsi_stage3_mean",
    }
    for (crop, practice), frame in panel.groupby(["crop", "practice"], observed=True):
        frame = frame.sort_values(["county_geoid", "harvest_year"]).copy()
        frame["log_yield"] = np.log(frame.yield_value.astype(float))
        grouped = frame.groupby("county_geoid", observed=True, sort=False)
        frame["previous_year"] = grouped.harvest_year.shift(1)
        frame["previous_log_yield"] = grouped.log_yield.shift(1)
        for name, column in levels.items():
            frame[f"previous_{name}"] = grouped[column].shift(1)
        frame = frame.loc[frame.harvest_year.sub(frame.previous_year).eq(1)].copy()
        frame["delta_log_yield"] = frame.log_yield - frame.previous_log_yield
        for name, column in levels.items():
            frame[f"delta_{name}"] = frame[column] - frame[f"previous_{name}"]
        frame["delta_season_squared"] = np.square(frame.pdsi_season_mean) - np.square(frame.previous_season)
        rows.append(frame[[
            "crop", "practice", "county_geoid", "state_alpha", "previous_year", "harvest_year",
            "delta_log_yield", "delta_season", "delta_season_squared",
            "delta_stage1", "delta_stage2", "delta_stage3",
        ]])
    result = pd.concat(rows, ignore_index=True)
    keys = ["crop", "practice", "county_geoid", "harvest_year"]
    numeric = ["delta_log_yield", "delta_season", "delta_season_squared", "delta_stage1", "delta_stage2", "delta_stage3"]
    if result.empty or result.duplicated(keys).any() or not np.isfinite(result[numeric]).all().all():
        raise ValueError("first-difference panel fails uniqueness or finite-value gates")
    return result.sort_values(keys).reset_index(drop=True)


def endpoints(frame: pd.DataFrame, mask: np.ndarray) -> set[tuple[str, int]]:
    result = set()
    for row in frame.loc[mask].itertuples(index=False):
        result.add((str(row.county_geoid), int(row.previous_year)))
        result.add((str(row.county_geoid), int(row.harvest_year)))
    return result


def purge(frame: pd.DataFrame, train: np.ndarray, test: np.ndarray) -> tuple[np.ndarray, int]:
    test_endpoints = endpoints(frame, test)
    keep = train.copy()
    for position in np.flatnonzero(train):
        row = frame.iloc[int(position)]
        if {(str(row.county_geoid), int(row.previous_year)), (str(row.county_geoid), int(row.harvest_year))} & test_endpoints:
            keep[position] = False
    if endpoints(frame, keep) & test_endpoints:
        raise ValueError("endpoint purge failed")
    return keep, int(train.sum() - keep.sum())


def score(y: np.ndarray, prediction: np.ndarray, training_mean: float) -> dict[str, float | None]:
    error = y - prediction
    denominator = float(np.sum(np.square(y - training_mean)))
    correlation = None
    if len(y) > 1 and np.std(y) > 0 and np.std(prediction) > 0:
        correlation = float(np.corrcoef(y, prediction)[0, 1])
    return {
        "rmse": float(np.sqrt(np.mean(np.square(error)))),
        "mae": float(np.mean(np.abs(error))),
        "r2_oos": None if denominator <= 0 else float(1 - np.sum(np.square(error)) / denominator),
        "correlation": correlation,
    }


def fit_predict(frame: pd.DataFrame, columns: list[str], train: np.ndarray, test: np.ndarray) -> dict[str, object]:
    if np.any(train & test) or not train.any() or not test.any():
        raise ValueError("invalid train/test masks")
    year = frame.harvest_year.to_numpy(dtype=float)
    year_scale = float(year[train].std(ddof=0))
    if not np.isfinite(year_scale) or year_scale <= 0:
        raise ValueError("training years do not vary")
    year_z = (year - float(year[train].mean())) / year_scale
    raw = np.column_stack([*[frame[column].to_numpy(float) for column in columns], year_z, np.square(year_z)])
    mean, scale = raw[train].mean(axis=0), raw[train].std(axis=0, ddof=0)
    floor = np.maximum(1e-10, 1e-8 * np.max(np.abs(raw[train]), axis=0))
    retain = np.isfinite(scale) & (scale > floor)
    design = np.column_stack([np.ones(len(frame)), (raw[:, retain] - mean[retain]) / scale[retain]])
    u, singular, vt = np.linalg.svd(design[train], full_matrices=False)
    if len(singular) == 0 or not np.isfinite(singular).all() or singular[0] <= 0:
        raise ValueError("training design has invalid singular values")
    active = singular > singular[0] * 1e-10
    if not active.any():
        raise ValueError("SVD drops every design direction")
    y_train = frame.loc[train, "delta_log_yield"].to_numpy(float)
    projected = np.einsum("ij,i->j", u[:, active], y_train, optimize=True)
    beta = np.einsum("ij,j->i", vt[active].T, projected / singular[active], optimize=True)
    prediction = np.einsum("ij,j->i", design[test], beta, optimize=True)
    if not np.isfinite(beta).all() or not np.isfinite(prediction).all():
        raise ValueError("fit or prediction is nonfinite")
    result = score(frame.loc[test, "delta_log_yield"].to_numpy(float), prediction, float(y_train.mean()))
    result.update({
        "training_rows": int(train.sum()), "test_rows": int(test.sum()),
        "candidate_predictor_count_including_year_terms": int(raw.shape[1]),
        "retained_scaled_predictor_count": int(retain.sum()),
        "design_rank_including_intercept": int(active.sum()),
        "dropped_svd_directions": int(len(singular) - active.sum()),
    })
    return result


def comparison(rows: list[dict[str, object]], comparator: str, candidate: str) -> dict[str, object]:
    folds = {}
    for row in rows:
        if row["model"] not in {comparator, candidate}:
            continue
        folds.setdefault((str(row["split"]), str(row["split_id"])), {})[str(row["model"])] = float(row["rmse"])
    details, passed = {}, True
    for key, values in sorted(folds.items()):
        if set(values) != {comparator, candidate}:
            raise ValueError("comparison fold lacks a model")
        improvement = values[comparator] - values[candidate]
        floor = max(0.0001, 0.01 * values[comparator])
        details[f"{key[0]}:{key[1]}"] = {"rmse_improvement": improvement, "required_floor": floor, "passed": improvement >= floor}
        passed &= improvement >= floor
    return {"comparator": comparator, "candidate": candidate, "folds": details, "all_folds_pass": bool(details and passed)}


def evaluate(differences: pd.DataFrame) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    results, summaries = [], []
    for (crop, practice), frame in differences.groupby(["crop", "practice"], observed=True, sort=True):
        frame = frame.reset_index(drop=True)
        development = frame.harvest_year.le(2007).to_numpy(bool)
        terminal = frame.harvest_year.ge(2008).to_numpy(bool)
        state_counts = frame.loc[development].state_alpha.astype(str).value_counts().sort_index()
        states = list(map(str, state_counts.loc[state_counts.ge(40)].index))
        if len(states) < 5:
            raise ValueError(f"{crop}/{practice} has fewer than five eligible state folds")
        splits = []
        for state in states:
            state_mask = frame.state_alpha.astype(str).eq(state).to_numpy(bool)
            splits.append(("development_leave_state_out", state, development & ~state_mask, development & state_mask))
        development_counties = set(frame.loc[development, "county_geoid"].astype(str))
        same_county_terminal = terminal & frame.county_geoid.astype(str).isin(development_counties).to_numpy(bool)
        if same_county_terminal.sum() < 50:
            raise ValueError(f"{crop}/{practice} has fewer than 50 terminal same-county rows")
        splits.append(("terminal_same_counties", "2008_2018", development, same_county_terminal))
        stratum_rows = []
        for split, split_id, train_before, test in splits:
            train, purged = purge(frame, train_before, test)
            for model, columns in MODELS.items():
                row = {
                    "crop": str(crop), "practice": str(practice), "split": split, "split_id": split_id,
                    "model": model, "train_rows_before_endpoint_purge": int(train_before.sum()),
                    "train_rows_purged_shared_level_endpoint": purged, "level_endpoints_disjoint": True,
                    **fit_predict(frame, columns, train, test),
                }
                results.append(row); stratum_rows.append(row)
        summaries.append({
            "crop": str(crop), "practice": str(practice), "eligible_development_states": states,
            "season_linear_vs_trend": comparison(stratum_rows, "trend_only", "season_linear"),
            "stage_linear_vs_season_linear": comparison(stratum_rows, "season_linear", "stage_linear"),
            "season_quadratic_vs_season_linear": comparison(stratum_rows, "season_linear", "season_quadratic"),
        })
    return results, summaries


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--join", required=True)
    parser.add_argument("--protocol", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    join_path, protocol_path, out_path = map(project_path, [args.join, args.protocol, args.out])
    if out_path.exists():
        raise FileExistsError(f"refusing to overwrite {out_path}")
    differences = build_differences(pd.read_parquet(join_path))
    results, summaries = evaluate(differences)
    support = {}
    for (crop, practice), frame in differences.groupby(["crop", "practice"], observed=True):
        support[f"{crop}:{practice}"] = {
            "difference_rows": len(frame), "counties": int(frame.county_geoid.nunique()),
            "states": int(frame.state_alpha.nunique()), "year_min": int(frame.harvest_year.min()),
            "year_max": int(frame.harvest_year.max()), "terminal_rows": int(frame.harvest_year.ge(2008).sum()),
        }
    payload = {
        "schema": "us_sorghum_cotton_pdsi_predictive_v1",
        "status": "completed_frozen_historical_predictive_diagnostic",
        "estimand": "out_of_sample_prediction_of_consecutive_year_log_yield_change",
        "moisture_family": "pdsi_only_not_stacked_with_direct_rainfall_temperature_or_other_drought_indices",
        "inputs": {
            "joined_panel": {"path": args.join, "sha256": digest(join_path)},
            "protocol": {"path": args.protocol, "sha256": digest(protocol_path)},
            "implementation": {"path": str(Path(__file__).resolve().relative_to(PROJECT)), "sha256": digest(Path(__file__))},
        },
        "first_difference_support": support, "model_families": MODELS,
        "results": results, "summaries": summaries,
        "coefficients_emitted": False, "row_predictions_emitted": False,
        "predictive_diagnostic_authorized": True, "causal_claim_authorized": False,
        "irrigation_treatment_claim_authorized": False, "national_representativeness_claim_authorized": False,
        "future_drought_claim_authorized": False, "global_transfer_authorized": False,
        "damage_claim_authorized": False, "scc_claim_authorized": False,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"out": args.out, "support": support, "summaries": summaries}, indent=2))


if __name__ == "__main__":
    main()
