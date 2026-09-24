#!/usr/bin/env python3

from __future__ import annotations

import unittest

from summarize_hultgren_yield_transports import summarize


class NamedModelSummaryTests(unittest.TestCase):
    def test_equal_model_mean_and_signs(self) -> None:
        result = summarize([
            {"climate_model": "A", "area_weighted_mean_delta_log_yield": -0.2, "coefficient_only_standard_error_log_points": 0.1},
            {"climate_model": "B", "area_weighted_mean_delta_log_yield": 0.1, "coefficient_only_standard_error_log_points": 0.2},
        ])
        self.assertAlmostEqual(result["equal_model_mean_delta_log_yield"], -0.05)
        self.assertEqual(result["models_negative"], 1)
        self.assertEqual(result["models_positive"], 1)


if __name__ == "__main__":
    unittest.main()
