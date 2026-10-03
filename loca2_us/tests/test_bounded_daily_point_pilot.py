import importlib.util
import unittest
from pathlib import Path

import numpy as np


MODULE_PATH = Path(__file__).parents[1] / "scripts" / "run_bounded_daily_point_pilot.py"
SPEC = importlib.util.spec_from_file_location("loca2_point_pilot", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class PointPilotTests(unittest.TestCase):
    def test_longitude_normalization(self):
        grid = np.array([200.0, 300.0])
        self.assertAlmostEqual(MODULE.normalize_longitude(-96.79, grid), 263.21)

    def test_summary(self):
        pr = np.array([0.0, 0.2, 2.0, 3.0, 4.0, 5.0, 0.0])
        tmin = np.arange(7.0)
        tmax = tmin + 10.0
        result = MODULE.summarize(pr, tmin, tmax)
        self.assertEqual(result["days"], 7)
        self.assertEqual(result["wet_days_ge_1mm"], 4)
        self.assertEqual(result["maximum_consecutive_dry_days_lt_1mm"], 2)
        self.assertAlmostEqual(result["precipitation_total_mm"], 14.2)
        self.assertAlmostEqual(result["rx1day_mm"], 5.0)
        self.assertAlmostEqual(result["rx5day_mm"], 14.2)

    def test_negative_precipitation_fails(self):
        with self.assertRaisesRegex(ValueError, "negative precipitation"):
            MODULE.summarize(np.array([-0.1]), np.array([1.0]), np.array([2.0]))


if __name__ == "__main__":
    unittest.main()
