import unittest
import numpy as np
import pandas as pd
from compare_future_precipitation_ranges import historical_ranges,compare,FEATURES,ZERO


def fixture():
    history=pd.DataFrame([dict(crop='mai',lat=39.25,lon_360=.25,harvest_year=y,
        yield_t_ha=1.,**{f:float(i) for f in FEATURES},**{ZERO:0.})
        for i,y in enumerate([2000,2001,2002])])
    return history


class RangeTests(unittest.TestCase):
    def test_bounds_missing_and_shape(self):
        history=fixture();ranges=historical_ranges(history)
        future=history.iloc[[0]].drop(columns='yield_t_ha').assign(harvest_year=2042)
        future.loc[:,FEATURES]=1.
        got=compare(future,ranges)
        self.assertEqual(got['any_feature_outside_fraction'],0.)
        future['precip_mm']=3.
        got=compare(future,ranges)
        self.assertEqual(got['features']['precip_mm']['above_range_rows'],1)
        self.assertEqual(got['any_feature_outside_fraction'],1.)
        future[ZERO]=.25
        got=compare(future,ranges)
        self.assertEqual(got['features']['stage1_precip_share']['evaluated_rows'],0)
        self.assertIsNone(got['any_feature_outside_fraction'])
        got=compare(future.assign(lat=39.75),ranges)
        self.assertEqual(got['features']['precip_mm']['range_unavailable_rows'],1)

    def test_single_year_and_rejections(self):
        history=fixture()
        ranges=historical_ranges(history.iloc[:1])
        self.assertTrue(ranges['precip_mm__min'].isna().all())
        for bad in (history.assign(harvest_year=2012),pd.concat([history,history.iloc[:1]]),
                    history.assign(yield_t_ha=0.)):
            with self.assertRaises(ValueError):historical_ranges(bad)
        history.loc[2,ZERO]=.25
        ranges=historical_ranges(history)
        self.assertEqual(ranges.iloc[0]['stage1_precip_share__max'],1.)
        self.assertEqual(ranges.iloc[0]['precip_mm__max'],2.)


if __name__=='__main__':unittest.main()
