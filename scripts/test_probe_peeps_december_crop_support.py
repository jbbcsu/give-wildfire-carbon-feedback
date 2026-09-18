import unittest
import numpy as np

from probe_peeps_december_crop_support import nearest_linear, nearest_circular


class NearestTests(unittest.TestCase):
    def test_linear_bounds_and_ties(self):
        centers = np.array([-1., 0., 1.])
        points = np.array([-5., -0.5, 0.49, 5.])
        self.assertEqual(nearest_linear(points, centers).tolist(), [0, 0, 1, 2])

    def test_circular_antimeridian(self):
        centers = np.array([0., 90., 180., 270.])
        points = np.array([359., 1., 179., 271., 315.])
        self.assertEqual(nearest_circular(points, centers).tolist(), [0, 0, 2, 3, 3])

    def test_invalid_centers(self):
        with self.assertRaises(ValueError):
            nearest_linear(np.array([0.]), np.array([1., 0.]))


if __name__ == '__main__':
    unittest.main()
