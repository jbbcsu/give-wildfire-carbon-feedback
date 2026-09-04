#!/usr/bin/env python3
"""Audit cross-crop overlap under the already locked fixed-share selectors.

Only county/crop/year keys, eligibility flags, and selector flags are read.
Yield magnitudes are excluded.
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
    "outcome_value_eligible", "irrigation_share_eligible",
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
    if frame.empty or frame.duplicated(["county_geoid", "outcome_crop", "harvest_year"]).any():
        raise ValueError("panel is empty or has duplicate county-crop-year keys")
    if set(frame.outcome_crop) != {"corn_grain", "soybeans"}:
        raise ValueError("crop coverage changed")
    if set(pd.to_numeric(frame.irrigation_share_vintage, errors="raise").astype(int)) != {2017}:
        raise ValueError("fixed selector vintage changed")
    years = list(range(1981, 2020))
    if sorted(pd.to_numeric(frame.harvest_year, errors="raise").astype(int).unique()) != years:
        raise ValueError("year coverage changed")
    if frame[COLUMNS[4:]].isna().any().any():
        raise ValueError("selector and eligibility flags must be explicit")

    results = []
    for threshold in THRESHOLDS:
        flag = f"rainfed_dominant_{threshold}pct"
        selected = frame.loc[frame[flag].astype(bool) & frame.outcome_value_eligible.astype(bool), ["county_geoid", "outcome_crop", "harvest_year"]]
        corn = selected.loc[selected.outcome_crop == "corn_grain", ["county_geoid", "harvest_year"]]
        soy = selected.loc[selected.outcome_crop == "soybeans", ["county_geoid", "harvest_year"]]
        overlap = corn.merge(soy, on=["county_geoid", "harvest_year"], how="inner", validate="one_to_one")
        corn_counties = set(corn.county_geoid)
        soy_counties = set(soy.county_geoid)
        common_counties = corn_counties & soy_counties
        union_counties = corn_counties | soy_counties
        annual = overlap.groupby("harvest_year").size().reindex(years, fill_value=0)
        results.append({
            "irrigation_share_at_most_percent": threshold,
            "corn_selected_county_years": int(len(corn)),
            "soybean_selected_county_years": int(len(soy)),
            "common_county_years": int(len(overlap)),
            "common_county_year_fraction_of_smaller_crop_panel": float(len(overlap) / min(len(corn), len(soy))),
            "corn_selected_counties": len(corn_counties),
            "soybean_selected_counties": len(soy_counties),
            "common_counties": len(common_counties),
            "county_set_jaccard": float(len(common_counties) / len(union_counties)),
            "annual_common_county_years_minimum": int(annual.min()),
            "annual_common_county_years_maximum": int(annual.max()),
        })

    return {
        "schema": "us_national_cross_crop_selector_overlap_v1",
        "status": "validated_key_only_cross_crop_overlap_not_response_damage_or_scc",
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
    print("validated key-only national cross-crop selector overlap")


if __name__ == "__main__":
    main()
