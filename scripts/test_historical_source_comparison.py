"""Synthetic distribution arithmetic; not empirical climate evidence."""
import unittest
import pandas as pd
from compare_historical_climate_sources import distribution_difference,model_heat_ranges

class DistributionComparison(unittest.TestCase):
    def setUp(self):
        self.a=pd.DataFrame(dict(crop=['mai']*3,lat=[39.25]*3,lon_360=[.25]*3,harvest_year=[1982,1983,1984],x=[1.,2.,3.]))
    def test_distribution_not_year_pair(self):
        b=self.a.copy();b.harvest_year+=50;b.x+=10
        r=distribution_difference(self.a,b,['x'])
        self.assertTrue(all(v['equal_cell_mean']==10 for v in r['x'].values()))
        b.x=[13.,11.,12.]
        self.assertEqual(r,distribution_difference(self.a,b,['x']))
    def test_range_and_invalid_support(self):
        b=self.a.copy();b.harvest_year+=50;b.x=[0.,2.,4.]
        self.assertEqual(model_heat_ranges(self.a,b,['x'])['outside_any_rows'],2)
        for wrong in (b.assign(lon_360=.75),pd.concat([b,b.iloc[:1]]),b.assign(x=float('nan'))):
            with self.assertRaises(ValueError):distribution_difference(self.a,wrong,['x'])

if __name__=='__main__':unittest.main()
