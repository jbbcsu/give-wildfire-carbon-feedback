import unittest

import numpy as np

from score_peeps_mpi_baseline_anomaly import metrics


class AnchoredMonthlyTests(unittest.TestCase):
    def test_perfect_change(self):
        base = np.ones((12, 2))
        target = base + 1
        result = metrics(base, target, base, target, np.array([1.0, 3.0]))
        self.assertEqual(result["anchored"]["spatial_annual_rmse_mm"], 0)
        self.assertEqual(result["negative_anchored_month_center_count"], 0)

    def test_negative_not_clipped(self):
        base = np.ones((12, 1))
        pub_new = base.copy()
        pub_new[0, 0] = -2
        result = metrics(base, base, base, pub_new, np.array([1.0]))
        self.assertEqual(result["negative_anchored_month_center_count"], 1)
        self.assertEqual(result["minimum_anchored_monthly_mm"], -2)
        self.assertEqual(result["common_valid_month_share_area_fraction"], 0)

    def test_mixed_valid_support(self):
        base = np.ones((12, 2))
        pub_new = base.copy()
        pub_new[0, 0] = -2
        result = metrics(base, base, base, pub_new, np.array([1.0, 3.0]))
        self.assertAlmostEqual(result["common_valid_month_share_area_fraction"], 0.75)
        self.assertAlmostEqual(result["anchored"]["valid_support_month_share_tv"], 0)


if __name__ == "__main__":
    unittest.main()
