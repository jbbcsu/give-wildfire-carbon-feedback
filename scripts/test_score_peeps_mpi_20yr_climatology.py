import unittest

import numpy as np

from score_peeps_mpi_20yr_climatology import aggregate_member, period_levels


class ClimatologyTests(unittest.TestCase):
    def test_exact_month_counts(self):
        a = {"early_sum_mm": np.ones((12, 2))*10, "early_counts": np.ones(12, int)*10,
             "late_sum_mm": np.ones((12, 2))*30, "late_counts": np.ones(12, int)*10}
        b = {"early_sum_mm": np.ones((12, 2))*20, "early_counts": np.ones(12, int)*10,
             "late_sum_mm": np.ones((12, 2))*50, "late_counts": np.ones(12, int)*10}
        result = aggregate_member([a, b])
        self.assertTrue(np.array_equal(result["early"], np.ones((12, 2))*1.5))
        self.assertTrue(np.array_equal(result["late"], np.ones((12, 2))*4))
        b["late_counts"][0] -= 1
        with self.assertRaises(ValueError):
            aggregate_member([a, b])

    def test_month_share_restricted_support(self):
        direct = {p: np.ones((12, 2)) for p in ("early", "late")}
        predicted = {p: np.ones((12, 2)) for p in ("early", "late")}
        predicted["late"][0, 0] = -1
        result = period_levels(direct, predicted, np.array([1.0, 3.0]))
        self.assertAlmostEqual(result["late"]["valid_share_area_fraction"], 0.75)
        self.assertAlmostEqual(result["early"]["fixed_both_periods_valid_area_fraction"], 0.75)
        self.assertAlmostEqual(result["late"]["fixed_both_periods_valid_area_fraction"], 0.75)
        self.assertEqual(result["late"]["negative_month_center_count"], 1)


if __name__ == "__main__":
    unittest.main()
