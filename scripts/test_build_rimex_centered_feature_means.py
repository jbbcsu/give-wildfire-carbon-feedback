#!/usr/bin/env python3
from __future__ import annotations

import pandas as pd

from build_rimex_centered_feature_means import reconcile, smooth_features, smooth_gmst


years = list(range(2000, 2024))
season_rows = []
stage_rows = []
for year in years:
    base = {
        "harvest_year": year, "plant_year": year - 1, "lat": 1.25, "lon": 2.25,
        "lon_360": 2.25, "crop": "mai", "irrigation": "noirr", "cross_year": True,
    }
    metrics = {
        "tmean_c": float(year), "precip_mm": float(3 * year), "wet_days_n": float(3 * (year - 1999)),
        "cdd_max_days": 4.0, "rx1day_mm": 6.0, "rx5day_mm": 10.0,
    }
    leap_geometry = int(year % 4 == 0)
    season_rows.append({**base, "plant_doy": 300, "maturity_doy": 100, "season_days": 166 + leap_geometry,
                        "wet_day_threshold_mm": 1.0, **metrics})
    for stage_id in (1, 2, 3):
        extra = leap_geometry if stage_id == 3 else 0
        stage_rows.append({
            **base, "stage_id": stage_id, "stage_start_offset_day": 1 + (stage_id - 1) * 55,
            "stage_end_offset_day": stage_id * 55 if stage_id < 3 else 166 + extra,
            "stage_days": 55 if stage_id < 3 else 56 + extra, "stage_fractions": "0,0.3,0.7,1",
            "tmean_c": float(year), "precip_mm": float(year), "wet_days_n": float(year - 1999),
            "cdd_max_days": 2.0, "rx1day_mm": 2.0, "rx5day_mm": 3.0,
        })

gmst = pd.DataFrame({
    "esm_id": "esm", "member_id": "r1", "scenario": "ssp", "gmst_source_id": "source",
    "year": years, "gmst_value_k": [280.0 + 0.1 * (year - 2000) for year in years],
})
season = smooth_features(pd.DataFrame(season_rows), stage=False, window=21)
stage = smooth_features(pd.DataFrame(stage_rows), stage=True, window=21)
gmst_mean = smooth_gmst(gmst, first_feature_year=2000, last_feature_year=2023, window=21)
assert season.center_year.tolist() == [2010, 2011, 2012, 2013]
assert gmst_mean.center_year.tolist() == [2010, 2011, 2012, 2013]
assert season.loc[0, "precip_mm_21yr_mean"] == 3 * 2010
assert season.loc[0, "season_days_21yr_mean"] > 166
audit = reconcile(season, stage, gmst_mean, window=21)
assert audit["center_years"] == [2010, 2011, 2012, 2013]
assert audit["stage_season_additive_max_absolute_differences"]["precip_mm"] == 0
assert audit["stage_season_additive_max_absolute_differences"]["stage_days"] == 0

broken = pd.DataFrame(season_rows).query("harvest_year != 2005")
try:
    smooth_features(broken, stage=False, window=21)
except ValueError as error:
    assert "exact consecutive" in str(error)
else:
    raise AssertionError("a gap in feature support must fail closed")

print("RIME-X centered-feature means tests passed")
