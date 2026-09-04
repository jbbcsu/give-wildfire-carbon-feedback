#!/usr/bin/env python3
from __future__ import annotations

import tempfile
from pathlib import Path

import pandas as pd

from audit_national_joint_crop_temporal_support import audit


rows = []
for year in range(1981, 2020):
    for county, crop, selected in (
        ("01001", "corn_grain", True),
        ("01001", "soybeans", True),
        ("01003", "corn_grain", year <= 1990),
        ("01003", "soybeans", year <= 1990),
        ("01005", "corn_grain", True),
        ("01005", "soybeans", False),
    ):
        rows.append({
            "county_geoid": county,
            "outcome_crop": crop,
            "harvest_year": year,
            "irrigation_share_vintage": 2017,
            "outcome_value_eligible": True,
            "rainfed_dominant_10pct": selected,
        })

with tempfile.TemporaryDirectory() as temporary:
    path = Path(temporary) / "panel.parquet"
    pd.DataFrame(rows).to_parquet(path, index=False)
    result = audit(path)
    assert result["yield_magnitudes_read"] is False
    assert result["common_county_years"] == 49
    assert result["common_counties"] == 2
    assert result["county_year_count_median"] == 24.5
    assert result["counties_with_at_least_n_years"] == {"10": 2, "20": 1, "30": 1, "39": 1}
    assert result["counties_with_consecutive_run_at_least_n_years"]["10"] == 2
    assert result["complete_1981_2019_counties"] == 1

print("national joint-crop temporal-support tests passed")
