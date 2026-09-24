#!/usr/bin/env python3

from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from build_hultgren_country_market_welfare_sensitivity import country_year_damage, damage_from_log_shift


class CountryMarketTests(unittest.TestCase):
    def test_zero_and_separate_country_aggregation(self) -> None:
        values = np.array([100.0, 200.0])
        np.testing.assert_allclose(damage_from_log_shift(values, 0.1, 0.04, np.zeros(2)), 0.0)
        frame = pd.DataFrame({"iso3": ["AAA", "AAA", "BBB"], "maize_gross_production_value_constant_2014_2016_usd": [25.0, 75.0, 200.0]})
        baseline = pd.Series({"AAA": 100.0, "BBB": 200.0})
        response = np.log(np.array([0.8, 0.8, 1.1]))
        damage, minimum, maximum = country_year_damage(frame, baseline, response, -10.0, 10.0, 1.0, 0.1, 0.04)
        shifts = np.log(np.array([0.8, 1.1]))
        expected = damage_from_log_shift(np.array([100.0, 200.0]), 0.1, 0.04, shifts).sum()
        self.assertAlmostEqual(damage, expected)
        self.assertAlmostEqual(minimum, 0.8)
        self.assertAlmostEqual(maximum, 1.1)


if __name__ == "__main__":
    unittest.main()
