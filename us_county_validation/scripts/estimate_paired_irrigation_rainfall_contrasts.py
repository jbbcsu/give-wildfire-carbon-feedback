"""Paired practice-association differences, not irrigation treatment effects."""
import argparse
import copy
import json
from pathlib import Path
import numpy as np
import pandas as pd

from summarize_rainfall_response_curves import base,qr_clustered_ols,HEAT,HEAT_RECEIPT,REFERENCE,PERCENTILES,rainfall_curve


def paired_difference(frame,crop,form,config):
    keys=['county_geoid','outcome_crop','harvest_year']
    selected=frame.loc[frame.outcome_crop.eq(crop)]
    left=selected.loc[selected.irrigation_practice.eq('non_irrigated')].sort_values(keys).copy()
    right=selected.loc[selected.irrigation_practice.eq('irrigated')].sort_values(keys).copy()
    if left.empty or left.duplicated(keys).any() or right.duplicated(keys).any() or not left[keys].reset_index(drop=True).equals(right[keys].reset_index(drop=True)):
        raise ValueError('outcome pairs not exact')
    a,names=base.raw_design(left,form,config)
    b,other_names=base.raw_design(right,form,config)
    if names!=other_names or not np.array_equal(a,b) or not np.array_equal(left.state.to_numpy(),right.state.to_numpy()):
        raise ValueError('practice designs differ')
    left['log_yield']=right.log_yield.to_numpy()-left.log_yield.to_numpy()
    return left


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--out',required=True,type=Path)
    args=parser.parse_args()
    if args.out.exists():
        raise ValueError('output exists')
    reference=json.loads(REFERENCE.read_text())
    cfg=base.load_config(base.DEFAULT_CONFIG)
    frame,source=base.validate_panel(cfg)
    for path,digest in [(base.DEFAULT_CONFIG,reference['config_sha256']),
                        (Path(base.__file__),reference['base_estimator_sha256']),
                        (Path(__file__).with_name('estimate_daily_heat_rainfall_associations.py'),reference['code_sha256']),
                        (HEAT,reference['heat_sha256']),(HEAT_RECEIPT,reference['heat_receipt_sha256'])]:
        if base.sha256(path)!=digest:
            raise ValueError('source/implementation identity changed')
    if source!=reference['input']:
        raise ValueError('source sample differs')
    heat=pd.read_parquet(HEAT)
    keys=['county_geoid','outcome_crop','harvest_year']
    columns=[f'stage{s}_{term}_{t}c'+('_c_days' if term=='tmax_exceedance' else '')
             for t in (29,30) for s in (1,2,3) for term in ('tmax_exceedance','tmax_days_gt')]
    order=list(frame[keys+['irrigation_practice']].itertuples(index=False,name=None))
    frame=frame.merge(heat[keys+columns],on=keys,how='left',validate='many_to_one')
    if order!=list(frame[keys+['irrigation_practice']].itertuples(index=False,name=None)) or not np.isfinite(frame[columns].to_numpy()).all():
        raise ValueError('heat join invalid')
    protocol=base.PROJECT/'us_county_validation/US_PAIRED_IRRIGATION_CONTRAST_PROTOCOL_20260907.md'
    result=dict(role='paired_historical_practice_association_difference',causal_or_scc_result=False,
                irrigation_treatment_effect=False,adaptation_value_estimate=False,
                source_reference_sha256=base.sha256(REFERENCE),protocol_sha256=base.sha256(protocol),
                code_sha256=base.sha256(Path(__file__)),
                curve_helper_sha256=base.sha256(Path(__file__).with_name('summarize_rainfall_response_curves.py')),
                residualization_code_sha256=base.sha256(base.ESTIMATION_PRIMITIVES),
                maximum_paired_coefficient_identity_difference=0.,estimates=[])
    captured={}
    def capture(y,x,clusters):
        fit=qr_clustered_ols(y,x,clusters)
        captured.clear();captured.update(fit)
        return fit
    original=base.clustered_ols;base.clustered_ols=capture
    try:
        for threshold in (None,29,30):
            current=copy.deepcopy(cfg)
            if threshold is not None:
                current['models']['heat_controls'] += [c for c in columns if f'_{threshold}c' in c]
            for crop in cfg['input']['crops']:
                for form in cfg['models']['forms']:
                    paired=paired_difference(frame,crop,form,current)
                    fit=base.estimate(paired,crop,'non_irrigated',form,current)
                    old={practice:next(r['result'] for r in reference['estimates'] if r['heat_threshold_c']==threshold
                            and r['crop']==crop and r['practice']==practice and r['form']==form and r['status']=='estimated')
                         for practice in ('irrigated','non_irrigated')}
                    for field in ('rows','counties','states','year_min','year_max'):
                        if not fit[field]==old['irrigated'][field]==old['non_irrigated'][field]:
                            raise ValueError('paired sample changed')
                    for index,coefficient in enumerate(fit['coefficients']):
                        a,b=(old[p]['coefficients'][index] for p in ('irrigated','non_irrigated'))
                        if coefficient['term']!=a['term'] or a['term']!=b['term']:
                            raise ValueError('coefficient identity differs')
                        difference=a['estimate']-b['estimate']
                        np.testing.assert_allclose(coefficient['estimate'],difference,rtol=1e-7,atol=1e-10)
                        result['maximum_paired_coefficient_identity_difference']=max(
                            result['maximum_paired_coefficient_identity_difference'],abs(coefficient['estimate']-difference))
                    names=[c['term'] for c in fit['coefficients']]
                    indices=[names.index(n) for n in ('precipitation_per_100mm','precipitation_per_100mm_squared')]
                    beta=captured['beta'][indices]
                    covariance=captured['covariance_beta_cluster_county'][np.ix_(indices,indices)]
                    quantiles=paired.precip_mm.quantile(PERCENTILES).to_numpy()
                    contrast=rainfall_curve(beta,covariance,quantiles,quantiles[3])
                    for percentile,row in zip(PERCENTILES,contrast):
                        row['rainfall_percentile']=percentile
                        row['log_yield_ratio_contrast']=row.pop('log_yield_contrast')
                        row['percent_change_in_fitted_yield_ratio']=row.pop('fitted_percent_difference')
                        row['pointwise_ci95_percent_change_in_ratio']=row.pop('pointwise_ci95_percent')
                    increments=[]
                    for p in (.25,.50,.75):
                        start=float(paired.precip_mm.quantile(p))
                        row=rainfall_curve(beta,covariance,[start+100],start)[0]
                        increments.append(dict(reference_percentile=p,reference_rainfall_mm=start,increment_mm=100.,
                            within_central_rainfall_range=bool(start>=quantiles[0] and start+100<=quantiles[-1]),
                            log_yield_ratio_contrast=row['log_yield_contrast'],standard_error_log_contrast=row['standard_error_log_contrast'],
                            percent_change_in_fitted_yield_ratio=row['fitted_percent_difference'],
                            pointwise_ci95_percent_change_in_ratio=row['pointwise_ci95_percent']))
                    result['estimates'].append(dict(crop=crop,form=form,heat_threshold_c=threshold,
                        sample={k:fit[k] for k in ('rows','counties','states','year_min','year_max')},
                        coefficients=fit['coefficients'],rainfall_covariance_county=covariance.tolist(),
                        median_rainfall_mm=float(quantiles[3]),percentile_contrasts=contrast,increment_contrasts=increments))
    finally:
        base.clustered_ols=original
    if len(result['estimates'])!=12:
        raise ValueError('incomplete paired fit matrix')
    temporary=args.out.with_suffix('.partial')
    temporary.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    temporary.replace(args.out)
    print('12 paired practice-difference fits complete; all coefficient identities verified')


if __name__=='__main__':
    main()
