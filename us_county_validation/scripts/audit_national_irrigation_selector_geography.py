#!/usr/bin/env python3
"""Audit geographic concentration of fixed national rainfed selectors.

This outcome-blind audit reads only county/crop keys and the already frozen
2017 irrigation-share selector flags. It does not read yield magnitudes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd


THRESHOLDS = (10, 20, 30)
COLUMNS = [
    "county_geoid", "outcome_crop", "harvest_year", "irrigation_share_vintage",
    "irrigation_share_eligible", "outcome_value_eligible",
    *[f"rainfed_dominant_{value}pct" for value in THRESHOLDS],
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def concentration(counts: pd.Series) -> dict[str, float | int]:
    positive = counts[counts > 0].astype(float).sort_values(ascending=False)
    if positive.empty:
        raise ValueError("selected support has no positive state counts")
    shares = positive / positive.sum()
    return {
        "states": int(len(positive)),
        "top1_state_county_year_share": float(shares.iloc[0]),
        "top5_state_county_year_share": float(shares.iloc[:5].sum()),
        "state_county_year_hhi": float((shares * shares).sum()),
        "minimum_state_county_years": int(positive.min()),
        "maximum_state_county_years": int(positive.max()),
    }


def audit(path: Path) -> dict[str, object]:
    frame = pd.read_parquet(path, columns=COLUMNS)
    if frame.empty:
        raise ValueError("national panel is empty")
    keys = ["county_geoid", "outcome_crop", "harvest_year"]
    if frame.duplicated(keys).any():
        raise ValueError("national panel has duplicate county-crop-year keys")
    geoids = frame.county_geoid.astype("string")
    if geoids.str.fullmatch(r"\d{5}").ne(True).any():
        raise ValueError("national panel has an invalid county GEOID")
    frame = frame.assign(state_fips=geoids.str[:2])
    years = [int(value) for value in sorted(
        pd.to_numeric(frame.harvest_year, errors="raise").astype(int).unique()
    )]
    if years != list(range(1981, 2020)):
        raise ValueError("national panel must cover 1981 through 2019")
    if set(frame.outcome_crop) != {"corn_grain", "soybeans"}:
        raise ValueError("national panel crop coverage changed")
    if set(pd.to_numeric(frame.irrigation_share_vintage, errors="raise").astype(int)) != {2017}:
        raise ValueError("selector vintage changed")
    if frame[["irrigation_share_eligible", "outcome_value_eligible"]].isna().any().any():
        raise ValueError("eligibility flags must be explicit")

    results = []
    for crop, part in frame.groupby("outcome_crop", sort=True):
        reported = part.outcome_value_eligible.astype(bool)
        crop_result: dict[str, object] = {
            "crop": str(crop),
            "reported_states": int(part.loc[reported, "state_fips"].nunique()),
            "thresholds": [],
        }
        for threshold in THRESHOLDS:
            selected = part[f"rainfed_dominant_{threshold}pct"]
            if selected.isna().any():
                raise ValueError("selector flags must be explicit")
            selected_reported = selected.astype(bool) & reported
            counts = part.loc[selected_reported].groupby("state_fips").size()
            metrics = concentration(counts)
            metrics.update({
                "irrigation_share_at_most_percent": threshold,
                "selected_reported_county_years": int(selected_reported.sum()),
                "reported_state_retention_fraction": float(metrics["states"] / crop_result["reported_states"]),
            })
            crop_result["thresholds"].append(metrics)
        results.append(crop_result)

    return {
        "schema": "us_national_irrigation_selector_geography_v1",
        "status": "validated_outcome_blind_geographic_support_not_response_damage_or_scc",
        "input": {"path": path.as_posix(), "sha256": sha256(path)},
        "years": years,
        "selector_vintage": 2017,
        "results": results,
        "yield_magnitudes_read": False,
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
    print("validated national irrigation-selector geographic support")


if __name__ == "__main__":
    main()
