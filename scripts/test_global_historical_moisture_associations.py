"""Synthetic numerical fixtures only; no generated empirical observations."""
import unittest

import numpy as np

from global_historical_moisture_associations import (
    cluster_fit, contrast_vectors, design, moments, partial_contrast,
)


class AssociationTests(unittest.TestCase):
    def test_cluster_moments_match_direct_ols(self):
        rng = np.random.default_rng(70926)
        x = np.column_stack([np.ones(400), rng.normal(size=(400, 4))])
        x[:, 2] *= 1000
        y = rng.normal(size=400)
        ids = np.repeat(np.arange(20), 20)
        blocks = {g: moments(x[ids == g], y[ids == g]) for g in np.unique(ids)}
        beta, covariance, audit = cluster_fit(blocks)
        expected = np.linalg.lstsq(x, y, rcond=None)[0]
        residual = y - np.einsum('ni,i->n', x, expected, optimize=False)
        score = np.stack([np.sum(x[ids == g] * residual[ids == g, None], axis=0)
                          for g in np.unique(ids)])
        bread = np.linalg.inv(sum(np.outer(row, row) for row in x))
        meat = sum(np.outer(row, row) for row in score)
        reference = (20/19)*(399/395)*np.einsum('ik,kl,lj->ij', bread, meat, bread,
                                               optimize=False)
        np.testing.assert_allclose(beta, expected, rtol=1e-10, atol=1e-12)
        np.testing.assert_allclose(covariance, reference, rtol=1e-9, atol=1e-12)
        self.assertEqual((audit['pairs'], audit['clusters']), (400, 20))

    def test_rank_and_cluster_fail_closed(self):
        x = np.ones((10, 2))
        with self.assertRaises(ValueError):
            cluster_fit({1: moments(x, np.ones(10))})
        with self.assertRaises(ValueError):
            cluster_fit({g: moments(x, np.ones(10)) for g in (1, 2)})

    def test_no_terminal_outcomes(self):
        with self.assertRaises(ValueError):
            design({'years': np.array([2012]), 'differences': {}}, [], 'quadratic_year')

    def test_contrasts_and_year_design(self):
        x, labels = design({'years': np.array([1983, 1984, 2010]),
                            'differences': {'stage2_precip_share': np.ones(3)}},
                           ['stage2_precip_share'], 'year_intercepts')
        self.assertEqual(x.shape, (3, 29))
        self.assertEqual(x[0, 1:28].sum(), 0)
        self.assertEqual(x[1, 1], 1)
        self.assertEqual(x[2, 27], 1)
        vectors = contrast_vectors(['intercept', 'log1p_precip_mm', 'stage2_precip_share'],
                                   'quantity_distribution')
        np.testing.assert_array_equal(vectors['stage3_to_stage2_share_0.1'], [0, 0, .1])
        result = partial_contrast(np.array([0, .2, .3]), np.eye(3)*.01,
                                  vectors['rain_index_plus_0.1'])
        self.assertAlmostEqual(result['log_yield_contrast'], .02)
        self.assertAlmostEqual(result['cluster_standard_error'], .01)


if __name__ == '__main__':
    np.seterr(invalid='raise', divide='raise', over='raise')
    unittest.main()
