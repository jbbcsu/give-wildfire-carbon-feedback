#!/usr/bin/env python3
"""Post-result robustness: state-specific rather than common yield trends."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from estimate_us_county_average_terminal_prediction import (
    MODELS, bootstrap_rmse_difference, design, fit_within, metrics, predict,
)

ROOT = Path(__file__).resolve().parents[1]
PANEL = ROOT / "data/interim/us_county/noaa_county_average_nass_panel_20260916/panel.parquet"
PRIMARY = ROOT / "data/interim/us_county/noaa_county_average_prediction_20260916/result.json"
PRIMARY_VALIDATION = ROOT / "data/interim/us_county/noaa_county_average_prediction_validation_20260916/result.json"
PROTOCOL = ROOT / "US_COUNTY_AVERAGE_STATE_TREND_SENSITIVITY_20260916.md"


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(2**20), b""):
            digest.update(block)
    return digest.hexdigest()


def state_design(frame: pd.DataFrame, model: str, states: list[str]) -> tuple[np.ndarray, list[str]]:
    if not states or states != sorted(set(states)) or not set(frame.state.astype(str)) <= set(states):
        raise ValueError("state-trend training/support identity invalid")
    x, original_names = design(frame, model)
    time = x[:, 0]
    assigned = frame.state.astype(str).to_numpy()
    slopes = np.column_stack([(assigned == state).astype(float) * time for state in states])
    result = np.column_stack([slopes, x[:, 1:]])
    names = [f"state_trend_{state}" for state in states] + original_names[1:]
    if result.shape != (len(frame), len(names)) or not np.isfinite(result).all():
        raise ValueError("state-trend design nonfinite or misdimensioned")
    return result, names


def score_split(train: pd.DataFrame, test: pd.DataFrame, model: str) -> tuple[np.ndarray, dict]:
    states = sorted(set(train.state.astype(str)))
    train_x, names = state_design(train, model, states)
    test_x, test_names = state_design(test, model, states)
    if names != test_names:
        raise ValueError("state-trend train/test columns differ")
    y = np.log(train.yield_bu_acre.to_numpy(dtype=float))
    fit = fit_within(y, train_x, train.county_geoid.to_numpy())
    estimate = predict(fit, test_x, test.county_geoid.to_numpy())
    return estimate, {"states": states, "rank": fit["rank"],
                      "condition": fit["condition"],
                      "max_county_mean_residual": fit["max_county_mean_residual"],
                      "normal_equation_relative_error": fit["normal_equation_relative_error"]}


def evaluate_crop(panel: pd.DataFrame, crop: str) -> dict:
    frame = panel.loc[panel.outcome_crop.eq(crop)].copy()
    train = frame.loc[frame.harvest_year.between(1981, 2019)].copy()
    terminal = frame.loc[frame.harvest_year.between(2020, 2025)].copy()
    terminal = terminal.loc[terminal.county_geoid.isin(set(train.county_geoid))].copy()
    earlier = frame.loc[frame.harvest_year.between(1981, 2010)].copy()
    blocked = frame.loc[frame.harvest_year.between(2012, 2019)].copy()
    blocked = blocked.loc[blocked.county_geoid.isin(set(earlier.county_geoid))].copy()
    if terminal.harvest_year.nunique() != 6 or blocked.harvest_year.nunique() != 8:
        raise ValueError("state-trend terminal or historical-blocked support incomplete")
    target = np.log(terminal.yield_bu_acre.to_numpy(dtype=float))
    blocked_target = np.log(blocked.yield_bu_acre.to_numpy(dtype=float))
    predictions, scores, diagnostics, historical = {}, {}, {}, {}
    for model in MODELS:
        prediction, fit_diagnostic = score_split(train, terminal, model)
        blocked_prediction, blocked_fit_diagnostic = score_split(earlier, blocked, model)
        predictions[model] = prediction
        scores[model] = metrics(target, prediction)
        diagnostics[model] = {"full_training": fit_diagnostic,
                              "historical_blocked_training": blocked_fit_diagnostic}
        historical[model] = metrics(blocked_target, blocked_prediction)
    years = terminal.harvest_year.to_numpy()
    annual = {str(year): {model: metrics(target[years == year], predictions[model][years == year])
                          for model in MODELS} for year in range(2020, 2026)}
    states = terminal.state.to_numpy(dtype=str)
    contrasts = {
        "quantity_vs_no_weather": bootstrap_rmse_difference(
            target, predictions["no_weather"], predictions["quantity_temperature"],
            states, seed=20260918),
        "pattern_vs_quantity": bootstrap_rmse_difference(
            target, predictions["quantity_temperature"],
            predictions["quantity_temperature_pattern"], states, seed=20260919),
    }
    return {"crop": crop, "historical_rows": len(train), "terminal_rows": len(terminal),
            "historical_blocked_rows": len(blocked),
            "terminal_scores": scores, "annual_scores": annual,
            "historical_blocked_scores": historical,
            "fits": diagnostics, "paired_conditional_uncertainty": contrasts,
            "post_result_sensitivity": True, "causal_or_scc_result": False}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    out = args.out_dir.resolve()
    if out.exists() or not out.is_relative_to(ROOT / "data/interim"):
        raise ValueError("fresh ignored state-trend sensitivity output required")
    primary = json.loads(PRIMARY.read_text())
    validation = json.loads(PRIMARY_VALIDATION.read_text())
    if (primary["status"] != "us_county_average_predictive_benchmark_not_causal" or
        primary["panel_sha256"] != sha(PANEL) or
        validation["status"] != "independent_us_county_average_prediction_validated" or
        validation["prediction_sha256"] != sha(PRIMARY)):
        raise ValueError("validated primary benchmark input unavailable")
    panel = pd.read_parquet(PANEL)
    crops = {crop: evaluate_crop(panel, crop) for crop in ("corn_grain", "soybeans")}
    for crop, record in crops.items():
        if record["terminal_rows"] != primary["crops"][crop]["terminal_rows_scored"]:
            raise ValueError("state-trend terminal support differs from primary benchmark")
    result = {"status": "post_result_us_state_trend_sensitivity_not_causal",
              "panel_sha256": sha(PANEL), "primary_prediction_sha256": sha(PRIMARY),
              "primary_validation_sha256": sha(PRIMARY_VALIDATION),
              "protocol_sha256": sha(PROTOCOL), "code_sha256": sha(Path(__file__)),
              "crops": crops, "climate_change_attribution_performed": False,
              "economic_damage_or_scc_estimated": False}
    out.mkdir(parents=True)
    (out / "result.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({crop: {model: record["terminal_scores"][model]["rmse_log_yield"]
                             for model in MODELS} for crop, record in crops.items()}))


if __name__ == "__main__":
    main()
