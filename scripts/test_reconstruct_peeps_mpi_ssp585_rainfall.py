import base64
import unittest

import numpy as np

from reconstruct_peeps_mpi_ssp585_rainfall import crc32c, summarize


class SourceReconstructionTests(unittest.TestCase):
    def test_crc32c_standard_vector(self):
        self.assertEqual(base64.b64decode(crc32c(b'123456789')).hex(), 'e3069283')

    def test_monthly_quantity_and_share_error(self):
        direct = np.full((12, 2), 10.0)
        published = direct.copy()
        published[0, 0], published[1, 0] = 20.0, 0.0
        published[:, 1] = 20.0
        result = summarize(direct, published, np.array([1.0, 1.0]))
        self.assertAlmostEqual(result['all_area_annual_bias_mm'], 60.0)
        self.assertAlmostEqual(result['common_valid_mean_month_share_tv_error'], 1 / 24)
        published[0, 0] = -1.0
        result = summarize(direct, published, np.array([3.0, 1.0]))
        self.assertEqual(result['common_valid_area_percent'], 25.0)
        self.assertEqual(result['predicted_any_negative_area_percent'], 75.0)


if __name__ == '__main__':
    unittest.main()
