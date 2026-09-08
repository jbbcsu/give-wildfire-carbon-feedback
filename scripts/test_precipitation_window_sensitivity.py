import unittest
import pandas as pd
from evaluate_precipitation_window_sensitivity import windows
from build_future_weighted_precipitation import FEATURES,ZERO

class TestWindows(unittest.TestCase):
    def setUp(self):
        self.a=pd.DataFrame(dict(harvest_year=list(range(2032,2060)),crop=['mai']*28,
            lat=[39.25]*28,lon_360=[1.25]*28,**{k:[1.]*28 for k in FEATURES},**{ZERO:[0.]*28}))
    def test_fixed_windows(self):
        b=self.a.copy();b.precip_mm+=b.harvest_year-2032
        r=windows(self.a,b)
        self.assertEqual([x['features']['precip_mm']['mean'] for x in r],[3.5,13.5,23.5])
    def test_incomplete_rejected(self):
        with self.assertRaises(ValueError):windows(self.a,self.a.iloc[1:])

if __name__=='__main__':unittest.main()
