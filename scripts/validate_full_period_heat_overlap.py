"""Exact overlap with prior real products; no new outcome model."""
import argparse
import json
from pathlib import Path
import pandas as pd
from allocate_outcome_exposures import KEYS
from summarize_contiguous_climate_contrasts import ROOT,checked,sha256


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True)
    p.add_argument('--model',choices=['gfdl','ipsl'],default='gfdl');args=p.parse_args()
    if args.out.exists():raise ValueError('new receipt required')
    mapping=[('ssp126','mai','two_crop_heat_real_20260908'),('ssp126','soy','soy_heat30_real_20260908'),
        ('ssp585','mai','ssp585_maize_heat29_20260908'),('ssp585','soy','ssp585_soy_heat30_20260908')]
    esm={'gfdl':'GFDL-ESM4','ipsl':'IPSL-CM6A-LR'}[args.model]
    if args.model=='ipsl':mapping=[(s,c,f'ipsl_{s}_{label}_heat{t}_20260908')
        for s in ('ssp126','ssp585') for c,label,t in [('mai','maize',29),('soy','soy',30)]]
    result=dict(role='exact_old_eight_year_overlap_of_full_period_climate_inputs',causal_or_scc_result=False,
        code_sha256=sha256(Path(__file__)),comparisons=[])
    for scenario,crop,old_dir in mapping:
        paths=[ROOT/'data/interim'/d/'receipt.json' for d in (old_dir,f'{args.model}_{scenario}_{crop}_full_heat_20260908')]
        receipts=[json.loads(p.read_text()) for p in paths];tables=[];products=[]
        for r in receipts:
            if r['status'] not in ('joint_climate_inputs_validated','two_crop_joint_climate_inputs_validated'):
                raise ValueError('unvalidated product')
            matches=[v for v in r['products'] if v['crop']==crop]
            if len(matches)!=1:raise ValueError('missing/duplicate crop')
            product=matches[0]
            if (product['esm'],product['member'],product['scenario'])!=(esm,'r1i1p1f1',scenario):
                raise ValueError('source realization differs')
            products.append(product);tables.append(pd.read_parquet(checked(product)))
        if receipts[0]['weight_sha256']!=receipts[1]['weight_sha256']:raise ValueError('weights differ')
        calendar_sets=[{k:v for k,v in r['calendars'].items() if f'_{crop}_' in k} for r in receipts]
        if calendar_sets[0]!=calendar_sets[1] or len(calendar_sets[0])!=2:raise ValueError('calendars differ')
        if receipts[0].get('threshold_c',29)!=receipts[1]['threshold_c']:raise ValueError('threshold differs')
        old,new=tables;new=new.loc[new.harvest_year.between(2042,2049)]
        old=old.set_index(KEYS).sort_index().sort_index(axis=1)
        new=new.set_index(KEYS).sort_index().sort_index(axis=1)
        pd.testing.assert_frame_equal(old,new,check_exact=True)
        result['comparisons'].append(dict(crop=crop,scenario=scenario,rows=len(old),columns=len(old.columns),
            exact_all_columns=True,sources=[dict(path=str(p.relative_to(ROOT)),sha256=sha256(p)) for p in paths],
            products=[dict(path=v['path'],sha256=v['sha256']) for v in products]))
    args.out.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print([(v['crop'],v['scenario'],v['rows'],v['exact_all_columns']) for v in result['comparisons']])


if __name__=='__main__':main()
