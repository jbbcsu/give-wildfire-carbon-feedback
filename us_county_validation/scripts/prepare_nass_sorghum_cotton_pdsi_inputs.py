#!/usr/bin/env python3
"""Geography-gate paired sorghum/cotton outcomes and prepare PDSI inputs."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd

from audit_nass_direct_practice_geography import audit_geography, load_tiger_counties, parse_change_page


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 << 20), b""):
            value.update(block)
    return value.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--calendar", type=Path, required=True)
    parser.add_argument("--tiger-counties", type=Path, required=True)
    for decade in (1980, 1990, 2000, 2010):
        parser.add_argument(f"--change-{decade}", dest=f"change_{decade}", type=Path, required=True)
    parser.add_argument("--geography-out", type=Path, required=True)
    parser.add_argument("--inventory-out", type=Path, required=True)
    parser.add_argument("--eligible-panel-out", type=Path, required=True)
    parser.add_argument("--primary-calendar-out", type=Path, required=True)
    parser.add_argument("--receipt-out", type=Path, required=True)
    args = parser.parse_args()

    source = pd.read_parquet(args.panel)
    adapted = source.rename(columns={
        "crop": "outcome_crop", "state_alpha": "state", "practice": "irrigation_practice",
    }).copy()
    adapted["response_estimation_authorized"] = False
    adapted["scc_authorized"] = False
    changes = pd.concat(
        [parse_change_page(getattr(args, f"change_{decade}"), decade) for decade in (1980, 1990, 2000, 2010)],
        ignore_index=True,
    )
    geography, geography_audit = audit_geography(adapted, load_tiger_counties(args.tiger_counties), changes)
    eligible_geoids = set(geography.loc[geography.feature_construction_eligible, "county_geoid"].astype(str))
    eligible = source.loc[source.county_geoid.astype(str).isin(eligible_geoids)].copy()
    pair_keys = ["crop", "county_geoid", "harvest_year"]
    if not eligible.groupby(pair_keys).practice.agg(set).map(lambda x: x == {"irrigated", "non_irrigated"}).all():
        raise ValueError("geography-filtered panel lost exact practice pairs")

    selected_geography = geography.loc[geography.feature_construction_eligible].copy()
    selected_geography["historical_status"] = selected_geography.census_change_categories.eq("name_or_code").map(
        {True: "explicit_crosswalk", False: "stable"}
    )
    selected_geography["crosswalk_source_id"] = selected_geography.historical_status.map(
        {"explicit_crosswalk": "us_census_county_changes_decade_pages", "stable": "not_applicable"}
    )
    inventory = pd.DataFrame({
        "county_geoid": selected_geography.county_geoid.astype(str),
        "state": selected_geography.state,
        "boundary_source_id": "us_census_tigerline_2019_county",
        "boundary_vintage": "2019",
        "historical_status": selected_geography.historical_status,
        "crosswalk_source_id": selected_geography.crosswalk_source_id,
        "feature_construction_eligible": True,
        "scc_authorized": False,
    }).sort_values("county_geoid")

    calendar = pd.read_csv(args.calendar)
    calendar = calendar.loc[calendar.calendar_role.eq("fixed_primary")].copy()
    support = eligible[["crop", "state_alpha", "harvest_year"]].drop_duplicates()
    primary = support.merge(
        calendar, left_on=["crop", "state_alpha", "harvest_year"],
        right_on=["calendar_crop", "state", "harvest_year"], how="left", validate="one_to_one",
    )[calendar.columns]
    if primary.isna().any().any() or len(primary) != len(support):
        raise ValueError("eligible crop/state/year support lacks a primary calendar")

    for path in [args.geography_out, args.inventory_out, args.eligible_panel_out, args.primary_calendar_out]:
        path.parent.mkdir(parents=True, exist_ok=True)
    geography.to_csv(args.geography_out, index=False)
    inventory.to_csv(args.inventory_out, index=False)
    eligible.to_parquet(args.eligible_panel_out, index=False)
    primary.to_csv(args.primary_calendar_out, index=False)
    pairs = eligible.drop_duplicates(pair_keys)
    receipt = {
        "status": "geography_gate_and_primary_calendar_inputs_pass",
        "source_panel_sha256": digest(args.panel), "source_calendar_sha256": digest(args.calendar),
        "unique_source_counties": int(source.county_geoid.nunique()),
        "exact_tiger2019_matches": geography_audit["exact_tiger2019_geoid_matches"],
        "geometry_review_counties_excluded": geography_audit["geometry_change_review_counties"],
        "eligible_counties": int(inventory.county_geoid.nunique()),
        "eligible_pairs_by_crop": {k: int(v) for k, v in pairs.groupby("crop").size().items()},
        "eligible_counties_by_crop": {k: int(v) for k, v in pairs.groupby("crop").county_geoid.nunique().items()},
        "primary_calendar_crop_state_year_rows": int(len(primary)),
        "all_cotton_calendar_for_upland_outcome": True,
        "calendar_shared_across_practices": True,
        "weather_joined": False, "response_estimation_authorized": False, "scc_authorized": False,
        "outputs": {
            "geography": {"path": str(args.geography_out), "sha256": digest(args.geography_out)},
            "inventory": {"path": str(args.inventory_out), "sha256": digest(args.inventory_out)},
            "eligible_panel": {"path": str(args.eligible_panel_out), "sha256": digest(args.eligible_panel_out)},
            "primary_calendar": {"path": str(args.primary_calendar_out), "sha256": digest(args.primary_calendar_out)},
        },
    }
    args.receipt_out.parent.mkdir(parents=True, exist_ok=True)
    args.receipt_out.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
