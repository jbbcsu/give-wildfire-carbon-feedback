"""Synthetic paired-input arithmetic only; not empirical crop/climate results."""
import copy
import unittest
import pandas as pd
from compare_factual_counterclim import paired_summary,factual_parity,ZERO,FEATURES,validate_precision_evidence


class FactualPair(unittest.TestCase):
    def setUp(self):
        self.f=pd.DataFrame(dict(crop=['mai']*3,lat=[39.25]*3,lon_360=[.25]*3,
            harvest_year=[1982,1983,1984],x=[1.,2.,3.]))
    def test_pair_alignment_and_sign(self):
        c=self.f.assign(x=[0.,0.,0.]).iloc[::-1]
        r=paired_summary(self.f,c,['x'])
        self.assertEqual(r['paired_difference']['x']['equal_cell_mean'],2.)
        self.assertEqual([a['x'] for a in r['annual_equal_cell_means']],[1.,2.,3.])
        self.assertEqual(paired_summary(c,self.f,['x'])['paired_difference']['x']['equal_cell_mean'],-2.)
    def test_missing_shifted_duplicate_nonfinite_rejected(self):
        for bad in (self.f.iloc[:2],self.f.assign(harvest_year=self.f.harvest_year+1),
                    pd.concat([self.f,self.f.iloc[:1]]),self.f.assign(x=float('nan'))):
            with self.assertRaises(ValueError):paired_summary(self.f,bad,['x'])
    def test_parity_tolerance_and_flags(self):
        a=self.f.assign(**{ZERO:0})
        self.assertEqual(factual_parity(a,a,['x',ZERO])['rows'],3)
        flags=a.assign(**{ZERO:False})
        self.assertEqual(factual_parity(flags,flags,['x',ZERO])['maximum_absolute_residual_by_feature'][ZERO],0.)
        factual_parity(a,a.assign(x=a.x+1e-9),['x',ZERO])
        for bad in (a.assign(x=a.x+.01),a.assign(**{ZERO:1}),a.iloc[:2]):
            with self.assertRaises(ValueError):factual_parity(a,bad,['x',ZERO])
    def test_precision_evidence_is_source_bound_and_complete(self):
        e=dict(crop='mai',new_source={'sha256':'SYNTHETIC_NEW'},old_sources=[{'sha256':'SYNTHETIC_OLD'}],
            compared_features=FEATURES+[ZERO],legacy_reference_parity=dict(atol=1e-8,rtol=1e-10,
                maximum_absolute_residual_by_feature={f:0. for f in FEATURES+[ZERO]}),
            primitive_audits=[dict(regime=r,new_float64_primitives_exact=True,season_rows=19894,stage_rows=59682,
                primitive_precision_counts={c:dict(both=5488,float32_only=0,float64_only=0)
                    for c in ('precip_mm','stage1_precip_mm','stage2_precip_mm','stage3_precip_mm')}) for r in ('noirr','firr')])
        validate_precision_evidence(e,'mai',e['new_source'],e['old_sources'])
        for mode in ('source','coverage','tolerance','residual','raw','count'):
            bad=copy.deepcopy(e)
            if mode=='source':bad['new_source']={'sha256':'DIFFERENT_SYNTHETIC'}
            if mode=='coverage':bad['compared_features'].pop()
            if mode=='tolerance':bad['legacy_reference_parity']['atol']=1.
            if mode=='residual':bad['legacy_reference_parity']['maximum_absolute_residual_by_feature']['precip_mm']=.001
            if mode=='raw':bad['primitive_audits'][0]['new_float64_primitives_exact']=False
            if mode=='count':bad['primitive_audits'][0]['primitive_precision_counts']['precip_mm']['both']=5487
            with self.subTest(mode=mode),self.assertRaises(ValueError):validate_precision_evidence(bad,'mai',e['new_source'],e['old_sources'])


if __name__=='__main__':unittest.main()
