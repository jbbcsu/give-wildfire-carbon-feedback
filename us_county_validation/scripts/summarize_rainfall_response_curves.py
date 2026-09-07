"""Conditional supported-range curves from unchanged U.S. association fits."""
import argparse
import copy
import json
from pathlib import Path

import numpy as np
import pandas as pd

from estimate_daily_heat_rainfall_associations import base,qr_clustered_ols,HEAT,HEAT_RECEIPT

REFERENCE=base.PROJECT/'data/provenance/us_daily_heat_rainfall_associations_20260907.json'
PROTOCOL=base.PROJECT/'us_county_validation/US_RAINFALL_CURVE_PROTOCOL_20260907.md'
PERCENTILES=[.05,.10,.25,.50,.75,.90,.95]


def rainfall_curve(beta,covariance,rainfall_mm,reference_mm):
    beta=np.asarray(beta,dtype=float)
    covariance=np.asarray(covariance,dtype=float)
    rain=np.asarray(rainfall_mm,dtype=float)
    if beta.shape!=(2,) or covariance.shape!=(2,2) or rain.ndim!=1 or len(rain)==0:
        raise ValueError('invalid curve dimensions')
    if not all(np.isfinite(a).all() for a in (beta,covariance,rain)) or not np.isfinite(reference_mm):
        raise ValueError('nonfinite input')
    if (rain<0).any() or reference_mm<0:
        raise ValueError('negative rainfall')
    if not np.allclose(covariance,covariance.T,rtol=0,atol=1e-12) or np.linalg.eigvalsh(covariance).min()<-1e-12:
        raise ValueError('invalid covariance')
    p,p0=rain/100.,reference_mm/100.
    gradient=np.column_stack([p-p0,(p-p0)*(p+p0)])
    delta=np.einsum('ni,i->n',gradient,beta,optimize=False)
    variance=np.einsum('ni,ij,nj->n',gradient,covariance,gradient,optimize=False)
    if variance.min()<-1e-10:
        raise ValueError('negative propagated variance')
    se=np.sqrt(np.maximum(variance,0.))
    with np.errstate(over='raise',invalid='raise'):
        percent=100*np.expm1(delta)
        low=100*np.expm1(delta-1.96*se)
        high=100*np.expm1(delta+1.96*se)
    return [dict(rainfall_mm=float(p),log_yield_contrast=float(d),standard_error_log_contrast=float(s),
                 fitted_percent_difference=float(v),pointwise_ci95_percent=[float(l),float(h)])
            for p,d,s,v,l,h in zip(rain,delta,se,percent,low,high)]


