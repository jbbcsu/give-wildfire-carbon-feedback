#!/usr/bin/env python3
"""Independent pandas within-estimator reconstruction of U.S. score ledger."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PANEL = ROOT / "data/interim/us_county/noaa_county_average_nass_panel_20260916/panel.parquet"
PREDICTION = ROOT / "data/interim/us_county/noaa_county_average_prediction_20260916/result.json"
MODELS = ("no_weather", "quantity_temperature", "quantity_temperature_pattern")


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(2**20), b""):
            h.update(block)
    return h.hexdigest()


def row_dot(matrix: np.ndarray, vector: np.ndarray) -> np.ndarray:
    """Return row-wise dot products with explicit finite/dimension checks.

    The project NumPy/BLAS build can leave floating-point status flags set by
    ``lstsq`` and then emit spurious divide/overflow warnings on a subsequent
    small ``@`` operation even when all operands and results are ordinary
    finite values.  Explicit multiplication and summation is independent of
    that matrix-multiply path and is ample for the at-most-ten-column audit
    design.
    """
    values = np.asarray(matrix, dtype="float64")
    weights = np.asarray(vector, dtype="float64")
    if (values.ndim != 2 or weights.ndim != 1 or
            values.shape[1] != len(weights) or
            not np.isfinite(values).all() or not np.isfinite(weights).all()):
        raise ValueError("independent row-dot inputs invalid")
    result = np.sum(values * weights[None, :], axis=1)
    if not np.isfinite(result).all():
        raise ValueError("independent row-dot result nonfinite")
    return result


def independent_design(frame: pd.DataFrame, model: str) -> pd.DataFrame:
    x = pd.DataFrame(index=frame.index)
    x["year_minus_2000_per_decade"] = (frame["harvest_year"].astype(float) - 2000) / 10
    if model in ("quantity_temperature", "quantity_temperature_pattern"):
        x["precip_mm_per_1000"] = frame["precip_mm"].astype(float) / 1000
        x["precip_mm_per_1000_squared"] = x["precip_mm_per_1000"] ** 2
        x["tmean_c_per_10"] = frame["tmean_c"].astype(float) / 10
        x["tmax_exceedance_29c_c_days_per_100"] = frame["tmax_exceedance_29c_c_days"].astype(float) / 100
    if model == "quantity_temperature_pattern":
        x["wet_days_ge_1mm_per_100"] = frame["wet_days_ge_1mm"].astype(float) / 100
        x["cdd_max_days_per_100"] = frame["cdd_max_days"].astype(float) / 100
        x["rx5day_mm_per_100"] = frame["rx5day_mm"].astype(float) / 100
        x["stage1_precip_share"] = frame["stage1_precip_share"].astype(float)
        x["stage2_precip_share"] = frame["stage2_precip_share"].astype(float)
    if model not in MODELS or x.isna().any().any():
        raise ValueError("independent registered design invalid")
    return x


def fit_score(train: pd.DataFrame, test: pd.DataFrame, model: str) -> tuple[dict, int]:
    x = independent_design(train, model)
    z = independent_design(test, model)
    y = np.log(train["yield_bu_acre"].to_numpy(dtype=float))
    label = train["county_geoid"].astype(str).reset_index(drop=True)
    x = x.reset_index(drop=True)
    y_series = pd.Series(y)
    x_mean = x.groupby(label).transform("mean")
    y_mean = y_series.groupby(label).transform("mean")
    beta, _, rank, _ = np.linalg.lstsq(
        (x - x_mean).to_numpy(dtype=float),
        (y_series - y_mean).to_numpy(dtype=float), rcond=None)
    if rank != len(x.columns):
        raise ValueError("independent within OLS rank failed")
    group_x = x.groupby(label).mean()
    group_y = y_series.groupby(label).mean()
    alpha = group_y - row_dot(group_x.to_numpy(dtype="float64"), beta)
    keys = test["county_geoid"].astype(str).to_numpy()
    if not set(keys) <= set(alpha.index):
        raise ValueError("independent score has unseen county")
    forecast = alpha.reindex(keys).to_numpy() + row_dot(z.to_numpy(dtype="float64"), beta)
    truth = np.log(test["yield_bu_acre"].to_numpy(dtype=float))
    residual = forecast - truth
    if not np.isfinite(residual).all():
        raise ValueError("independent predictive residual nonfinite")
    return {"n": len(test), "rmse_log_yield": float(np.sqrt(np.mean(residual**2))),
            "mae_log_yield": float(np.mean(np.abs(residual))),
            "mean_error_log_yield": float(np.mean(residual)),
            "beta": [float(value) for value in beta],
            "names": list(x.columns)}, len(alpha)


def reconcile(actual: float, expected: float, label: str, tolerance: float = 1e-8) -> None:
    if not np.isfinite(actual) or abs(actual - expected) > tolerance:
        raise ValueError(f"independent U.S. score mismatch: {label}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    out = args.out_dir.resolve()
    if out.exists() or not out.is_relative_to(ROOT / "data/interim"):
        raise ValueError("fresh ignored independent score-validation output required")
    reported = json.loads(PREDICTION.read_text())
    if reported["status"] != "us_county_average_predictive_benchmark_not_causal" or sha(PANEL) != reported["panel_sha256"]:
        raise ValueError("registered predictive result or panel identity invalid")
    panel = pd.read_parquet(PANEL)
    checks = 0
    for crop in ("corn_grain", "soybeans"):
        crop_frame = panel.loc[panel.outcome_crop.eq(crop)].copy()
        training = crop_frame.loc[crop_frame.harvest_year.between(1981, 2019)]
        recent = crop_frame.loc[crop_frame.harvest_year.between(2020, 2025)]
        recent = recent.loc[recent.county_geoid.isin(set(training.county_geoid))]
        earlier = crop_frame.loc[crop_frame.harvest_year.between(1981, 2010)]
        diagnostic = crop_frame.loc[crop_frame.harvest_year.between(2012, 2019)]
        diagnostic = diagnostic.loc[diagnostic.county_geoid.isin(set(earlier.county_geoid))]
        for model in MODELS:
            score, n_counties = fit_score(training, recent, model)
            target = reported["crops"][crop]
            if score["n"] != target["terminal_scores"][model]["n"] or n_counties != target["historical_counties"]:
                raise ValueError("independent common-support count changed")
            if score["names"] != target["fits"][model]["terms"]:
                raise ValueError("independent model columns differ")
            for value, expected in zip(score["beta"], target["fits"][model]["beta"]):
                reconcile(value, expected, "coefficient")
                checks += 1
            for field in ("rmse_log_yield", "mae_log_yield", "mean_error_log_yield"):
                reconcile(score[field], target["terminal_scores"][model][field], field)
                checks += 1
            blocked, _ = fit_score(earlier, diagnostic, model)
            if blocked["n"] != target["historical_blocked_scores"][model]["n"]:
                raise ValueError("independent blocked-support count changed")
            for field in ("rmse_log_yield", "mae_log_yield", "mean_error_log_yield"):
                reconcile(blocked[field], target["historical_blocked_scores"][model][field],
                          "blocked " + field)
                checks += 1
    result = {"status": "independent_us_county_average_prediction_validated",
              "numeric_checks": checks, "crops": ["corn_grain", "soybeans"],
              "models": list(MODELS), "prediction_sha256": sha(PREDICTION),
              "panel_sha256": sha(PANEL), "code_sha256": sha(Path(__file__)),
              "climate_change_attribution_performed": False,
              "economic_damage_or_scc_estimated": False}
    out.mkdir(parents=True)
    (out / "result.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"status": result["status"], "numeric_checks": checks}))


if __name__ == "__main__":
    main()
