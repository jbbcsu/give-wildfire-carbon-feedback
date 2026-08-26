#!/usr/bin/env python3
"""Build the complete paired-practice NASS yield support panel.

This script is intentionally limited to outcome-support construction.  It does
not join weather, calculate a yield response, or authorize estimation.  A
county--crop--year enters only when both IRRIGATED and NON-IRRIGATED yields are
positive numeric observations in the exact locked Quick Stats series.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from audit_nass_irrigation_practice_coverage import prepare_yield


CROP_TO_OUTCOME = {
    "corn": "corn_grain",
    "soybeans": "soybeans",
    "wheat": "wheat_all_classes",
}
PRACTICE_MAP = {"IRRIGATED": "irrigated", "NON-IRRIGATED": "non_irrigated"}
PAIR_KEYS = ["crop", "year", "county_geoid"]


def build_panel(
    frames: list[pd.DataFrame], year_min: int = 1981, year_max: int = 2019
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Return a long two-row-per-pair support panel and a non-result audit."""
    if not frames:
        raise ValueError("At least one prepared NASS frame is required")
    if year_min > year_max:
        raise ValueError("year_min must not exceed year_max")
    combined = pd.concat(frames, ignore_index=True)
    required = {
        "crop", "year", "county_geoid", "practice", "yield_eligible",
        "analysis_value", "value_raw", "state_alpha", "county_name",
    }
    if missing := required - set(combined.columns):
        raise ValueError(f"Prepared NASS support lacks columns {sorted(missing)}")
    if set(combined["crop"]) != set(CROP_TO_OUTCOME):
        raise ValueError(
            "Inputs must contain exactly corn, soybeans, and all-classes wheat"
        )
    if set(combined["practice"]) != set(PRACTICE_MAP):
        raise ValueError("Inputs must contain exactly both irrigation practices")
    if combined.duplicated(PAIR_KEYS + ["practice"]).any():
        examples = combined.loc[
            combined.duplicated(PAIR_KEYS + ["practice"], keep=False),
            PAIR_KEYS + ["practice"],
        ].head(5)
        raise ValueError(f"Duplicate crop/county/year/practice keys: {examples.to_dict('records')}")

    eligible = combined.loc[
        combined["yield_eligible"] & combined["year"].between(year_min, year_max)
    ].copy()
    if eligible.empty:
        raise ValueError("No eligible NASS observations exist in the requested year window")
    pair_counts = eligible.groupby(PAIR_KEYS, observed=True)["practice"].nunique()
    paired_keys = pair_counts.loc[pair_counts.eq(len(PRACTICE_MAP))].reset_index()[PAIR_KEYS]
    if paired_keys.empty:
        raise ValueError("No county/crop/year has both irrigation practices")
    paired = eligible.merge(paired_keys, on=PAIR_KEYS, how="inner", validate="many_to_one")
    if len(paired) != 2 * len(paired_keys):
        raise ValueError("Paired support must contain exactly two practice rows per key")

    metadata = paired.groupby(PAIR_KEYS, observed=True).agg(
        state_count=("state_alpha", "nunique"),
        county_name_count=("county_name", "nunique"),
    )
    if (metadata[["state_count", "county_name_count"]] != 1).any(axis=None):
        raise ValueError("Practice-paired rows disagree on state or county metadata")
    values = pd.to_numeric(paired["analysis_value"], errors="coerce")
    if values.isna().any() or not np.isfinite(values).all() or (values <= 0).any():
        raise ValueError("Paired support contains a nonpositive or nonfinite yield")

    panel = pd.DataFrame(
        {
            "county_geoid": paired["county_geoid"].astype("string"),
            "state": paired["state_alpha"].astype("string"),
            "county_name": paired["county_name"].astype("string"),
            "outcome_crop": paired["crop"].map(CROP_TO_OUTCOME).astype("string"),
            "harvest_year": paired["year"].astype("int64"),
            "irrigation_practice": paired["practice"].map(PRACTICE_MAP).astype("string"),
            "yield_bu_acre": values.astype(float),
            "source_value_raw": paired["value_raw"].astype("string"),
            "outcome_source_id": "nass_quickstats_direct_practice_screen",
            "sample_role": "regional_direct_practice_support_inventory",
            "weather_exposure_role": "shared_county_polygon_proxy_across_practices",
            "calendar_mapping_status": np.where(
                paired["crop"].eq("wheat"),
                "blocked_all_classes_wheat_requires_class_weights",
                "state_crop_calendar_available_pending_join",
            ),
            "geography_harmonization_status": "pending_historical_county_change_audit",
            "feature_construction_eligible": False,
            "response_estimation_authorized": False,
            "scc_authorized": False,
        }
    )
    output_keys = ["outcome_crop", "county_geoid", "harvest_year", "irrigation_practice"]
    if panel.duplicated(output_keys).any():
        raise ValueError("Output contains duplicate outcome support keys")
    pair_size = panel.groupby(output_keys[:-1], observed=True).size()
    if not pair_size.eq(2).all():
        raise ValueError("Output pair invariant failed")
    panel = panel.sort_values(output_keys).reset_index(drop=True)

    crop_audit: dict[str, Any] = {}
    for outcome_crop, group in panel.groupby("outcome_crop", observed=True, sort=True):
        pairs = group.drop_duplicates(output_keys[:-1])
        crop_audit[str(outcome_crop)] = {
            "paired_county_years": int(len(pairs)),
            "long_practice_rows": int(len(group)),
            "counties": int(group["county_geoid"].nunique()),
            "states": int(group["state"].nunique()),
            "first_year": int(group["harvest_year"].min()),
            "last_year": int(group["harvest_year"].max()),
            "year_count": int(group["harvest_year"].nunique()),
            "calendar_status": str(group["calendar_mapping_status"].iloc[0]),
        }
    audit = {
        "role": "paired NASS outcome support inventory only; not a climate-yield result",
        "requested_year_min": int(year_min),
        "requested_year_max": int(year_max),
        "paired_county_years_total": int(len(panel) // 2),
        "long_practice_rows_total": int(len(panel)),
        "crops": crop_audit,
        "weather_joined": False,
        "geography_harmonized": False,
        "response_estimated": False,
        "scc_calculated": False,
        "wheat_gate": (
            "all-classes wheat outcomes remain blocked from weather-feature construction "
            "until winter, spring, and durum outcome/exposure weights are specified"
        ),
    }
    return panel, audit


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corn-irrigated", required=True)
    parser.add_argument("--corn-non-irrigated", required=True)
    parser.add_argument("--soy-irrigated", required=True)
    parser.add_argument("--soy-non-irrigated", required=True)
    parser.add_argument("--wheat-irrigated", required=True)
    parser.add_argument("--wheat-non-irrigated", required=True)
    parser.add_argument("--year-min", type=int, default=1981)
    parser.add_argument("--year-max", type=int, default=2019)
    parser.add_argument("--out", required=True)
    parser.add_argument("--audit-out", required=True)
    args = parser.parse_args()
    paths = [
        args.corn_irrigated,
        args.corn_non_irrigated,
        args.soy_irrigated,
        args.soy_non_irrigated,
        args.wheat_irrigated,
        args.wheat_non_irrigated,
    ]
    panel, audit = build_panel(
        [prepare_yield(Path(path)) for path in paths], args.year_min, args.year_max
    )
    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    panel.to_parquet(output, index=False)
    audit_output = Path(args.audit_out)
    audit_output.parent.mkdir(parents=True, exist_ok=True)
    audit_output.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n")
    print(
        f"wrote {len(panel)} practice rows ({len(panel) // 2} paired county-years); "
        "no weather joined and no response estimated"
    )


if __name__ == "__main__":
    main()
