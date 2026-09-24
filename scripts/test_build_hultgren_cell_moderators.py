#!/usr/bin/env python3
"""Unit tests for cell-moderator assembly."""

from __future__ import annotations

import unittest

import pandas as pd

from build_hultgren_cell_moderators import choose_pwt_snapshot, combine_regimes, dominant_geometry_country


class ModeratorAssemblyTests(unittest.TestCase):
    def test_nearest_pwt_prefers_earlier_tie(self) -> None:
        frame = pd.DataFrame({
            "countrycode": ["AAA", "AAA", "AAA", "BBB"], "country": ["A", "A", "A", "B"],
            "year": [1999, 2001, 2000, 2000], "pop": [1.0, 1.0, 0.0, 2.0], "cgdpo": [10.0, 12.0, 20.0, 40.0],
        })
        result = choose_pwt_snapshot(frame, 2000).set_index("countrycode")
        self.assertEqual(int(result.loc["AAA", "pwt_year"]), 1999)
        self.assertAlmostEqual(float(result.loc["BBB", "ln_gdppc"]), 2.995732273553991)

    def test_dominant_country_does_not_sum_overlapping_regions(self) -> None:
        frame = pd.DataFrame({
            "native_lat_index": [1, 1, 1], "native_lon_index": [2, 2, 2],
            "region_key": ["AAA.x", "AAA.y", "BBB.z"],
            "intersection_area_equal_area_m2": [6.0, 6.0, 10.0],
        })
        result = dominant_geometry_country(frame).iloc[0]
        self.assertEqual(result.geometry_country, "BBB")
        self.assertEqual(int(result.geometry_country_candidates), 2)

    def test_regime_combination_is_area_weighted(self) -> None:
        base = {"native_lat_index": 1, "native_lon_index": 2, "latitude": 1.25, "longitude": 2.25}
        rainfed = pd.DataFrame([{**base, "mirca_area_ha": 3.0, "lr_tmax_crop": 10.0, "lr_prcp_crop": 100.0}])
        irrigated = pd.DataFrame([{**base, "mirca_area_ha": 1.0, "lr_tmax_crop": 14.0, "lr_prcp_crop": 60.0}])
        result = combine_regimes(rainfed, irrigated).iloc[0]
        self.assertAlmostEqual(result.irrigated_share, 0.25)
        self.assertAlmostEqual(result.lr_tmax_crop, 11.0)
        self.assertAlmostEqual(result.lr_prcp_crop, 90.0)


if __name__ == "__main__":
    unittest.main()
