#!/usr/bin/env python3
"""Self-contained tests for the published-maize response algebra."""

from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.hultgren_maize_response import MaizeBasis, PublishedEstimate


def basis(**updates: float) -> MaizeBasis:
    values = {
        "gdd": 100.0,
        "kdd": 5.0,
        "prcp_poly_1_bins": (10.0, 20.0, 30.0),
        "prcp_poly_2_bins": (100.0, 400.0, 900.0),
        "ln_gdppc": 9.0,
        "irrigated_share": 0.25,
        "lr_tmax_crop": 24.0,
        "lr_prcp_crop": 300.0,
    }
    values.update(updates)
    return MaizeBasis(**values)


class TestMaizeBasis(unittest.TestCase):
    def test_published_precipitation_caps(self) -> None:
        values = basis().primitive_values()
        self.assertEqual(values["pbarcut_gdd"], 200.0)
        self.assertEqual(values["pbarcut_kdd"], 100.0)
        self.assertEqual(values["pbarcut_prcp"], 250.0)

    def test_interaction_parser(self) -> None:
        vector = basis().design_vector([
            "gdd", "c.gdd#c.ln_gdppc",
            "c.prcp_poly_2_bin3#c.lr_tmax_crop#c.pbarcut_prcp", "_cons",
        ])
        np.testing.assert_allclose(vector, [100.0, 900.0, 900.0 * 24.0 * 250.0, 1.0])

    def test_invalid_inputs_fail(self) -> None:
        with self.assertRaises(ValueError):
            basis(irrigated_share=1.1).primitive_values()
        with self.assertRaises(ValueError):
            basis(lr_prcp_crop=-1.0).primitive_values()
        with self.assertRaises(ValueError):
            basis().design_vector(["not_a_published_term"])


class TestPublishedEstimate(unittest.TestCase):
    def setUp(self) -> None:
        self.estimate = PublishedEstimate(
            terms=["gdd", "_cons"],
            coefficients=np.asarray([0.01, 2.0]),
            covariance=np.asarray([[0.0004, 0.0], [0.0, 0.01]]),
        )

    def test_zero_contrast(self) -> None:
        result = self.estimate.contrast(basis(), basis())
        self.assertEqual(result["delta_log_yield"], 0.0)
        self.assertEqual(result["exact_percent_yield_change"], 0.0)
        self.assertEqual(result["coefficient_only_standard_error"], 0.0)

    def test_known_contrast_and_uncertainty(self) -> None:
        result = self.estimate.contrast(basis(), basis(gdd=103.0))
        self.assertAlmostEqual(result["delta_log_yield"], 0.03)
        self.assertAlmostEqual(result["exact_percent_yield_change"], 100.0 * math.expm1(0.03))
        self.assertAlmostEqual(result["coefficient_only_standard_error"], 0.06)


if __name__ == "__main__":
    unittest.main()
