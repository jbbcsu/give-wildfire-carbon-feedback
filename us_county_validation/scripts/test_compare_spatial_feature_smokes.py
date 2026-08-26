#!/usr/bin/env python3
"""Synthetic invariants for the spatial feature-smoke comparison."""
from __future__ import annotations

import pandas as pd

from compare_spatial_feature_smokes import FEATURES, compare


def panel(weight_role: str, crop_pixel: bool, shift: float) -> pd.DataFrame:
    rows = []
    for practice in ["irrigated", "non_irrigated"]:
        row = {
            "county_geoid": "31039",
            "outcome_crop": "corn_grain",
            "harvest_year": 1981,
            "irrigation_practice": practice,
            "weather_source_id": "nclimgrid_daily_v1_0_0_20220829",
            "weather_grid_id": "nclimgrid_daily_conus_1_24_degree",
            "calendar_role": "fixed_primary",
            "weight_role": weight_role,
            "crop_pixel_exposure": crop_pixel,
            "response_estimation_authorized": False,
            "scc_authorized": False,
        }
        row.update({feature: float(index + 1) + shift for index, feature in enumerate(FEATURES)})
        if crop_pixel:
            row["mask_temporal_role"] = "retrospective_2017_mask_sensitivity"
        rows.append(row)
    return pd.DataFrame(rows)


primary = panel("county_polygon_primary_proxy", False, 0.0)
sensitivity = panel("fixed_crop_mask_sensitivity", True, 0.5)
result, audit = compare(primary, sensitivity)
assert len(result) == len(FEATURES)
assert result.absolute_difference.eq(0.5).all()
assert not result.relationship_estimated.any()
assert audit["county_crop_year_keys"] == 1
assert audit["relationship_estimated"] is False

bad = sensitivity.copy()
bad.loc[bad.irrigation_practice.eq("irrigated"), FEATURES[0]] = 999
try:
    compare(primary, bad)
    raise AssertionError("Practice-varying weather should fail")
except ValueError as error:
    assert "differs across practices" in str(error)

print("spatial feature-smoke comparison tests passed")
