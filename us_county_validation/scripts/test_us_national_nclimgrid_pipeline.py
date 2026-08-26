#!/usr/bin/env python3
"""Synthetic fail-closed tests for the national U.S. nClimGrid pipeline."""
from __future__ import annotations

import copy
import json
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

from build_county_nclimgrid_feature_smoke import (
    EXPECTED_FIELDS,
    EXPECTED_TITLE,
    EXPECTED_VERSION,
    build_cell_basis,
)
from build_us_national_nclimgrid_features import (
    build_cell_basis_matrix,
    build_year_panel,
    load_daily_unique_cells,
    required_month_keys,
    validate_year_partition_checkpoint,
    validate_year_output,
)
from us_national_nclimgrid_common import (
    OUTCOME_KEYS,
    canonical_sha256,
    load_contract,
    prepare_support,
    sha256_file,
    sha256_records,
)


contract = copy.deepcopy(load_contract())
panel_rows = []
for geoid, state, name, crop, yields in [
    ("31039", "NE", "CUMING", "corn_grain", (150.0, 90.0)),
    ("31041", "NE", "CUSTER", "soybeans", (55.0, 40.0)),
]:
    for practice, value in zip(["irrigated", "non_irrigated"], yields, strict=True):
        panel_rows.append(
            {
                "county_geoid": geoid,
                "state": state,
                "county_name": name,
                "outcome_crop": crop,
                "harvest_year": 1981,
                "irrigation_practice": practice,
                "yield_bu_acre": value,
                "outcome_source_id": contract["sample"]["outcome_source_id"],
                "response_estimation_authorized": False,
                "scc_authorized": False,
            }
        )
panel = pd.DataFrame(panel_rows)
geography = pd.DataFrame(
    {
        "county_geoid": ["31039", "31041"],
        "state": ["NE", "NE"],
        "feature_construction_eligible": [True, True],
        "response_estimation_authorized": [False, False],
        "scc_authorized": [False, False],
    }
)
calendar = pd.DataFrame(
    {
        "state": ["NE", "NE"],
        "calendar_crop": ["corn_grain", "soybeans"],
        "harvest_year": [1981, 1981],
        "season_start": ["1981-05-01", "1981-05-01"],
        "season_end": ["1981-06-29", "1981-06-29"],
        "calendar_source_id": [contract["calendar"]["source_id"]] * 2,
        "calendar_vintage": [contract["calendar"]["vintage"]] * 2,
        "calendar_role": [contract["calendar"]["role"]] * 2,
        "boundary_rule": [contract["calendar"]["boundary_rule"]] * 2,
        "stage_definition": [contract["calendar"]["stage_definition"]] * 2,
        "feature_construction_eligible": [True, True],
        "response_estimation_authorized": [False, False],
        "scc_authorized": [False, False],
    }
)

support, seasons, audit = prepare_support(
    panel, geography, calendar, contract, enforce_registered_counts=False
)
assert len(support) == 4 and audit["eligible_counties"] == 2
assert required_month_keys(seasons) == [(1981, 5), (1981, 6)]

bad_geography = geography.copy()
bad_geography.loc[0, "state"] = "KS"
try:
    prepare_support(panel, bad_geography, calendar, contract, enforce_registered_counts=False)
except ValueError as error:
    assert "GEOID does not reconcile" in str(error)
else:
    raise AssertionError("FIPS/state mismatch should fail closed")

unpaired = panel.loc[~(
    panel.county_geoid.eq("31039") & panel.irrigation_practice.eq("irrigated")
)]
try:
    prepare_support(unpaired, geography, calendar, contract, enforce_registered_counts=False)
except ValueError as error:
    assert "exact irrigation-practice pairs" in str(error)
else:
    raise AssertionError("missing irrigation practice should fail closed")

