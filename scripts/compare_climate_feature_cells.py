#!/usr/bin/env python3
"""Paired descriptive comparison of two bounded daily-climate feature cells.

This audit quantifies feature differences on identical crop/calendar/grid/year
keys. It is not an emulator holdout, a yield response, or an SCC result.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


KEYS = ["harvest_year", "lat", "lon_360", "crop", "irrigation"]
SEASON_METRICS = [
    "tmean_c",
    "precip_mm",
    "wet_days_n",
    "cdd_max_days",
    "rx1day_mm",
    "rx5day_mm",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_years(path: Path, year_start: int, year_end: int) -> pd.DataFrame:
    frame = pd.read_parquet(path)
    if missing := set(KEYS) - set(frame.columns):
        raise ValueError(f"{path} missing key columns {sorted(missing)}")
    return frame.loc[frame.harvest_year.between(year_start, year_end)].copy()


def checked_sort(frame: pd.DataFrame, keys: list[str], label: str) -> pd.DataFrame:
    if frame.empty:
        raise ValueError(f"{label} has no rows in the requested years")
    if frame.duplicated(keys).any():
        raise ValueError(f"{label} has duplicate keys")
    return frame.sort_values(keys).reset_index(drop=True)


def require_same_keys(reference: pd.DataFrame, candidate: pd.DataFrame, keys: list[str]) -> None:
    left = reference[keys].reset_index(drop=True)
    right = candidate[keys].reset_index(drop=True)
    if not left.equals(right):
        raise ValueError("reference and candidate do not have identical ordered keys")


def timing_features(
    season: pd.DataFrame,
    stages: pd.DataFrame,
    expected_stages: int,
) -> pd.DataFrame:
    required = set(KEYS + ["stage_id", "precip_mm"])
    if missing := required - set(stages.columns):
        raise ValueError(f"stage input missing {sorted(missing)}")
    stages = checked_sort(stages, KEYS + ["stage_id"], "stage input")
    season_keys = season[KEYS].drop_duplicates().sort_values(KEYS).reset_index(drop=True)
    stage_keys = stages[KEYS].drop_duplicates().sort_values(KEYS).reset_index(drop=True)
    if not season_keys.equals(stage_keys):
        raise ValueError("stage and season inputs do not have identical keys")
    expected = set(range(1, expected_stages + 1))
    observed = stages.groupby(KEYS, observed=True).stage_id.agg(lambda values: set(values))
    if not observed.map(lambda value: value == expected).all():
        raise ValueError("stage input does not have exactly the expected stage IDs")
    wide = stages.pivot(index=KEYS, columns="stage_id", values="precip_mm")
    wide = wide.rename(columns=lambda stage: f"stage{stage}_precip_mm").reset_index()
    merged = season[KEYS + ["precip_mm"]].merge(wide, on=KEYS, how="left", validate="one_to_one")
    stage_columns = [f"stage{stage}_precip_mm" for stage in range(1, expected_stages + 1)]
    if merged[stage_columns].isna().any().any():
        raise ValueError("stage input is missing one or more season keys")
    stage_values = merged[stage_columns].to_numpy(float)
    total = merged.precip_mm.to_numpy(float)
    if not np.isfinite(stage_values).all() or not np.isfinite(total).all():
        raise ValueError("precipitation values must be finite")
    if (stage_values < 0).any() or (total < 0).any():
        raise ValueError("precipitation values must be nonnegative")
    if not np.allclose(stage_values.sum(axis=1), total, rtol=0, atol=1e-3):
        raise ValueError("stage precipitation does not reproduce seasonal precipitation")
    shares = np.divide(
        stage_values,
        total[:, None],
        out=np.zeros_like(stage_values),
        where=total[:, None] > 0,
    )
    result = merged[KEYS].copy()
    for index in range(expected_stages):
        result[f"stage{index + 1}_precip_share"] = shares[:, index]
    midpoints = (np.arange(expected_stages, dtype=float) + 0.5) / expected_stages
    # Some sandboxed BLAS builds emit spurious floating-point status warnings
    # for finite matrix products, so check the result explicitly.
    with np.errstate(over="ignore", divide="ignore", invalid="ignore"):
        timing_centroid = shares @ midpoints
    if not np.isfinite(timing_centroid).all():
        raise ValueError("precipitation timing centroid must be finite")
    result["precipitation_timing_centroid"] = timing_centroid
    result["precipitation_concentration_hhi"] = (shares**2).sum(axis=1)
    return result


def paired_summary(reference: pd.Series, candidate: pd.Series) -> dict[str, float | int | None]:
    left = reference.to_numpy(float)
    right = candidate.to_numpy(float)
    if not np.isfinite(left).all() or not np.isfinite(right).all():
        raise ValueError("comparison metrics must be finite")
    difference = right - left
    correlation: float | None
    if len(left) < 2 or np.std(left) == 0 or np.std(right) == 0:
        correlation = None
    else:
        correlation = float(np.corrcoef(left, right)[0, 1])
    return {
        "rows": len(left),
        "reference_mean": float(left.mean()),
        "candidate_mean": float(right.mean()),
        "reference_p05": float(np.quantile(left, 0.05)),
        "candidate_p05": float(np.quantile(right, 0.05)),
        "reference_median": float(np.median(left)),
        "candidate_median": float(np.median(right)),
        "reference_p95": float(np.quantile(left, 0.95)),
        "candidate_p95": float(np.quantile(right, 0.95)),
        "paired_mean_difference_candidate_minus_reference": float(difference.mean()),
        "paired_median_difference_candidate_minus_reference": float(np.median(difference)),
        "paired_mean_absolute_difference": float(np.abs(difference).mean()),
        "paired_root_mean_square_difference": float(np.sqrt(np.mean(difference**2))),
        "paired_pearson_correlation": correlation,
    }


def compare(
    reference_season_path: Path,
    reference_stage_path: Path,
    candidate_season_path: Path,
    candidate_stage_path: Path,
    *,
    reference_label: str,
    candidate_label: str,
    year_start: int,
    year_end: int,
    expected_stages: int = 3,
) -> dict[str, object]:
    if year_end < year_start:
        raise ValueError("year_end must not precede year_start")
    if expected_stages < 2:
        raise ValueError("expected_stages must be at least two")
    reference = checked_sort(
        read_years(reference_season_path, year_start, year_end), KEYS, "reference season"
    )
    candidate = checked_sort(
        read_years(candidate_season_path, year_start, year_end), KEYS, "candidate season"
    )
    if missing := set(SEASON_METRICS) - set(reference.columns):
        raise ValueError(f"reference season missing metrics {sorted(missing)}")
    if missing := set(SEASON_METRICS) - set(candidate.columns):
        raise ValueError(f"candidate season missing metrics {sorted(missing)}")
    require_same_keys(reference, candidate, KEYS)

    reference_stages = read_years(reference_stage_path, year_start, year_end)
    candidate_stages = read_years(candidate_stage_path, year_start, year_end)
    reference_timing = checked_sort(
        timing_features(reference, reference_stages, expected_stages), KEYS, "reference timing"
    )
    candidate_timing = checked_sort(
        timing_features(candidate, candidate_stages, expected_stages), KEYS, "candidate timing"
    )
    require_same_keys(reference_timing, candidate_timing, KEYS)

    timing_metrics = [f"stage{stage}_precip_share" for stage in range(1, expected_stages + 1)]
    timing_metrics += ["precipitation_timing_centroid", "precipitation_concentration_hhi"]
    summaries = {
        metric: paired_summary(reference[metric], candidate[metric])
        for metric in SEASON_METRICS
    }
    summaries.update(
        {
            metric: paired_summary(reference_timing[metric], candidate_timing[metric])
            for metric in timing_metrics
        }
    )
    paths = {
        "reference_season": reference_season_path,
        "reference_stages": reference_stage_path,
        "candidate_season": candidate_season_path,
        "candidate_stages": candidate_stage_path,
    }
    return {
        "schema": "bounded_paired_climate_feature_cell_comparison_v1",
        "role": "descriptive_feature_cell_comparison_not_emulator_holdout_yield_response_damage_or_scc",
        "reference_label": reference_label,
        "candidate_label": candidate_label,
        "year_start": year_start,
        "year_end": year_end,
        "season_rows": len(reference),
        "expected_stages": expected_stages,
        "inputs": {
            name: {"path": str(path), "sha256": sha256(path)} for name, path in paths.items()
        },
        "metrics": summaries,
        "result": "passed",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reference-season", type=Path, required=True)
    parser.add_argument("--reference-stages", type=Path, required=True)
    parser.add_argument("--candidate-season", type=Path, required=True)
    parser.add_argument("--candidate-stages", type=Path, required=True)
    parser.add_argument("--reference-label", required=True)
    parser.add_argument("--candidate-label", required=True)
    parser.add_argument("--year-start", type=int, required=True)
    parser.add_argument("--year-end", type=int, required=True)
    parser.add_argument("--expected-stages", type=int, default=3)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = compare(
        args.reference_season,
        args.reference_stages,
        args.candidate_season,
        args.candidate_stages,
        reference_label=args.reference_label,
        candidate_label=args.candidate_label,
        year_start=args.year_start,
        year_end=args.year_end,
        expected_stages=args.expected_stages,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"paired climate-feature comparison passed: {result['season_rows']} rows")


if __name__ == "__main__":
    main()
