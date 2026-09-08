import unittest
import pandas as pd
from compare_future_heat_ranges import diagnose, HEAT

class TestRanges(unittest.TestCase):
    def setUp(self):
        self.h=pd.DataFrame(dict(crop=['mai']*2,lat=[39.25]*2,lon_360=[1.25]*2,harvest_year=[1982,1983],yield_t_ha=[1.,2.],**{c:[0.,10.] for c in HEAT}))
        self.f=self.h.drop(columns='yield_t_ha').copy();self.f.harvest_year=[2042,2043]
    def test_boundaries_and_outside(self):
        self.assertEqual(diagnose(self.h,self.f)['any_heat_outside_rows'],0)
        self.f.loc[1,HEAT[0]]=11.
        self.assertEqual(diagnose(self.h,self.f)['any_heat_outside_rows'],1)
    def test_missing_range(self):
        self.f.loc[1,'lon_360']=2.25
        r=diagnose(self.h,self.f);self.assertEqual(r['common_evaluable_rows'],1)
        self.assertIsNone(diagnose(self.h.iloc[:1],self.f)['any_heat_outside_fraction'])
    def test_duplicate_and_nonfinite(self):
        with self.assertRaises(ValueError):diagnose(pd.concat([self.h,self.h]),self.f)
        self.h.loc[0,HEAT[0]]=float('nan')
        with self.assertRaises(ValueError):diagnose(self.h,self.f)

if __name__=='__main__':unittest.main()
