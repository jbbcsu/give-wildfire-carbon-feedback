#!/usr/bin/env python3
import unittest

from summarize_isimip3b_late_drought_crop_windows import add, new_accumulator


class TestCropWindowSummary(unittest.TestCase):
    def test_area_weighted_accumulator_and_incomplete_denominator(self):
        value = new_accumulator()
        add(value, 2.0, {"status": "complete", "spei_mean": -1.5, "tail_clipped_months": 1})
        add(value, 3.0, {"status": "invalid_calendar"})
        self.assertEqual(value["declared_area_ha"], 5.0)
        self.assertEqual(value["complete_area_ha"], 2.0)
        self.assertEqual(value["area_x_spei"], -3.0)
        self.assertEqual(value["tail_clipped_area_ha"], 2.0)
        self.assertEqual(dict(value["status_counts"]), {"complete": 1, "invalid_calendar": 1})


if __name__ == "__main__":
    unittest.main()
