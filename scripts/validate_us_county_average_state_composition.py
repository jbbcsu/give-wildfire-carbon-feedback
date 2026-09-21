#!/usr/bin/env python3
"""Independent grouped-normal-equation audit of state composition scores."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PANEL = ROOT / "data/interim/us_county/noaa_county_average_nass_panel_20260916/panel.parquet"
PROTOCOL = ROOT / "US_COUNTY_AVERAGE_STATE_COMPOSITION_DIAGNOSTIC_20260916.md"
MODELS = ("quantity_temperature", "quantity_temperature_pattern")


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(2**20), b""):
            h.update(block)
    return h.hexdigest()


def matrix(frame: pd.DataFrame, model: str) -> np.ndarray:
    rain = frame.precip_mm.to_numpy(dtype=float) / 1000
    columns = [(frame.harvest_year.to_numpy(dtype=float) - 2000) / 10,
               rain, rain * rain, frame.tmean_c.to_numpy(dtype=float) / 10,
               frame.tmax_exceedance_29c_c_days.to_numpy(dtype=float) / 100]
    if model == MODELS[1]:
        columns += [frame.wet_days_ge_1mm.to_numpy(dtype=float) / 100,
                    frame.cdd_max_days.to_numpy(dtype=float) / 100,
                    frame.rx5day_mm.to_numpy(dtype=float) / 100,
                    frame.stage1_precip_share.to_numpy(dtype=float),
                    frame.stage2_precip_share.to_numpy(dtype=float)]
    return np.stack(columns, axis=1)


def predict(train: pd.DataFrame, test: pd.DataFrame, model: str) -> np.ndarray:
    x = matrix(train, model)
    y = np.log(train.yield_bu_acre.to_numpy(dtype=float))
    county = train.county_geoid.to_numpy(dtype=str)
    unique, inverse = np.unique(county, return_inverse=True)
    counts = np.bincount(inverse).astype(float)
    xmean = np.stack([np.bincount(inverse, weights=x[:, j]) / counts
                      for j in range(x.shape[1])], axis=1)
    ymean = np.bincount(inverse, weights=y) / counts
    centered = x - xmean[inverse]
    target = y - ymean[inverse]
    gram = np.einsum("ni,nj->ij", centered, centered, optimize=False)
    rhs = np.einsum("ni,n->i", centered, target, optimize=False)
    beta = np.linalg.solve(gram, rhs)
    alpha = ymean - np.sum(xmean * beta, axis=1)
    lookup = dict(zip(unique.tolist(), alpha.tolist()))
    test_alpha = np.asarray([lookup[str(value)] for value in test.county_geoid], dtype=float)
    forecast = test_alpha + np.sum(matrix(test, model) * beta, axis=1)
    if not np.isfinite(forecast).all():
        raise ValueError("validator forecast nonfinite")
    return forecast


def near(got: float, want: float, label: str, tolerance: float = 1e-8) -> None:
    if not np.isfinite(got) or not np.isfinite(want) or abs(got - want) > tolerance:
        raise ValueError(f"{label}: {got} != {want}")


def check_crop(frame: pd.DataFrame, result: dict) -> int:
    crop = result["crop"]
    data = frame.loc[frame.outcome_crop.eq(crop)]
    train = data.loc[data.harvest_year.between(1981, 2019)]
    test = data.loc[data.harvest_year.between(2020, 2025) &
                    data.county_geoid.isin(set(train.county_geoid))].copy()
    if len(test) != result["terminal_rows"]:
        raise ValueError("validator terminal support differs")
    actual = np.log(test.yield_bu_acre.to_numpy(dtype=float))
    residuals = {model: predict(train, test, model) - actual for model in MODELS}
    states = test.state.to_numpy(dtype=str)
    if sorted(set(states)) != [row["state"] for row in result["rows"]]:
        raise ValueError("state set differs")
    checks = 0
    pooled = {}
    for model in MODELS:
        pooled[model] = float(np.sqrt(np.mean(residuals[model] ** 2)))
        near(pooled[model], result["pooled_rmse"][model], f"{crop} pooled {model}")
        checks += 1
    near(pooled[MODELS[0]] - pooled[MODELS[1]],
         result["pooled_quantity_minus_pattern_rmse"], f"{crop} pooled contrast")
    checks += 1
    equal_sq = {model: [] for model in MODELS}
    for row in result["rows"]:
        mask = states == row["state"]
        n = int(mask.sum())
        if n != row["rows"] or int(test.loc[mask, "harvest_year"].nunique()) != row["years"]:
            raise ValueError("state count/year coverage differs")
        checks += 2
        near(float(n < 30 or row["years"] < 3), float(row["small_state_flag"]), "small-state flag", 0)
        checks += 1
        rmses = {}
        for model, prefix in zip(MODELS, ("quantity", "pattern")):
            sse = float(np.sum(residuals[model][mask] ** 2))
            rmses[model] = float(np.sqrt(sse / n))
            equal_sq[model].append(sse / n)
            near(sse, row[f"{prefix}_sse"], f"{crop} {row['state']} {prefix} SSE", 1e-7)
            near(rmses[model], row[f"{prefix}_rmse"], f"{crop} {row['state']} {prefix} RMSE")
            checks += 2
        near(rmses[MODELS[0]] - rmses[MODELS[1]],
             row["quantity_minus_pattern_rmse"], f"{crop} {row['state']} contrast")
        remaining = ~mask
        leave = {model: float(np.sqrt(np.mean(residuals[model][remaining] ** 2)))
                 for model in MODELS}
        near(leave[MODELS[0]] - leave[MODELS[1]],
             row["without_state_quantity_minus_pattern_rmse"],
             f"{crop} {row['state']} leave-one-out")
        checks += 2
    equal = {model: float(np.sqrt(np.mean(equal_sq[model]))) for model in MODELS}
    for model in MODELS:
        near(equal[model], result["equal_state_rmse"][model], f"{crop} equal-state {model}")
        checks += 1
    near(equal[MODELS[0]] - equal[MODELS[1]],
         result["equal_state_quantity_minus_pattern_rmse"], f"{crop} equal-state contrast")
    checks += 1
    return checks


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    if out.exists() or not out.is_relative_to(ROOT / "data/interim"):
        raise ValueError("fresh ignored validator output required")
    payload = json.loads(args.result.read_text())
    if (payload["status"] != "post_result_fixed_forecast_state_composition_not_causal_or_scc" or
        payload["panel_sha256"] != sha(PANEL) or payload["protocol_sha256"] != sha(PROTOCOL)):
        raise ValueError("source or protocol identity differs")
    panel = pd.read_parquet(PANEL)
    checks = sum(check_crop(panel, payload["crops"][crop])
                 for crop in ("corn_grain", "soybeans"))
    outcome = {"status": "independent_state_decomposition_numerical_validation_passed",
               "checks": checks, "result_sha256": sha(args.result), "panel_sha256": sha(PANEL),
               "validator_sha256": sha(Path(__file__)), "causal_or_scc_result": False}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(outcome, indent=2) + "\n")
    print(json.dumps(outcome))


if __name__ == "__main__":
    main()
