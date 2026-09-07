"""Synthetic paired-covariance and identity tests only."""
import unittest
import numpy as np
import pandas as pd
from estimate_paired_irrigation_rainfall_contrasts import paired_difference,qr_clustered_ols


class TestPaired(unittest.TestCase):
    def test_slope_linearity_and_direct_covariance(self):
        rng=np.random.default_rng(822)
        x=rng.normal(size=(120,3));cluster=np.repeat(np.arange(24),5)
        shared=rng.normal(size=120)
        a=shared+rng.normal(size=120);b=.5*shared+rng.normal(size=120)
        fit=qr_clustered_ols(b-a,x,cluster)
        np.testing.assert_allclose(fit['beta'],qr_clustered_ols(b,x,cluster)['beta']-qr_clustered_ols(a,x,cluster)['beta'],atol=1e-12)
        beta=np.linalg.lstsq(x,b-a,rcond=None)[0]
        residual=(b-a)-x@beta
        bread=np.linalg.inv(x.T@x)
        scores=np.array([(x[cluster==g]*residual[cluster==g,None]).sum(axis=0) for g in range(24)])
        expected=(24/23)*(119/117)*bread@(scores.T@scores)@bread
        np.testing.assert_allclose(fit['covariance_beta_cluster_county'],expected,rtol=1e-10,atol=1e-12)

    def test_pair_identity_and_rejections(self):
        config={'models':{'heat_controls':['t'],'quantity_scale_mm':100.,'quantity_feature':'precip_mm','timing_features':[]}}
        rows=[]
        for practice in ('non_irrigated','irrigated'):
            for year in (2000,2001):
                rows.append(dict(county_geoid='01001',state='01',outcome_crop='corn',harvest_year=year,
                    irrigation_practice=practice,log_yield=1.+int(practice=='irrigated'),t=20.,precip_mm=300.))
        frame=pd.DataFrame(rows)
        result=paired_difference(frame.iloc[::-1],'corn','quantity',config)
        np.testing.assert_array_equal(result.log_yield,[1.,1.])
        with self.assertRaises(ValueError): paired_difference(frame.iloc[:-1],'corn','quantity',config)
        frame.loc[3,'precip_mm']=301.
        with self.assertRaises(ValueError): paired_difference(frame,'corn','quantity',config)


if __name__=='__main__':
    unittest.main()
