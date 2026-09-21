#!/usr/bin/env python3
"""Independent within-estimator reconstruction of all PDSI comparison scores."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from validate_us_county_average_terminal_prediction import independent_design, row_dot

ROOT = Path(__file__).resolve().parents[1]
PANEL = ROOT / "data/interim/us_county/noaa_county_average_pdsi_competitor_panel_20260916/panel_pdsi.parquet"
REPORTED = ROOT / "data/interim/us_county/noaa_county_average_pdsi_competitor_prediction_20260916/result.json"
MODELS = ("rain_quantity_temperature", "rain_pattern_temperature",
          "pdsi_mean_temperature", "pdsi_mean_min_temperature")


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(2**20), b""):
            h.update(block)
    return h.hexdigest()


def matrix(frame: pd.DataFrame, model: str, trend: str, states: list[str]) -> pd.DataFrame:
    if model not in MODELS or trend not in ("common", "state"):
        raise ValueError("independent PDSI model/trend identity invalid")
    if model.startswith("rain_"):
        equivalent = ("quantity_temperature" if model == "rain_quantity_temperature"
                      else "quantity_temperature_pattern")
        x = independent_design(frame, equivalent).reset_index(drop=True)
    else:
        x = pd.DataFrame(index=range(len(frame)))
        x["year_minus_2000_per_decade"] = (frame.harvest_year.to_numpy(dtype=float) - 2000) / 10
        mean = frame.pdsi_season_mean.to_numpy(dtype=float) / 5
        x["pdsi_season_mean_per_5"] = mean
        x["pdsi_season_mean_per_5_squared"] = mean**2
        x["tmean_c_per_10"] = frame.tmean_c.to_numpy(dtype=float) / 10
        x["tmax_exceedance_29c_c_days_per_100"] = frame.tmax_exceedance_29c_c_days.to_numpy(dtype=float) / 100
        if model == "pdsi_mean_min_temperature":
            x["pdsi_season_min_per_5"] = frame.pdsi_season_min.to_numpy(dtype=float) / 5
    if trend == "state":
        time = x.pop("year_minus_2000_per_decade")
        assigned = frame.state.astype(str).to_numpy()
        slopes = pd.DataFrame({f"state_trend_{state}": time.to_numpy() * (assigned == state)
                               for state in states})
        x = pd.concat([slopes, x], axis=1)
    if not np.isfinite(x.to_numpy(dtype=float)).all():
        raise ValueError("independent PDSI competitor design nonfinite")
    return x


def score(train: pd.DataFrame, test: pd.DataFrame, model: str, trend: str) -> dict:
    states = sorted(set(train.state.astype(str)))
    if not set(test.state.astype(str)) <= set(states):
        raise ValueError("independent PDSI test has unseen state")
    x, z = matrix(train, model, trend, states), matrix(test, model, trend, states)
    if list(x.columns) != list(z.columns):
        raise ValueError("independent PDSI train/test columns differ")
    labels = train.county_geoid.astype(str).reset_index(drop=True)
    y = pd.Series(np.log(train.yield_bu_acre.to_numpy(dtype=float)))
    xm = x.groupby(labels).transform("mean")
    ym = y.groupby(labels).transform("mean")
    beta, _, rank, _ = np.linalg.lstsq((x - xm).to_numpy(), (y - ym).to_numpy(), rcond=None)
    if rank != x.shape[1]:
        raise ValueError("independent PDSI within fit rank failure")
    gx = x.groupby(labels).mean()
    gy = y.groupby(labels).mean()
    alpha = gy - row_dot(gx.to_numpy(dtype="float64"), beta)
    keys = test.county_geoid.astype(str).to_numpy()
    if not set(keys) <= set(alpha.index):
        raise ValueError("independent PDSI test has unseen county")
    prediction = (alpha.reindex(keys).to_numpy() +
                  row_dot(z.to_numpy(dtype="float64"), beta))
    residual = prediction - np.log(test.yield_bu_acre.to_numpy(dtype=float))
    if not np.isfinite(residual).all():
        raise ValueError("independent PDSI prediction nonfinite")
    return {"n": len(test), "rmse_log_yield": float(np.sqrt(np.mean(residual**2))),
            "mae_log_yield": float(np.mean(np.abs(residual))),
            "mean_error_log_yield": float(np.mean(residual))}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    out = args.out_dir.resolve()
    if out.exists() or not out.is_relative_to(ROOT / "data/interim"):
        raise ValueError("fresh ignored PDSI score validation output required")
    reported = json.loads(REPORTED.read_text())
    if reported["status"] != "post_result_pdsi_competing_prediction_not_causal" or reported["pdsi_panel_sha256"] != sha(PANEL):
        raise ValueError("registered PDSI comparison identity invalid")
    panel = pd.read_parquet(PANEL)
    checks = 0
    for crop in ("corn_grain", "soybeans"):
        frame = panel.loc[panel.outcome_crop.eq(crop)]
        train = frame.loc[frame.harvest_year.between(1981, 2019)]
        recent = frame.loc[frame.harvest_year.between(2020, 2025)]
        recent = recent.loc[recent.county_geoid.isin(set(train.county_geoid))]
        early = frame.loc[frame.harvest_year.between(1981, 2010)]
        blocked = frame.loc[frame.harvest_year.between(2012, 2019)]
        blocked = blocked.loc[blocked.county_geoid.isin(set(early.county_geoid))]
        for trend in ("common", "state"):
            for model in MODELS:
                for label, left, right, key in (
                    ("terminal", train, recent, "terminal_scores"),
                    ("historical_blocked", early, blocked, "historical_blocked_scores"),
                ):
                    actual = score(left, right, model, trend)
                    expected = reported["crops"][trend][crop][key][model]
                    if actual["n"] != expected["n"]:
                        raise ValueError(f"independent PDSI {label} support differs")
                    for field in ("rmse_log_yield", "mae_log_yield", "mean_error_log_yield"):
                        if abs(actual[field] - expected[field]) > 1e-8:
                            raise ValueError(f"independent PDSI {label} score differs: {crop}/{trend}/{model}/{field}")
                        checks += 1
    result = {"status": "independent_post_result_pdsi_competitor_validated",
              "numeric_checks": checks, "source_result_sha256": sha(REPORTED),
              "panel_sha256": sha(PANEL), "code_sha256": sha(Path(__file__)),
              "post_result_sensitivity": True,
              "climate_change_attribution_performed": False,
              "economic_damage_or_scc_estimated": False}
    out.mkdir(parents=True)
    (out / "result.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"status": result["status"], "numeric_checks": checks}))


if __name__ == "__main__":
    main()
