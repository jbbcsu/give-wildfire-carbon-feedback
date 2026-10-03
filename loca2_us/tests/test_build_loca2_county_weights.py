import importlib.util
import unittest
from pathlib import Path

import numpy as np


MODULE_PATH = Path(__file__).parents[1] / "scripts" / "build_loca2_county_weights.py"
SPEC = importlib.util.spec_from_file_location("loca2_county_weights", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class CountyWeightTests(unittest.TestCase):
    def test_coordinate_edges(self):
        result = MODULE.coordinate_edges(np.array([0.5, 1.5, 2.5]), "x")
        np.testing.assert_allclose(result, [0.0, 1.0, 2.0, 3.0])

    def test_irregular_coordinate_fails(self):
        with self.assertRaisesRegex(ValueError, "not regular"):
            MODULE.coordinate_edges(np.array([0.0, 1.0, 2.1]), "x")

    def test_longitude_conversion(self):
        result = MODULE.longitude_west_east(np.array([234.53125, 263.21875, 293.46875]))
        np.testing.assert_allclose(result, [-125.46875, -96.78125, -66.53125])


if __name__ == "__main__":
    unittest.main()
