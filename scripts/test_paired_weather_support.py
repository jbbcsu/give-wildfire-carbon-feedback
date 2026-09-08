"""Small synthetic checks; no synthetic values enter research products."""
import unittest
import numpy as np
import pandas as pd
from diagnose_paired_weather_support import cell_support, select_observed_keys, summarize_support, verify_prior


class SupportTests(unittest.TestCase):
    def test_joint_gap_inside_marginals(self):
        a = np.column_stack([np.linspace(0, 1, 29)] * 2)
        b = a.copy()
        b[0] = [0, 1]
        r = cell_support(a, b)
        self.assertTrue(r['inside_marginals_beyond_joint'][0])
        self.assertFalse(r['outside_any_marginal'].any())

    def test_exact_match(self):
        a = np.arange(29.)[:, None]
        r = cell_support(a, a)
        self.assertFalse(r['joint_or_constant'].any())
        self.assertTrue((r['nearest'] == 0).all())

    def test_constant_dimension(self):
        a = np.ones((4, 2))
        b = a.copy()
        b[0, 1] = 2
        r = cell_support(a, b)
        self.assertEqual(r['varying_dimensions'], 0)
        self.assertEqual(r['threshold'], 0)
        self.assertTrue(r['constant_violation'][0])
        self.assertTrue(r['outside_any_marginal'][0])
        self.assertFalse(r['beyond_joint_distance'].any())

    def test_invalid_arrays(self):
        for a, b in [(np.ones((2, 2)), np.ones((2, 2))),
                     (np.ones((3, 2)), np.ones((4, 2))),
                     (np.full((4, 2), np.nan), np.ones((4, 2)))]:
            with self.assertRaises(ValueError):
                cell_support(a, b)

    def frame(self):
        return pd.DataFrame(dict(crop=['mai'] * 4, lat=[39.25] * 4, lon_360=[1.] * 4,
                                 harvest_year=[1982, 1983, 1984, 1985], x=[1., 2., 3., 4.]))

    def test_key_and_order_validation(self):
        a = self.frame()
        f, c = select_observed_keys(a, a.iloc[::-1], a)
        pd.testing.assert_frame_equal(f, c)
        self.assertEqual(summarize_support(f, c, ['x'])['rows'], 4)
        for wrong in [a.iloc[:-1], pd.concat([a, a.iloc[:1]])]:
            with self.assertRaises(ValueError):
                select_observed_keys(a, wrong, a)
            with self.assertRaises(ValueError):
                summarize_support(a, wrong, ['x'])

    def test_changed_prior_source(self):
        p = dict(status='paired_climate_diagnostic_validated', comparisons=[
            dict(crop='mai', sources=['a', 'b'], retained_observed_sources=['c'])])
        verify_prior(p, 'mai', ['a', 'b'], ['c'])
        with self.assertRaises(ValueError):
            verify_prior(p, 'mai', ['a', 'changed'], ['c'])


if __name__ == '__main__':
    unittest.main()
