#!/usr/bin/env python3
"""Build the bounded RIME-X 21-year centered-means mechanics artifact.

This script only smooths already validated, daily-derived crop indicators and
same-realization GMST.  It does not fit a response, construct stochastic
draws, or authorize damage/SCC use.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


BASE_KEYS = ["lat", "lon", "lon_360", "crop", "irrigation"]
SEASON_CONSTANTS = [
    "cross_year", "plant_doy", "maturity_doy", "wet_day_threshold_mm",
]
SEASON_GEOMETRY = ["season_days"]
STAGE_CONSTANTS = [
    "cross_year", "stage_id", "stage_fractions",
]
STAGE_GEOMETRY = ["stage_start_offset_day", "stage_end_offset_day", "stage_days"]
METRICS = ["tmean_c", "precip_mm", "wet_days_n", "cdd_max_days", "rx1day_mm", "rx5day_mm"]


def _require_odd_window(window: int) -> int:
    if window < 3 or window % 2 != 1:
        raise ValueError("centered window must be an odd integer of at least three years")
    return window // 2


def _exact_years(values: pd.Series, expected: list[int], label: str) -> None:
    actual = sorted(pd.to_numeric(values, errors="raise").astype(int).tolist())
    if actual != expected:
        raise ValueError(f"{label} does not contain the exact consecutive feature years")


def smooth_features(frame: pd.DataFrame, *, stage: bool, window: int) -> pd.DataFrame:
    half = _require_odd_window(window)
    constants = STAGE_CONSTANTS if stage else SEASON_CONSTANTS
    geometry = STAGE_GEOMETRY if stage else SEASON_GEOMETRY
    group_keys = BASE_KEYS + (["stage_id"] if stage else [])
    required = {"harvest_year", "plant_year", *group_keys, *constants, *geometry, *METRICS}
    if missing := required - set(frame.columns):
        raise ValueError(f"feature table lacks {sorted(missing)}")
    if frame.empty or frame.duplicated(group_keys + ["harvest_year"]).any():
        raise ValueError("feature table is empty or has duplicate cell-years")
    first_year = int(frame.harvest_year.min())
    last_year = int(frame.harvest_year.max())
    expected = list(range(first_year, last_year + 1))
    if len(expected) < window:
        raise ValueError("feature support is shorter than the centered window")
    if not np.isfinite(frame[geometry + METRICS].to_numpy(dtype=float)).all():
        raise ValueError("feature metrics and calendar geometry must be complete and finite before smoothing")

    rows: list[dict[str, object]] = []
    for key, group in frame.groupby(group_keys, observed=True, sort=True):
        ordered = group.sort_values("harvest_year")
        _exact_years(ordered.harvest_year, expected, "a feature cell")
        if not ordered[constants].nunique(dropna=False).eq(1).all():
            raise ValueError("calendar/stage identity changes within a feature cell")
        key_values = key if isinstance(key, tuple) else (key,)
        identity = dict(zip(group_keys, key_values))
        identity.update({name: ordered.iloc[0][name] for name in constants})
        for center in range(first_year + half, last_year - half + 1):
            block = ordered.loc[ordered.harvest_year.between(center - half, center + half)]
            if len(block) != window:
                raise AssertionError("centered selector did not retain the registered window")
            row: dict[str, object] = {
                **identity,
                "center_year": center,
                "window_start_year": center - half,
                "window_end_year": center + half,
                "window_years": window,
            }
            row.update({f"{name}_{window}yr_mean": float(block[name].mean()) for name in geometry + METRICS})
            rows.append(row)
    output = pd.DataFrame(rows)
    if output.empty:
        raise ValueError("no complete centered feature windows were emitted")
    return output.sort_values(group_keys + ["center_year"]).reset_index(drop=True)


def smooth_gmst(frame: pd.DataFrame, *, first_feature_year: int, last_feature_year: int, window: int) -> pd.DataFrame:
    half = _require_odd_window(window)
    required = {"esm_id", "member_id", "scenario", "gmst_source_id", "year", "gmst_value_k"}
    if missing := required - set(frame.columns):
        raise ValueError(f"GMST table lacks {sorted(missing)}")
    if frame[list(required - {"year", "gmst_value_k"})].nunique(dropna=False).max() != 1:
        raise ValueError("GMST table mixes realizations, scenarios, or source identifiers")
    selected = frame.loc[frame.year.between(first_feature_year, last_feature_year)].sort_values("year")
    expected = list(range(first_feature_year, last_feature_year + 1))
    _exact_years(selected.year, expected, "same-realization GMST")
    if not np.isfinite(selected.gmst_value_k.to_numpy(dtype=float)).all():
        raise ValueError("GMST values must be finite")
    identity = {name: selected.iloc[0][name] for name in ["esm_id", "member_id", "scenario", "gmst_source_id"]}
    rows = []
    for center in range(first_feature_year + half, last_feature_year - half + 1):
        block = selected.loc[selected.year.between(center - half, center + half)]
        rows.append({
            **identity,
            "center_year": center,
            "window_start_year": center - half,
            "window_end_year": center + half,
            "window_years": window,
            f"gmst_value_k_{window}yr_mean": float(block.gmst_value_k.mean()),
        })
    return pd.DataFrame(rows)


def reconcile(season: pd.DataFrame, stage: pd.DataFrame, gmst: pd.DataFrame, *, window: int) -> dict[str, object]:
    keys = BASE_KEYS + ["center_year"]
    additive = ["stage_days", "precip_mm", "wet_days_n"]
    grouped = stage.groupby(keys, observed=True).agg(
        **{f"{name}_{window}yr_mean": (f"{name}_{window}yr_mean", "sum") for name in additive}
    ).reset_index()
    joined = season.merge(grouped, on=keys, suffixes=("_season", "_stages"), validate="one_to_one")
    if len(joined) != len(season):
        raise ValueError("smoothed stage rows do not cover every smoothed season row")
    differences = {
        "stage_days": np.abs(joined[f"season_days_{window}yr_mean"] - joined[f"stage_days_{window}yr_mean"]),
        **{
            name: np.abs(joined[f"{name}_{window}yr_mean_season"] - joined[f"{name}_{window}yr_mean_stages"])
            for name in ("precip_mm", "wet_days_n")
        },
    }
    limits = {"stage_days": 1e-12, "precip_mm": 1e-9, "wet_days_n": 1e-12}
    failures = {name: float(values.max()) for name, values in differences.items() if values.max() > limits[name]}
    if failures:
        raise ValueError(f"centered stage/season additive reconciliation failed: {failures}")
    feature_years = sorted(season.center_year.unique().astype(int).tolist())
    if sorted(stage.center_year.unique().astype(int).tolist()) != feature_years:
        raise ValueError("season and stage centered years differ")
    if gmst.center_year.astype(int).tolist() != feature_years:
        raise ValueError("same-realization GMST and feature centered years differ")
    return {
        "role": "contiguous_centered_means_mechanics_not_response_damage_or_scc",
        "window_years": window,
        "center_years": feature_years,
        "season_rows": int(len(season)),
        "stage_rows": int(len(stage)),
        "gmst_rows": int(len(gmst)),
        "stage_season_additive_max_absolute_differences": {
            name: float(values.max()) for name, values in differences.items()
        },
        "result": "passed",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--season", type=Path, required=True)
    parser.add_argument("--stage", type=Path, required=True)
    parser.add_argument("--gmst", type=Path, required=True)
    parser.add_argument("--window", type=int, default=21)
    parser.add_argument("--season-out", type=Path, required=True)
    parser.add_argument("--stage-out", type=Path, required=True)
    parser.add_argument("--gmst-out", type=Path, required=True)
    parser.add_argument("--audit-out", type=Path, required=True)
    args = parser.parse_args()
    raw_season = pd.read_parquet(args.season)
    raw_stage = pd.read_parquet(args.stage)
    raw_gmst = pd.read_parquet(args.gmst)
    season = smooth_features(raw_season, stage=False, window=args.window)
    stage = smooth_features(raw_stage, stage=True, window=args.window)
    gmst = smooth_gmst(
        raw_gmst,
        first_feature_year=int(raw_season.harvest_year.min()),
        last_feature_year=int(raw_season.harvest_year.max()),
        window=args.window,
    )
    audit = reconcile(season, stage, gmst, window=args.window)
    for path, frame in [(args.season_out, season), (args.stage_out, stage), (args.gmst_out, gmst)]:
        path.parent.mkdir(parents=True, exist_ok=True)
        frame.to_parquet(path, index=False)
    args.audit_out.parent.mkdir(parents=True, exist_ok=True)
    args.audit_out.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(audit, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
