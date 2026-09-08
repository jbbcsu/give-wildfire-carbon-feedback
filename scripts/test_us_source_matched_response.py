"""Synthetic-only tests; not crop estimates or validation results."""
import unittest
import numpy as np
import pandas as pd
from estimate_us_source_matched_response import align_sources, qr_clustered_ols, WEATHER


class SourceMatchedTests(unittest.TestCase):
    def fixture(self):
        factual = pd.DataFrame(dict(county_geoid=['20005'], outcome_crop=['corn_grain'], harvest_year=[1982],
            scenario=['obsclim'], season_start=['1982-05-01'], season_end=['1982-10-01'], season_days=[154]))
        for c in WEATHER:
            factual[c] = .2 if 'share' in c else 1.
        factual['precip_mm'] = 300.
        frame = pd.concat([factual, factual], ignore_index=True).drop(columns='scenario')
        frame['irrigation_practice'] = ['non_irrigated', 'irrigated']
        frame['yield_bu_acre'] = [100., 200.]
        frame['log_yield'] = np.log(frame.yield_bu_acre)
        frame['precip_mm'] = 400.
        return frame, factual

    def test_replacement_preserves_outcomes_and_keys(self):
        frame, factual = self.fixture()
        frames, mask = align_sources(frame, factual)
        self.assertTrue(mask.all())
        self.assertEqual(set(frames['gswp_obsclim'].precip_mm), {300.})
        self.assertEqual(set(frames['nclimgrid'].precip_mm), {400.})
        np.testing.assert_array_equal(frames['nclimgrid'].yield_bu_acre, frames['gswp_obsclim'].yield_bu_acre)

    def test_counterclim_or_duplicate_rejected(self):
        frame, factual = self.fixture()
        wrong = factual.assign(scenario='counterclim')
        with self.assertRaises(ValueError): align_sources(frame, wrong)
        with self.assertRaises(ValueError): align_sources(frame, pd.concat([factual, factual]))
        with self.assertRaises(ValueError): align_sources(frame.iloc[:1], factual)

    def test_zero_rain_is_retained_only_in_core(self):
        frame, factual = self.fixture()
        factual['precip_mm'] = 0.
        frames, mask = align_sources(frame, factual)
        self.assertFalse(mask.any())
        self.assertEqual(len(frames['gswp_obsclim']), 2)

    def test_known_coefficients_and_rank_rejection(self):
        rng = np.random.default_rng(923)
        x = rng.normal(size=(300, 3))
        q, _ = np.linalg.qr(x, mode='reduced')
        noise = rng.normal(size=300)
        noise -= q@(q.T@noise)
        beta = np.array([.1, -.5, 2.])
        fit = qr_clustered_ols(x@beta+noise, x, np.repeat(np.arange(30), 10))
        np.testing.assert_allclose(fit['beta'], beta, atol=1e-12)
        with self.assertRaises(ValueError):
            qr_clustered_ols(x@beta+noise, np.column_stack([x, x[:, 0]]), np.repeat(np.arange(30), 10))


if __name__ == '__main__':
    unittest.main()
