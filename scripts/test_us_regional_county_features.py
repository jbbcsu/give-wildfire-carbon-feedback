import unittest
import pandas as pd
from shapely.geometry import box
from build_us_regional_county_climate import candidate_cells, county_weights, pilot_parity


class RegionalFeatureTests(unittest.TestCase):
    def test_candidate_pruning_matches_full_scan(self):
        centers = [(lat, lon) for lat in [.25, .75, 1.25] for lon in [.25, .75, 1.25]]
        geometry = box(.1, .1, .8, .9)
        projection = lambda x, y, z=None: (x, y)
        full, a = county_weights(geometry, centers, [True]*9, projection)
        selected = candidate_cells(geometry, centers)
        small, b = county_weights(geometry, [centers[i] for i in selected], [True]*len(selected), projection)
        self.assertEqual(full, [(selected[i], w) for i, w in small])
        self.assertEqual(a, b)

    def test_band_boundary_candidates(self):
        centers = [(41.75, -100.25), (41.25, -100.25), (40.75, -100.25)]
        selected = candidate_cells(box(-100.4, 41.4, -100.1, 41.6), centers)
        self.assertEqual(selected, [0, 1])

    def test_overlap_parity_and_changed_values(self):
        f = pd.DataFrame(dict(county_geoid=['20199'], outcome_crop=['corn_grain'], harvest_year=[1982],
            scenario=['obsclim'], season_start=[pd.Timestamp('1982-05-01')], season_end=[pd.Timestamp('1982-10-01')],
            season_days=[154], zero_precipitation_season=[0.], precip_mm=[400.]))
        self.assertEqual(pilot_parity(f, f)['maximum_absolute_residual_by_feature']['precip_mm'], 0)
        wrong = f.copy()
        wrong['precip_mm'] += 1
        with self.assertRaises(ValueError):
            pilot_parity(wrong, f)


if __name__ == '__main__':
    unittest.main()
