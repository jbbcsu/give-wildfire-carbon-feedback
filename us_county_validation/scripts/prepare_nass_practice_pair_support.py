#!/usr/bin/env python3
"""Select a bounded real paired-practice NASS support table without fitting it."""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from audit_nass_irrigation_practice_coverage import prepare_yield


CROP_TO_OUTCOME = {"corn": "corn_grain", "soybeans": "soybeans"}
PRACTICE_MAP = {"IRRIGATED": "irrigated", "NON-IRRIGATED": "non_irrigated"}


def select_support(
    frames: list[pd.DataFrame], county_geoid: str, harvest_year: int
) -> pd.DataFrame:
    if not isinstance(county_geoid, str) or not county_geoid.isdigit() or len(county_geoid) != 5:
        raise ValueError("county_geoid must be a five-digit GEOID")
    if not frames:
        raise ValueError("At least one prepared NASS frame is required")
    combined = pd.concat(frames, ignore_index=True)
    required = {
        "crop", "year", "county_geoid", "practice", "yield_eligible",
        "analysis_value", "value_raw", "state_alpha", "county_name",
    }
    if missing := required - set(combined.columns):
        raise ValueError(f"Prepared NASS support lacks columns {sorted(missing)}")
    selected = combined.loc[
        combined.county_geoid.eq(county_geoid)
        & combined.year.eq(harvest_year)
        & combined.yield_eligible
        & combined.crop.isin(CROP_TO_OUTCOME)
    ].copy()
    if selected.empty:
        raise ValueError("No positive paired-practice support matches the requested key")
    if selected.duplicated(["crop", "practice"]).any():
        raise ValueError("Requested support contains duplicate crop/practice rows")
    for crop, group in selected.groupby("crop", observed=True):
        if set(group.practice) != set(PRACTICE_MAP):
            raise ValueError(f"{crop} does not contain exactly both irrigation practices")
    if set(selected.crop) != set(CROP_TO_OUTCOME):
        raise ValueError("Requested smoke must contain both corn and soybean support")
    if selected.state_alpha.nunique() != 1 or selected.county_name.nunique() != 1:
        raise ValueError("Selected support has inconsistent county metadata")
    values = pd.to_numeric(selected.analysis_value, errors="coerce")
    if values.isna().any() or not np.isfinite(values).all() or (values <= 0).any():
        raise ValueError("Selected NASS support contains invalid yield values")
    output = pd.DataFrame(
        {
            "county_geoid": selected.county_geoid.astype("string"),
            "state": selected.state_alpha.astype("string"),
            "county_name": selected.county_name.astype("string"),
            "outcome_crop": selected.crop.map(CROP_TO_OUTCOME),
            "harvest_year": selected.year.astype("int64"),
            "irrigation_practice": selected.practice.map(PRACTICE_MAP),
            "yield_bu_acre": values.astype(float),
            "source_value_raw": selected.value_raw.astype("string"),
            "outcome_source_id": "nass_quickstats_direct_practice_screen",
            "sample_role": "direct_practice_pair",
            "weather_exposure_role": "shared_county_polygon_proxy_across_practices",
            "analysis_role": "historical_county_validation_smoke_only",
            "feature_construction_eligible": True,
            "response_estimation_authorized": False,
            "scc_authorized": False,
        }
    )
    keys = ["county_geoid", "outcome_crop", "harvest_year", "irrigation_practice"]
    if output.duplicated(keys).any() or len(output) != 4:
        raise ValueError("Selected support does not contain the exact four-row smoke product")
    return output.sort_values(keys).reset_index(drop=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corn-irrigated", required=True)
    parser.add_argument("--corn-non-irrigated", required=True)
    parser.add_argument("--soy-irrigated", required=True)
    parser.add_argument("--soy-non-irrigated", required=True)
    parser.add_argument("--county-geoid", required=True)
    parser.add_argument("--harvest-year", required=True, type=int)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    paths = [
        args.corn_irrigated,
        args.corn_non_irrigated,
        args.soy_irrigated,
        args.soy_non_irrigated,
    ]
    output = select_support(
        [prepare_yield(Path(path)) for path in paths],
        args.county_geoid,
        args.harvest_year,
    )
    destination = Path(args.out)
    destination.parent.mkdir(parents=True, exist_ok=True)
    output.to_parquet(destination, index=False)
    print(
        f"wrote {len(output)} real NASS support rows for {args.county_geoid}/"
        f"{args.harvest_year}; no response estimated"
    )


if __name__ == "__main__":
    main()
