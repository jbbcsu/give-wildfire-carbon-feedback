#!/usr/bin/env python3
"""Independent aggregate checks for the U.S. daily-heat assembly."""
import argparse
import glob
import json
from pathlib import Path

import numpy as np
import pandas as pd

from build_us_daily_heat_expansion import (
    DEFAULT_ASSEMBLY, DEFAULT_ASSEMBLY_RECEIPT, DEFAULT_CONTRACT,
    PAIR_KEYS, load_contract, metric_names, validate_heat_partition,
)
from us_national_nclimgrid_common import PROJECT_ROOT, sha256_file


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--out',required=True,type=Path)
    args=parser.parse_args()
    if args.out.exists(): raise ValueError('validation output exists')
    contract=load_contract(DEFAULT_CONTRACT)
    receipt=json.loads(DEFAULT_ASSEMBLY_RECEIPT.read_text())
    if receipt.get('output_sha256')!=sha256_file(DEFAULT_ASSEMBLY):
        raise ValueError('heat assembly hash differs from receipt')
    frame=pd.read_parquet(DEFAULT_ASSEMBLY).sort_values(PAIR_KEYS).reset_index(drop=True)
    source=pd.read_parquet(PROJECT_ROOT/'data/interim/us_county/nass_direct_practice_nclimgrid_1981_2019.parquet')
    pairs=source.drop_duplicates(PAIR_KEYS).sort_values(PAIR_KEYS).reset_index(drop=True)
    validate_heat_partition(frame,pairs,contract['thresholds_c'])
    pilot=json.loads((PROJECT_ROOT/'data/provenance/us_daily_heat_pilot_20260907.json').read_text())
    pilot_index={}
    for record in pilot['records']:
        key=(record['crop'],int(record['threshold_c']))
        comparable={name:value for name,value in record.items() if name!='practice'}
        if key in pilot_index:
            if comparable!=pilot_index[key]: raise ValueError('pilot practices differ in weather')
        else: pilot_index[key]=comparable
    checked=0
    for (crop,threshold),record in pilot_index.items():
        row=frame.loc[(frame.county_geoid.astype(str)=='31039') & (frame.outcome_crop==crop) & (frame.harvest_year==1981)]
        if len(row)!=1: raise ValueError('Cuming pilot key absent from expansion')
        row=row.iloc[0]
        for prefix,pilot_metrics in [('season',record['season']),*((f'stage{s["stage"]}',s) for s in record['stages'])]:
            for original,column in metric_names(threshold,prefix).items():
                if not np.isclose(float(row[column]),float(pilot_metrics[original]),rtol=0,atol=1e-10):
                    raise ValueError(f'Cuming pilot mismatch: {crop}/{threshold}/{prefix}/{original}')
                checked+=1
    resource_paths=sorted(glob.glob(str(PROJECT_ROOT/'outputs/us_county/daily_heat_resources/*_batch*.resource.json')))
    resources=[json.load(open(path)) for path in resource_paths]
    if len(resources)!=149 or any(item['status']!='completed' for item in resources):
        raise ValueError('batch resource receipts are incomplete')
    failed=json.loads((PROJECT_ROOT/'outputs/us_county/daily_heat_resources/1984.resource.json').read_text())
    if failed.get('status')!='memory_budget_exceeded': raise ValueError('resource amendment trigger changed')
    summaries=[]
    for crop,group in frame.groupby('outcome_crop',sort=True):
        row={'crop':crop,'rows':len(group),'counties':group.county_geoid.nunique()}
        for threshold in (29,30):
            for measure in ('tmax_exceedance','tmax_days_gt'):
                suffix='_c_days' if measure=='tmax_exceedance' else ''
                values=group[f'season_{measure}_{threshold}c{suffix}']
                row[f'mean_season_{measure}_{threshold}c']=float(values.mean())
                row[f'median_season_{measure}_{threshold}c']=float(values.median())
        summaries.append(row)
    result={'schema':'us_daily_heat_expansion_validation_v1','status':'validated_complete_historical_heat_input_not_response',
            'assembly_sha256':sha256_file(DEFAULT_ASSEMBLY),'assembly_receipt_sha256':sha256_file(DEFAULT_ASSEMBLY_RECEIPT),
            'rows':len(frame),'counties':frame.county_geoid.nunique(),'years':frame.harvest_year.nunique(),
            'cuming_pilot_values_reconciled':checked,'batch_resource_receipts':len(resources),
            'maximum_sampled_batch_rss_bytes':max(item['sampled_peak_group_rss_bytes'] for item in resources),
            'full_year_1984_failure_preserved':True,'crop_summaries':summaries,
            'coefficients_emitted':False,'causal_response_authorized':False,'damage_or_scc_authorized':False}
    temporary=args.out.with_suffix('.partial'); temporary.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n'); temporary.replace(args.out)
    print(f"validated {len(frame)} heat rows and {checked} pilot values; no response or SCC")

if __name__=='__main__': main()
