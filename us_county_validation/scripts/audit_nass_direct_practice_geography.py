#!/usr/bin/env python3
"""Audit paired NASS support against TIGER 2019 and Census change notices.

The Census pages enumerate substantial changes, plus new/deleted entities and
name/code corrections.  A page hit is a conservative review flag rather than
an inferred crosswalk.  Absence from those pages does not prove that no minor
boundary adjustment occurred.
"""
from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path
from typing import Any

import pandas as pd
import shapefile


CATEGORY_MAP = {
    "New Counties or County Equivalent Entities": "new_entity",
    "Deleted Counties or County Equivalent Entities": "deleted_entity",
    "Name and/or Code Changes or Corrections for Counties or County Equivalent Entities": (
        "name_or_code"
    ),
    "Substantial County or County Equivalent Entity Boundary Changes": (
        "substantial_boundary"
    ),
    "Substantial County or County Equivalent Boundary Changes": "substantial_boundary",
}
GEOMETRY_CHANGE_CATEGORIES = {"new_entity", "deleted_entity", "substantial_boundary"}
FIPS_PATTERN = re.compile(r"\((\d{2})-(\d{3})\)")
TOKEN_PATTERN = re.compile(r"<h4[^>]*>(.*?)</h4>|<li[^>]*>(.*?)</li>", re.I | re.S)
TAG_PATTERN = re.compile(r"<[^>]+>")


def _clean_html(fragment: str) -> str:
    fragment = re.sub(r"<br\s*/?>", " ", fragment, flags=re.I)
    return " ".join(html.unescape(TAG_PATTERN.sub(" ", fragment)).split())


def parse_change_page(path: Path, decade: int) -> pd.DataFrame:
    """Parse one pinned Census decade page into mentioned-FIPS records."""
    if decade not in {1980, 1990, 2000, 2010}:
        raise ValueError("decade must be one of 1980, 1990, 2000, or 2010")
    source = path.read_text(encoding="utf-8")
    expected_title = f"Changes to Counties or County Equivalent Entities: {decade}s"
    if expected_title not in source:
        raise ValueError(f"{path}: expected Census decade title is absent")
    category: str | None = None
    records: list[dict[str, object]] = []
    for match in TOKEN_PATTERN.finditer(source):
        heading, list_item = match.groups()
        if heading is not None:
            category = CATEGORY_MAP.get(_clean_html(heading))
            continue
        if category is None or list_item is None:
            continue
        entry_text = _clean_html(list_item)
        codes = [state + county for state, county in FIPS_PATTERN.findall(entry_text)]
        if not codes:
            continue
        listed_geoid = codes[0]
        effective_years = sorted(
            {
                int(value)
                for value in re.findall(
                    r"(?:effective|reported as of)[^.;]{0,100}?((?:19|20)\d{2})",
                    entry_text,
                    flags=re.I,
                )
            }
        )
        for mentioned_geoid in sorted(set(codes)):
            records.append(
                {
                    "source_decade": decade,
                    "change_category": category,
                    "listed_geoid": listed_geoid,
                    "mentioned_geoid": mentioned_geoid,
                    "mention_role": (
                        "listed_entity" if mentioned_geoid == listed_geoid else "referenced_entity"
                    ),
                    "effective_years": ";".join(str(value) for value in effective_years),
                    "entry_text": entry_text,
                    "source_url": (
                        "https://www.census.gov/programs-surveys/geography/"
                        f"technical-documentation/county-changes/{decade}.html"
                    ),
                }
            )
    if not records:
        raise ValueError(f"{path}: no Census county-change records parsed")
    frame = pd.DataFrame(records).drop_duplicates().sort_values(
        ["source_decade", "change_category", "listed_geoid", "mentioned_geoid"]
    )
    if not set(frame["change_category"]).issubset(set(CATEGORY_MAP.values())):
        raise ValueError("Unexpected Census change category")
    return frame.reset_index(drop=True)


