#!/usr/bin/env python3
"""Synthetic invariants for the county crop-weather/calendar contract."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd


SCRIPT = Path(__file__).with_name("validate_county_crop_weather_contract.py")
spec = importlib.util.spec_from_file_location("county_weather_contract", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def flags(rows: int) -> dict[str, list[bool]]:
    return {"feature_construction_eligible": [True] * rows, "scc_authorized": [False] * rows}


counties = pd.DataFrame(
    {
        "county_geoid": ["19001", "38001"],
        "state": ["IA", "ND"],
        "boundary_source_id": ["tigerline_2019_county"] * 2,
        "boundary_vintage": ["2019"] * 2,
        "historical_status": ["stable", "explicit_crosswalk"],
        "crosswalk_source_id": ["not_applicable", "census_county_change_file_v1"],
        **flags(2),
    }
)

outcomes = pd.DataFrame(
    {
        "county_geoid": ["19001", "19001", "38001", "38001"],
        "state": ["IA", "IA", "ND", "ND"],
        "outcome_crop": ["corn_grain", "corn_grain", "wheat_all_classes", "wheat_all_classes"],
        "harvest_year": [1981] * 4,
        "outcome_source_id": ["nass_quickstats_practice_screen"] * 4,
        "irrigation_practice": ["irrigated", "non_irrigated", "irrigated", "non_irrigated"],
        "sample_role": ["direct_practice_pair"] * 4,
        **flags(4),
    }
)

common = {
    "weather_source_id": module.PRIMARY_WEATHER_SOURCE,
    "weather_grid_id": module.PRIMARY_WEATHER_GRID,
    "calendar_class_share_source_id": "synthetic_fixed_crop_mask",
    "mask_source_id": "synthetic_fixed_crop_mask",
    "mask_vintage": "fixed_test_v1",
    "boundary_source_id": "tigerline_2019_county",
    "boundary_vintage": "2019",
    "coverage_fraction": 0.98,
    "weight_role": "fixed_crop_mask_sensitivity",
    "feature_construction_eligible": True,
    "scc_authorized": False,
}
weights = pd.DataFrame(
    [
        {
            **common,
            "county_geoid": "19001",
            "state": "IA",
            "outcome_crop": "corn_grain",
            "calendar_crop": "corn_grain",
            "grid_lat_index": 100,
            "grid_lon_index": 300,
            "crop_area_m2": 60.0,
            "county_calendar_crop_area_m2": 100.0,
            "county_outcome_crop_area_m2": 100.0,
            "spatial_weight": 0.6,
            "calendar_class_share": 1.0,
        },
        {
            **common,
            "county_geoid": "19001",
            "state": "IA",
            "outcome_crop": "corn_grain",
            "calendar_crop": "corn_grain",
            "grid_lat_index": 100,
            "grid_lon_index": 301,
            "crop_area_m2": 40.0,
            "county_calendar_crop_area_m2": 100.0,
            "county_outcome_crop_area_m2": 100.0,
            "spatial_weight": 0.4,
            "calendar_class_share": 1.0,
        },
        {
            **common,
            "county_geoid": "38001",
            "state": "ND",
            "outcome_crop": "wheat_all_classes",
            "calendar_crop": "spring_wheat",
            "grid_lat_index": 400,
            "grid_lon_index": 700,
            "crop_area_m2": 70.0,
            "county_calendar_crop_area_m2": 70.0,
            "county_outcome_crop_area_m2": 100.0,
            "spatial_weight": 1.0,
            "calendar_class_share": 0.7,
        },
        {
            **common,
            "county_geoid": "38001",
            "state": "ND",
            "outcome_crop": "wheat_all_classes",
            "calendar_crop": "winter_wheat",
            "grid_lat_index": 401,
            "grid_lon_index": 701,
            "crop_area_m2": 30.0,
            "county_calendar_crop_area_m2": 30.0,
            "county_outcome_crop_area_m2": 100.0,
            "spatial_weight": 1.0,
            "calendar_class_share": 0.3,
        },
    ]
)

calendar = pd.DataFrame(
    {
        "state": ["IA", "ND", "ND"],
        "calendar_crop": ["corn_grain", "spring_wheat", "winter_wheat"],
        "harvest_year": [1981] * 3,
        "season_start": ["1981-04-01", "1981-04-01", "1980-09-01"],
        "season_end": ["1981-11-30", "1981-09-30", "1981-08-31"],
        "calendar_source_id": ["usda_nass_usual_dates_2010"] * 3,
        "calendar_source_url": ["https://example.invalid/reviewed-calendar"] * 3,
        "calendar_vintage": ["2010"] * 3,
        "calendar_role": ["fixed_primary"] * 3,
        "boundary_rule": ["synthetic_representative_dates"] * 3,
        "stage_definition": ["synthetic_equal_duration_thirds"] * 3,
        **flags(3),
    }
)

valid_counties = module.validate_counties(counties)
valid_outcomes = module.validate_outcomes(outcomes)
valid_weights = module.validate_weights(weights, 1e-8)
valid_calendar = module.validate_calendar(calendar)
audit = module.validate_links(valid_weights, valid_calendar, valid_outcomes, valid_counties)
assert audit["county_crop_years"] == 2
assert audit["weight_rows"] == 4
assert audit["calendar_classes"] == ["corn_grain", "spring_wheat", "winter_wheat"]
assert not audit["response_estimation_authorized"]
assert not audit["scc_authorized"]


def must_fail(function, frame, expected: str) -> None:
    try:
        function(frame)
    except ValueError as error:
        assert expected in str(error), str(error)
    else:
        raise AssertionError(f"Expected failure containing {expected!r}")


must_fail(
    lambda frame: module.validate_weights(frame, 1e-8),
    weights.assign(spatial_weight=[0.7, 0.3, 1.0, 1.0]),
    "spatial_weight does not equal",
)
must_fail(
    lambda frame: module.validate_weights(frame, 1e-8),
    pd.concat([weights, weights.iloc[[0]]], ignore_index=True),
    "duplicate county-crop-grid-cell",
)
must_fail(
    lambda frame: module.validate_weights(frame, 1e-8),
    weights.assign(grid_lat_index=[596, 100, 400, 401]),
    "outside the nClimGrid grid",
)
must_fail(
    lambda frame: module.validate_weights(frame, 1e-8),
    weights.assign(calendar_class_share=[1.0, 1.0, 0.6, 0.3]),
    "calendar_class_share does not reconcile",
)
must_fail(
    module.validate_calendar,
    calendar.assign(calendar_crop=["corn_grain", "wheat_all_classes", "winter_wheat"]),
    "unknown or aggregate calendar_crop",
)
must_fail(
    module.validate_counties,
    counties.assign(historical_status=["stable", "unresolved_change"]),
    "Unresolved historical county changes",
)
must_fail(
    module.validate_outcomes,
    outcomes.loc[~((outcomes.county_geoid == "38001") & (outcomes.irrigation_practice == "irrigated"))],
    "practice support does not match",
)

try:
    module.validate_links(
        valid_weights,
        valid_calendar.loc[~valid_calendar.calendar_crop.eq("winter_wheat")],
        valid_outcomes,
        valid_counties,
    )
except ValueError as error:
    assert "lacks required state-class-year" in str(error)
else:
    raise AssertionError("Missing wheat-class calendar should fail")

bad_fips = counties.copy()
bad_fips.loc[0, "county_geoid"] = "1901"
must_fail(module.validate_counties, bad_fips, "five-digit real-FIPS")

print("county crop-weather contract tests passed")
