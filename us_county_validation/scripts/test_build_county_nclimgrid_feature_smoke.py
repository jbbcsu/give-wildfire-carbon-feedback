#!/usr/bin/env python3
"""Synthetic cell-first feature and join tests for the county smoke."""
from __future__ import annotations

import importlib.util
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr


SCRIPT = Path(__file__).with_name("build_county_nclimgrid_feature_smoke.py")
sys.path.insert(0, str(SCRIPT.parent))
spec = importlib.util.spec_from_file_location("feature_smoke", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


weights = pd.DataFrame(
    {
        "county_geoid": ["31039", "31039"],
        "state": ["NE", "NE"],
        "county_name": ["Cuming", "Cuming"],
        "weather_source_id": [module.WEATHER_SOURCE_ID] * 2,
        "weather_grid_id": [module.WEATHER_GRID_ID] * 2,
        "grid_lat_index": [0, 0],
        "grid_lon_index": [0, 1],
        "grid_lat": [41.0, 41.0],
        "grid_lon": [-97.0, -96.0],
        "intersection_area_m2": [25.0, 75.0],
        "county_polygon_area_m2": [100.0, 100.0],
        "spatial_weight": [0.25, 0.75],
        "coverage_fraction": [1.0, 1.0],
        "boundary_source_id": ["tigerline_2019_county"] * 2,
        "boundary_vintage": ["2019-01-01"] * 2,
        "area_crs": ["EPSG:5070"] * 2,
        "weight_role": ["county_polygon_primary_proxy"] * 2,
        "analysis_role": ["historical_county_validation_only"] * 2,
        "feature_construction_eligible": [True, True],
        "scc_authorized": [False, False],
    }
)

calendar = pd.DataFrame(
    {
        "state": ["NE", "NE"],
        "calendar_crop": ["corn_grain", "soybeans"],
        "harvest_year": [1981, 1981],
        "season_start": ["1981-05-01", "1981-05-01"],
        "season_end": ["1981-05-30", "1981-05-30"],
        "calendar_source_id": ["synthetic_calendar"] * 2,
        "calendar_source_url": ["https://example.invalid/calendar"] * 2,
        "calendar_vintage": ["test"] * 2,
        "calendar_role": ["fixed_primary"] * 2,
        "boundary_rule": ["synthetic"] * 2,
        "stage_definition": ["equal_duration_0_30_70_100_engineering_proxy"] * 2,
        "feature_construction_eligible": [True, True],
        "scc_authorized": [False, False],
    }
)

outcome_rows = []
for crop in ["corn_grain", "soybeans"]:
    for practice, value in [("irrigated", 100.0), ("non_irrigated", 80.0)]:
        outcome_rows.append(
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
        )
outcomes = pd.DataFrame(outcome_rows)

with tempfile.TemporaryDirectory() as directory:
    path = Path(directory) / "weather.nc"
    dates = np.arange("1981-05-01", "1981-05-31", dtype="datetime64[D]")
    # Cell 0 has a five-day dry spell; cell 1 alternates wet/dry. The weighted
    # average of cell-level CDD is 0.25*5 + 0.75*1 = 2, while CDD computed from
    # county-mean rainfall would differ. This tests the required operation order.
    ten_day_rain = np.asarray(
        [
            [0.0, 2.0], [0.0, 0.0], [0.0, 2.0], [0.0, 0.0], [0.0, 2.0],
            [2.0, 0.0], [2.0, 2.0], [2.0, 0.0], [2.0, 2.0], [2.0, 0.0],
        ]
    )
    rain = np.tile(ten_day_rain, (3, 1))
    data_vars = {}
    for name, (standard_name, units) in module.EXPECTED_FIELDS.items():
        values = rain if name == "prcp" else np.full_like(rain, 20.0)
        data_vars[name] = (
            ("time", "lat", "lon"),
            values[:, None, :],
            {"standard_name": standard_name, "units": units},
        )
    dataset = xr.Dataset(
        data_vars,
        coords={"time": dates, "lat": [41.0], "lon": [-97.0, -96.0]},
        attrs={"title": module.EXPECTED_TITLE, "product_version": module.EXPECTED_VERSION},
    )
    dataset.to_netcdf(path, engine="h5netcdf")
    valid_weights = module.validate_polygon_weights(weights)
    loaded_dates, climate = module.load_daily_cells([path], valid_weights)
    panel, audit = module.build_panel(
        valid_weights, loaded_dates, climate, calendar, outcomes, "fixed_primary", 1.0
    )
    assert len(panel) == 4
    assert np.allclose(panel.cdd_max_days, 2.0)
    assert np.allclose(panel.precip_mm, 30.0)
    assert panel.weather_exposure_shared_across_practices.all()
    assert panel.groupby("outcome_crop").precip_mm.nunique().eq(1).all()
    assert audit["cell_first_nonlinear_basis"]
    assert not audit["relationship_estimated"]
    assert not panel.response_estimation_authorized.any()
    assert not panel.scc_authorized.any()

    bad_weights = weights.assign(spatial_weight=[0.5, 0.5])
    try:
        module.validate_polygon_weights(bad_weights)
    except ValueError as error:
        assert "do not reconcile to area" in str(error)
    else:
        raise AssertionError("Tampered spatial weights should fail")

    shifted = dataset.assign_coords(time=np.arange("1981-05-02", "1981-06-01", dtype="datetime64[D]"))
    shifted.to_netcdf(path, engine="h5netcdf", mode="w")
    shifted_dates, shifted_climate = module.load_daily_cells([path], valid_weights)
    try:
        module.build_panel(
            valid_weights, shifted_dates, shifted_climate, calendar, outcomes, "fixed_primary", 1.0
        )
    except ValueError as error:
        assert "do not cover exact" in str(error)
    else:
        raise AssertionError("Incomplete season boundary should fail")

print("county nClimGrid feature-smoke tests passed")