def load_tiger_counties(path: Path) -> pd.DataFrame:
    reader = shapefile.Reader(str(path))
    fields = [field[0] for field in reader.fields[1:]]
    required = {"GEOID", "STATEFP", "COUNTYFP", "NAME"}
    if missing := required - set(fields):
        raise ValueError(f"TIGER county file lacks fields {sorted(missing)}")
    positions = {name: fields.index(name) for name in required}
    rows = []
    for record in reader.iterRecords():
        state = str(record[positions["STATEFP"]]).zfill(2)
        county = str(record[positions["COUNTYFP"]]).zfill(3)
        geoid = str(record[positions["GEOID"]]).zfill(5)
        if state + county != geoid:
            raise ValueError("TIGER STATEFP/COUNTYFP do not reconcile to GEOID")
        rows.append(
            {
                "county_geoid": geoid,
                "tiger2019_county_name": str(record[positions["NAME"]]),
            }
        )
    frame = pd.DataFrame(rows)
    if frame.empty or frame.duplicated("county_geoid").any():
        raise ValueError("TIGER county GEOIDs are empty or duplicated")
    return frame


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
        raise ValueError(f"NASS support panel lacks columns {sorted(missing)}")
    if panel["response_estimation_authorized"].any() or panel["scc_authorized"].any():
        raise ValueError("Geography audit cannot consume response- or SCC-authorized rows")
    keys = ["outcome_crop", "county_geoid", "harvest_year"]
    pair_sizes = panel.groupby(keys, observed=True).size()
    if not pair_sizes.eq(2).all():
        raise ValueError("NASS support panel does not contain exact practice pairs")
    practices = panel.groupby(keys, observed=True)["irrigation_practice"].agg(set)
    if not practices.map(lambda value: value == {"irrigated", "non_irrigated"}).all():
        raise ValueError("NASS support pairs do not contain both named practices")

    unique = panel.groupby(["county_geoid", "state", "county_name"], observed=True).agg(
        outcome_crops=("outcome_crop", lambda values: ";".join(sorted(set(values)))),
        first_outcome_year=("harvest_year", "min"),
        last_outcome_year=("harvest_year", "max"),
        paired_crop_county_years=("harvest_year", "size"),
    ).reset_index()
    unique["paired_crop_county_years"] //= 2
    if unique.duplicated("county_geoid").any():
        raise ValueError("NASS county GEOID maps to inconsistent metadata")
    output = unique.merge(tiger, on="county_geoid", how="left", validate="one_to_one")
    output["tiger2019_exact_geoid_match"] = output["tiger2019_county_name"].notna()

    change_hits = changes.loc[changes["mentioned_geoid"].isin(output["county_geoid"])].copy()
    grouped = change_hits.groupby("mentioned_geoid", observed=True).agg(
        census_change_categories=(
            "change_category", lambda values: ";".join(sorted(set(values)))
        ),
        census_change_decades=(
            "source_decade", lambda values: ";".join(str(value) for value in sorted(set(values)))
        ),
    ).reset_index().rename(columns={"mentioned_geoid": "county_geoid"})
    # Count unique official entries separately from repeated mentioned-code rows.
    unique_entries = change_hits[
        ["mentioned_geoid", "source_decade", "change_category", "listed_geoid", "entry_text"]
    ].drop_duplicates()
    entry_count = (
        unique_entries.groupby("mentioned_geoid", observed=True)
        .size()
        .rename("census_change_entry_count")
        .reset_index()
        .rename(columns={"mentioned_geoid": "county_geoid"})
    )
    grouped = grouped.merge(
        entry_count, on="county_geoid", how="left", validate="one_to_one"
    )
    output = output.merge(grouped, on="county_geoid", how="left", validate="one_to_one")
    output["census_change_categories"] = output["census_change_categories"].fillna("")
    output["census_change_decades"] = output["census_change_decades"].fillna("")
    output["census_change_entry_count"] = (
        output["census_change_entry_count"].fillna(0).astype("int64")
    )
    output["census_substantial_page_hit"] = output["census_change_entry_count"].gt(0)
    output["geometry_change_review_required"] = output["census_change_categories"].map(
        lambda value: bool(set(str(value).split(";")) & GEOMETRY_CHANGE_CATEGORIES)
    )
    output["geography_gate_status"] = "fixed_2019_proxy_no_substantial_page_hit"
    output.loc[
        output["census_change_categories"].eq("name_or_code"), "geography_gate_status"
    ] = "name_or_code_review_no_boundary_change_in_page_entry"
    output.loc[
        output["geometry_change_review_required"], "geography_gate_status"
    ] = "blocked_pending_historical_boundary_resolution"
    output.loc[
        ~output["tiger2019_exact_geoid_match"], "geography_gate_status"
    ] = "blocked_missing_tiger2019_geometry"
    output["minor_boundary_change_caveat"] = True
    output["feature_construction_eligible"] = (
        output["tiger2019_exact_geoid_match"]
        & ~output["geometry_change_review_required"]
    )
    output["response_estimation_authorized"] = False
    output["scc_authorized"] = False
    output = output.sort_values("county_geoid").reset_index(drop=True)

    audit = {
        "role": "historical county geography support gate only; not a climate-yield result",
        "unique_nass_counties": int(len(output)),
        "exact_tiger2019_geoid_matches": int(output["tiger2019_exact_geoid_match"].sum()),
        "missing_tiger2019_geoid_matches": int((~output["tiger2019_exact_geoid_match"]).sum()),
        "census_change_page_hit_counties": int(output["census_substantial_page_hit"].sum()),
        "geometry_change_review_counties": int(output["geometry_change_review_required"].sum()),
        "name_or_code_only_review_counties": int(
            output["census_change_categories"].eq("name_or_code").sum()
        ),
        "fixed_2019_proxy_candidates_after_screen": int(
            output["feature_construction_eligible"].sum()
        ),
        "geometry_change_review_geoids": sorted(
            output.loc[output["geometry_change_review_required"], "county_geoid"].astype(str)
        ),
        "page_scope_caveat": (
            "Census pages enumerate substantial changes plus entity/name/code changes; "
            "no page hit does not establish absence of smaller boundary changes"
        ),
        "measurement_choice": (
            "2019 TIGER polygons remain a fixed county-average exposure proxy; page-hit "
            "counties require an explicit exclusion or historical-boundary sensitivity"
        ),
        "response_estimated": False,
        "scc_calculated": False,
    }
    return output, audit


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--panel", required=True)
    parser.add_argument("--tiger-counties", required=True)
    parser.add_argument("--change-1980", required=True)
    parser.add_argument("--change-1990", required=True)
    parser.add_argument("--change-2000", required=True)
    parser.add_argument("--change-2010", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--audit-out", required=True)
    args = parser.parse_args()
    changes = pd.concat(
        [
            parse_change_page(Path(getattr(args, f"change_{decade}")), decade)
            for decade in (1980, 1990, 2000, 2010)
        ],
        ignore_index=True,
    )
    output, audit = audit_geography(
        pd.read_parquet(args.panel), load_tiger_counties(Path(args.tiger_counties)), changes
    )
    destination = Path(args.out)
    destination.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(destination, index=False)
    audit_path = Path(args.audit_out)
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n")
    print(
        f"audited {len(output)} NASS counties: "
        f"{audit['exact_tiger2019_geoid_matches']} current TIGER matches, "
        f"{audit['geometry_change_review_counties']} historical-boundary reviews; "
        "no response estimated"
    )


if __name__ == "__main__":
    main()
