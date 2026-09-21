#!/usr/bin/env python3
"""Prespecified U.S. county FE prediction ladder; not a causal/SCC estimate."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PANEL_DIR = ROOT / "data/interim/us_county/noaa_county_average_nass_panel_20260916"
PROTOCOL = ROOT / "US_COUNTY_AVERAGE_RESPONSE_PREANALYSIS_20260916.md"
MODELS = ("no_weather", "quantity_temperature", "quantity_temperature_pattern")


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(2**20), b""):
            digest.update(block)
    return digest.hexdigest()


def row_dot(matrix: np.ndarray, vector: np.ndarray) -> np.ndarray:
    """Checked row-wise dot products for the small fixed-effect designs."""
    values = np.asarray(matrix, dtype="float64")
    weights = np.asarray(vector, dtype="float64")
    if (values.ndim != 2 or weights.ndim != 1 or
            values.shape[1] != len(weights) or
            not np.isfinite(values).all() or not np.isfinite(weights).all()):
        raise ValueError("fixed-effect row-dot inputs invalid")
    result = np.sum(values * weights[None, :], axis=1)
    if not np.isfinite(result).all():
        raise ValueError("fixed-effect row-dot result nonfinite")
    return result


def design(frame: pd.DataFrame, model: str) -> tuple[np.ndarray, list[str]]:
    if model not in MODELS:
        raise ValueError("unregistered prediction model")
    time = (frame.harvest_year.to_numpy(dtype="float64") - 2000.0) / 10.0
    columns = [time]
    names = ["year_minus_2000_per_decade"]
    if model != "no_weather":
        rain = frame.precip_mm.to_numpy(dtype="float64") / 1000.0
        columns.extend([rain, rain**2,
                        frame.tmean_c.to_numpy(dtype="float64") / 10.0,
                        frame.tmax_exceedance_29c_c_days.to_numpy(dtype="float64") / 100.0])
        names.extend(["precip_mm_per_1000", "precip_mm_per_1000_squared",
                      "tmean_c_per_10", "tmax_exceedance_29c_c_days_per_100"])
    if model == "quantity_temperature_pattern":
        for source, label in (("wet_days_ge_1mm", "wet_days_ge_1mm_per_100"),
                              ("cdd_max_days", "cdd_max_days_per_100"),
                              ("rx5day_mm", "rx5day_mm_per_100")):
            columns.append(frame[source].to_numpy(dtype="float64") / 100.0)
            names.append(label)
        for stage in (1, 2):
            name = f"stage{stage}_precip_share"
            columns.append(frame[name].to_numpy(dtype="float64"))
            names.append(name)
    matrix = np.column_stack(columns)
    if matrix.shape != (len(frame), len(names)) or not np.isfinite(matrix).all():
        raise ValueError("nonfinite or misdimensioned prespecified response design")
    return matrix, names


def fit_within(y: np.ndarray, x: np.ndarray, groups: np.ndarray) -> dict:
    """OLS county fixed effects through exact within transformation."""
    if len(y) != len(x) or len(groups) != len(y) or len(y) <= x.shape[1] + 1:
        raise ValueError("invalid fixed-effect fit dimensions")
    counties, inverse = np.unique(groups.astype(str), return_inverse=True)
    counts = np.bincount(inverse).astype("float64")
    ymeans = np.bincount(inverse, weights=y) / counts
    xmeans = np.column_stack([
        np.bincount(inverse, weights=x[:, column]) / counts
        for column in range(x.shape[1])])
    xwithin = x - xmeans[inverse]
    ywithin = y - ymeans[inverse]
    beta, _, rank, singular = np.linalg.lstsq(xwithin, ywithin, rcond=None)
    condition = float(singular[0] / singular[-1]) if singular[-1] > 0 else float("inf")
    if rank != x.shape[1] or not np.isfinite(beta).all() or not np.isfinite(condition) or condition > 1e9:
        raise ValueError("registered weather design is rank deficient or poorly conditioned")
    alpha = ymeans - row_dot(xmeans, beta)
    residual = y - (alpha[inverse] + row_dot(x, beta))
    max_county_mean_residual = float(np.max(np.abs(np.bincount(inverse, weights=residual) / counts)))
    normal_equation_relative_error = float(
        np.max(np.abs(np.sum(xwithin * residual[:, None], axis=0))) /
        (1.0 + np.linalg.norm(xwithin) * np.linalg.norm(residual)))
    if max_county_mean_residual > 1e-9 or normal_equation_relative_error > 1e-8:
        raise ValueError("county FE OLS residual orthogonality check failed")
    return {"counties": counties, "alpha": alpha, "beta": beta, "condition": condition,
            "rank": int(rank), "within_rmse": float(np.sqrt(np.mean(residual**2))),
            "max_county_mean_residual": max_county_mean_residual,
            "normal_equation_relative_error": normal_equation_relative_error}


def predict(fitted: dict, x: np.ndarray, groups: np.ndarray) -> np.ndarray:
    counties = fitted["counties"]
    index = np.searchsorted(counties, groups.astype(str))
    if (index >= len(counties)).any() or not np.array_equal(counties[index], groups.astype(str)):
        raise ValueError("terminal county has no historical fixed effect")
    return fitted["alpha"][index] + row_dot(x, fitted["beta"])


def metrics(actual: np.ndarray, forecast: np.ndarray) -> dict:
    errors = forecast - actual
    return {"n": len(errors), "rmse_log_yield": float(np.sqrt(np.mean(errors**2))),
            "mae_log_yield": float(np.mean(np.abs(errors))),
            "mean_error_log_yield": float(np.mean(errors))}


def bootstrap_rmse_difference(
    actual: np.ndarray, left: np.ndarray, right: np.ndarray, states: np.ndarray,
    *, seed: int, replicates: int = 2000,
) -> dict:
    """Conditional paired state-resampling of two fixed terminal forecasts."""
    unique = np.unique(states.astype(str))
    counts = np.asarray([np.sum(states == state) for state in unique], dtype="float64")
    left_sse = np.asarray([np.sum((left[states == state] - actual[states == state])**2)
                           for state in unique])
    right_sse = np.asarray([np.sum((right[states == state] - actual[states == state])**2)
                            for state in unique])
    rng = np.random.default_rng(seed)
    sampled = rng.integers(0, len(unique), size=(replicates, len(unique)))
    n = counts[sampled].sum(axis=1)
    diff = np.sqrt(left_sse[sampled].sum(axis=1) / n) - np.sqrt(right_sse[sampled].sum(axis=1) / n)
    return {"difference_definition": "left_RMSE_minus_right_RMSE_log_yield",
            "point_difference": metrics(actual, left)["rmse_log_yield"] - metrics(actual, right)["rmse_log_yield"],
            "conditional_state_bootstrap_percentiles_2p5_50_97p5":
                [float(value) for value in np.quantile(diff, [0.025, 0.5, 0.975])],
            "states": len(unique), "replicates": replicates, "seed": seed,
            "caveat": "conditional on fitted forecasts; six terminal years and model-selection uncertainty not resampled"}


def one_crop(frame: pd.DataFrame, crop: str) -> dict:
    data = frame.loc[frame.outcome_crop.eq(crop)].copy()
    train = data.loc[data.harvest_year.between(1981, 2019)].copy()
    recent = data.loc[data.harvest_year.between(2020, 2025)].copy()
    if train.empty or recent.empty or not train.period.eq("historical").all() or not recent.period.eq("terminal").all():
        raise ValueError("historical or terminal county crop panel invalid")
    train_counties = set(train.county_geoid)
    unseen = recent.loc[~recent.county_geoid.isin(train_counties)]
    test = recent.loc[recent.county_geoid.isin(train_counties)].copy()
    if test.empty or test.harvest_year.nunique() != 6:
        raise ValueError("common-history terminal crop years incomplete")
    y_train = np.log(train.yield_bu_acre.to_numpy(dtype="float64"))
    y_test = np.log(test.yield_bu_acre.to_numpy(dtype="float64"))
    if not np.isfinite(y_train).all() or not np.isfinite(y_test).all():
        raise ValueError("invalid positive NASS log-yield outcome")
    fits, forecasts, scores = {}, {}, {}
    for model in MODELS:
        x_train, names = design(train, model)
        x_test, names_test = design(test, model)
        if names_test != names:
            raise ValueError("historical/terminal feature terms differ")
        support = {name: {"historical_min": float(np.min(x_train[:, index])),
                          "historical_max": float(np.max(x_train[:, index])),
                          "terminal_rows_outside_historical_min_max": int(np.sum(
                              (x_test[:, index] < np.min(x_train[:, index])) |
                              (x_test[:, index] > np.max(x_train[:, index]))))}
                   for index, name in enumerate(names)}
        fitted = fit_within(y_train, x_train, train.county_geoid.to_numpy())
        prediction = predict(fitted, x_test, test.county_geoid.to_numpy())
        forecasts[model] = prediction
        fits[model] = {"terms": names, "beta": [float(value) for value in fitted["beta"]],
                       "rank": fitted["rank"], "condition": fitted["condition"],
                       "historical_within_rmse_log_yield": fitted["within_rmse"],
                       "max_county_mean_residual": fitted["max_county_mean_residual"],
                       "normal_equation_relative_error": fitted["normal_equation_relative_error"],
                       "terminal_predictor_support": support}
        scores[model] = metrics(y_test, prediction)
    annual = {}
    test_year = test.harvest_year.to_numpy()
    for year in range(2020, 2026):
        selected = test_year == year
        annual[str(year)] = {model: metrics(y_test[selected], forecasts[model][selected])
                             for model in MODELS}
    states = test.state.to_numpy(dtype=str)
    contrasts = {
        "quantity_vs_no_weather": bootstrap_rmse_difference(
            y_test, forecasts["no_weather"], forecasts["quantity_temperature"],
            states, seed=20260916),
        "pattern_vs_quantity": bootstrap_rmse_difference(
            y_test, forecasts["quantity_temperature"],
            forecasts["quantity_temperature_pattern"], states, seed=20260917),
    }
    early = data.loc[data.harvest_year.between(1981, 2010)].copy()
    diagnostic = data.loc[data.harvest_year.between(2012, 2019)].copy()
    diagnostic = diagnostic.loc[diagnostic.county_geoid.isin(set(early.county_geoid))].copy()
    if early.empty or diagnostic.empty or diagnostic.harvest_year.nunique() != 8:
        raise ValueError("historical blocked diagnostic support incomplete")
    y_early = np.log(early.yield_bu_acre.to_numpy(dtype="float64"))
    y_diagnostic = np.log(diagnostic.yield_bu_acre.to_numpy(dtype="float64"))
    blocked_scores = {}
    for model in MODELS:
        early_x, early_names = design(early, model)
        diagnostic_x, diagnostic_names = design(diagnostic, model)
        if early_names != diagnostic_names:
            raise ValueError("historical blocked model terms differ")
        early_fit = fit_within(y_early, early_x, early.county_geoid.to_numpy())
        blocked_scores[model] = metrics(
            y_diagnostic,
            predict(early_fit, diagnostic_x, diagnostic.county_geoid.to_numpy()))
    return {"crop": crop, "historical_rows": len(train),
            "historical_counties": train.county_geoid.nunique(),
            "terminal_rows_before_historical_county_filter": len(recent),
            "terminal_rows_excluded_unseen_county": len(unseen),
            "terminal_rows_scored": len(test),
            "terminal_counties_scored": test.county_geoid.nunique(),
            "fits": fits, "terminal_scores": scores, "annual_scores": annual,
            "historical_blocked_train_years": [1981, 2010],
            "historical_blocked_purged_year": 2011,
            "historical_blocked_test_years": [2012, 2019],
            "historical_blocked_test_counties": diagnostic.county_geoid.nunique(),
            "historical_blocked_scores": blocked_scores,
            "paired_conditional_uncertainty": contrasts,
            "causal_or_scc_result": False}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    out = args.out_dir.resolve()
    if out.exists() or not out.is_relative_to(ROOT / "data/interim"):
        raise ValueError("fresh ignored prediction output required")
    panel_path = PANEL_DIR / "panel.parquet"
    panel_receipt = json.loads((PANEL_DIR / "result.json").read_text())
    if (panel_receipt["status"] != "county_average_nass_panel_assembled_no_response" or
        panel_receipt["panel_sha256"] != sha(panel_path) or
        panel_receipt["preanalysis_protocol_sha256"] != sha(PROTOCOL)):
        raise ValueError("fixed U.S. response input/protocol identity invalid")
    panel = pd.read_parquet(panel_path)
    if panel.duplicated(["outcome_crop", "county_geoid", "harvest_year"]).any():
        raise ValueError("U.S. response panel duplicate key")
    results = {crop: one_crop(panel, crop) for crop in ("corn_grain", "soybeans")}
    result = {"status": "us_county_average_predictive_benchmark_not_causal",
              "models": list(MODELS), "training_years": [1981, 2019],
              "terminal_years": [2020, 2025], "crops": results,
              "panel_sha256": sha(panel_path), "panel_receipt_sha256": sha(PANEL_DIR / "result.json"),
              "preanalysis_protocol_sha256": sha(PROTOCOL), "code_sha256": sha(Path(__file__)),
              "climate_change_attribution_performed": False,
              "economic_damage_or_scc_estimated": False}
    out.mkdir(parents=True)
    (out / "result.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({crop: {model: results[crop]["terminal_scores"][model]["rmse_log_yield"]
                             for model in MODELS} for crop in results}))


if __name__ == "__main__":
    main()
