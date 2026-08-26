#!/usr/bin/env python3
"""Audit national all-practice NASS support against the fixed 2019 proxy.

This is intentionally separate from the regional paired-practice audit.  It
uses the same pinned TIGER file and Census change-page parser but validates one
all-practice outcome per crop-county-year.  Page hits are conservative review
flags, not inferred historical crosswalks.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

from audit_nass_direct_practice_geography import (
    GEOMETRY_CHANGE_CATEGORIES,
    load_tiger_counties,
    parse_change_page,
)


KEYS = ["outcome_crop", "county_geoid", "harvest_year"]


def _strict_false(series: pd.Series, label: str) -> None:
    if pd.api.types.is_bool_dtype(series):
        value = series.astype("boolean")
    else:
        text = series.astype("string").str.strip().str.lower()
        if text.isna().any() or (~text.isin(["true", "false"])).any():
            raise ValueError(f"{label} must contain only true/false")
        value = text.eq("true")
    if value.isna().any() or value.any():
        raise ValueError(f"{label} unexpectedly authorizes downstream use")


def audit_geography(
    panel: pd.DataFrame,
    tiger: pd.DataFrame,
    changes: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    required = {
        "county_geoid", "state", "county_name", "outcome_crop", "harvest_year",
        "irrigation_practice", "response_estimation_authorized", "scc_authorized",
    }
    if missing := required - set(panel.columns):
        raise ValueError(f"national all-practice panel lacks columns {sorted(missing)}")
    if panel.empty:
        raise ValueError("national all-practice panel is empty")
    work = panel.copy()
    for column in ["county_geoid", "state", "county_name", "outcome_crop", "irrigation_practice"]:
        work[column] = work[column].astype("string").str.strip()
    work["state"] = work.state.str.upper()
    work["harvest_year"] = pd.to_numeric(work.harvest_year, errors="raise").astype("int64")
    _strict_false(work.response_estimation_authorized, "response gate")
    _strict_false(work.scc_authorized, "SCC gate")
    if set(work.irrigation_practice) != {"all_practices"}:
        raise ValueError("national geography route requires all-practice outcomes only")
    if work.duplicated(KEYS).any():
        raise ValueError("national all-practice panel duplicates crop-county-year keys")
    if work.county_geoid.str.fullmatch(r"\d{5}").ne(True).any():
        raise ValueError("national all-practice panel contains malformed GEOIDs")

    unique = work.groupby(["county_geoid", "state", "county_name"], observed=True).agg(
        outcome_crops=("outcome_crop", lambda values: ";".join(sorted(set(values)))),
        first_outcome_year=("harvest_year", "min"),
        last_outcome_year=("harvest_year", "max"),
        crop_county_years=("harvest_year", "size"),
    ).reset_index()
    if unique.duplicated("county_geoid").any():
        raise ValueError("national NASS GEOID maps to inconsistent county metadata")
    output = unique.merge(tiger, on="county_geoid", how="left", validate="one_to_one")
    output["tiger2019_exact_geoid_match"] = output.tiger2019_county_name.notna()

    hits = changes.loc[changes.mentioned_geoid.isin(output.county_geoid)].copy()
    grouped = hits.groupby("mentioned_geoid", observed=True).agg(
        census_change_categories=("change_category", lambda values: ";".join(sorted(set(values)))),
        census_change_decades=("source_decade", lambda values: ";".join(str(value) for value in sorted(set(values)))),
    ).reset_index().rename(columns={"mentioned_geoid": "county_geoid"})
    entries = hits[
        ["mentioned_geoid", "source_decade", "change_category", "listed_geoid", "entry_text"]
    ].drop_duplicates()
    counts = entries.groupby("mentioned_geoid", observed=True).size().rename(
        "census_change_entry_count"
    ).reset_index().rename(columns={"mentioned_geoid": "county_geoid"})
    grouped = grouped.merge(counts, on="county_geoid", how="left", validate="one_to_one")
    output = output.merge(grouped, on="county_geoid", how="left", validate="one_to_one")
    output["census_change_categories"] = output.census_change_categories.fillna("")
    output["census_change_decades"] = output.census_change_decades.fillna("")
    output["census_change_entry_count"] = output.census_change_entry_count.fillna(0).astype("int64")
    output["census_change_page_hit"] = output.census_change_entry_count.gt(0)
    output["geometry_change_review_required"] = output.census_change_categories.map(
        lambda value: bool(set(str(value).split(";")) & GEOMETRY_CHANGE_CATEGORIES)
    )
    output["geography_gate_status"] = "fixed_2019_proxy_no_substantial_page_hit"
    output.loc[
        output.census_change_categories.eq("name_or_code"), "geography_gate_status"
    ] = "name_or_code_review_no_boundary_change_in_page_entry"
    output.loc[
        output.geometry_change_review_required, "geography_gate_status"
    ] = "blocked_pending_historical_boundary_resolution"
    output.loc[
        ~output.tiger2019_exact_geoid_match, "geography_gate_status"
    ] = "blocked_missing_tiger2019_geometry"
    output["minor_boundary_change_caveat"] = True
    output["feature_construction_eligible"] = (
        output.tiger2019_exact_geoid_match & ~output.geometry_change_review_required
    )
    output["response_estimation_authorized"] = False
    output["scc_authorized"] = False
    output = output.sort_values("county_geoid").reset_index(drop=True)

    audit: dict[str, Any] = {
        "role": "national_all_practice_historical_geography_gate_only_not_response_or_scc",
        "unique_nass_counties": int(len(output)),
        "exact_tiger2019_geoid_matches": int(output.tiger2019_exact_geoid_match.sum()),
        "missing_tiger2019_geoid_matches": int((~output.tiger2019_exact_geoid_match).sum()),
        "census_change_page_hit_counties": int(output.census_change_page_hit.sum()),
        "geometry_change_review_counties": int(output.geometry_change_review_required.sum()),
        "name_or_code_only_review_counties": int(output.census_change_categories.eq("name_or_code").sum()),
        "fixed_2019_proxy_candidates_after_screen": int(output.feature_construction_eligible.sum()),
        "geometry_change_review_geoids": sorted(
            output.loc[output.geometry_change_review_required, "county_geoid"].astype(str)
        ),
        "page_scope_caveat": (
            "Census pages enumerate substantial changes plus entity/name/code changes; "
            "no page hit does not establish absence of smaller boundary changes"
        ),
        "measurement_choice": (
            "2019 TIGER polygons are a fixed county-average exposure proxy; page-hit "
            "counties are excluded pending historical-boundary resolution"
        ),
        "response_estimated": False,
        "scc_calculated": False,
    }
    return output, audit


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--tiger-counties", type=Path, required=True)
    for decade in (1980, 1990, 2000, 2010):
        parser.add_argument(f"--change-{decade}", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--audit-out", type=Path, required=True)
    args = parser.parse_args()
    changes = pd.concat(
        [
            parse_change_page(getattr(args, f"change_{decade}"), decade)
            for decade in (1980, 1990, 2000, 2010)
        ],
        ignore_index=True,
    )
    output, audit = audit_geography(
        pd.read_parquet(args.panel), load_tiger_counties(args.tiger_counties), changes
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.audit_out.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(args.out, index=False)
    args.audit_out.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        f"audited {len(output)} national NASS counties: "
        f"{audit['fixed_2019_proxy_candidates_after_screen']} fixed-proxy candidates; "
        "no response estimated"
    )


if __name__ == "__main__":
    main()
