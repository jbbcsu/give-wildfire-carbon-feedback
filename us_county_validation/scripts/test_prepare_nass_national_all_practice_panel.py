#!/usr/bin/env python3
"""Synthetic checks for the national all-practice panel and irrigation flags."""
from __future__ import annotations

import pandas as pd

from prepare_nass_national_all_practice_panel import prepare


def crop(commodity: str, util: str, geoids: list[str]) -> pd.DataFrame:
    rows = []
    for year in range(1981, 2020):
        for geoid in geoids:
            rows.append(
                {
                    "harvest_year": year,
                    "county_geoid": geoid,
                    "state_alpha": "NE",
                    "county_name": "TEST",
                    "commodity": commodity,
                    "yield_unit": "BU / ACRE",
                    "yield_value": 100.0,
                    "yield_reported": True,
                    "prodn_practice_desc": "ALL PRODUCTION PRACTICES",
                    "util_practice_desc": util,
                }
            )
    return pd.DataFrame(rows)


corn = crop("CORN", "GRAIN", ["31001", "31003"])
soy = crop("SOYBEANS", "ALL UTILIZATION PRACTICES", ["31001", "31005"])
shares = pd.DataFrame(
    [
        {"crop": "corn", "census_year": 2017, "county_geoid": "31001", "state_alpha": "NE", "irrigation_share": 0.05, "share_eligible": True, "exclusion_reason": ""},
        {"crop": "corn", "census_year": 2017, "county_geoid": "31003", "state_alpha": "NE", "irrigation_share": None, "share_eligible": False, "exclusion_reason": "missing_or_suppressed_irrigated_area_not_assumed_zero"},
        {"crop": "soybeans", "census_year": 2017, "county_geoid": "31001", "state_alpha": "NE", "irrigation_share": 0.25, "share_eligible": True, "exclusion_reason": ""},
    ]
)

panel, audit = prepare([corn, soy], shares)
assert len(panel) == 156
assert panel.duplicated(["county_geoid", "outcome_crop", "harvest_year"]).sum() == 0
assert panel.loc[panel.county_geoid.eq("31001") & panel.outcome_crop.eq("corn_grain"), "rainfed_dominant_10pct"].all()
assert not panel.loc[panel.outcome_crop.eq("soybeans"), "rainfed_dominant_10pct"].any()
assert panel.loc[panel.county_geoid.eq("31005"), "irrigation_share_missing_reason"].eq("county_absent_from_2017_crop_area_series").all()
assert audit["primary_rainfed_dominant_threshold"] == 0.10
assert audit["relationship_estimated"] is False

bad_share = shares.copy()
bad_share.loc[0, "irrigation_share"] = 1.1
try:
    prepare([corn, soy], bad_share)
except ValueError as error:
    assert "[0,1]" in str(error)
else:
    raise AssertionError("expected invalid irrigation share failure")

bad_corn = corn.copy()
bad_corn.loc[0, "prodn_practice_desc"] = "IRRIGATED"
try:
    prepare([bad_corn, soy], shares)
except ValueError as error:
    assert "all production practices" in str(error).lower()
else:
    raise AssertionError("expected wrong-practice failure")

duplicate = pd.concat([corn, corn.iloc[[0]]], ignore_index=True)
try:
    prepare([duplicate, soy], shares)
except ValueError as error:
    assert "duplicates county-year" in str(error)
else:
    raise AssertionError("expected duplicate county-year failure")

print("national all-practice panel tests passed")
