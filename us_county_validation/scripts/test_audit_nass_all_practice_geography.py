#!/usr/bin/env python3
"""Synthetic checks for the national all-practice geography gate."""
from __future__ import annotations

import pandas as pd

from audit_nass_all_practice_geography import audit_geography


panel = pd.DataFrame(
    [
        {
            "county_geoid": geoid, "state": state, "county_name": name,
            "outcome_crop": "corn_grain", "harvest_year": 1985,
            "irrigation_practice": "all_practices",
            "response_estimation_authorized": False, "scc_authorized": False,
        }
        for geoid, state, name in [
            ("35006", "NM", "CIBOLA"), ("38045", "ND", "LA MOURE"),
            ("08001", "CO", "ADAMS"), ("31039", "NE", "CUMING"),
        ]
    ]
)
tiger = pd.DataFrame(
    {
        "county_geoid": ["35006", "38045", "08001", "31039"],
        "tiger2019_county_name": ["Cibola", "LaMoure", "Adams", "Cuming"],
    }
)
changes = pd.DataFrame(
    [
        {"mentioned_geoid": "35006", "source_decade": 1980, "change_category": "new_entity", "listed_geoid": "35006", "entry_text": "created"},
        {"mentioned_geoid": "38045", "source_decade": 1980, "change_category": "name_or_code", "listed_geoid": "38045", "entry_text": "name"},
        {"mentioned_geoid": "08001", "source_decade": 1980, "change_category": "substantial_boundary", "listed_geoid": "08001", "entry_text": "boundary"},
    ]
)

output, audit = audit_geography(panel, tiger, changes)
assert audit["unique_nass_counties"] == 4
assert audit["geometry_change_review_counties"] == 2
assert audit["fixed_2019_proxy_candidates_after_screen"] == 2
status = output.set_index("county_geoid").geography_gate_status.to_dict()
assert status["35006"] == "blocked_pending_historical_boundary_resolution"
assert status["38045"] == "name_or_code_review_no_boundary_change_in_page_entry"
assert status["31039"] == "fixed_2019_proxy_no_substantial_page_hit"

duplicate = pd.concat([panel, panel.iloc[[0]]], ignore_index=True)
try:
    audit_geography(duplicate, tiger, changes)
except ValueError as error:
    assert "duplicates" in str(error)
else:
    raise AssertionError("expected duplicate-key failure")

wrong = panel.copy()
wrong.loc[0, "irrigation_practice"] = "irrigated"
try:
    audit_geography(wrong, tiger, changes)
except ValueError as error:
    assert "all-practice" in str(error)
else:
    raise AssertionError("expected practice-route failure")

print("national all-practice geography audit tests passed")
