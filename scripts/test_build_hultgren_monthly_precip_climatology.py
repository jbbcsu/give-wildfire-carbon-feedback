#!/usr/bin/env python3
"""Unit tests for the crop-season monthly precipitation climatology."""

import unittest

import numpy as np
import pandas as pd

from build_hultgren_monthly_precip_climatology import offset_climatology


class MonthlyClimatologyTests(unittest.TestCase):
    def test_same_year_calendar_and_means(self):
        months = pd.date_range("1981-01-01", "1983-12-01", freq="MS")
        lookup = {(int(value.year), int(value.month)): i for i, value in enumerate(months)}
        rain = np.arange(1, len(months) + 1, dtype=float)
        values, squared_values, calendar_months = offset_climatology(rain, lookup, 5, 8, range(1982, 1984))
        expected = np.mean([[17, 18, 19, 20], [29, 30, 31, 32]], axis=0)
        expected_squared = np.mean(np.square([[17, 18, 19, 20], [29, 30, 31, 32]]), axis=0)
        np.testing.assert_allclose(values, expected)
        np.testing.assert_allclose(squared_values, expected_squared)
        np.testing.assert_array_equal(calendar_months, [5, 6, 7, 8])

    def test_cross_year_calendar(self):
        months = pd.date_range("1980-01-01", "1983-12-01", freq="MS")
        lookup = {(int(value.year), int(value.month)): i for i, value in enumerate(months)}
        rain = np.ones(len(months), dtype=float)
        values, squared_values, calendar_months = offset_climatology(rain, lookup, 10, 3, range(1981, 1984))
        np.testing.assert_allclose(values, np.ones(6))
        np.testing.assert_allclose(squared_values, np.ones(6))
        np.testing.assert_array_equal(calendar_months, [10, 11, 12, 1, 2, 3])

    def test_rejects_negative_rainfall(self):
        months = pd.date_range("1981-01-01", "1982-12-01", freq="MS")
        lookup = {(int(value.year), int(value.month)): i for i, value in enumerate(months)}
        rain = np.ones(len(months), dtype=float)
        rain[16] = -1.0
        with self.assertRaisesRegex(ValueError, "invalid crop-season monthly rainfall"):
            offset_climatology(rain, lookup, 5, 8, range(1982, 1983))


if __name__ == "__main__":
    unittest.main()
