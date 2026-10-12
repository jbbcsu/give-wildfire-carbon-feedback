#!/usr/bin/env python3
"""Small deterministic tests for the U.S. PEEPS bridge arithmetic."""

from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from build_us_corn_peeps_climate_yield_bridge import equal_county_vector, month_overlap_days


class CropSeasonOverlapTests(unittest.TestCase):
    def test_leap_year_partial_months(self) -> None:
        values = month_overlap_days(pd.Timestamp("2020-02-15"), pd.Timestamp("2020-03-10"))
        self.assertEqual(values[1], 15.0)
        self.assertEqual(values[2], 10.0)
        self.assertEqual(values.sum(), 25.0)

    def test_full_cross_year_season(self) -> None:
        values = month_overlap_days(pd.Timestamp("2019-11-01"), pd.Timestamp("2020-02-29"))
        np.testing.assert_array_equal(values[[10, 11, 0, 1]], [30.0, 31.0, 31.0, 29.0])
        self.assertEqual(values.sum(), 121.0)


class WeightingTests(unittest.TestCase):
    def test_equal_county_not_equal_row(self) -> None:
        frame = pd.DataFrame({"county_geoid": ["001", "001", "002"], **{f"contrast_{index}": [0.0, 2.0, 4.0] for index in range(8)}})
        result = equal_county_vector(frame)
        np.testing.assert_array_equal(result, np.full(8, 2.5))
        self.assertNotEqual(float(result[0]), float(frame.contrast_0.mean()))


if __name__ == "__main__":
    unittest.main(verbosity=2)
