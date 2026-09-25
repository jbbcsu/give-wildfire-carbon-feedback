#!/usr/bin/env python3
"""Unit tests for the five-ESM timing promotion gate algebra."""

import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from evaluate_hultgren_timing_gmst_promotion_gate import evaluate_component, origin_slope


class TimingGateTests(unittest.TestCase):
    def test_origin_slope(self):
        points = [
            {"climate_model": "a", "gmst_difference_k": 1.0, "delta_log_yield": -2.0},
            {"climate_model": "b", "gmst_difference_k": 2.0, "delta_log_yield": -4.0},
        ]
        self.assertEqual(origin_slope(points), -2.0)

    def test_stable_linear_component_passes(self):
        points = [
            {"climate_model": name, "gmst_difference_k": value, "delta_log_yield": -0.1 * value}
            for name, value in zip("abcde", [1.0, 1.5, 2.0, 2.5, 3.0])
        ]
        result = evaluate_component(points)
        self.assertTrue(result["sign_stable"])
        self.assertTrue(result["all_whole_esm_holdouts_improve_on_zero"])
        self.assertTrue(math.isclose(result["origin_constrained_slope_delta_log_yield_per_k"], -0.1))

    def test_sign_reversal_fails_stability(self):
        points = [
            {"climate_model": name, "gmst_difference_k": value, "delta_log_yield": response}
            for name, value, response in zip("abcde", [1, 2, 3, 4, 5], [-0.1, -0.2, 0.1, -0.4, -0.5])
        ]
        result = evaluate_component(points)
        self.assertFalse(result["sign_stable"])
        self.assertEqual(result["models_positive"], 1)
        self.assertEqual(result["models_negative"], 4)


if __name__ == "__main__":
    unittest.main()
