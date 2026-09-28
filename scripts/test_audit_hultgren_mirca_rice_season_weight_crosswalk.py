#!/usr/bin/env python3
"""Small invariants for the Hultgren/MIRCA rice crosswalk audit."""
from __future__ import annotations

import unittest

import numpy as np

from audit_hultgren_mirca_rice_season_weight_crosswalk import recover_unrepaired


class CrosswalkTests(unittest.TestCase):
    def test_unrepaired_area_recovery(self) -> None:
        repaired = np.array([0.0, 9.0, 5.0])
        scale = np.array([0.0, 0.9, 1.0])
        np.testing.assert_allclose(recover_unrepaired(repaired, scale), [0.0, 10.0, 5.0])

    def test_positive_area_with_zero_scale_fails(self) -> None:
        with self.assertRaisesRegex(ValueError, "zero scale"):
            recover_unrepaired(np.array([1.0]), np.array([0.0]))


if __name__ == "__main__":
    unittest.main()
