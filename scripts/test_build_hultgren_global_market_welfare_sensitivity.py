#!/usr/bin/env python3

from __future__ import annotations

import unittest

import numpy as np

from build_hultgren_global_market_welfare_sensitivity import adaptation_factor


class GlobalMarketSensitivityTests(unittest.TestCase):
    def test_adaptation_factors(self) -> None:
        years = np.array([2020, 2100])
        np.testing.assert_allclose(adaptation_factor(years, "fixed"), [1.0, 1.0])
        np.testing.assert_allclose(adaptation_factor(years, "trend"), [1.0, 0.76])
        np.testing.assert_allclose(adaptation_factor(years, "upper"), [1.0, 0.44])


if __name__ == "__main__":
    unittest.main()
