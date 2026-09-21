#!/usr/bin/env python3
"""Post-result predictive PDSI alternative on exact U.S. county support."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from estimate_us_county_average_terminal_prediction import (
    bootstrap_rmse_difference, design, fit_within, metrics, predict,
)
from evaluate_us_county_average_state_trends import state_design

ROOT = Path(__file__).resolve().parents[1]
PDSI_PANEL = ROOT / "data/interim/us_county/noaa_county_average_pdsi_competitor_panel_20260916/panel_pdsi.parquet"
PDSI_RECEIPT = ROOT / "data/interim/us_county/noaa_county_average_pdsi_competitor_panel_20260916/result.json"
MAIN_PANEL = ROOT / "data/interim/us_county/noaa_county_average_nass_panel_20260916/panel.parquet"
PRIMARY = ROOT / "data/interim/us_county/noaa_county_average_prediction_20260916/result.json"
STATE_PRIMARY = ROOT / "data/interim/us_county/noaa_county_average_state_trend_sensitivity_20260916/result.json"
PROTOCOL = ROOT / "US_COUNTY_AVERAGE_PDSI_COMPETING_SENSITIVITY_20260916.md"
MODELS = ("rain_quantity_temperature", "rain_pattern_temperature",
          "pdsi_mean_temperature", "pdsi_mean_min_temperature")


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(2**20), b""):
            digest.update(block)
    return digest.hexdigest()


def model_matrix(frame: pd.DataFrame, model: str, trend: str, states: list[str]) -> tuple[np.ndarray, list[str]]:
    if model not in MODELS or trend not in ("common", "state"):
        raise ValueError("unregistered PDSI competitor model/trend")
    if model.startswith("rain_"):
        source_model = ("quantity_temperature" if model == "rain_quantity_temperature"
                        else "quantity_temperature_pattern")
        if trend == "common":
            return design(frame, source_model)
        return state_design(frame, source_model, states)
    time = (frame.harvest_year.to_numpy(dtype=float) - 2000.0) / 10.0
    if trend == "common":
        terms = [time]
        names = ["year_minus_2000_per_decade"]
    else:
        if states != sorted(set(states)) or not set(frame.state.astype(str)) <= set(states):
            raise ValueError("PDSI state-trend identities differ")
        observed = frame.state.astype(str).to_numpy()
        terms = [(observed == state).astype(float) * time for state in states]
        names = [f"state_trend_{state}" for state in states]
    mean = frame.pdsi_season_mean.to_numpy(dtype=float) / 5.0
    terms.extend([mean, mean**2,
                  frame.tmean_c.to_numpy(dtype=float) / 10.0,
                  frame.tmax_exceedance_29c_c_days.to_numpy(dtype=float) / 100.0])
    names.extend(["pdsi_season_mean_per_5", "pdsi_season_mean_per_5_squared",
                  "tmean_c_per_10", "tmax_exceedance_29c_c_days_per_100"])
    if model == "pdsi_mean_min_temperature":
        terms.append(frame.pdsi_season_min.to_numpy(dtype=float) / 5.0)
        names.append("pdsi_season_min_per_5")
    matrix = np.column_stack(terms)
    if matrix.shape != (len(frame), len(names)) or not np.isfinite(matrix).all():
        raise ValueError("PDSI competitor has nonfinite/misdimensioned design")
    return matrix, names


def fit_forecast(train: pd.DataFrame, test: pd.DataFrame, model: str, trend: str) -> tuple[np.ndarray, dict]:
    states = sorted(set(train.state.astype(str)))
    x, terms = model_matrix(train, model, trend, states)
    z, test_terms = model_matrix(test, model, trend, states)
    if terms != test_terms:
        raise ValueError("PDSI competitor train/test terms differ")
    y = np.log(train.yield_bu_acre.to_numpy(dtype=float))
    fitted = fit_within(y, x, train.county_geoid.to_numpy())
    forecast = predict(fitted, z, test.county_geoid.to_numpy())
    return forecast, {"terms": terms, "beta": [float(value) for value in fitted["beta"]],
                      "rank": fitted["rank"], "condition": fitted["condition"],
                      "max_county_mean_residual": fitted["max_county_mean_residual"],
                      "normal_equation_relative_error": fitted["normal_equation_relative_error"]}


def check_original_score(crop: str, trend: str, model: str, score: dict,
                         primary: dict, state_primary: dict) -> None:
    source = primary if trend == "common" else state_primary
    equivalent = ("quantity_temperature" if model == "rain_quantity_temperature"
                  else "quantity_temperature_pattern")
    reported = source["crops"][crop]["terminal_scores"][equivalent]
    for key in ("n", "rmse_log_yield", "mae_log_yield", "mean_error_log_yield"):
        if abs(score[key] - reported[key]) > 1e-9:
            raise ValueError(f"PDSI same-support rain-model score differs from validated primary: {crop}/{trend}/{key}")


def evaluate_crop(panel: pd.DataFrame, crop: str, trend: str,
                  primary: dict, state_primary: dict) -> dict:
    frame = panel.loc[panel.outcome_crop.eq(crop)].copy()
    train = frame.loc[frame.harvest_year.between(1981, 2019)].copy()
    terminal = frame.loc[frame.harvest_year.between(2020, 2025)].copy()
    terminal = terminal.loc[terminal.county_geoid.isin(set(train.county_geoid))].copy()
    early = frame.loc[frame.harvest_year.between(1981, 2010)].copy()
    blocked = frame.loc[frame.harvest_year.between(2012, 2019)].copy()
    blocked = blocked.loc[blocked.county_geoid.isin(set(early.county_geoid))].copy()
    if terminal.harvest_year.nunique() != 6 or blocked.harvest_year.nunique() != 8:
        raise ValueError("PDSI competitor common-support years incomplete")
    truth = np.log(terminal.yield_bu_acre.to_numpy(dtype=float))
    blocked_truth = np.log(blocked.yield_bu_acre.to_numpy(dtype=float))
    scores, fits, forecasts, blocked_scores = {}, {}, {}, {}
    for model in MODELS:
        forecast, fit = fit_forecast(train, terminal, model, trend)
        historical_forecast, _ = fit_forecast(early, blocked, model, trend)
        scores[model] = metrics(truth, forecast)
        blocked_scores[model] = metrics(blocked_truth, historical_forecast)
        fits[model] = fit
        forecasts[model] = forecast
        if model.startswith("rain_"):
            check_original_score(crop, trend, model, scores[model], primary, state_primary)
    years = terminal.harvest_year.to_numpy()
    annual = {str(year): {model: metrics(truth[years == year], forecasts[model][years == year])
                          for model in MODELS} for year in range(2020, 2026)}
    states = terminal.state.to_numpy(dtype=str)
    contrasts = {
        "pdsi_mean_vs_rain_quantity": bootstrap_rmse_difference(
            truth, forecasts["rain_quantity_temperature"], forecasts["pdsi_mean_temperature"],
            states, seed=20260920),
        "pdsi_mean_vs_rain_pattern": bootstrap_rmse_difference(
            truth, forecasts["rain_pattern_temperature"], forecasts["pdsi_mean_temperature"],
            states, seed=20260921),
        "pdsi_min_extension_vs_pdsi_mean": bootstrap_rmse_difference(
            truth, forecasts["pdsi_mean_temperature"], forecasts["pdsi_mean_min_temperature"],
            states, seed=20260922),
    }
    return {"crop": crop, "trend": trend, "historical_rows": len(train),
            "terminal_rows": len(terminal), "blocked_rows": len(blocked),
            "fits": fits, "terminal_scores": scores, "historical_blocked_scores": blocked_scores,
            "annual_scores": annual, "paired_conditional_uncertainty": contrasts,
            "post_result_competing_moisture_sensitivity": True,
            "causal_or_scc_result": False}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    out = args.out_dir.resolve()
    if out.exists() or not out.is_relative_to(ROOT / "data/interim"):
        raise ValueError("fresh ignored PDSI comparison output required")
    source = json.loads(PDSI_RECEIPT.read_text())
    primary = json.loads(PRIMARY.read_text())
    state_primary = json.loads(STATE_PRIMARY.read_text())
    if (source["status"] != "exact_support_us_pdsi_competitor_panel_built" or
        source["panel_sha256"] != sha(PDSI_PANEL) or
        source["main_panel_sha256"] != sha(MAIN_PANEL) or
        source["protocol_sha256"] != sha(PROTOCOL) or
        primary["panel_sha256"] != sha(MAIN_PANEL) or
        state_primary["panel_sha256"] != sha(MAIN_PANEL)):
        raise ValueError("PDSI competitor data/source/protocol identity invalid")
    panel = pd.read_parquet(PDSI_PANEL)
    reference = pd.read_parquet(MAIN_PANEL, columns=["county_geoid", "outcome_crop", "harvest_year"])
    if not panel[["county_geoid", "outcome_crop", "harvest_year"]].equals(reference):
        raise ValueError("PDSI competitor row order/keys differ from primary panel")
    crops = {trend: {crop: evaluate_crop(panel, crop, trend, primary, state_primary)
                     for crop in ("corn_grain", "soybeans")}
             for trend in ("common", "state")}
    result = {"status": "post_result_pdsi_competing_prediction_not_causal",
              "trend_specifications": ["common", "state"], "models": list(MODELS),
              "crops": crops, "pdsi_panel_sha256": sha(PDSI_PANEL),
              "pdsi_panel_receipt_sha256": sha(PDSI_RECEIPT),
              "primary_result_sha256": sha(PRIMARY), "state_trend_result_sha256": sha(STATE_PRIMARY),
              "protocol_sha256": sha(PROTOCOL), "code_sha256": sha(Path(__file__)),
              "climate_change_attribution_performed": False,
              "economic_damage_or_scc_estimated": False}
    out.mkdir(parents=True)
    (out / "result.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({trend: {crop: {model: record["terminal_scores"][model]["rmse_log_yield"]
                                    for model in MODELS} for crop, record in crops[trend].items()}
                      for trend in crops}))


if __name__ == "__main__":
    main()
