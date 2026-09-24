#!/usr/bin/env python3

from __future__ import annotations

import unittest

import numpy as np


class IncidenceArithmeticTests(unittest.TestCase):
    def test_region_and_global_mean_commute(self) -> None:
        country_by_model = np.array([[1.0, -2.0, 3.0], [2.0, -1.0, 5.0]])
        direct = country_by_model.sum(axis=1).mean()
        country_then_models = country_by_model.mean(axis=0).sum()
        self.assertAlmostEqual(direct, country_then_models)


if __name__ == "__main__":
    unittest.main()
