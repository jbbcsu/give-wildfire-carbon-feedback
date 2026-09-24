#!/usr/bin/env python3

from __future__ import annotations

import unittest

import numpy as np

from build_hultgren_precip_basis_climatology import phase_basis


class PrecipBasisClimatologyTests(unittest.TestCase):
    def test_four_month_basis(self) -> None:
        result = phase_basis(np.array([1.0, 2.0, 3.0, 4.0]))
        np.testing.assert_allclose(result, [1.0, 9.0, 0.0, 1.0, 29.0, 0.0])

    def test_longer_basis(self) -> None:
        result = phase_basis(np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0]))
        np.testing.assert_allclose(result, [1.0, 9.0, 11.0, 1.0, 29.0, 61.0])

    def test_invalid_rain_rejected(self) -> None:
        for values in (np.array([1.0, 2.0, 3.0]), np.array([1.0, 2.0, 3.0, -1.0])):
            with self.assertRaises(ValueError):
                phase_basis(values)


if __name__ == "__main__":
    unittest.main()
