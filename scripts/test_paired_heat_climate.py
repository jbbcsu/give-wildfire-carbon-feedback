import unittest
import pandas as pd
from compare_paired_heat_climate import compare
from allocate_irrigation_heat_basis import heat_basis_feature_names

class TestPair(unittest.TestCase):
    def setUp(self):
        self.cols=['precip_mm','log1p_precip_mm','cdd_max_days','rx5day_mm']+heat_basis_feature_names([29],3)
        self.a=pd.DataFrame(dict(crop=['mai']*8,lat=[39.25]*8,lon_360=[1.25]*8,
            harvest_year=list(range(2042,2050)),**{c:[1.]*8 for c in self.cols}))
    def test_exact_delta_and_order(self):
        b=self.a.copy();b[self.cols]+=2
        r=compare(self.a,b.iloc[::-1],29)
        self.assertEqual(r['paired_crop_years'],8)
        self.assertTrue(all(v['equal_cell_mean']==2 for v in r['features'].values()))
    def test_incomplete_duplicate_mismatch(self):
        shifted=self.a.copy();shifted.lon_360+=.5
        for b in [self.a.iloc[:-1],pd.concat([self.a,self.a.iloc[:1]]),shifted]:
            with self.assertRaises(ValueError):compare(self.a,b,29)
    def test_nonfinite(self):
        b=self.a.copy();b.loc[0,self.cols[0]]=float('nan')
        with self.assertRaises(ValueError):compare(self.a,b,29)

if __name__=='__main__':unittest.main()
