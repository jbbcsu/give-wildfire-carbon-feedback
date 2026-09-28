#!/usr/bin/env python3
"""Boundary-year regression tests for the multi-block Rice2 builder."""
from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from build_hultgren_rice_grid_weather_basis import assemble_year, crop_month_keys


class RiceMultiblockTests(unittest.TestCase):
    @staticmethod
    def support() -> pd.DataFrame:
        return pd.DataFrame({
            "native_lat_index": [1], "native_lon_index": [2],
            "latitude": [89.25], "longitude": [-178.75],
            "plant_month": [12], "harvest_month": [3], "season_months": [4],
        })

    def test_cross_year_uses_previous_block_month(self) -> None:
        self.assertEqual(
            crop_month_keys(1991, 12, 3),
            ((1990, 12), (1991, 1), (1991, 2), (1991, 3)),
        )
        months = pd.date_range("1990-12-01", "1991-03-01", freq="MS")
        arrays = {
            "rain": np.array([[1.0], [2.0], [3.0], [4.0]]),
            "dd14": np.array([[10.0], [20.0], [30.0], [40.0]]),
            "dd30": np.zeros((4, 1)),
            "monthly_tmin": np.array([[11.0], [12.0], [13.0], [14.0]]),
        }
        result = assemble_year(1991, months, arrays, self.support(), "ri2_noirr").iloc[0]
        self.assertTrue(result.cross_year)
        self.assertEqual(result.prcp_poly_1_bin1, 3.0)
        self.assertEqual(result.prcp_poly_1_bin2, 7.0)
        self.assertEqual(result.prcp_poly_1_bin3, 0.0)
        self.assertEqual(result.prcp_poly_2_bin3, 0.0)

    def test_first_source_year_cross_year_season_fails_closed(self) -> None:
        months = pd.date_range("1981-01-01", "1981-12-01", freq="MS")
        arrays = {
            "rain": np.ones((12, 1)), "dd14": np.ones((12, 1)),
            "dd30": np.zeros((12, 1)), "monthly_tmin": np.ones((12, 1)),
        }
        with self.assertRaisesRegex(ValueError, "source period lacks crop season"):
            assemble_year(1981, months, arrays, self.support(), "ri2_noirr")


if __name__ == "__main__":
    unittest.main()
