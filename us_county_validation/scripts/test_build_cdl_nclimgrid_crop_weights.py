#!/usr/bin/env python3
"""Synthetic tests for fixed-CDL-to-nClimGrid crop-pixel weights."""
from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np
import rasterio
import shapefile
import xarray as xr
from pyproj import CRS, Transformer
from rasterio.transform import from_origin

from build_cdl_nclimgrid_crop_weights import build_weights


def write_county(path: Path, bounds: tuple[float, float, float, float]) -> None:
    left, bottom, right, top = bounds
    writer = shapefile.Writer(str(path))
    writer.field("STATEFP", "C", size=2)
    writer.field("COUNTYFP", "C", size=3)
    writer.field("GEOID", "C", size=5)
    writer.field("NAME", "C", size=80)
    writer.field("ALAND", "N", size=18, decimal=0)
    writer.field("AWATER", "N", size=18, decimal=0)
    writer.poly(
        [[
            [left, bottom], [left, top], [right, top], [right, bottom], [left, bottom]
        ]]
    )
    writer.record("31", "039", "31039", "Synthetic", int((right - left) * (top - bottom)), 0)
    writer.close()
    path.with_suffix(".prj").write_text(CRS.from_epsg(5070).to_wkt(), encoding="utf-8")


def write_climate(path: Path, transform, width: int, height: int) -> None:
    to_wgs84 = Transformer.from_crs(5070, 4326, always_xy=True)
    columns = np.arange(width, dtype=float)
    rows = np.arange(height, dtype=float)
    xx, yy = np.meshgrid(
        transform.c + (columns + 0.5) * transform.a,
        transform.f + (rows + 0.5) * transform.e,
    )
    lon, lat = to_wgs84.transform(xx, yy)
    lon_mid = float((lon.min() + lon.max()) / 2)
    lat_mid = float((lat.min() + lat.max()) / 2)
    lon_span = float(lon.max() - lon.min()) * 1.2
    lat_span = float(lat.max() - lat.min()) * 1.2
    longitude = np.array([lon_mid - lon_span / 4, lon_mid + lon_span / 4])
    latitude = np.array([lat_mid - lat_span / 4, lat_mid + lat_span / 4])
    values = np.zeros((1, 2, 2), dtype="float32")
    dataset = xr.Dataset(
        {
            "prcp": (("time", "lat", "lon"), values.copy()),
            "tavg": (("time", "lat", "lon"), values.copy()),
            "tmin": (("time", "lat", "lon"), values.copy()),
            "tmax": (("time", "lat", "lon"), values.copy()),
        },
        coords={"time": [np.datetime64("1981-01-01")], "lat": latitude, "lon": longitude},
        attrs={"title": "nClimGrid-Daily, Gridded Fields", "product_version": "v1-0-0 20220829"},
    )
    dataset.prcp.attrs.update(standard_name="precipitation_amount", units="millimeter")
    for field in ["tavg", "tmin", "tmax"]:
        dataset[field].attrs.update(standard_name="air_temperature", units="degree_Celsius")
    dataset.to_netcdf(path, engine="h5netcdf")


with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    width = height = 12
    to_area = Transformer.from_crs(4326, 5070, always_xy=True)
    center_x, center_y = to_area.transform(-96.0, 41.0)
    left = center_x - width * 30 / 2
    top = center_y + height * 30 / 2
    transform_affine = from_origin(left, top, 30, 30)
    bounds = (left, top - height * 30, left + width * 30, top)

    county_path = root / "counties.shp"
    write_county(county_path, bounds)
    climate_path = root / "climate.nc"
    write_climate(climate_path, transform_affine, width, height)

    crop = np.zeros((height, width), dtype="uint8")
    crop[:, :5] = 1
    crop[:, 5:10] = 5
    crop[:, 10] = 241  # distinct double-crop class: deliberately excluded
    raster_path = root / "cdl.tif"
    with rasterio.open(
        raster_path,
        "w",
        driver="GTiff",
        height=height,
        width=width,
        count=1,
        dtype="uint8",
        crs="EPSG:5070",
        transform=transform_affine,
        tiled=True,
        blockxsize=16,
        blockysize=16,
    ) as dataset:
        dataset.write(crop, 1)
        dataset.update_tags(AREA_OR_POINT="Area")

    weights, audit = build_weights(
        county_path,
        "31039",
        climate_path,
        str(raster_path),
        ["corn_grain", "soybeans"],
        "retrospective_2017_mask_sensitivity",
        strict_official_profile=False,
    )
    assert set(weights.calendar_crop) == {"corn_grain", "soybeans"}
    assert set(weights.cdl_class_code) == {1, 5}
    assert not weights.double_crop_classes_included.any()
    assert weights.groupby("calendar_crop").spatial_weight.sum().round(12).eq(1).all()
    assert weights.groupby("calendar_crop").crop_area_m2.sum().eq(60 * 900).all()
    assert weights.groupby("calendar_crop").calendar_class_share.first().eq(1).all()
    assert weights.coverage_fraction.eq(1).all()
    assert not weights.response_estimation_authorized.any()
    assert not weights.scc_authorized.any()
    assert audit["county_center_pixel_count"] == 144
    assert audit["crops"]["corn_grain"]["in_county_pixels"] == 60
    assert audit["crops"]["soybeans"]["in_county_pixels"] == 60
    assert audit["relationship_estimated"] is False

    try:
        build_weights(
            county_path,
            "31039",
            climate_path,
            str(raster_path),
            ["winter_wheat"],
            "retrospective_2017_mask_sensitivity",
            strict_official_profile=False,
        )
        raise AssertionError("Incomplete wheat-class requests should fail")
    except ValueError as error:
        assert "winter, spring, and durum" in str(error)

    try:
        build_weights(
            county_path,
            "31039",
            climate_path,
            str(raster_path),
            ["corn_grain"],
            "unlabeled_historical_mask",
            strict_official_profile=False,
        )
        raise AssertionError("Unregistered temporal roles should fail")
    except ValueError as error:
        assert "temporal role" in str(error)

print("fixed-CDL nClimGrid crop-weight tests passed")
