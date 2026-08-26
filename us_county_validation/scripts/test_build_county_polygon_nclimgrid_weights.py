#!/usr/bin/env python3
"""Synthetic geometry tests for county-polygon nClimGrid weights."""
from __future__ import annotations

import importlib.util
import tempfile
from pathlib import Path

import numpy as np
import shapefile
import xarray as xr
from pyproj import CRS, Transformer
from shapely.geometry import box
from shapely.ops import transform


SCRIPT = Path(__file__).with_name("build_county_polygon_nclimgrid_weights.py")
spec = importlib.util.spec_from_file_location("county_weights", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    shp = root / "counties.shp"
    county = box(-100.0, 40.0, -99.0, 41.0)
    transformer = Transformer.from_crs(4326, 5070, always_xy=True)
    declared_area = int(transform(transformer.transform, county).area)
    with shapefile.Writer(str(shp), shapeType=shapefile.POLYGON) as writer:
        writer.field("STATEFP", "C", size=2)
        writer.field("COUNTYFP", "C", size=3)
        writer.field("GEOID", "C", size=5)
        writer.field("NAME", "C", size=100)
        writer.field("ALAND", "N", size=18, decimal=0)
        writer.field("AWATER", "N", size=18, decimal=0)
        writer.poly([list(reversed(county.exterior.coords))])
        writer.record("01", "001", "01001", "Synthetic", declared_area, 0)
    shp.with_suffix(".prj").write_text(CRS.from_epsg(4326).to_wkt(), encoding="utf-8")

    climate = root / "weather.nc"
    shape3 = (2, 2, 2)
    variables = {
        name: (("time", "lat", "lon"), np.ones(shape3, dtype=np.int8))
        for name in module.EXPECTED_FIELDS
    }
    dataset = xr.Dataset(
        variables,
        coords={
            "time": np.arange("1981-01-01", "1981-01-03", dtype="datetime64[D]"),
            "lat": [40.25, 40.75],
            "lon": [-99.75, -99.25],
        },
        attrs={"title": module.EXPECTED_TITLE, "product_version": module.EXPECTED_VERSION},
    )
    dataset.to_netcdf(climate, engine="h5netcdf")
    weights, audit = module.build_weights(shp, "01001", climate, min_coverage=0.999)
    assert len(weights) == 4
    assert weights[["grid_lat_index", "grid_lon_index"]].drop_duplicates().shape[0] == 4
    assert abs(weights.spatial_weight.sum() - 1) < 1e-12
    assert audit["coverage_fraction"] > 0.999
    assert audit["county_geoid"] == "01001"
    assert audit["state"] == "AL"
    assert not audit["crop_pixel_exposure"]
    assert not audit["response_estimation_authorized"]
    assert not weights.scc_authorized.any()

    try:
        module.build_weights(shp, "1001", climate)
    except ValueError as error:
        assert "five-digit GEOID" in str(error)
    else:
        raise AssertionError("Malformed county GEOID should fail")

    descending = dataset.sortby("lat", ascending=False)
    descending.to_netcdf(climate, engine="h5netcdf", mode="w")
    try:
        module.build_weights(shp, "01001", climate)
    except ValueError as error:
        assert "strictly increasing" in str(error)
    else:
        raise AssertionError("Descending nClimGrid coordinates should fail")

print("county-polygon nClimGrid weight tests passed")
