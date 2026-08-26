#!/usr/bin/env python3
"""Adversarial isolation tests for the all-practice nClimGrid route."""
from __future__ import annotations

import copy
import json
from pathlib import Path

import numpy as np
import pandas as pd

from build_us_national_all_practice_nclimgrid_features import (
    build_all_practice_year_panel,
    validate_all_practice_year_output,
)
from run_us_national_all_practice_nclimgrid_route import (
    DIRECT_FEATURE_DIR,
    DIRECT_WEIGHT_DIR,
    FEATURE_DIR,
    ROUTE_ID,
    TRACKED_SMOKE_RECEIPT,
    WEIGHT_DIR,
    validate_tracked_smoke_receipt,
)
from us_national_nclimgrid_common import PAIR_KEYS, load_contract, prepare_support


direct = copy.deepcopy(load_contract())
all_practice = copy.deepcopy(
    load_contract(
        Path(__file__).parents[1] / "us_national_all_practice_nclimgrid_features_v1.toml"
    )
)
assert direct["contract_id"] == "us_national_nclimgrid_features_v1"
assert set(direct["sample"]["irrigation_practices"]) == {"irrigated", "non_irrigated"}
assert direct["sample"]["expected_counties"] == 419
assert direct["sample"]["expected_crop_county_years"] == 11861
assert direct["sample"]["expected_practice_rows"] == 23722
assert all_practice["contract_id"] == ROUTE_ID
assert set(all_practice["sample"]["irrigation_practices"]) == {"all_practices"}
assert all_practice["sample"]["expected_counties"] == 2628
assert all_practice["sample"]["expected_crop_county_years"] == 136539
assert all_practice["sample"]["expected_practice_rows"] == 136539
assert WEIGHT_DIR != DIRECT_WEIGHT_DIR and FEATURE_DIR != DIRECT_FEATURE_DIR


def rows(practices: list[str], source: str) -> pd.DataFrame:
    output = []
    for crop, value in [("corn_grain", 150.0), ("soybeans", 55.0)]:
        for practice in practices:
            output.append(
                {
                    "county_geoid": "31039",
                    "state": "NE",
                    "county_name": "CUMING",
                    "outcome_crop": crop,
                    "harvest_year": 1981,
                    "irrigation_practice": practice,
                    "yield_bu_acre": value,
                    "outcome_source_id": source,
                    "response_estimation_authorized": False,
                    "scc_authorized": False,
                }
            )
    return pd.DataFrame(output)


geography = pd.DataFrame(
    {
        "county_geoid": ["31039"],
        "state": ["NE"],
        "feature_construction_eligible": [True],
        "response_estimation_authorized": [False],
        "scc_authorized": [False],
    }
)
calendar = pd.DataFrame(
    {
        "state": ["NE", "NE"],
        "calendar_crop": ["corn_grain", "soybeans"],
        "harvest_year": [1981, 1981],
        "season_start": ["1981-05-01", "1981-05-01"],
        "season_end": ["1981-06-29", "1981-06-29"],
        "calendar_source_id": [all_practice["calendar"]["source_id"]] * 2,
        "calendar_vintage": [all_practice["calendar"]["vintage"]] * 2,
        "calendar_role": [all_practice["calendar"]["role"]] * 2,
        "boundary_rule": [all_practice["calendar"]["boundary_rule"]] * 2,
        "stage_definition": [all_practice["calendar"]["stage_definition"]] * 2,
        "feature_construction_eligible": [True, True],
        "response_estimation_authorized": [False, False],
        "scc_authorized": [False, False],
    }
)

direct_panel = rows(
    ["irrigated", "non_irrigated"], direct["sample"]["outcome_source_id"]
)
direct_support, _, direct_audit = prepare_support(
    direct_panel, geography, calendar, direct, enforce_registered_counts=False
)
assert len(direct_support) == 4 and direct_audit["eligible_practice_rows"] == 4
assert direct_support.groupby(PAIR_KEYS).irrigation_practice.agg(set).map(
    lambda value: value == {"irrigated", "non_irrigated"}
).all()

