#!/usr/bin/env python3
"""Synthetic checks for geographic clustering and Holm adjustment."""
from __future__ import annotations

import unittest

import numpy as np

from evaluate_multicrop_rainfed_distribution_geographic_audit import (
    geographic_cluster_codes,
    holm_adjust,
)


class GeographicAuditTests(unittest.TestCase):
    def test_cluster_boundaries(self) -> None:
        codes = geographic_cluster_codes(
            np.array([-89.9, -80.0, 0.0, 89.9]),
            np.array([0.0, 9.9, 10.0, 359.9]),
            10,
            10,
        )
        self.assertEqual(codes.tolist(), [0, 36, 325, 647])

    def test_holm_known_values_and_monotonicity(self) -> None:
        actual = holm_adjust([0.01, 0.04, 0.03, 0.20])
        np.testing.assert_allclose(actual, [0.04, 0.09, 0.09, 0.20])
        order = np.argsort([0.01, 0.04, 0.03, 0.20])
        ordered_adjusted = np.asarray(actual)[order]
        self.assertTrue(np.all(np.diff(ordered_adjusted) >= 0))


if __name__ == "__main__":
    unittest.main()
