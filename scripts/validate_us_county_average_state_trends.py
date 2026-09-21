#!/usr/bin/env python3
"""Independent pandas reconstruction of post-result state-trend scores."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from validate_us_county_average_terminal_prediction import independent_design, row_dot

ROOT = Path(__file__).resolve().parents[1]
PANEL = ROOT / "data/interim/us_county/noaa_county_average_nass_panel_20260916/panel.parquet"
SENSITIVITY = ROOT / "data/interim/us_county/noaa_county_average_state_trend_sensitivity_20260916/result.json"
MODELS = ("no_weather", "quantity_temperature", "quantity_temperature_pattern")


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(2**20), b""):
            h.update(block)
    return h.hexdigest()


def matrix(frame: pd.DataFrame, model: str, states: list[str]) -> pd.DataFrame:
    ordinary = independent_design(frame, model).reset_index(drop=True)
    time = ordinary.pop("year_minus_2000_per_decade")
    columns = {f"state_trend_{state}": time * frame.state.astype(str).reset_index(drop=True).eq(state)
               for state in states}
    return pd.concat([pd.DataFrame(columns), ordinary], axis=1)


def score(train: pd.DataFrame, test: pd.DataFrame, model: str) -> dict:
    states = sorted(set(train.state.astype(str)))
    if not set(test.state.astype(str)) <= set(states):
        raise ValueError("independent state-trend test contains unseen state")
    x = matrix(train, model, states)
    z = matrix(test, model, states)
    labels = train.county_geoid.astype(str).reset_index(drop=True)
    y = pd.Series(np.log(train.yield_bu_acre.to_numpy(dtype=float)))
    xm = x.groupby(labels).transform("mean")
    ym = y.groupby(labels).transform("mean")
    beta, _, rank, _ = np.linalg.lstsq((x - xm).to_numpy(), (y - ym).to_numpy(), rcond=None)
    if rank != x.shape[1]:
        raise ValueError("independent state-trend fit lacks full rank")
    gx = x.groupby(labels).mean()
    gy = y.groupby(labels).mean()
    alpha = gy - row_dot(gx.to_numpy(dtype="float64"), beta)
    if not set(test.county_geoid.astype(str)) <= set(alpha.index):
        raise ValueError("independent state-trend test contains unseen county")
    forecast = (alpha.reindex(test.county_geoid.astype(str).to_numpy()).to_numpy() +
                row_dot(z.to_numpy(dtype="float64"), beta))
    residual = forecast - np.log(test.yield_bu_acre.to_numpy(dtype=float))
    if not np.isfinite(residual).all():
        raise ValueError("independent state-trend residual nonfinite")
    return {"n": len(test), "rmse_log_yield": float(np.sqrt(np.mean(residual**2))),
            "mae_log_yield": float(np.mean(np.abs(residual))),
            "mean_error_log_yield": float(np.mean(residual))}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    out = args.out_dir.resolve()
    if out.exists() or not out.is_relative_to(ROOT / "data/interim"):
        raise ValueError("fresh ignored state-trend validation output required")
    reported = json.loads(SENSITIVITY.read_text())
    if (reported["status"] != "post_result_us_state_trend_sensitivity_not_causal" or
        reported["panel_sha256"] != sha(PANEL)):
        raise ValueError("registered state-trend result/panel identity invalid")
    panel = pd.read_parquet(PANEL)
    checks = 0
    for crop in ("corn_grain", "soybeans"):
        data = panel.loc[panel.outcome_crop.eq(crop)]
        train = data.loc[data.harvest_year.between(1981, 2019)]
        recent = data.loc[data.harvest_year.between(2020, 2025)]
        recent = recent.loc[recent.county_geoid.isin(set(train.county_geoid))]
        earlier = data.loc[data.harvest_year.between(1981, 2010)]
        blocked = data.loc[data.harvest_year.between(2012, 2019)]
        blocked = blocked.loc[blocked.county_geoid.isin(set(earlier.county_geoid))]
        for model in MODELS:
            for label, left, right, key in (
                ("terminal", train, recent, "terminal_scores"),
                ("blocked", earlier, blocked, "historical_blocked_scores"),
            ):
                actual = score(left, right, model)
                expected = reported["crops"][crop][key][model]
                if actual["n"] != expected["n"]:
                    raise ValueError(f"independent {label} state-trend row count differs")
                for field in ("rmse_log_yield", "mae_log_yield", "mean_error_log_yield"):
                    if abs(actual[field] - expected[field]) > 1e-8:
                        raise ValueError(f"independent {label} state-trend score differs: {crop}/{model}/{field}")
                    checks += 1
    result = {"status": "independent_post_result_state_trend_sensitivity_validated",
              "numeric_checks": checks, "source_result_sha256": sha(SENSITIVITY),
              "panel_sha256": sha(PANEL), "code_sha256": sha(Path(__file__)),
              "post_result_sensitivity": True,
              "climate_change_attribution_performed": False,
              "economic_damage_or_scc_estimated": False}
    out.mkdir(parents=True)
    (out / "result.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"status": result["status"], "numeric_checks": checks}))


if __name__ == "__main__":
    main()
