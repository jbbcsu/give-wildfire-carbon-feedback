#!/usr/bin/env python3
"""Small independent arithmetic-audit tests; no network or project data."""
import unittest

import numpy as np

from audit_peeps_mpi_source_reconstruction import audit_year, compare


class AuditTests(unittest.TestCase):
    def test_all_positive_constant_months(self):
        area = np.array([1.0, 3.0])
        direct = np.full((12, 2), 10.0)
        published = np.full((12, 2), 12.0)
        result = audit_year(2015, direct, published, area)
        self.assertEqual(result["common_valid_centers"], 2)
        self.assertEqual(result["predicted_any_negative_area_percent"], 0)
        self.assertAlmostEqual(result["all_area_annual_bias_mm"], 24.0)
        self.assertAlmostEqual(result["all_area_annual_rmse_mm"], 24.0)
        self.assertAlmostEqual(result["common_valid_mean_month_share_tv_error"], 0)
        self.assertAlmostEqual(result["months"][0]["mean_bias_mm"], 2.0)

    def test_negative_levels_excluded_only_from_share_score(self):
        area = np.array([1.0, 3.0])
        direct = np.full((12, 2), 10.0)
        published = direct.copy()
        published[0, 0] = -1.0
        result = audit_year(2100, direct, published, area)
        self.assertEqual(result["predicted_any_negative_area_percent"], 25.0)
        self.assertEqual(result["common_valid_centers"], 1)
        self.assertAlmostEqual(result["common_valid_area_percent"], 75.0)
        self.assertAlmostEqual(result["months"][0]["mean_bias_mm"], -11.0/4.0)
        self.assertAlmostEqual(result["common_valid_mean_month_share_tv_error"], 0)

    def test_report_disagreement_fails(self):
        with self.assertRaises(ValueError):
            compare({"x": 1.0}, {"x": 1.01})


if __name__ == "__main__":
    unittest.main()
