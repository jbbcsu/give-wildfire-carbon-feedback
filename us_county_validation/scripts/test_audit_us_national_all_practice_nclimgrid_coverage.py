#!/usr/bin/env python3
"""Unit tests for the no-weight national all-practice coverage audit."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from pyproj import CRS, Transformer
from shapely.geometry import Polygon
from shapely.ops import transform

from audit_us_national_all_practice_nclimgrid_coverage import (
    PROJECT_ROOT,
    compute_county_coverage,
    county_outcome_support,
    relative_path,
    threshold_summary,
)
from build_us_national_county_nclimgrid_weights import build_county_partition


latitude = np.array([0.0, 1.0])
longitude = np.array([0.0, 1.0])
# Keep the synthetic county inside the four-cell envelope.  Using the exact
# lon/lat envelope boundary creates a projection-curvature sliver that is not
# relevant to the audit/builder equivalence being tested.
county = Polygon([(-0.4, -0.4), (1.4, -0.4), (1.4, 1.4), (-0.4, 1.4)])
to_area = Transformer.from_crs(CRS.from_epsg(4326), CRS.from_epsg(5070), always_xy=True)
area = float(transform(to_area.transform, county).area)
metadata = {
    "county_geoid": "01001",
    "state": "AL",
    "county_name": "Synthetic",
    "nass_county_name": "SYNTHETIC",
    "declared_land_area_m2": int(round(area)),
    "declared_water_area_m2": 0,
}

all_valid = np.ones((2, 2), dtype=bool)
audit = compute_county_coverage(
    county, metadata, CRS.from_epsg(4326), latitude, longitude, all_valid,
    minimum_geometric_coverage=0.999,
    minimum_valid_land_coverage=0.95,
    maximum_declared_area_relative_error=0.03,
)
weights, builder = build_county_partition(
    county, metadata, CRS.from_epsg(4326), latitude, longitude,
    min_coverage=0.999,
    valid_grid_mask=all_valid,
    min_valid_land_coverage=0.95,
    declared_area_relative_tolerance=0.03,
)
for audit_name, builder_name in [
    ("geometric_grid_coverage_fraction", "coverage_fraction"),
    ("weather_valid_coverage_fraction", "weather_valid_coverage_fraction"),
    (
        "weather_valid_area_relative_to_declared_land",
        "weather_valid_area_relative_to_declared_land",
    ),
    ("weather_masked_intersection_area_m2", "weather_masked_intersection_area_m2"),
]:
    assert np.isclose(audit[audit_name], builder[builder_name], rtol=0, atol=1e-12)
assert audit["positive_weather_cells"] == len(weights) == 4
assert audit["passes_registered_primary_coverage_gate"] is True
assert audit["geometric_grid_coverage_fraction"] > 0.999
assert audit["weight_rows_written"] == 0

one_masked = all_valid.copy()
one_masked[0, 0] = False
masked = compute_county_coverage(
    county, metadata, CRS.from_epsg(4326), latitude, longitude, one_masked,
    minimum_geometric_coverage=0.999,
    minimum_valid_land_coverage=0.95,
    maximum_declared_area_relative_error=0.03,
)
assert masked["positive_geometric_cells"] == 4
assert masked["positive_weather_cells"] == 3
assert masked["passes_geometric_grid_gate"] is True
assert masked["passes_weather_valid_land_gate"] is False
assert masked["passes_registered_primary_coverage_gate"] is False
assert masked["weight_rows_written"] == 0
assert 0.70 < masked["weather_valid_area_relative_to_declared_land"] < 0.80

support = pd.DataFrame(
    [
        {
            "county_geoid": "01001", "state": "AL", "county_name": "A",
            "outcome_crop": crop, "harvest_year": year,
            "irrigation_practice": "all_practices", "irrigation_share_eligible": True,
            "rainfed_dominant_10pct": rainfed, "rainfed_dominant_20pct": rainfed,
            "rainfed_dominant_30pct": True,
        }
        for crop, year, rainfed in [
            ("corn_grain", 1981, True), ("soybeans", 1981, False)
        ]
    ]
)
collapsed = county_outcome_support(support)
assert collapsed.iloc[0].to_dict()["outcome_crop_county_years"] == 2
assert collapsed.iloc[0].to_dict()["corn_crop_county_years"] == 1
assert collapsed.iloc[0].to_dict()["soy_crop_county_years"] == 1
assert collapsed.iloc[0].to_dict()["rainfed_dominant_10pct_rows"] == 1

summary_input = pd.concat(
    [
        collapsed.assign(
            passes_declared_area_gate=True,
            passes_geometric_grid_gate=True,
            weather_valid_area_relative_to_declared_land=0.96,
        ),
        collapsed.assign(
            county_geoid="01003",
            passes_declared_area_gate=True,
            passes_geometric_grid_gate=True,
            weather_valid_area_relative_to_declared_land=0.94,
        ),
    ],
    ignore_index=True,
)
summary = threshold_summary(summary_input, 0.95)
assert summary["passed"]["counties"] == 1
assert summary["excluded"]["counties"] == 1
assert summary["passed"]["outcome_crop_county_years"] == 2
assert summary["excluded"]["outcome_crop_county_years"] == 2

assert relative_path(PROJECT_ROOT / "us_county_validation") == "us_county_validation"
try:
    relative_path(Path("/tmp/outside-precipitation-project.csv"))
except ValueError as error:
    assert "outside the precipitation project" in str(error)
else:
    raise AssertionError("coverage audit must reject an external output path")

print("national all-practice no-weight coverage-audit tests passed")