rng = np.random.default_rng(20260826)
n_days, n_cells = 60, 4
rain = rng.gamma(0.8, 3.0, size=(n_days, n_cells))
rain[rng.random(size=rain.shape) < 0.45] = 0
rain[:, 0] = 0
tavg = rng.normal(20, 5, size=(n_days, n_cells))
tmin = tavg - 5
tmax = tavg + 7
matrix = build_cell_basis_matrix(rain, tavg, tmin, tmax, 1.0)
for cell in range(n_cells):
    scalar = build_cell_basis(
        rain[:, cell], tavg[:, cell], tmin[:, cell], tmax[:, cell], 1.0
    )
    assert set(matrix.columns) == set(scalar)
    for column, expected in scalar.items():
        assert np.isclose(matrix.loc[cell, column], expected, rtol=0, atol=1e-10), (
            cell, column, matrix.loc[cell, column], expected
        )

# A nonlinear counterexample makes the cell-first requirement observable.
counterexample_rain = np.tile(np.asarray(
    [
        [0.0, 2.0], [0.0, 0.0], [0.0, 2.0], [0.0, 0.0], [0.0, 2.0],
        [2.0, 0.0], [2.0, 2.0], [2.0, 0.0], [2.0, 2.0], [2.0, 0.0],
    ]
), (3, 1))
counterexample_temp = np.full_like(counterexample_rain, 20.0)
counterexample_basis = build_cell_basis_matrix(
    counterexample_rain, counterexample_temp, counterexample_temp,
    counterexample_temp, 1.0,
)
cell_first_cdd = float(np.dot(counterexample_basis.cdd_max_days, [0.25, 0.75]))
county_mean_rain = counterexample_rain @ np.asarray([0.25, 0.75])
county_mean_cdd = build_cell_basis(
    county_mean_rain, np.full(30, 20.0), np.full(30, 20.0), np.full(30, 20.0), 1.0
)["cdd_max_days"]
assert cell_first_cdd == 2.0 and county_mean_cdd != cell_first_cdd

weights = pd.DataFrame(
    {
        "county_geoid": ["31039", "31039", "31041", "31041"],
        "state": ["NE"] * 4,
        "county_name": ["Cuming", "Cuming", "Custer", "Custer"],
        "grid_lat_index": [0, 0, 0, 0],
        "grid_lon_index": [0, 1, 1, 2],
        "grid_lat": [41.0] * 4,
        "grid_lon": [-100.0, -99.0, -99.0, -98.0],
        "spatial_weight": [0.25, 0.75, 0.6, 0.4],
        "coverage_fraction": [1.0] * 4,
        "weather_valid_coverage_fraction": [1.0] * 4,
        "weather_valid_area_relative_to_declared_land": [1.0] * 4,
    }
)
cells = (
    weights[["grid_lat_index", "grid_lon_index", "grid_lat", "grid_lon"]]
    .drop_duplicates(["grid_lat_index", "grid_lon_index"])
    .sort_values(["grid_lat_index", "grid_lon_index"])
    .reset_index(drop=True)
)
dates = pd.date_range("1981-05-01", "1981-06-29", freq="D")
climate = {
    "prcp": rain[:, :3], "tavg": tavg[:, :3],
    "tmin": tmin[:, :3], "tmax": tmax[:, :3],
}
year_panel, year_audit = build_year_panel(
    support, seasons, weights, cells, dates, climate, contract
)
validate_year_output(year_panel, support)
assert len(year_panel) == 4 and year_audit["cell_first_nonlinear_basis"]
for _, group in year_panel.groupby(["county_geoid", "outcome_crop", "harvest_year"]):
    assert len(group) == 2
    assert group.precip_mm.nunique() == 1
    assert group.cdd_max_days.nunique() == 1
assert not year_panel.response_estimation_authorized.any()
assert not year_panel.scc_authorized.any()

tampered = year_panel.copy()
tampered.loc[tampered.irrigation_practice.eq("irrigated").idxmax(), "precip_mm"] += 1
try:
    validate_year_output(tampered, support)
except ValueError as error:
    assert "differs between practices" in str(error)
else:
    raise AssertionError("practice-specific weather tampering should fail")

tampered_yield = year_panel.copy()
tampered_yield.loc[0, "yield_bu_acre"] += 1
try:
    validate_year_output(tampered_yield, support)
except ValueError as error:
    assert "exact NASS support" in str(error)
else:
    raise AssertionError("positive yield tampering should fail exact support binding")

bad_coverage = year_panel.assign(weather_valid_area_relative_to_declared_land=0.94)
try:
    validate_year_output(bad_coverage, support)