def range_support(county_min,county_max,rainfall_mm,reference_mm):
    lo,hi=np.asarray(county_min),np.asarray(county_max)
    if lo.ndim!=1 or hi.shape!=lo.shape or len(lo)==0 or not np.isfinite([lo,hi]).all() or (lo>hi).any():
        raise ValueError('invalid county ranges')
    n=int(((lo<=min(rainfall_mm,reference_mm))&(hi>=max(rainfall_mm,reference_mm))).sum())
    return dict(counties_containing_both_values=n,total_counties=len(lo),fraction_counties=n/len(lo))


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--out',required=True,type=Path)
    args=parser.parse_args()
    if args.out.exists():
        raise ValueError('output exists')
    reference=json.loads(REFERENCE.read_text())
    cfg=base.load_config(base.DEFAULT_CONFIG)
    if reference['config_sha256']!=base.sha256(base.DEFAULT_CONFIG) or reference['base_estimator_sha256']!=base.sha256(Path(base.__file__)):
        raise ValueError('reference config/estimator changed')
    qr_path=Path(__file__).with_name('estimate_daily_heat_rainfall_associations.py')
    if reference['code_sha256']!=base.sha256(qr_path):
        raise ValueError('reference QR implementation changed')
    frame,input_record=base.validate_panel(cfg)
    if input_record!=reference['input'] or base.sha256(HEAT)!=reference['heat_sha256'] or base.sha256(HEAT_RECEIPT)!=reference['heat_receipt_sha256']:
        raise ValueError('source identity differs from reference')
    heat=pd.read_parquet(HEAT)
    keys=['county_geoid','outcome_crop','harvest_year']
    heat_columns=[f'stage{s}_{term}_{t}c'+('_c_days' if term=='tmax_exceedance' else '')
                  for t in (29,30) for s in (1,2,3) for term in ('tmax_exceedance','tmax_days_gt')]
    prior_keys=list(frame[keys+['irrigation_practice']].itertuples(index=False,name=None))
    frame=frame.merge(heat[keys+heat_columns],on=keys,how='left',validate='many_to_one')
    if prior_keys!=list(frame[keys+['irrigation_practice']].itertuples(index=False,name=None)) or not np.isfinite(frame[heat_columns].to_numpy()).all():
        raise ValueError('heat join changes support/order or has missing values')
    output=dict(role='supported_range_historical_association_curves',causal_or_scc_result=False,
                national_estimate=False,pointwise_not_simultaneous_intervals=True,
                reference_path=str(REFERENCE.relative_to(base.PROJECT)),reference_sha256=base.sha256(REFERENCE),
                code_sha256=base.sha256(Path(__file__)),protocol_sha256=base.sha256(PROTOCOL),
                residualization_code_sha256=base.sha256(base.ESTIMATION_PRIMITIVES),
                curves=[],maximum_coefficient_or_se_reproduction_difference=0.)
    captured={}
    def capture(y,x,clusters):
        fit=qr_clustered_ols(y,x,clusters)
        captured.clear(); captured.update(fit)
        return fit
    original=base.clustered_ols
    base.clustered_ols=capture
    try:
        for entry in reference['estimates']:
            if entry['status']!='estimated':
                raise ValueError('reference includes failed fit')
            threshold,crop,practice,form=(entry[k] for k in ('heat_threshold_c','crop','practice','form'))
            current=copy.deepcopy(cfg)
            if threshold is not None:
                current['models']['heat_controls'] += [c for c in heat_columns if f'_{threshold}c' in c]
            fitted=base.estimate(frame,crop,practice,form,current)
            saved=entry['result']
            for field in ('rows','counties','states','year_min','year_max','cluster_count'):
                if fitted[field]!=saved[field]:
                    raise ValueError('reference sample changed')
            if len(fitted['coefficients'])!=len(saved['coefficients']):
                raise ValueError('coefficient count differs')
            for a,b in zip(fitted['coefficients'],saved['coefficients']):
                if a['term']!=b['term']:
                    raise ValueError('coefficient order changed')
                for field in ('estimate','standard_error_cluster_county'):
                    np.testing.assert_allclose(a[field],b[field],rtol=1e-7,atol=1e-10)
                    output['maximum_coefficient_or_se_reproduction_difference']=max(
                        output['maximum_coefficient_or_se_reproduction_difference'],abs(a[field]-b[field]))
            names=[c['term'] for c in fitted['coefficients']]
            indices=[names.index(n) for n in ('precipitation_per_100mm','precipitation_per_100mm_squared')]
            beta=captured['beta'][indices]
            covariance=captured['covariance_beta_cluster_county'][np.ix_(indices,indices)]
            subset=frame.loc[frame.outcome_crop.eq(crop)&frame.irrigation_practice.eq(practice)]
            quantiles=subset.precip_mm.quantile(PERCENTILES)
            q=quantiles.to_numpy()
            grid=np.unique(np.r_[np.linspace(q[0],q[-1],91),q])
            county=subset.groupby('county_geoid').precip_mm.agg(['min','max'])
            points=rainfall_curve(beta,covariance,grid,q[3])
            anchors=rainfall_curve(beta,covariance,q,q[3])
            for point in points+anchors:
                point['marginal_range_support']=range_support(county['min'],county['max'],point['rainfall_mm'],q[3])
            for percentile,point in zip(PERCENTILES,anchors):
                point['rainfall_percentile']=percentile
            output['curves'].append(dict(heat_threshold_c=threshold,crop=crop,practice=practice,form=form,
                sample={k:fitted[k] for k in ('rows','counties','states','year_min','year_max')},
                reference_rainfall_mm=float(q[3]),rainfall_coefficient_order=[names[i] for i in indices],
                rainfall_coefficients=beta.tolist(),rainfall_covariance_county=covariance.tolist(),
                percentile_contrasts=anchors,points=points))
    finally:
        base.clustered_ols=original
    if len(output['curves'])!=24:
        raise ValueError('incomplete original fit matrix')
    temporary=args.out.with_suffix('.partial')
    temporary.write_text(json.dumps(output,indent=2,allow_nan=False)+'\n')
    temporary.replace(args.out)
    print('24 unchanged fits reproduced; supported-range curves and complete rainfall covariance exported')


if __name__=='__main__':
    main()
