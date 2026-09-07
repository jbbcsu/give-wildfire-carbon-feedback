"""Synthetic QR checks plus source-bound saved-result consistency."""
import json
import numpy as np
from estimate_daily_heat_rainfall_associations import qr_clustered_ols,base


def main():
    rng=np.random.default_rng(31)
    x=rng.normal(size=(150,5));y=rng.normal(size=150);cluster=np.repeat(np.arange(30),5)
    fit=qr_clustered_ols(y,x,cluster)
    b=np.linalg.lstsq(x,y,rcond=None)[0]
    residual=y-np.einsum('ni,i->n',x,b,optimize=False)
    bread=np.linalg.inv(np.einsum('ni,nj->ij',x,x,optimize=False))
    scores=np.stack([np.sum(x[cluster==g]*residual[cluster==g,None],axis=0) for g in range(30)])
    meat=np.einsum('gi,gj->ij',scores,scores,optimize=False)
    covariance=(30/29)*(149/145)*np.einsum('ij,jk,kl->il',bread,meat,bread,optimize=False)
    np.testing.assert_allclose(fit['beta'],b,rtol=1e-10,atol=1e-12)
    np.testing.assert_allclose(fit['covariance_beta_cluster_county'],covariance,rtol=1e-10,atol=1e-12)
    artifact=base.PROJECT/'data/provenance/us_daily_heat_rainfall_associations_20260907.json'
    result=json.loads(artifact.read_text());assert len(result['estimates'])==24
    assert all(r['status']=='estimated' for r in result['estimates'])
    assert result['maximum_baseline_coefficient_or_se_difference']<1e-10
    for crop in ['corn_grain','soybeans']:
        for practice in ['irrigated','non_irrigated']:
            rows=[r['result']['rows'] for r in result['estimates'] if r['crop']==crop and r['practice']==practice]
            assert len(set(rows))==1
    print('QR coefficients/covariance, all24 fits, baseline reproduction and common support passed')


if __name__=='__main__':main()
