#!/usr/bin/env python3
"""Compare two validated Hultgren grid-weather bases without claiming impacts."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
KEYS = ["harvest_year", "native_lat_index", "native_lon_index"]
SUPPORT = ["plant_month", "harvest_month", "season_months", "cross_year", "mirca_area_ha"]
WEATHER = [
    "gdd", "kdd",
    "prcp_poly_1_bin1", "prcp_poly_1_bin2", "prcp_poly_1_bin3",
    "prcp_poly_2_bin1", "prcp_poly_2_bin2", "prcp_poly_2_bin3",
]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def derived(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    linear = [f"prcp_poly_1_bin{phase}" for phase in (1, 2, 3)]
    squared = [f"prcp_poly_2_bin{phase}" for phase in (1, 2, 3)]
    result["season_total_mm"] = result[linear].sum(axis=1)
    result["monthly_square_sum_mm2"] = result[squared].sum(axis=1)
    require((result.season_total_mm >= 0).all(), "negative seasonal precipitation is outside comparison contract")
    positive = result.season_total_mm > 0
    result["monthly_concentration"] = np.nan
    result.loc[positive, "monthly_concentration"] = (
        result.loc[positive, "monthly_square_sum_mm2"] / result.loc[positive, "season_total_mm"].pow(2)
    )
    for phase in (1, 2, 3):
        result[f"phase{phase}_share"] = np.nan
        result.loc[positive, f"phase{phase}_share"] = (
            result.loc[positive, f"prcp_poly_1_bin{phase}"] / result.loc[positive, "season_total_mm"]
        )
    return result


def weighted_mean(values: pd.Series, weights: pd.Series) -> float:
    return float(np.average(values.to_numpy(dtype=float), weights=weights.to_numpy(dtype=float)))


def compare(reference: pd.DataFrame, comparison: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, object]]:
    expected = set(KEYS + SUPPORT + WEATHER)
    require(expected <= set(reference.columns) and expected <= set(comparison.columns), "basis columns absent")
    left = reference[KEYS + SUPPORT + WEATHER].sort_values(KEYS).reset_index(drop=True)
    right = comparison[KEYS + SUPPORT + WEATHER].sort_values(KEYS).reset_index(drop=True)
    require(left[KEYS].equals(right[KEYS]), "scenario cell-year keys differ")
    for column in SUPPORT:
        require(np.allclose(left[column], right[column], rtol=0.0, atol=0.0), f"scenario support differs: {column}")
    left = derived(left)
    right = derived(right)
    all_support_metrics = WEATHER + ["season_total_mm", "monthly_square_sum_mm2"]
    distribution_metrics = ["monthly_concentration"] + [
        f"phase{phase}_share" for phase in (1, 2, 3)
    ]
    annual_rows = []
    weights = left.mirca_area_ha
    for year in sorted(left.harvest_year.unique()):
        take = left.harvest_year == year
        row: dict[str, object] = {"harvest_year": int(year), "cells": int(take.sum()), "area_ha": float(weights[take].sum())}
        common_positive = take & left.season_total_mm.gt(0) & right.season_total_mm.gt(0)
        require(common_positive.any(), f"no common positive-precipitation support in {year}")
        row["reference_zero_precipitation_area_fraction"] = float(
            weights[take & left.season_total_mm.eq(0)].sum() / weights[take].sum()
        )
        row["comparison_zero_precipitation_area_fraction"] = float(
            weights[take & right.season_total_mm.eq(0)].sum() / weights[take].sum()
        )
        row["distribution_common_positive_area_fraction"] = float(weights[common_positive].sum() / weights[take].sum())
        for metric in all_support_metrics:
            reference_mean = weighted_mean(left.loc[take, metric], weights[take])
            comparison_mean = weighted_mean(right.loc[take, metric], weights[take])
            row[f"reference_{metric}"] = reference_mean
            row[f"comparison_{metric}"] = comparison_mean
            row[f"delta_{metric}"] = comparison_mean - reference_mean
        for metric in distribution_metrics:
            reference_mean = weighted_mean(left.loc[common_positive, metric], weights[common_positive])
            comparison_mean = weighted_mean(right.loc[common_positive, metric], weights[common_positive])
            row[f"reference_{metric}"] = reference_mean
            row[f"comparison_{metric}"] = comparison_mean
            row[f"delta_{metric}"] = comparison_mean - reference_mean
        annual_rows.append(row)
    annual = pd.DataFrame(annual_rows)
    pooled: dict[str, object] = {"cell_years": len(left), "years": int(left.harvest_year.nunique())}
    common_positive = left.season_total_mm.gt(0) & right.season_total_mm.gt(0)
    require(common_positive.any(), "no pooled common positive-precipitation support")
    pooled["reference_zero_precipitation_area_year_fraction"] = float(
        weights[left.season_total_mm.eq(0)].sum() / weights.sum()
    )
    pooled["comparison_zero_precipitation_area_year_fraction"] = float(
        weights[right.season_total_mm.eq(0)].sum() / weights.sum()
    )
    pooled["distribution_common_positive_area_year_fraction"] = float(weights[common_positive].sum() / weights.sum())
    for metric in all_support_metrics:
        pooled[f"reference_{metric}"] = weighted_mean(left[metric], weights)
        pooled[f"comparison_{metric}"] = weighted_mean(right[metric], weights)
        pooled[f"delta_{metric}"] = pooled[f"comparison_{metric}"] - pooled[f"reference_{metric}"]
    for metric in distribution_metrics:
        pooled[f"reference_{metric}"] = weighted_mean(left.loc[common_positive, metric], weights[common_positive])
        pooled[f"comparison_{metric}"] = weighted_mean(right.loc[common_positive, metric], weights[common_positive])
        pooled[f"delta_{metric}"] = pooled[f"comparison_{metric}"] - pooled[f"reference_{metric}"]
    return annual, pooled


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--comparison", type=Path, required=True)
    parser.add_argument("--reference-label", required=True)
    parser.add_argument("--comparison-label", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), "fresh comparison output required")
    columns = KEYS + SUPPORT + WEATHER
    reference = pd.read_parquet(args.reference, columns=columns)
    comparison = pd.read_parquet(args.comparison, columns=columns)
    annual, pooled = compare(reference, comparison)
    result = {
        "schema": "hultgren_grid_weather_scenario_comparison/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "weather_basis_comparison_not_yield_damage_or_scc",
        "reference": {"label": args.reference_label, "path": str(args.reference), "sha256": digest(args.reference)},
        "comparison": {"label": args.comparison_label, "path": str(args.comparison), "sha256": digest(args.comparison)},
        "direction": "comparison_minus_reference",
        "annual_area_weighted": annual.to_dict(orient="records"),
        "pooled_area_year_weighted": pooled,
        "interpretation": {
            "quantity": "season_total_mm and three phase totals",
            "within_season_distribution": "phase shares and scale-normalized monthly concentration on common positive-precipitation support; sum of squared monthly precipitation remains an all-support level metric",
            "zero_precipitation": "zero-total area shares are reported separately rather than assigning undefined phase shares or concentration a fabricated value",
            "limits": "one climate-model/window scenario contrast; no response, causality, monetary damage, or SCC claim",
        },
        "implementation": {
            "path": str(Path(__file__).resolve().relative_to(ROOT)),
            "sha256": digest(Path(__file__).resolve()),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "pooled": pooled}, indent=2))


if __name__ == "__main__":
    main()
