#!/usr/bin/env python3

import math
import unittest

import numpy as np

from build_epa_fair_hultgren_quantity_market_sensitivities import damage_from_ratio


class MarketSensitivityTests(unittest.TestCase):
    def test_zero_and_scalar_formula(self) -> None:
        value = np.array([100.0, 250.0])
        ratio = np.ones((2, 3))
        self.assertTrue(np.array_equal(damage_from_ratio(value, ratio, 0.1, 0.04), np.zeros((2, 3))))

        ratio = np.array([[math.exp(0.01)], [math.exp(-0.02)]])
        actual = damage_from_ratio(value, ratio, 0.5, 0.06)[:, 0]
        expected = []
        for baseline, shift in zip(value, (0.01, -0.02), strict=True):
            price_shift = -shift / 0.56
            z = 0.94 * price_shift
            expected.append(-baseline * shift / 1.5 * math.expm1(z) / z)
        np.testing.assert_allclose(actual, expected, rtol=2e-14, atol=0.0)


if __name__ == "__main__":
    unittest.main()
