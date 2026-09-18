import unittest

import numpy as np

from probe_peeps_full_month_crop_support import summarize_common_support


class FullMonthCropScreenTests(unittest.TestCase):
    def test_quantity_and_month_share_are_distinct(self):
        a = np.full((12, 2), 10.0)
        b = a.copy()
        b[0, 0], b[1, 0] = 20.0, 0.0  # same annual total, changed timing
        b[:, 1] = 20.0  # changed total, identical shares
        found = summarize_common_support(a, b, np.array([1.0, 1.0]))
        self.assertEqual(found['common_valid_centers'], 2)
        self.assertAlmostEqual(found['mean_annual_2015_mm'], 120)
        self.assertAlmostEqual(found['mean_annual_2100_mm'], 180)
        self.assertAlmostEqual(found['mean_cell_month_share_tv'], 1 / 24)

    def test_negative_month_excluded_without_clipping(self):
        a = np.full((12, 2), 10.0)
        b = a.copy()
        b[0, 0] = -1.0
        found = summarize_common_support(a, b, np.array([3.0, 1.0]))
        self.assertEqual(found['common_valid_centers'], 1)
        self.assertEqual(found['common_valid_area_ha'], 1.0)
        self.assertEqual(found['common_valid_area_percent'], 25.0)


if __name__ == '__main__':
    unittest.main()
