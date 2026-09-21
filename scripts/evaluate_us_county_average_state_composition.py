#!/usr/bin/env python3
"""Post-result state decomposition of fixed U.S. terminal forecasts."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

import estimate_us_county_average_terminal_prediction as base

ROOT = Path(__file__).resolve().parents[1]
PANEL = base.PANEL_DIR / "panel.parquet"
PANEL_RECEIPT = base.PANEL_DIR / "result.json"
ORIGINAL = ROOT / "data/interim/us_county/noaa_county_average_prediction_20260916/result.json"
PROTOCOL = ROOT / "US_COUNTY_AVERAGE_STATE_COMPOSITION_DIAGNOSTIC_20260916.md"
MODELS = ("quantity_temperature", "quantity_temperature_pattern")


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(2**20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rmse(sse: float, n: int) -> float:
    if n <= 0 or sse < 0:
        raise ValueError("invalid score support")
    return float(np.sqrt(sse / n))


def one_crop(panel: pd.DataFrame, crop: str, original: dict) -> dict:
    data = panel.loc[panel.outcome_crop.eq(crop)]
    train = data.loc[data.harvest_year.between(1981, 2019)]
    recent = data.loc[data.harvest_year.between(2020, 2025)]
    test = recent.loc[recent.county_geoid.isin(set(train.county_geoid))].copy()
    expected = original["crops"][crop]
    if (len(train) != expected["historical_rows"] or
        len(test) != expected["terminal_rows_scored"] or
        len(recent) - len(test) != expected["terminal_rows_excluded_unseen_county"] or
        test.duplicated(["county_geoid", "harvest_year"]).any()):
        raise ValueError("original crop sample is not reproduced")
    actual = np.log(test.yield_bu_acre.to_numpy(dtype=float))
    forecasts: dict[str, np.ndarray] = {}
    pooled: dict[str, float] = {}
    for model in MODELS:
        x_train, terms = base.design(train, model)
        x_test, test_terms = base.design(test, model)
        if terms != test_terms:
            raise ValueError("design terms changed")
        fitted = base.fit_within(np.log(train.yield_bu_acre.to_numpy(dtype=float)),
                                 x_train, train.county_geoid.to_numpy())
        forecasts[model] = base.predict(fitted, x_test, test.county_geoid.to_numpy())
        pooled[model] = base.metrics(actual, forecasts[model])["rmse_log_yield"]
        if abs(pooled[model] - expected["terminal_scores"][model]["rmse_log_yield"]) > 1e-12:
            raise ValueError("original terminal forecast score parity failed")

    states = test.state.to_numpy(dtype=str)
    if np.any(states == "") or not np.isfinite(actual).all():
        raise ValueError("incomplete state or outcome identity")
    residual = {model: forecasts[model] - actual for model in MODELS}
    totals = {model: float(np.square(residual[model]).sum()) for model in MODELS}
    rows = []
    for state in sorted(set(states)):
        mask = states == state
        n = int(mask.sum())
        years = int(test.loc[mask, "harvest_year"].nunique())
        sse = {model: float(np.square(residual[model][mask]).sum()) for model in MODELS}
        quantity = rmse(sse[MODELS[0]], n)
        pattern = rmse(sse[MODELS[1]], n)
        remainder_n = len(test) - n
        if remainder_n <= 0:
            raise ValueError("state exhausts terminal sample")
        without = {model: rmse(max(0.0, totals[model] - sse[model]), remainder_n)
                   for model in MODELS}
        rows.append({"state": state, "rows": n, "years": years,
                     "small_state_flag": n < 30 or years < 3,
                     "quantity_rmse": quantity, "pattern_rmse": pattern,
                     "quantity_minus_pattern_rmse": quantity - pattern,
                     "quantity_sse": sse[MODELS[0]], "pattern_sse": sse[MODELS[1]],
                     "without_state_quantity_minus_pattern_rmse":
                         without[MODELS[0]] - without[MODELS[1]]})
    if sum(row["rows"] for row in rows) != len(test):
        raise ValueError("state partition fails to cover terminal rows")
    equal = {model: float(np.sqrt(np.mean([
        row[("quantity_rmse" if model == MODELS[0] else "pattern_rmse")]**2
        for row in rows]))) for model in MODELS}
    difference = pooled[MODELS[0]] - pooled[MODELS[1]]
    prior = expected["paired_conditional_uncertainty"]["pattern_vs_quantity"]["point_difference"]
    if abs(difference - prior) > 1e-12:
        raise ValueError("original pattern contrast parity failed")
    return {"crop": crop, "terminal_rows": len(test), "states": len(rows),
            "pooled_rmse": pooled, "pooled_quantity_minus_pattern_rmse": difference,
            "equal_state_rmse": equal,
            "equal_state_quantity_minus_pattern_rmse": equal[MODELS[0]] - equal[MODELS[1]],
            "positive_state_count": sum(row["quantity_minus_pattern_rmse"] > 0 for row in rows),
            "small_state_count": sum(row["small_state_flag"] for row in rows),
            "leave_one_state_out_difference_min": min(row["without_state_quantity_minus_pattern_rmse"] for row in rows),
            "leave_one_state_out_difference_max": max(row["without_state_quantity_minus_pattern_rmse"] for row in rows),
            "rows": rows}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    if out.exists() or not out.is_relative_to(ROOT / "data/interim"):
        raise ValueError("fresh ignored output required")
    panel_receipt = json.loads(PANEL_RECEIPT.read_text())
    original = json.loads(ORIGINAL.read_text())
    if (panel_receipt["panel_sha256"] != sha(PANEL) or
        original["panel_sha256"] != sha(PANEL) or
        original["preanalysis_protocol_sha256"] != sha(base.PROTOCOL)):
        raise ValueError("source/original protocol identity failed")
    panel = pd.read_parquet(PANEL)
    if panel.duplicated(["outcome_crop", "county_geoid", "harvest_year"]).any():
        raise ValueError("duplicate panel keys")
    crops = {crop: one_crop(panel, crop, original) for crop in ("corn_grain", "soybeans")}
    result = {"status": "post_result_fixed_forecast_state_composition_not_causal_or_scc",
              "protocol_sha256": sha(PROTOCOL), "panel_sha256": sha(PANEL),
              "original_result_sha256": sha(ORIGINAL), "code_sha256": sha(Path(__file__)),
              "crops": crops, "climate_damage_or_scc_estimated": False}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({crop: {"states": item["states"],
                             "positive_states": item["positive_state_count"],
                             "pooled_gain": item["pooled_quantity_minus_pattern_rmse"],
                             "equal_state_gain": item["equal_state_quantity_minus_pattern_rmse"],
                             "loo_min": item["leave_one_state_out_difference_min"]}
                      for crop, item in crops.items()}))


if __name__ == "__main__":
    main()
