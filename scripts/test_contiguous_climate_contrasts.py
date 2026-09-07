"""Synthetic tests only; fixture weather is not empirical evidence."""
import unittest
import numpy as np
import pandas as pd
from summarize_contiguous_climate_contrasts import annual_features


def fixture():
    keys=dict(harvest_year=2032,lat=39.25,lon_360=250.25,crop='mai',irrigation='noirr')
    season=pd.DataFrame([dict(**keys,season_days=100,tmean_c=21,precip_mm=100,
        wet_days_n=10,cdd_max_days=20,rx1day_mm=20,rx5day_mm=40,wet_day_threshold_mm=1.0)])
    stages=pd.DataFrame([dict(**keys,stage_id=i,stage_days=days,stage_fractions='0,0.3,0.7,1',
        tmean_c=t,precip_mm=p) for i,days,t,p in [(1,30,10,20),(2,40,30,50),(3,30,20,30)]])
    return season,stages


class TestAnnualFeatures(unittest.TestCase):
    def test_known_features(self):
        season,stages=fixture()
        result=annual_features(season,stages.iloc[::-1]).iloc[0]
        self.assertAlmostEqual(result.precipitation_concentration_hhi,.38)
        self.assertAlmostEqual(result.precipitation_timing_centroid,.2/6+.5/2+.3*5/6)
        self.assertAlmostEqual(result.tmean_c,21)

    def test_zero_rain_not_invented(self):
        season,stages=fixture()
        season['precip_mm']=0.; stages['precip_mm']=0.
        result=annual_features(season,stages).iloc[0]
        self.assertEqual(result.stage1_precip_share,0)
        self.assertEqual(result.precipitation_concentration_hhi,0)
        # These placeholders are excluded by describe's positive-rain mask.

    def test_identity_and_reconciliation_rejection(self):
        season,stages=fixture()
        for bad in [pd.concat([stages,stages.iloc[:1]]),stages.iloc[:2],
                    stages.assign(tmean_c=stages.tmean_c+1),
                    stages.assign(stage_fractions='0,0.5,1'),
                    stages.assign(precip_mm=stages.precip_mm+1)]:
            with self.subTest(),self.assertRaises(ValueError):
                annual_features(season,bad)

    def test_explicit_temperature_precision_tolerance(self):
        season,stages=fixture()
        adjusted=stages.assign(tmean_c=stages.tmean_c+2e-5)
        result=annual_features(season,adjusted)
        self.assertAlmostEqual(result.attrs['stage_temperature_max_residual_c'],2e-5)
        with self.assertRaises(ValueError):
            annual_features(season,stages.assign(tmean_c=stages.tmean_c+2e-4))


if __name__=='__main__':
    unittest.main()
