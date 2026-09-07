"""Daily heat/rainfall fixed-effect historical associations; no causal/SCC use."""
import argparse
import copy
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import estimate_us_direct_practice_precipitation_association as base
from evaluate_daily_heat_moisture_sensitivity import HEAT, HEAT_RECEIPT


def qr_clustered_ols(y, x, cluster):
    scale=x.std(axis=0)
    if not np.isfinite(scale).all() or np.any(scale<=0):
        raise ValueError('invalid within scales')
    z=x/scale
    q,r=np.linalg.qr(z,mode='reduced')
    condition=float(np.linalg.cond(r))
    if not np.isfinite(condition) or condition>1e8:
        raise ValueError('rank/condition gate failed')
    b=np.linalg.solve(r,np.einsum('ni,n->i',q,y,optimize=False))
    residual=y-np.einsum('ni,i->n',z,b,optimize=False)
    codes,labels=pd.factorize(cluster,sort=True)
    g=len(labels);n,k=x.shape
    if g<=1 or n<=k:
        raise ValueError('insufficient cluster/design support')
    scores=np.stack([np.einsum('ni,n->i',z[codes==i],residual[codes==i],optimize=False)
                     for i in range(g)])
    influence=np.linalg.solve(r,np.linalg.solve(r.T,scores.T)).T/scale
    covariance=(g/(g-1))*((n-1)/(n-k))*np.einsum('gi,gj->ij',influence,influence,optimize=False)
    if not np.isfinite(covariance).all() or np.any(np.diag(covariance)<=0):
        raise ValueError('invalid cluster covariance')
    beta=b/scale;se=np.sqrt(np.diag(covariance))
    return dict(beta=beta,standard_error_cluster_county=se,
        covariance_beta_cluster_county=covariance,
        normal_approx_p_value=np.array([math.erfc(abs(float(v))/math.sqrt(2)) for v in beta/se]),
        residual_rmse=float(np.sqrt(np.mean(residual**2))),
        within_r_squared=float(1-np.sum(residual**2)/np.sum(y**2)),clusters=g)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',required=True,type=Path)
    args=parser.parse_args()
    if args.out.exists():raise ValueError('output exists')
    cfg=base.load_config(base.DEFAULT_CONFIG);frame,source=base.validate_panel(cfg)
    receipt=json.loads(HEAT_RECEIPT.read_text())
    if receipt['output_sha256']!=base.sha256(HEAT):raise ValueError('heat hash mismatch')
    heat=pd.read_parquet(HEAT)
    keys=['county_geoid','outcome_crop','harvest_year']
    columns=[f'stage{s}_{term}_{t}c'+('_c_days' if term=='tmax_exceedance' else '')
             for t in [29,30] for s in [1,2,3] for term in ['tmax_exceedance','tmax_days_gt']]
    original_keys=list(frame[keys+['irrigation_practice']].itertuples(index=False,name=None))
    frame=frame.merge(heat[keys+columns],on=keys,how='left',validate='many_to_one')
    if list(frame[keys+['irrigation_practice']].itertuples(index=False,name=None))!=original_keys:
        raise ValueError('join changed support/order')
    if not np.isfinite(frame[columns].to_numpy()).all():raise ValueError('missing heat controls')
    baseline_path=base.PROJECT/'data/provenance/us_reporting_heat_sensitivity_20260904.json'
    reference=json.loads(baseline_path.read_text())
    base.clustered_ols=qr_clustered_ols
    results=[];maximum_baseline_difference=0.
    for threshold in [None,29,30]:
        current=copy.deepcopy(cfg)
        if threshold is not None:
            current['models']['heat_controls'] += [c for c in columns if f'_{threshold}c' in c]
        for crop in cfg['input']['crops']:
            for practice in cfg['input']['practices']:
                for form in cfg['models']['forms']:
                    entry=dict(heat_threshold_c=threshold,crop=crop,practice=practice,form=form)
                    try:
                        fitted=base.estimate(frame,crop,practice,form,current)
                        fitted['is_registered_primary_form_for_crop']=False
                        if threshold is None:
                            old=next(e['result'] for e in reference['estimates'] if e['variant']=='baseline'
                                     and e['crop']==crop and e['practice']==practice and e['form']==form)
                            for a,b in zip(fitted['coefficients'],old['coefficients']):
                                if a['term']!=b['term']:raise ValueError('baseline term mismatch')
                                for field in ['estimate','standard_error_cluster_county']:
                                    np.testing.assert_allclose(a[field],b[field],rtol=1e-7,atol=1e-10)
                                    maximum_baseline_difference=max(maximum_baseline_difference,abs(a[field]-b[field]))
                        entry.update(status='estimated',result=fitted)
                    except ValueError as error:
                        entry.update(status='failed',reason=str(error))
                    results.append(entry)
    output=dict(schema='us_daily_heat_rainfall_associations_v1',role='exploratory_historical_associations',
        causal_or_scc_result=False,input=source,heat_sha256=base.sha256(HEAT),
        heat_receipt_sha256=base.sha256(HEAT_RECEIPT),config_sha256=base.sha256(base.DEFAULT_CONFIG),
        code_sha256=base.sha256(Path(__file__)),base_estimator_sha256=base.sha256(Path(base.__file__)),
        baseline_reference_sha256=base.sha256(baseline_path),
        protocol_sha256=base.sha256(base.PROJECT/'us_county_validation/US_DAILY_HEAT_ASSOCIATION_PROTOCOL_20260907.md'),
        maximum_baseline_coefficient_or_se_difference=maximum_baseline_difference,estimates=results)
    temporary=args.out.with_suffix('.partial');temporary.write_text(json.dumps(output,indent=2,allow_nan=False)+'\n');temporary.replace(args.out)
    print(f'{len(results)} fits; {sum(r["status"]=="failed" for r in results)} failed')


if __name__=='__main__':main()
