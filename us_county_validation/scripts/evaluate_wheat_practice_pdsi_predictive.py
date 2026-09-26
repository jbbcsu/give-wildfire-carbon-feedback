#!/usr/bin/env python3
"""Run the frozen weighted-wheat PDSI first-difference predictive diagnostic."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


PROJECT = Path(__file__).resolve().parents[2]
ASSOCIATION_SCRIPT = PROJECT / "us_county_validation/scripts/estimate_wheat_practice_pdsi_sensitivity.py"
MODELS = {
    "trend_only": [],
    "pdsi_linear": ["delta_pdsi"],
    "pdsi_quadratic": ["delta_pdsi", "delta_pdsi_squared"],
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def project_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("paths must be project-relative")
    result = (PROJECT / path).resolve()
    result.relative_to(PROJECT.resolve())
    return result


def load_association_module():
    spec = importlib.util.spec_from_file_location("wheat_pdsi_association", ASSOCIATION_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load weighted wheat panel builder")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def build_differences(pairs: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for practice, outcome in (
        ("irrigated", "log_yield_irrigated"),
        ("non_irrigated", "log_yield_non_irrigated"),
    ):
        frame = pairs[["county_geoid", "state", "harvest_year", "pdsi", outcome]].copy()
        frame = frame.sort_values(["county_geoid", "harvest_year"]).reset_index(drop=True)
        grouped = frame.groupby("county_geoid", observed=True, sort=False)
        frame["difference_previous_harvest_year"] = grouped.harvest_year.shift(1)
        frame["previous_log_yield"] = grouped[outcome].shift(1)
        frame["previous_pdsi"] = grouped.pdsi.shift(1)
        consecutive = frame.harvest_year.sub(frame.difference_previous_harvest_year).eq(1)
        frame = frame.loc[consecutive].copy()
        frame["irrigation_practice"] = practice
        frame["delta_log_yield"] = frame[outcome] - frame.previous_log_yield
        frame["delta_pdsi"] = frame.pdsi - frame.previous_pdsi
        frame["delta_pdsi_squared"] = np.square(frame.pdsi) - np.square(frame.previous_pdsi)
        rows.append(frame[[
            "county_geoid", "state", "irrigation_practice",
            "difference_previous_harvest_year", "harvest_year",
            "delta_log_yield", "delta_pdsi", "delta_pdsi_squared",
        ]])
    result = pd.concat(rows, ignore_index=True)
    keys = ["county_geoid", "irrigation_practice", "harvest_year"]
    if result.empty or result.duplicated(keys).any():
        raise ValueError("wheat first-difference support is empty or duplicated")
    numeric = ["delta_log_yield", "delta_pdsi", "delta_pdsi_squared"]
    if not np.isfinite(result[numeric]).all().all():
        raise ValueError("wheat first differences contain nonfinite values")
    if not result.harvest_year.sub(result.difference_previous_harvest_year).eq(1).all():
        raise ValueError("wheat first differences bridge a year gap")
    return result.sort_values(keys).reset_index(drop=True)


def endpoint_set(frame: pd.DataFrame, mask: np.ndarray) -> set[tuple[str, str, int]]:
    endpoints: set[tuple[str, str, int]] = set()
    for row in frame.loc[mask].itertuples(index=False):
        prefix = (str(row.county_geoid), str(row.irrigation_practice))
        endpoints.add((*prefix, int(row.difference_previous_harvest_year)))
        endpoints.add((*prefix, int(row.harvest_year)))
    return endpoints


def purge_endpoints(
    frame: pd.DataFrame, train: np.ndarray, test: np.ndarray,
) -> tuple[np.ndarray, int]:
    if np.any(train & test):
        raise ValueError("train and test rows overlap")
    test_endpoints = endpoint_set(frame, test)
    keep = train.copy()
    for position in np.flatnonzero(train):
        row = frame.iloc[int(position)]
        prefix = (str(row.county_geoid), str(row.irrigation_practice))
        row_endpoints = {
            (*prefix, int(row.difference_previous_harvest_year)),
            (*prefix, int(row.harvest_year)),
        }
        if row_endpoints & test_endpoints:
            keep[position] = False
    if endpoint_set(frame, keep) & test_endpoints:
        raise ValueError("endpoint purge left shared level endpoints")
    return keep, int(train.sum() - keep.sum())


def metrics(y: np.ndarray, prediction: np.ndarray, training_mean: float) -> dict[str, Any]:
    error = y - prediction
    rmse = float(np.sqrt(np.mean(np.square(error))))
    mae = float(np.mean(np.abs(error)))
    denominator = float(np.sum(np.square(y - training_mean)))
    r2 = None if denominator <= 0 else float(1 - np.sum(np.square(error)) / denominator)
    correlation = None
    if len(y) > 1 and np.std(y) > 0 and np.std(prediction) > 0:
        correlation = float(np.corrcoef(y, prediction)[0, 1])
    return {"rmse": rmse, "mae": mae, "r2_oos": r2, "correlation": correlation}


def fit_predict(
    frame: pd.DataFrame, columns: list[str], train: np.ndarray, test: np.ndarray,
) -> dict[str, Any]:
    if np.any(train & test) or not train.any() or not test.any():
        raise ValueError("invalid predictive masks")
    year = frame.harvest_year.to_numpy(dtype=float)
    year_scale = float(year[train].std(ddof=0))
    if not np.isfinite(year_scale) or year_scale <= 0:
        raise ValueError("training years do not vary")
    year_z = (year - float(year[train].mean())) / year_scale
    raw_parts = [frame[column].to_numpy(dtype=float) for column in columns]
    raw_parts.extend([year_z, np.square(year_z)])
    raw = np.column_stack(raw_parts)
    if not np.isfinite(raw).all():
        raise ValueError("predictors are nonfinite")
    mean = raw[train].mean(axis=0)
    scale = raw[train].std(axis=0, ddof=0)
    magnitude = np.max(np.abs(raw[train]), axis=0)
    floor = np.maximum(1e-10, 1e-8 * magnitude)
    retain = np.isfinite(scale) & (scale > floor)
    if not retain.any():
        raise ValueError("all predictors are constant in training")
    design = (raw[:, retain] - mean[retain]) / scale[retain]
    design = np.column_stack([np.ones(len(frame)), design])
    training_design = design[train]
    u, singular, vt = np.linalg.svd(training_design, full_matrices=False)
    if len(singular) == 0 or singular[0] <= 0:
        raise ValueError("training design has no singular values")
    active = singular > singular[0] * 1e-10
    if not active.any():
        raise ValueError("SVD drops every design direction")
    y_train = frame.loc[train, "delta_log_yield"].to_numpy(dtype=float)
    projected = np.einsum("ij,i->j", u[:, active], y_train, optimize=True)
    beta = np.einsum(
        "ij,j->i", vt[active].T, projected / singular[active], optimize=True,
    )
    prediction = np.einsum("ij,j->i", design[test], beta, optimize=True)
    y_test = frame.loc[test, "delta_log_yield"].to_numpy(dtype=float)
    output = metrics(
        y_test, prediction,
        float(frame.loc[train, "delta_log_yield"].mean()),
    )
    output.update({
        "training_rows": int(train.sum()), "test_rows": int(test.sum()),
        "candidate_predictor_count_including_year_terms": int(raw.shape[1]),
        "retained_scaled_predictor_count": int(retain.sum()),
        "design_rank_including_intercept": int(active.sum()),
        "dropped_svd_directions": int(len(singular) - active.sum()),
    })
    return output


def evaluate(differences: pd.DataFrame) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    output = []
    summaries = []
    for practice, stratum in differences.groupby("irrigation_practice", observed=True, sort=True):
        stratum = stratum.reset_index(drop=True)
        terminal = stratum.harvest_year.ge(2001).to_numpy(dtype=bool)
        development = ~terminal
        if not terminal.any() or not development.any():
            raise ValueError("terminal or development wheat split is empty")
        state_counts = stratum.loc[development].state.astype(str).value_counts().sort_index()
        eligible_states = list(map(str, state_counts.loc[state_counts.ge(50)].index))
        if len(eligible_states) < 5:
            raise ValueError(f"{practice} has fewer than five eligible state tests")
        splits: list[tuple[str, str, np.ndarray, np.ndarray]] = []
        for state in eligible_states:
            state_mask = stratum.state.astype(str).eq(state).to_numpy(dtype=bool)
            splits.append((
                "development_leave_state_out", state,
                development & ~state_mask, development & state_mask,
            ))
        development_counties = set(stratum.loc[development, "county_geoid"].astype(str))
        same_county_terminal = terminal & stratum.county_geoid.astype(str).isin(
            development_counties
        ).to_numpy(dtype=bool)
        splits.append((
            "terminal_same_counties", "2001_2007", development, same_county_terminal,
        ))
        for split, split_id, train_before, test in splits:
            if int(test.sum()) < 50:
                raise ValueError(f"{practice}/{split}/{split_id} has fewer than 50 test rows")
            train, purged = purge_endpoints(stratum, train_before, test)
            train_keys = set(map(tuple, stratum.loc[train, [
                "county_geoid", "irrigation_practice", "harvest_year",
            ]].itertuples(index=False, name=None)))
            test_keys = set(map(tuple, stratum.loc[test, [
                "county_geoid", "irrigation_practice", "harvest_year",
            ]].itertuples(index=False, name=None)))
            if train_keys & test_keys:
                raise ValueError("predictive row keys overlap")
            for model, columns in MODELS.items():
                output.append({
                    "irrigation_practice": str(practice),
                    "split": split, "split_id": split_id, "model": model,
                    "train_rows_before_endpoint_purge": int(train_before.sum()),
                    "train_rows_purged_shared_level_endpoint": purged,
                    "level_endpoints_disjoint": True,
                    **fit_predict(stratum, columns, train, test),
                })
        improvements = {}
        floors = {}
        excess = {}
        for state in eligible_states:
            selected = {
                row["model"]: float(row["rmse"])
                for row in output
                if row["irrigation_practice"] == practice
                and row["split"] == "development_leave_state_out"
                and row["split_id"] == state
                and row["model"] in {"trend_only", "pdsi_linear"}
            }
            improvement = selected["trend_only"] - selected["pdsi_linear"]
            floor = max(0.0001, 0.01 * selected["trend_only"])
            improvements[state] = improvement
            floors[state] = floor
            excess[state] = improvement - floor
        terminal_rows = {
            row["model"]: float(row["rmse"])
            for row in output
            if row["irrigation_practice"] == practice
            and row["split"] == "terminal_same_counties"
            and row["split_id"] == "2001_2007"
            and row["model"] in {"trend_only", "pdsi_linear"}
        }
        terminal_improvement = terminal_rows["trend_only"] - terminal_rows["pdsi_linear"]
        summaries.append({
            "irrigation_practice": str(practice),
            "eligible_development_states": eligible_states,
            "development_state_improvements": improvements,
            "development_state_required_floors": floors,
            "development_state_excess_over_floor": excess,
            "all_development_states_pass_materiality": bool(
                excess and all(value >= 0 for value in excess.values())
            ),
            "terminal_rmse_improvement": terminal_improvement,
            "terminal_improves": bool(terminal_improvement > 0),
            "pdsi_linear_predictive_gate_passed": bool(
                excess and all(value >= 0 for value in excess.values())
                and terminal_improvement > 0
            ),
        })
    return output, summaries


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--join", default="data/interim/us_county/nass_direct_practice_pdsi_join_1981_2019.parquet"
    )
    parser.add_argument(
        "--calendar", default="config/us_county_nass_usual_date_definitions_2010.csv"
    )
    parser.add_argument(
        "--association-protocol", default="US_WHEAT_PRACTICE_PDSI_PROTOCOL_20260925.md"
    )
    parser.add_argument(
        "--predictive-protocol", default="US_WHEAT_PRACTICE_PDSI_PREDICTIVE_PROTOCOL_20260925.md"
    )
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    out_path = project_path(args.out)
    if out_path.exists():
        raise FileExistsError(f"refusing to overwrite {out_path}")
    module = load_association_module()
    join_path = project_path(args.join)
    calendar_path = project_path(args.calendar)
    weights = module.wheat_state_weights(calendar_path)
    pairs, panel_audit = module.prepare_panel(join_path, weights)
    differences = build_differences(pairs)
    results, summaries = evaluate(differences)
    support = {
        practice: {
            "difference_rows": int(len(part)),
            "counties": int(part.county_geoid.nunique()),
            "states": int(part.state.nunique()),
            "difference_year_min": int(part.harvest_year.min()),
            "difference_year_max": int(part.harvest_year.max()),
            "terminal_rows": int(part.harvest_year.ge(2001).sum()),
        }
        for practice, part in differences.groupby("irrigation_practice", observed=True)
    }
    payload = {
        "schema": "us_wheat_practice_pdsi_predictive_v1",
        "status": "completed_historical_predictive_diagnostic",
        "estimand": "out_of_sample_prediction_of_consecutive_year_log_yield_change",
        "moisture_family": "pdsi_only_not_stacked_with_direct_rainfall",
        "inputs": {
            "joined_panel": {"path": args.join, "sha256": sha256(join_path)},
            "calendar_definitions": {
                "path": args.calendar, "sha256": sha256(calendar_path),
            },
            "association_protocol": {
                "path": args.association_protocol,
                "sha256": sha256(project_path(args.association_protocol)),
            },
            "predictive_protocol": {
                "path": args.predictive_protocol,
                "sha256": sha256(project_path(args.predictive_protocol)),
            },
            "panel_builder": {
                "path": "us_county_validation/scripts/estimate_wheat_practice_pdsi_sensitivity.py",
                "sha256": sha256(ASSOCIATION_SCRIPT),
            },
            "implementation": {
                "path": "us_county_validation/scripts/evaluate_wheat_practice_pdsi_predictive.py",
                "sha256": sha256(Path(__file__).resolve()),
            },
        },
        "level_panel": panel_audit,
        "first_difference_support": support,
        "model_families": {
            "trend_only": "deterministic linear and quadratic year terms",
            "pdsi_linear": "trend terms plus change in weighted seasonal PDSI",
            "pdsi_quadratic": "trend terms plus changes in PDSI and PDSI squared",
        },
        "results": results,
        "summaries": summaries,
        "coefficients_emitted": False,
        "row_predictions_emitted": False,
        "predictive_diagnostic_authorized": True,
        "causal_claim_authorized": False,
        "irrigation_treatment_claim_authorized": False,
        "national_representativeness_claim_authorized": False,
        "future_drought_claim_authorized": False,
        "global_transfer_authorized": False,
        "damage_claim_authorized": False,
        "scc_claim_authorized": False,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "out": args.out, "first_difference_support": support,
        "summaries": summaries,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
