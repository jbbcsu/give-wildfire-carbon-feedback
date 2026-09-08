"""Synthetic exact-join contract tests; no network or empirical fitting."""
import unittest
import pandas as pd
from extend_heat_cutout_two_crops import exact_join, FEATURES, HEAT, validate_realization

class TestJoin(unittest.TestCase):
    def test_realization_no_relabeling(self):
        identity=dict(climate_scenario='ssp585',climate_forcing='ipsl-cm6a-lr',ensemble_member='r1i1p1f1',
            climate_variable='tasmax',bias_adjustment='w5e5',simulation_round='ISIMIP3b',time_step='daily',region='global')
        config=dict(specifiers=identity)
        validate_realization(config,'IPSL-CM6A-LR','r1i1p1f1','ssp585')
        for esm,member,scenario in [('GFDL-ESM4','r1i1p1f1','ssp585'),('IPSL-CM6A-LR','r2i1p1f1','ssp585'),('IPSL-CM6A-LR','r1i1p1f1','ssp126')]:
            with self.assertRaises(ValueError):validate_realization(config,esm,member,scenario)
        for field,value in [('climate_variable','tas'),('bias_adjustment','other'),('time_step','monthly')]:
            with self.assertRaises(ValueError):validate_realization(dict(specifiers=identity|{field:value}),'IPSL-CM6A-LR','r1i1p1f1','ssp585')
    def setUp(self):
        self.rain=pd.DataFrame(dict(harvest_year=[2042,2043],lat=[39.25]*2,lon_360=[100.25]*2,
            crop=['mai']*2,precip_mm=[100.,200.],**{f'stage{i}_tmean_c':[20.,21.] for i in (1,2,3)}))
        self.heat=self.rain.drop(columns='precip_mm').assign(**{k:[1.,2.] for k in HEAT})
    def test_exact_reordered(self):
        out=exact_join(self.rain,self.heat.iloc[::-1])
        self.assertEqual(len(out),2);self.assertEqual(out.precip_mm.tolist(),[100.,200.])
        self.assertTrue(set(FEATURES).issubset(out))
    def test_missing_duplicate_keys(self):
        for heat in (self.heat.iloc[:1],pd.concat([self.heat,self.heat.iloc[:1]])):
            with self.assertRaises(ValueError):exact_join(self.rain,heat)
    def test_nonfinite_and_temperature(self):
        for col,value in ((HEAT[0],float('nan')),('stage1_tmean_c',20.0001)):
            heat=self.heat.copy();heat.loc[0,col]=value
            with self.assertRaises(ValueError):exact_join(self.rain,heat)
    def test_30c_not_29c(self):
        heat=self.heat.rename(columns={c:c.replace('29c','30c') for c in HEAT})
        out=exact_join(self.rain,heat,30.)
        self.assertIn('stage1_tmax_30c_degree_days',out)
        self.assertNotIn('stage1_tmax_29c_degree_days',out)
        with self.assertRaises(KeyError):exact_join(self.rain,self.heat,30.)

if __name__=='__main__':unittest.main()
