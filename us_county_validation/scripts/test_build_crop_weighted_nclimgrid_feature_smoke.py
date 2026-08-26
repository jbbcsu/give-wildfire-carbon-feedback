#!/usr/bin/env python3
"""Synthetic cell-first tests for the fixed-CDL feature sensitivity smoke."""
from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

from build_county_nclimgrid_feature_smoke import EXPECTED_FIELDS, EXPECTED_TITLE, EXPECTED_VERSION, load_daily_cells
from build_crop_weighted_nclimgrid_feature_smoke import build_panel, validate_crop_weights


weight_rows = []
for crop, crop_weights, class_code in [
    ("corn_grain", [0.25, 0.75], 1),
    ("soybeans", [0.75, 0.25], 5),
]:
    for lon_index, weight in enumerate(crop_weights):
        weight_rows.append(
            {
                "county_geoid": "31039",
                "state": "NE",
                "county_name": "Cuming",
                "outcome_crop": crop,
                "calendar_crop": crop,
                "weather_source_id": "nclimgrid_daily_v1_0_0_20220829",
                "weather_grid_id": "nclimgrid_daily_conus_1_24_degree",
                "grid_lat_index": 0,
                "grid_lon_index": lon_index,
                "grid_lat": 41.0,
                "grid_lon": -97.0 + lon_index,
                "crop_area_m2": weight * 100,
                "county_calendar_crop_area_m2": 100.0,
                "county_outcome_crop_area_m2": 100.0,
                "spatial_weight": weight,
                "calendar_class_share": 1.0,
                "calendar_class_share_source_id": "synthetic",
                "mask_source_id": "usda_nass_cdl_2017_30m_national",
                "mask_vintage": "2017-01-01",
                "mask_temporal_role": "retrospective_2017_mask_sensitivity",
                "boundary_source_id": "tigerline_2019_county",
                "boundary_vintage": "2019-01-01",
                "coverage_fraction": 1.0,
                "weight_role": "fixed_crop_mask_sensitivity",
                "analysis_role": "historical_county_validation_sensitivity_only",
                "feature_construction_eligible": True,
                "response_estimation_authorized": False,
                "scc_authorized": False,
                "cdl_class_code": class_code,
            }
        )
weights = pd.DataFrame(weight_rows)

calendar = pd.DataFrame(
    {
        "state": ["NE", "NE"],
        "calendar_crop": ["corn_grain", "soybeans"],
        "harvest_year": [1981, 1981],
        "season_start": ["1981-05-01", "1981-05-01"],
        "season_end": ["1981-05-30", "1981-05-30"],
        "calendar_source_id": ["synthetic"] * 2,
        "calendar_source_url": ["https://example.invalid/calendar"] * 2,
        "calendar_vintage": ["test"] * 2,
        "calendar_role": ["fixed_primary"] * 2,
        "boundary_rule": ["synthetic"] * 2,
        "stage_definition": ["equal_duration_0_30_70_100_engineering_proxy"] * 2,
        "feature_construction_eligible": [True, True],
        "scc_authorized": [False, False],
    }
)

outcomes = pd.DataFrame(
    [
        {
            "county_geoid": "31039",
            "state": "NE",
            "county_name": "Cuming",
            "outcome_crop": crop,
            "harvest_year": 1981,
            "outcome_source_id": "synthetic_nass",
            "irrigation_practice": practice,
            "sample_role": "direct_practice_pair",
            "yield_bu_acre": value,
            "feature_construction_eligible": True,
            "response_estimation_authorized": False,
            "scc_authorized": False,
        }
        for crop in ["corn_grain", "soybeans"]
        for practice, value in [("irrigated", 100.0), ("non_irrigated", 80.0)]
    ]
)

with tempfile.TemporaryDirectory() as directory:
    path = Path(directory) / "weather.nc"
    dates = np.arange("1981-05-01", "1981-05-31", dtype="datetime64[D]")
    ten_day_rain = np.asarray(
        [
            [0.0, 2.0], [0.0, 0.0], [0.0, 2.0], [0.0, 0.0], [0.0, 2.0],
            [2.0, 0.0], [2.0, 2.0], [2.0, 0.0], [2.0, 2.0], [2.0, 0.0],
        ]
    )
    rain = np.tile(ten_day_rain, (3, 1))
    data_vars = {}
    for name, (standard_name, units) in EXPECTED_FIELDS.items():
        values = rain if name == "prcp" else np.full_like(rain, 20.0)
        data_vars[name] = (
            ("time", "lat", "lon"),
            values[:, None, :],
            {"standard_name": standard_name, "units": units},
        )
    dataset = xr.Dataset(
        data_vars,
        coords={"time": dates, "lat": [41.0], "lon": [-97.0, -96.0]},
        attrs={"title": EXPECTED_TITLE, "product_version": EXPECTED_VERSION},
    )
    dataset.to_netcdf(path, engine="h5netcdf")

    valid_weights = validate_crop_weights(weights)
    cells = (
        valid_weights[["grid_lat_index", "grid_lon_index", "grid_lat", "grid_lon"]]
        .drop_duplicates()
        .sort_values(["grid_lat_index", "grid_lon_index"])
        .reset_index(drop=True)
    )
    loaded_dates, climate = load_daily_cells([path], cells)
    panel, audit = build_panel(
        valid_weights, loaded_dates, climate, cells, calendar, outcomes, "fixed_primary", 1.0
    )
    assert len(panel) == 4
    corn = panel.loc[panel.outcome_crop.eq("corn_grain")]
    soy = panel.loc[panel.outcome_crop.eq("soybeans")]
    assert np.allclose(corn.cdd_max_days, 2.0)
    assert np.allclose(soy.cdd_max_days, 4.0)
    assert corn.groupby("outcome_crop").precip_mm.nunique().eq(1).all()
    assert soy.groupby("outcome_crop").precip_mm.nunique().eq(1).all()
    assert panel.crop_pixel_exposure.all()
    assert panel.weather_exposure_shared_across_practices.all()
    assert not panel.response_estimation_authorized.any()
    assert not panel.scc_authorized.any()
    assert audit["cell_first_nonlinear_basis"]
    assert audit["crop_pixel_exposure"]
    assert not audit["relationship_estimated"]

    bad = weights.copy()
    bad.loc[0, "mask_temporal_role"] = "unlabeled"
    try:
        validate_crop_weights(bad)
        raise AssertionError("Mixed/unregistered temporal roles should fail")
    except ValueError as error:
        assert "temporal role" in str(error)

print("fixed-CDL crop-weighted feature-smoke tests passed")
