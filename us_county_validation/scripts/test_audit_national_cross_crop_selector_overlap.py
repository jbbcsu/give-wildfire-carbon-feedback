#!/usr/bin/env python3
from __future__ import annotations

import tempfile
from pathlib import Path

import pandas as pd

from audit_national_cross_crop_selector_overlap import audit


rows = []
for year in range(1981, 2020):
    for county, crop, eligible in (
        ("01001", "corn_grain", True),
        ("01001", "soybeans", True),
        ("01003", "corn_grain", True),
        ("01005", "soybeans", False),
    ):
        rows.append({
            "county_geoid": county,
            "outcome_crop": crop,
            "harvest_year": year,
            "irrigation_share_vintage": 2017,
            "outcome_value_eligible": True,
            "irrigation_share_eligible": eligible,
            "rainfed_dominant_10pct": eligible,
            "rainfed_dominant_20pct": eligible,
            "rainfed_dominant_30pct": eligible,
        })

with tempfile.TemporaryDirectory() as temporary:
    path = Path(temporary) / "panel.parquet"
    pd.DataFrame(rows).to_parquet(path, index=False)
    result = audit(path)
    assert result["yield_magnitudes_read"] is False
    assert len(result["results"]) == 3
    primary = result["results"][0]
    assert primary["common_county_years"] == 39
    assert primary["common_counties"] == 1
    assert primary["annual_common_county_years_minimum"] == 1
    assert primary["annual_common_county_years_maximum"] == 1

print("national cross-crop selector-overlap tests passed")
