#!/usr/bin/env python3

from __future__ import annotations

import unittest

import numpy as np

from build_epa_fair_hultgren_quantity_damage_paths import adaptation_factors, country_market_damage


class QuantityDamagePathTests(unittest.TestCase):
    def test_adaptation_factors(self) -> None:
        years = np.array([2020, 2100, 2300])
        np.testing.assert_allclose(adaptation_factors(years, "fixed"), [1.0, 1.0, 1.0])
        np.testing.assert_allclose(adaptation_factors(years, "trend"), [1.0, 0.76, 0.65])
        np.testing.assert_allclose(adaptation_factors(years, "upper"), [1.0, 0.44, 0.30])

    def test_zero_and_adverse_market_shifts(self) -> None:
        values = np.array([100.0, 200.0])
        ratios = np.array([[1.0, 0.99], [1.0, 0.95]])
        damage = country_market_damage(values, ratios)
        np.testing.assert_array_equal(damage[:, 0], 0.0)
        self.assertTrue(np.all(damage[:, 1] > 0.0))


if __name__ == "__main__":
    unittest.main()
