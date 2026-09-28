#!/usr/bin/env python3
"""Small invariants for the Hultgren Rice2 feasibility audit."""
from __future__ import annotations

import unittest

import numpy as np

from audit_hultgren_rice2_weather_basis_feasibility import phase_partition_counts, recover_unrepaired


class Rice2FeasibilityTests(unittest.TestCase):
    def test_source_phase_partition_supports_short_seasons(self) -> None:
        self.assertEqual(phase_partition_counts(3), (2, 1, 0))
        self.assertEqual(phase_partition_counts(4), (2, 2, 0))
        self.assertEqual(phase_partition_counts(5), (2, 3, 0))
        self.assertEqual(phase_partition_counts(6), (2, 3, 1))
        self.assertEqual(phase_partition_counts(12), (2, 3, 7))

    def test_outside_source_observed_domain_fails(self) -> None:
        with self.assertRaisesRegex(ValueError, "3 through 12"):
            phase_partition_counts(2)
        with self.assertRaisesRegex(ValueError, "3 through 12"):
            phase_partition_counts(13)

    def test_unrepaired_area_recovery_preserves_positive_mask(self) -> None:
        repaired = np.array([0.0, 9.0, 5.0])
        scale = np.array([0.0, 0.9, 1.0])
        original = recover_unrepaired(repaired, scale)
        np.testing.assert_allclose(original, [0.0, 10.0, 5.0])
        np.testing.assert_array_equal(original > 0, repaired > 0)

    def test_positive_repaired_area_cannot_have_zero_scale(self) -> None:
        with self.assertRaisesRegex(ValueError, "zero scale"):
            recover_unrepaired(np.array([1.0]), np.array([0.0]))


if __name__ == "__main__":
    unittest.main()
