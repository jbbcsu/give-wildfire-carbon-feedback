#!/usr/bin/env python3
"""Synthetic checks for irrigation-share vintage stability audit."""

from pathlib import Path
import tempfile

import pandas as pd

from audit_irrigation_share_vintage_stability import load, summarize


with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    paths = {}
    for year, shift in ((2012, 0.00), (2017, 0.02), (2022, 0.04)):
        rows = []
        for crop in ("corn", "soybeans", "wheat"):
            rows.extend([
                {"crop": crop, "census_year": year, "county_geoid": "1001", "irrigation_share": 0.05 + shift, "share_eligible": True},
                {"crop": crop, "census_year": year, "county_geoid": "01003", "irrigation_share": 0.25 + shift, "share_eligible": True},
                {"crop": crop, "census_year": year, "county_geoid": "01005", "irrigation_share": "", "share_eligible": False},
            ])
        path = root / f"shares_{year}.csv"
        pd.DataFrame(rows).to_csv(path, index=False)
        paths[year] = path

    result = summarize(paths)
    assert result["response_damage_or_scc_authorized"] is False
    assert [row["common_numeric_counties"] for row in result["results"]] == [2, 2, 2]
    corn = result["results"][0]
    assert corn["pairs"][0]["thresholds"][0]["switching_counties"] == 0
    assert load(paths[2012], 2012).county_geoid.str.len().eq(5).all()

    bad = pd.read_csv(paths[2012])
    bad.loc[0, "irrigation_share"] = 1.2
    bad.to_csv(paths[2012], index=False)
    try:
        summarize(paths)
    except ValueError as exc:
        assert "within [0,1]" in str(exc)
    else:
        raise AssertionError("invalid eligible share was accepted")

print("irrigation-share vintage stability tests passed")
