#!/usr/bin/env python3

from __future__ import annotations

import unittest

import numpy as np

from build_hultgren_cell_annual_precip_climatology import summarize_annual


class AnnualPrecipClimatologyTests(unittest.TestCase):
    def test_summary(self) -> None:
        annual = np.array([[100.0, 200.0], [300.0, 600.0]])
        result = summarize_annual(annual)
        np.testing.assert_allclose(result["annual_precip_mean_mm"], [200.0, 400.0])
        np.testing.assert_allclose(result["annual_precip_min_mm"], [100.0, 200.0])
        np.testing.assert_allclose(result["annual_precip_max_mm"], [300.0, 600.0])
        np.testing.assert_allclose(result["annual_precip_sd_mm"], [np.sqrt(20_000.0), np.sqrt(80_000.0)])

    def test_zero_is_retained(self) -> None:
        result = summarize_annual(np.array([[0.0], [0.0]]))
        self.assertEqual(result["annual_precip_mean_mm"][0], 0.0)

    def test_negative_or_nonfinite_rejected(self) -> None:
        for annual in (np.array([[1.0], [-0.1]]), np.array([[1.0], [np.nan]])):
            with self.assertRaises(ValueError):
                summarize_annual(annual)


if __name__ == "__main__":
    unittest.main()
