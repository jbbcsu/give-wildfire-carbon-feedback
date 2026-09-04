#!/usr/bin/env python3
"""Audit temporal completeness of the locked corn/soy joint selector sample.

Only county/crop/year keys and pre-existing eligibility/selector flags are
read. Yield magnitudes are excluded.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd


YEARS = list(range(1981, 2020))
COLUMNS = [
    "county_geoid", "outcome_crop", "harvest_year", "irrigation_share_vintage",
    "outcome_value_eligible", "rainfed_dominant_10pct",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def longest_run(values: list[int]) -> int:
    ordered = sorted(set(values))
    if not ordered:
        return 0
    best = current = 1
    for previous, value in zip(ordered, ordered[1:]):
        current = current + 1 if value == previous + 1 else 1
        best = max(best, current)
    return best


def audit(path: Path) -> dict[str, object]:
    frame = pd.read_parquet(path, columns=COLUMNS)
    if frame.empty or frame.duplicated(["county_geoid", "outcome_crop", "harvest_year"]).any():
        raise ValueError("panel is empty or has duplicate county-crop-year keys")
    if set(frame.outcome_crop) != {"corn_grain", "soybeans"}:
        raise ValueError("crop coverage changed")
    if set(pd.to_numeric(frame.irrigation_share_vintage, errors="raise").astype(int)) != {2017}:
        raise ValueError("fixed selector vintage changed")
    if sorted(pd.to_numeric(frame.harvest_year, errors="raise").astype(int).unique()) != YEARS:
        raise ValueError("year coverage changed")
    if frame[["outcome_value_eligible", "rainfed_dominant_10pct"]].isna().any().any():
        raise ValueError("eligibility and selector flags must be explicit")

    selected = frame.loc[
        frame.outcome_value_eligible.astype(bool) & frame.rainfed_dominant_10pct.astype(bool),
        ["county_geoid", "outcome_crop", "harvest_year"],
    ]
    corn = selected.loc[selected.outcome_crop == "corn_grain", ["county_geoid", "harvest_year"]]
    soy = selected.loc[selected.outcome_crop == "soybeans", ["county_geoid", "harvest_year"]]
    common = corn.merge(soy, on=["county_geoid", "harvest_year"], how="inner", validate="one_to_one")
    if common.empty:
        raise ValueError("joint crop support is empty")

    county_rows = []
    for county, group in common.groupby("county_geoid", sort=True):
        years = sorted(pd.to_numeric(group.harvest_year, errors="raise").astype(int).tolist())
        county_rows.append({
            "county_geoid": str(county),
            "years": len(years),
            "longest_consecutive_year_run": longest_run(years),
        })
    support = pd.DataFrame(county_rows)
    thresholds = [10, 20, 30, 39]
    run_thresholds = [5, 10, 20, 39]
    complete = support.loc[support.years == len(YEARS)]
    return {
        "schema": "us_national_joint_crop_temporal_support_v1",
        "status": "validated_key_only_joint_crop_temporal_support_not_response_damage_or_scc",
        "input": {"path": path.as_posix(), "sha256": sha256(path)},
        "selector_vintage": 2017,
        "irrigation_share_at_most_percent": 10,
        "years": YEARS,
        "common_county_years": int(len(common)),
        "common_counties": int(len(support)),
        "common_states": int(support.county_geoid.str[:2].nunique()),
        "county_year_count_minimum": int(support.years.min()),
        "county_year_count_median": float(support.years.median()),
        "county_year_count_maximum": int(support.years.max()),
        "longest_run_minimum": int(support.longest_consecutive_year_run.min()),
        "longest_run_median": float(support.longest_consecutive_year_run.median()),
        "longest_run_maximum": int(support.longest_consecutive_year_run.max()),
        "counties_with_at_least_n_years": {
            str(value): int((support.years >= value).sum()) for value in thresholds
        },
        "counties_with_consecutive_run_at_least_n_years": {
            str(value): int((support.longest_consecutive_year_run >= value).sum()) for value in run_thresholds
        },
        "complete_1981_2019_counties": int(len(complete)),
        "complete_1981_2019_states": int(complete.county_geoid.str[:2].nunique()),
        "yield_magnitudes_read": False,
        "balanced_panel_required_for_future_model": False,
        "primary_selector_changed": False,
        "irrigation_effect_authorized": False,
        "response_damage_or_scc_authorized": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.panel)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("validated key-only national joint-crop temporal support")


if __name__ == "__main__":
    main()