except ValueError as error:
    assert "declared-land gate" in str(error)
else:
    raise AssertionError("sub-contract weather-valid land coverage should fail")

with tempfile.TemporaryDirectory() as directory:
    weather_path = Path(directory) / "synthetic.nc"
    data_vars = {}
    for name, (standard_name, units) in EXPECTED_FIELDS.items():
        values = rain[:, :3] if name == "prcp" else climate[name]
        data_vars[name] = (
            ("time", "lat", "lon"), values[:, None, :],
            {"standard_name": standard_name, "units": units},
        )
    dataset = xr.Dataset(
        data_vars,
        coords={"time": dates, "lat": [41.0], "lon": [-100.0, -99.0, -98.0]},
        attrs={"title": EXPECTED_TITLE, "product_version": EXPECTED_VERSION},
    )
    dataset.to_netcdf(weather_path, engine="h5netcdf")
    loaded_dates, loaded = load_daily_unique_cells([weather_path], cells)
    assert loaded_dates.equals(dates)
    assert np.array_equal(loaded["prcp"], rain[:, :3])
    bad_cells = cells.copy()
    bad_cells.loc[0, "grid_lon"] = -97.5
    try:
        load_daily_unique_cells([weather_path], bad_cells)
    except ValueError as error:
        assert "longitude does not match" in str(error)
    else:
        raise AssertionError("coordinate/index mismatch should fail")

    output = Path(directory) / "year.parquet"
    receipt_path = Path(directory) / "year.receipt.json"
    year_panel.to_parquet(output, index=False)
    identity = {
        "schema": "us_national_nclimgrid_feature_year_partition_v1",
        "harvest_year": 1981,
        "bounded_smoke_geoids": None,
        "synthetic_input": "fixed",
    }
    national_sample = {"synthetic_registered_sample": True}
    receipt = {
        "schema": "us_national_nclimgrid_feature_year_partition_v1",
        "harvest_year": 1981,
        "bounded_smoke": False,
        "bounded_smoke_geoids": None,
        "complete_year_support": True,
        "input_identity": identity,
        "input_fingerprint_sha256": canonical_sha256(identity),
        "output_sha256": sha256_file(output),
        "output_key_sha256": sha256_records(year_panel, OUTCOME_KEYS),
        "registered_national_sample": national_sample,
        "build_audit": year_audit,
        "relationship_estimated": False,
        "response_estimation_authorized": False,
        "damage_estimated": False,
        "scc_authorized": False,
    }
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    validated, _ = validate_year_partition_checkpoint(
        output, receipt_path, support,
        expected_identity=identity, expected_national_sample=national_sample,
    )
    assert len(validated) == len(year_panel)

    tampered_receipt = copy.deepcopy(receipt)
    tampered_receipt["input_identity"]["synthetic_input"] = "changed"
    receipt_path.write_text(json.dumps(tampered_receipt), encoding="utf-8")
    try:
        validate_year_partition_checkpoint(
            output, receipt_path, support,
            expected_identity=identity, expected_national_sample=national_sample,
        )
    except ValueError as error:
        assert "fingerprint does not reconcile" in str(error)
    else:
        raise AssertionError("tampered receipt identity should fail")

    tampered_receipt["input_fingerprint_sha256"] = canonical_sha256(
        tampered_receipt["input_identity"]
    )
    receipt_path.write_text(json.dumps(tampered_receipt), encoding="utf-8")
    try:
        validate_year_partition_checkpoint(
            output, receipt_path, support,
            expected_identity=identity, expected_national_sample=national_sample,
        )
    except ValueError as error:
        assert "current exact input identity" in str(error)
    else:
        raise AssertionError("self-consistent but stale receipt identity should fail")

    false_gate_receipt = copy.deepcopy(receipt)
    false_gate_receipt["scc_authorized"] = True
    receipt_path.write_text(json.dumps(false_gate_receipt), encoding="utf-8")
    try:
        validate_year_partition_checkpoint(
            output, receipt_path, support,
            expected_identity=identity, expected_national_sample=national_sample,
        )
    except ValueError as error:
        assert "scc_authorized" in str(error)
    else:
        raise AssertionError("receipt SCC authorization should fail")

print("national U.S. nClimGrid pipeline tests passed")
