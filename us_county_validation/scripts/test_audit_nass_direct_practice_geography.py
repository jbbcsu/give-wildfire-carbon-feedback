#!/usr/bin/env python3
"""Synthetic tests for the NASS/TIGER/Census county geography gate."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import tempfile

import pandas as pd


SCRIPT = Path(__file__).with_name("audit_nass_direct_practice_geography.py")
sys.path.insert(0, str(SCRIPT.parent))
spec = importlib.util.spec_from_file_location("geography_audit", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


with tempfile.TemporaryDirectory() as temporary:
    page = Path(temporary) / "1980.html"
    page.write_text(
        """
        <h3>Changes to Counties or County Equivalent Entities: 1980s</h3>
        <h4><b>New Counties or County Equivalent Entities</b></h4>
        <li>Cibola County (35-006): Created from Valencia County (35-061)
        effective June 19, 1981; 1980 population: 30,347.</li>
        <h4>Name and/or Code Changes or Corrections for Counties or County Equivalent Entities</h4>
        <li>LaMoure County (38-045): Name corrected from La Moure County.</li>
        <h4>Substantial County or County Equivalent Entity Boundary Changes</h4>
        <li>Adams County (08-001): Changed effective May 17, 1988.</li>
        """,
        encoding="utf-8",
    )
    changes = module.parse_change_page(page, 1980)

assert set(changes.mentioned_geoid) == {"35006", "35061", "38045", "08001"}
assert set(changes.change_category) == {"new_entity", "name_or_code", "substantial_boundary"}
assert changes.loc[changes.listed_geoid.eq("35006"), "effective_years"].eq("1981").all()

rows = []
for geoid, state, name in [
    ("35006", "NM", "CIBOLA"),
    ("38045", "ND", "LA MOURE"),
    ("08001", "CO", "ADAMS"),
    ("31039", "NE", "CUMING"),
]:
    for practice in ("irrigated", "non_irrigated"):
        rows.append(
            {
                "county_geoid": geoid,
                "state": state,
                "county_name": name,
                "outcome_crop": "corn_grain",
                "harvest_year": 1985,
                "irrigation_practice": practice,
                "response_estimation_authorized": False,
                "scc_authorized": False,
            }
        )
panel = pd.DataFrame(rows)
tiger = pd.DataFrame(
    {
        "county_geoid": ["35006", "38045", "08001", "31039"],
        "tiger2019_county_name": ["Cibola", "LaMoure", "Adams", "Cuming"],
    }
)
output, audit = module.audit_geography(panel, tiger, changes)
assert audit["unique_nass_counties"] == 4
assert audit["exact_tiger2019_geoid_matches"] == 4
assert audit["geometry_change_review_counties"] == 2
assert audit["name_or_code_only_review_counties"] == 1
assert audit["fixed_2019_proxy_candidates_after_screen"] == 2
status = output.set_index("county_geoid")["geography_gate_status"].to_dict()
assert status["35006"] == "blocked_pending_historical_boundary_resolution"
assert status["08001"] == "blocked_pending_historical_boundary_resolution"
assert status["38045"] == "name_or_code_review_no_boundary_change_in_page_entry"
assert status["31039"] == "fixed_2019_proxy_no_substantial_page_hit"
assert not output.response_estimation_authorized.any()
assert not output.scc_authorized.any()

missing = tiger.loc[tiger.county_geoid.ne("31039")].copy()
output_missing, _ = module.audit_geography(panel, missing, changes)
assert output_missing.loc[
    output_missing.county_geoid.eq("31039"), "geography_gate_status"
].eq("blocked_missing_tiger2019_geometry").all()

print("NASS direct-practice geography audit tests passed")
