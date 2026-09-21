#!/usr/bin/env python3
import sys
from pathlib import Path
from statistics import NormalDist
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_isimip3b_late_drought_pair import normal_ppf, source_record, standardize_vectorized
from spei_distribution import GloParameters, standardize_glo


class TestLateDroughtPair(unittest.TestCase):
    def test_normal_ppf_matches_standard_library(self):
        probabilities = np.r_[np.logspace(-12, -2, 100), np.linspace(.011, .989, 500), 1-np.logspace(-2, -12, 100)]
        reference = np.array([NormalDist().inv_cdf(float(value)) for value in probabilities])
        np.testing.assert_allclose(normal_ppf(probabilities), reference, rtol=0, atol=8e-9)

    def test_vectorized_glo_matches_scalar_reference(self):
        values = np.array([[-50., -5., 0.], [0., 2., 5.], [50., 10., 20.]])
        xi = np.array([0., 1., 2.]); alpha = np.array([10., 3., 4.]); kappa = np.array([0., .2, -.2])
        actual, clips = standardize_vectorized(values, xi, alpha, kappa)
        for column in range(values.shape[1]):
            params = GloParameters(float(xi[column]), float(alpha[column]), float(kappa[column]), 30, 0, 0, 0, 0, 0, 0)
            expected = standardize_glo(values[:, column], params)
            np.testing.assert_allclose(actual[:, column], expected.spei, rtol=0, atol=8e-9)
            np.testing.assert_array_equal(clips[:, column], expected.clip_code)

    def test_rejects_invalid_shapes_and_parameters(self):
        with self.assertRaises(ValueError):
            standardize_vectorized(np.ones((2, 3)), np.ones(2), np.ones(3), np.zeros(3))
        with self.assertRaises(ValueError):
            standardize_vectorized(np.ones((2, 3)), np.ones(3), np.zeros(3), np.zeros(3))

    def test_missing_value_retains_missing_clip_code(self):
        for shape in (0.0, 0.2, -0.2):
            values, clips = standardize_vectorized(np.array([[np.nan], [0.0]]), np.array([0.0]),
                                                   np.array([1.0]), np.array([shape]))
            self.assertTrue(np.isnan(values[0, 0]))
            self.assertEqual(int(clips[0, 0]), -9)

    def test_real_plan_binding_selects_exact_decade(self):
        record = source_record("gfdl-esm4", "ssp126", "pr")
        self.assertEqual(record["bytes"], 2_077_308_090)
        self.assertTrue(record["file_name"].endswith("_2091_2100.nc"))


if __name__ == "__main__":
    unittest.main()
