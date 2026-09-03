#!/usr/bin/env python3
"""Count national panel support retained by fixed irrigation-share selectors.

The audit deliberately reads keys, eligibility flags, and the fixed share only;
it never reads yield magnitudes or estimates a response.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


THRESHOLDS = (10, 20, 30)
COLUMNS = [
    "county_geoid", "outcome_crop", "harvest_year", "irrigation_share_vintage",
    "irrigation_share", "irrigation_share_eligible", "outcome_value_eligible",
    *[f"rainfed_dominant_{value}pct" for value in THRESHOLDS],
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def audit(path: Path) -> dict[str, object]:
    frame = pd.read_parquet(path, columns=COLUMNS)
    if frame.empty:
        raise ValueError("national panel is empty")
    if frame.duplicated(["county_geoid", "outcome_crop", "harvest_year"]).any():
        raise ValueError("national panel has duplicate county-crop-year keys")
    if frame.county_geoid.astype("string").str.fullmatch(r"\d{5}").ne(True).any():
        raise ValueError("national panel has an invalid county GEOID")
    years = [int(value) for value in sorted(pd.to_numeric(frame.harvest_year, errors="raise").astype(int).unique())]
    if years != list(range(1981, 2020)):
        raise ValueError("national panel must cover every harvest year from 1981 through 2019")
    if set(frame.outcome_crop) != {"corn_grain", "soybeans"}:
        raise ValueError("national panel crop coverage changed")
    if set(pd.to_numeric(frame.irrigation_share_vintage, errors="raise").astype(int)) != {2017}:
        raise ValueError("selector must use only the preregistered 2017 Census share")
    if frame[["irrigation_share_eligible", "outcome_value_eligible"]].isna().any().any():
        raise ValueError("eligibility flags must be explicit")

    eligible = frame.irrigation_share_eligible.astype(bool)
    shares = pd.to_numeric(frame.irrigation_share, errors="coerce")
    if shares[eligible].isna().any() or not shares[eligible].between(0.0, 1.0).all():
        raise ValueError("eligible irrigation shares must be finite and within [0,1]")
    if shares[~eligible].notna().any():
        raise ValueError("ineligible irrigation shares must remain missing")
    for threshold in THRESHOLDS:
        column = f"rainfed_dominant_{threshold}pct"
        flag = frame[column]
        if flag.isna().any() or not flag.equals(eligible & shares.le(threshold / 100.0)):
            raise ValueError(f"{column} differs from the fixed-share rule")

    results = []
    for crop, part in frame.groupby("outcome_crop", sort=True):
        reported = part.outcome_value_eligible.astype(bool)
        crop_result: dict[str, object] = {
            "crop": crop,
            "panel_county_years": int(len(part)),
            "panel_counties": int(part.county_geoid.nunique()),
            "reported_outcome_county_years": int(reported.sum()),
            "share_eligible_county_years": int(part.irrigation_share_eligible.sum()),
            "share_eligible_counties": int(part.loc[part.irrigation_share_eligible, "county_geoid"].nunique()),
            "thresholds": [],
        }
        for threshold in THRESHOLDS:
            selected = part[f"rainfed_dominant_{threshold}pct"].astype(bool)
            selected_reported = selected & reported
            annual = selected_reported.groupby(part.harvest_year).sum().reindex(years, fill_value=0)
            crop_result["thresholds"].append({
                "irrigation_share_at_most_percent": threshold,
                "selected_county_years": int(selected.sum()),
                "selected_counties": int(part.loc[selected, "county_geoid"].nunique()),
                "selected_reported_county_years": int(selected_reported.sum()),
                "reported_outcome_retention_fraction": float(selected_reported.sum() / reported.sum()),
                "annual_selected_reported_minimum": int(annual.min()),
                "annual_selected_reported_maximum": int(annual.max()),
            })
        results.append(crop_result)

    return {
        "schema": "us_national_irrigation_selector_support_v1",
        "status": "validated_counts_only_selector_support_not_response_damage_or_scc",
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
    print("validated counts-only national irrigation-selector support")


if __name__ == "__main__":
    main()
