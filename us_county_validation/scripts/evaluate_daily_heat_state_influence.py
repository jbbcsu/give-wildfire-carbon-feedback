"""Geographic coefficient influence following daily-heat sensitivity."""
import argparse
import copy
import json
from pathlib import Path
import numpy as np
import pandas as pd
from estimate_daily_heat_rainfall_associations import base,qr_clustered_ols,HEAT,HEAT_RECEIPT
from run_state_influence import point_contrasts


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',required=True,type=Path);args=parser.parse_args()
    if args.out.exists():raise ValueError('output exists')
    config=base.load_config(base.DEFAULT_CONFIG);frame,source=base.validate_panel(config)
    if json.loads(HEAT_RECEIPT.read_text())['output_sha256']!=base.sha256(HEAT):raise ValueError('heat hash mismatch')
    heat=pd.read_parquet(HEAT);keys=['county_geoid','outcome_crop','harvest_year']
    names=[f'stage{s}_{term}_{t}c'+('_c_days' if term=='tmax_exceedance' else '')
           for t in [29,30] for s in [1,2,3] for term in ['tmax_exceedance','tmax_days_gt']]
    frame=frame.merge(heat[keys+names],on=keys,how='left',validate='many_to_one')
    if not np.isfinite(frame[names].to_numpy()).all():raise ValueError('missing heat')
    base.clustered_ols=qr_clustered_ols;records=[]
    for threshold in [29,30]:
        cfg=copy.deepcopy(config);cfg['models']['heat_controls'] += [c for c in names if f'_{threshold}c' in c]
        for crop in ['corn_grain','soybeans']:
            subset=frame.loc[frame.outcome_crop.eq(crop)&frame.irrigation_practice.eq('non_irrigated')]
            reference=float(subset.precip_mm.median());form=cfg['models']['primary_form_by_crop'][crop]
            for state in [None,*sorted(subset.state.unique())]:
                data=subset if state is None else subset.loc[subset.state.ne(state)]
                entry=dict(threshold_c=threshold,crop=crop,form=form,omitted_state=state,
                           reference_precipitation_mm=reference,rows=len(data))
                try:
                    fit=base.estimate(data,crop,'non_irrigated',form,cfg)
                    entry.update(status='estimated',contrasts=point_contrasts(fit,reference))
                except ValueError as error:entry.update(status='failed',reason=str(error))
                records.append(entry)
    result=dict(role='exploratory_geographic_coefficient_influence',causal_or_scc_result=False,input=source,
        heat_sha256=base.sha256(HEAT),heat_receipt_sha256=base.sha256(HEAT_RECEIPT),
        code_sha256=base.sha256(Path(__file__)),
        qr_estimator_sha256=base.sha256(Path(__file__).with_name('estimate_daily_heat_rainfall_associations.py')),
        protocol_sha256=base.sha256(base.PROJECT/'us_county_validation/US_DAILY_HEAT_STATE_PROTOCOL_20260907.md'),estimates=records)
    temporary=args.out.with_suffix('.partial');temporary.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');temporary.replace(args.out)
    print(f'{len(records)} geographic fits; {sum(r["status"]=="failed" for r in records)} failures')


if __name__=='__main__':main()
