#!/usr/bin/env python3
import unittest

from validate_isimip3b_late_drought_crop_windows import Kahan, state, update


class TestCropWindowValidation(unittest.TestCase):
    def test_independent_accumulator(self):
        value = state()
        update(value, 2.0, {"status": "complete", "spei_mean": -1.5, "tail_clipped_months": 1})
        update(value, 3.0, {"status": "invalid_calendar"})
        self.assertEqual(value["declared"].total, 5.0)
        self.assertEqual(value["complete"].total, 2.0)
        self.assertEqual(value["weighted"].total, -3.0)
        self.assertEqual(value["clipped"].total, 2.0)

    def test_kahan_deterministic_order(self):
        value = Kahan()
        for number in (1e16, -1e16, 1.0): value.add(number)
        self.assertEqual(value.total, 1.0)


if __name__ == "__main__":
    unittest.main()
