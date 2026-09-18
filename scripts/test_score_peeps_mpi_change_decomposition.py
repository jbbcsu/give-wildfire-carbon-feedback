import unittest

import numpy as np

from score_peeps_mpi_change_decomposition import compute


class ChangeDecompositionTests(unittest.TestCase):
    def test_exact_total_and_redistribution(self):
        baseline = np.full((12, 2), 10.0)
        direct_end = baseline.copy()
        direct_end[0] += [12, 0]
        direct_end[1] += [0, 12]
        published_end = baseline.copy()
        published_end[0] += [6, 6]
        published_end[1] += [6, 6]
        result = compute(baseline, direct_end, baseline, published_end, np.array([1.0, 3.0]))
        self.assertAlmostEqual(result["annual"]["published_minus_direct_mean_change_mm"], 0)
        self.assertAlmostEqual(result["decomposition"]["annual_amount_component_rmse_per_month_mm"], 0)
        self.assertGreater(result["decomposition"]["within_year_redistribution_component_rmse_mm"], 0)

    def test_negative_published_levels_are_not_clipped(self):
        baseline = np.ones((12, 1))
        end = baseline.copy()
        end[0] = -1
        result = compute(baseline, baseline, baseline, end, np.array([1.0]))
        self.assertAlmostEqual(result["annual"]["published_mean_change_mm"], -2)

    def test_invalid_direct_rainfall_rejected(self):
        baseline = np.ones((12, 1))
        bad = baseline.copy()
        bad[0] = -1
        with self.assertRaises(ValueError):
            compute(baseline, bad, baseline, baseline, np.array([1.0]))


if __name__ == "__main__":
    unittest.main()
