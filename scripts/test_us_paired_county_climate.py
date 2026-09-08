import unittest
import numpy as np
import pandas as pd
from shapely.geometry import box
from build_us_paired_county_climate import county_weights, features, validate_dates


class CountyClimateTests(unittest.TestCase):
    def test_cell_first_heat_and_rain(self):
        rain = np.column_stack([np.zeros(100), np.ones(100)*2])
        tmean = np.ones((100, 2))*20
        tmax = np.tile([20., 40.], (100, 1))
        f = features(rain, tmean, tmax, [.5, .5])
        self.assertEqual(f['precip_mm'], 100)
        self.assertEqual(f['cdd_max_days'], 50)
        self.assertEqual(f['zero_precipitation_season'], .5)
        self.assertAlmostEqual(f['stage1_precip_share'], .15)
        self.assertEqual(sum(f[f'stage{s}_tmax_exceedance_30c_c_days'] for s in (1, 2, 3)), 500)
        self.assertEqual(sum(f[f'stage{s}_tmax_days_gt_30c'] for s in (1, 2, 3)), 50)

    def test_invalid_weather(self):
        a = np.ones((30, 2))
        for rain, mean, maximum in [(a, a*40, a*20), (a*-1, a, a), (a*np.nan, a, a)]:
            with self.assertRaises(ValueError):
                features(rain, mean, maximum, [.5, .5])

    def test_dates(self):
        dates = pd.date_range('2000-01-01', '2000-12-31')
        validate_dates(dates, '2000-01-01', '2000-12-31')
        with self.assertRaises(ValueError):
            validate_dates(dates.delete(30), '2000-01-01', '2000-12-31')

    def test_geographic_weight_coverage(self):
        project = lambda x, y, z=None: (x, y)
        w, audit = county_weights(box(0, 0, 1, .5), [(.25, .25), (.25, .75)], [True, True], project)
        self.assertEqual(w, [(0, .5), (1, .5)])
        self.assertEqual(audit['partition_relative_difference'], 0)
        for geometry, valid in [(box(0, 0, 1.2, .5), [True, True]),
                                (box(0, 0, 1, .5), [True, False])]:
            with self.assertRaises(ValueError):
                county_weights(geometry, [(.25, .25), (.25, .75)], valid, project)


if __name__ == '__main__':
    unittest.main()
