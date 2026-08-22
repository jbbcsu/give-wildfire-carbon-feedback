#!/usr/bin/env python3
"""Reconcile combined stage heat features to the seasonal heat product."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


KEYS = ["harvest_year", "lat", "lon_360", "crop", "irrigation"]
IDENTITY_FIELDS = ["plant_year", "cross_year", "lon"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--season", required=True)
    parser.add_argument("--stages", required=True)
    parser.add_argument("--out-audit", required=True)
    parser.add_argument("--expected-stages", type=int, default=3)
    parser.add_argument("--tolerance", type=float, default=1e-9)
    args = parser.parse_args()
    if args.expected_stages < 1 or args.tolerance < 0:
        raise ValueError("Expected stages must be positive and tolerance nonnegative")
    season = pd.read_parquet(args.season)
    stages = pd.read_parquet(args.stages)
    required_season = set(KEYS + IDENTITY_FIELDS + ["season_days", "tmax_mean_c"])
    required_stages = set(KEYS + IDENTITY_FIELDS + ["stage_id", "stage_days", "tmax_mean_c"])
    if missing := required_season - set(season.columns):
        raise ValueError(f"Season heat input missing {sorted(missing)}")
    if missing := required_stages - set(stages.columns):
        raise ValueError(f"Stage heat input missing {sorted(missing)}")
    if season.empty or stages.empty:
        raise ValueError("Season and stage heat inputs must be nonempty")
    if season.duplicated(KEYS).any() or stages.duplicated(KEYS + ["stage_id"]).any():
        raise ValueError("Duplicate season or stage keys")

    seasonal_metrics = {
        name for name in season.columns
        if name.startswith("tmax_") and (name.endswith("_days") or name.endswith("_degree_days"))
    }
    stage_metrics = {
        name for name in stages.columns
        if name.startswith("tmax_") and (name.endswith("_days") or name.endswith("_degree_days"))
    }
    if not seasonal_metrics or seasonal_metrics != stage_metrics:
        raise ValueError("Season and stage heat threshold metrics differ")
    expected = set(range(1, args.expected_stages + 1))
    stage_sets = stages.groupby(KEYS, observed=True).stage_id.agg(lambda values: set(values))
    if not stage_sets.map(lambda values: values == expected).all():
        raise ValueError("Stage heat input does not have exactly the expected stages")

    aggregation = {name: "first" for name in IDENTITY_FIELDS}
    aggregation.update({"stage_days": "sum"})
    aggregation.update({name: "sum" for name in sorted(stage_metrics)})
    grouped = stages.groupby(KEYS, as_index=False, observed=True).agg(aggregation)
    weighted = (
        stages.assign(weighted_tmax=stages.tmax_mean_c * stages.stage_days)
        .groupby(KEYS, as_index=False, observed=True)
        .weighted_tmax.sum()
    )
    grouped = grouped.merge(weighted, on=KEYS, validate="one_to_one")
    grouped["stage_weighted_tmax_mean_c"] = grouped.weighted_tmax / grouped.stage_days
    grouped = grouped.drop(columns="weighted_tmax")
    comparison = season.merge(grouped, on=KEYS, how="outer", validate="one_to_one", indicator=True,
                              suffixes=("_season", "_stage"))
    if not comparison._merge.eq("both").all():
        raise ValueError("Season and stage heat products do not have identical keys")
    for field in IDENTITY_FIELDS:
        left, right = comparison[f"{field}_season"], comparison[f"{field}_stage"]
        if pd.api.types.is_numeric_dtype(left):
            matched = np.allclose(left.to_numpy(dtype=float), right.to_numpy(dtype=float), rtol=0, atol=args.tolerance)
        else:
            matched = left.astype(str).equals(right.astype(str))
        if not matched:
            raise ValueError(f"Season and stage identity field {field} differs")
    if not np.array_equal(comparison.season_days.to_numpy(), comparison.stage_days.to_numpy()):
        raise ValueError("Stage lengths do not sum to season_days")

    maximum_differences: dict[str, float] = {}
    for name in sorted(seasonal_metrics):
        difference = np.abs(comparison[f"{name}_season"] - comparison[f"{name}_stage"])
        maximum_differences[name] = float(difference.max())
        if (difference > args.tolerance).any():
            raise ValueError(f"Stage metric {name} does not reconcile to the season")
    mean_difference = np.abs(comparison.tmax_mean_c - comparison.stage_weighted_tmax_mean_c)
    maximum_differences["stage_weighted_tmax_mean_c"] = float(mean_difference.max())
    if (mean_difference > args.tolerance).any():
        raise ValueError("Stage-day-weighted tmax mean does not reconcile to the season")

    audit = {
        "status": "stage_heat_reconciled",
        "n_crop_year_grid_rows": int(len(comparison)),
        "expected_stages": args.expected_stages,
        "tolerance": args.tolerance,
        "maximum_absolute_differences": maximum_differences,
    }
    output = Path(args.out_audit)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(audit, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
