#!/usr/bin/env python3
"""Focused Rice2 support and Rice1 compatibility tests for the grid builder."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np
import rasterio
import xarray as xr
from rasterio.transform import from_origin

from build_hultgren_rice_grid_weather_basis import load_support


class RiceGridSupportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        root = Path(self.temporary.name)
        self.calendar = root / "calendar.nc"
        self.irrigated = root / "irrigated.tif"
        self.rainfed = root / "rainfed.tif"
        latitude = 89.75 - 0.5 * np.arange(360)
        longitude = -179.75 + 0.5 * np.arange(720)
        planting = np.full((360, 720), np.nan, dtype=np.float32)
        maturity = np.full((360, 720), np.nan, dtype=np.float32)
        fraction = np.zeros((360, 720), dtype=np.float32)
        # Three, five, six, and six whole months. Cell 2 has zero publisher
        # season fraction but remains in the legacy broad-Rice1 mask.
        planting[0, :4] = 1.0
        maturity[0, :4] = [61.0, 122.0, 153.0, 153.0]
        fraction[0, [0, 1, 3]] = 1.0
        xr.Dataset(
            {
                "planting_day": (("lat", "lon"), planting),
                "maturity_day": (("lat", "lon"), maturity),
                "fraction_of_harvested_area": (("lat", "lon"), fraction),
            },
            coords={"lat": latitude, "lon": longitude},
        ).to_netcdf(self.calendar, engine="h5netcdf")
        profile = {
            "driver": "GTiff", "height": 360, "width": 720, "count": 1,
            "dtype": "float32", "crs": "EPSG:4326",
            "transform": from_origin(-180.0, 90.0, 0.5, 0.5), "nodata": 0.0,
        }
        for path in (self.irrigated, self.rainfed):
            values = np.zeros((360, 720), dtype=np.float32)
            values[0, :4] = 1.0
            with rasterio.open(path, "w", **profile) as target:
                target.write(values, 1)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_rice2_uses_positive_fraction_and_three_month_minimum(self) -> None:
        support, audit = load_support(self.calendar, None, None, "ri2_noirr")
        self.assertEqual(support.native_lon_index.tolist(), [0, 1, 3])
        self.assertEqual(support.season_months.tolist(), [3, 5, 6])
        self.assertEqual(audit["eligible_minimum_months"], 3)
        self.assertTrue(audit["publisher_fraction_used_only_as_boolean_support"])
        self.assertFalse(audit["annual_mirca_inputs_used"])

    def test_rice1_legacy_mask_and_six_month_minimum_are_preserved(self) -> None:
        support, audit = load_support(
            self.calendar, self.irrigated, self.rainfed, "ri1_noirr"
        )
        self.assertEqual(support.native_lon_index.tolist(), [2, 3])
        self.assertEqual(support.season_months.tolist(), [6, 6])
        self.assertEqual(audit["eligible_minimum_months"], 6)
        self.assertEqual(audit["eligible_six_to_twelve_month_cells"], 2)
        self.assertTrue(audit["annual_mirca_inputs_used"])
        self.assertFalse(audit["publisher_fraction_used_only_as_boolean_support"])


if __name__ == "__main__":
    unittest.main()