all_panel = rows(["all_practices"], all_practice["sample"]["outcome_source_id"])
support, seasons, audit = prepare_support(
    all_panel, geography, calendar, all_practice, enforce_registered_counts=False
)
assert len(support) == 2 and audit["eligible_crop_county_years"] == 2
assert not support.duplicated(PAIR_KEYS).any()
assert support.irrigation_practice.eq("all_practices").all()

mixed = pd.concat(
    [all_panel, all_panel.iloc[[0]].assign(irrigation_practice="irrigated")],
    ignore_index=True,
)
try:
    prepare_support(mixed, geography, calendar, all_practice, enforce_registered_counts=False)
except ValueError as error:
    assert "practice scope differs" in str(error)
else:
    raise AssertionError("foreign direct-practice row should fail the all-practice route")

duplicate = pd.concat([all_panel, all_panel.iloc[[0]]], ignore_index=True)
try:
    prepare_support(duplicate, geography, calendar, all_practice, enforce_registered_counts=False)
except ValueError as error:
    assert "duplicates outcome keys" in str(error)
else:
    raise AssertionError("duplicate all-practice crop-county-year should fail")

try:
    prepare_support(all_panel, geography, calendar, direct, enforce_registered_counts=False)
except ValueError as error:
    assert "outcome source" in str(error) or "practice scope differs" in str(error)
else:
    raise AssertionError("all-practice source should not enter the direct-practice contract")

dates = pd.date_range("1981-05-01", "1981-06-29", freq="D")
rng = np.random.default_rng(20260826)
rain = rng.gamma(0.8, 3.0, size=(len(dates), 1))
tavg = rng.normal(20, 4, size=(len(dates), 1))
weights = pd.DataFrame(
    {
        "county_geoid": ["31039"],
        "state": ["NE"],
        "county_name": ["Cuming"],
        "grid_lat_index": [0],
        "grid_lon_index": [0],
        "grid_lat": [41.0],
        "grid_lon": [-97.0],
        "spatial_weight": [1.0],
        "coverage_fraction": [1.0],
        "weather_valid_coverage_fraction": [1.0],
        "weather_valid_area_relative_to_declared_land": [1.0],
    }
)
cells = weights[["grid_lat_index", "grid_lon_index", "grid_lat", "grid_lon"]]
year_panel, year_audit = build_all_practice_year_panel(
    support,
    seasons,
    weights,
    cells,
    dates,
    {"prcp": rain, "tavg": tavg, "tmin": tavg - 5, "tmax": tavg + 7},
    all_practice,
)
validate_all_practice_year_output(year_panel, support)
assert len(year_panel) == 2 == year_audit["practice_rows"]
assert not year_panel.duplicated(PAIR_KEYS).any()
assert year_panel.irrigation_practice.eq("all_practices").all()
assert "weather_exposure_shared_across_practices" not in year_panel
assert "weather_exposure_shared_across_practices" not in year_audit
assert year_audit["single_all_practices_outcome_per_crop_county_year"] is True
assert set(year_panel.weather_exposure_application) == {
    "one_county_crop_year_exposure_joined_to_one_all_practices_outcome"
}

duplicated_output = pd.concat([year_panel, year_panel.iloc[[0]]], ignore_index=True)
try:
    validate_all_practice_year_output(duplicated_output, support)
except ValueError as error:
    assert "duplicates crop-county-year keys" in str(error)
else:
    raise AssertionError("duplicated all-practice feature output should fail")

false_shared_claim = year_panel.assign(weather_exposure_shared_across_practices=True)
try:
    validate_all_practice_year_output(false_shared_claim, support)
except ValueError as error:
    assert "incorrectly claims shared practices" in str(error)
else:
    raise AssertionError("single all-practice output should reject shared-practice metadata")

if TRACKED_SMOKE_RECEIPT.is_file():
    tracked = json.loads(TRACKED_SMOKE_RECEIPT.read_text(encoding="utf-8"))
    validate_tracked_smoke_receipt(tracked)
    contaminated = copy.deepcopy(tracked)
    contaminated["bounded_smoke"]["weather_exposure_shared_across_practices"] = True
    try:
        validate_tracked_smoke_receipt(contaminated)
    except ValueError as error:
        assert "falsely claims" in str(error)
    else:
        raise AssertionError("tracked receipt should reject paired-practice language")

print("national all-practice nClimGrid route tests passed")
