#!/usr/bin/env python3
"""Exploratory competing-moisture prediction with daily heat controls."""
import argparse
import copy
import json
from pathlib import Path

import numpy as np
import pandas as pd

from build_us_competing_moisture_inputs import KEYS, PAIR_KEYS, DEFAULT_PROTOCOL, load_protocol, sha256
from evaluate_us_competing_moisture import evaluate_frames

PROJECT=Path(__file__).resolve().parents[2]
HEAT=PROJECT/'data/interim/us_county/nass_direct_practice_daily_heat_1981_2019.parquet'
HEAT_RECEIPT=PROJECT/'data/provenance/us_daily_heat_expansion_20260907.json'
PROTOCOL=PROJECT/'us_county_validation/US_DAILY_HEAT_MOISTURE_SENSITIVITY_PROTOCOL_20260907.md'


def add_heat(common,levels,threshold):
    if levels.duplicated(PAIR_KEYS).any(): raise ValueError('duplicate heat level keys')
    names=[]
    for stage in (1,2,3):
        names += [f'stage{stage}_tmax_exceedance_{threshold}c_c_days',f'stage{stage}_tmax_days_gt_{threshold}c']
    selected=levels[PAIR_KEYS+names].copy()
    if not np.isfinite(selected[names].to_numpy(float)).all(): raise ValueError('nonfinite heat input')
    joined=common.merge(selected,on=PAIR_KEYS,how='left',validate='many_to_one')
    previous=selected.rename(columns={'harvest_year':'difference_previous_harvest_year',**{n:n+'_previous' for n in names}})
    joined=joined.merge(previous,on=['county_geoid','outcome_crop','difference_previous_harvest_year'],how='left',validate='many_to_one')
    if list(joined[KEYS].itertuples(index=False,name=None))!=list(common[KEYS].itertuples(index=False,name=None)):
        raise ValueError('heat endpoint join changed support/order')
    result=common.copy()
    for name in names:
        values=joined[name].to_numpy()-joined[name+'_previous'].to_numpy()
        if not np.isfinite(values).all(): raise ValueError('missing heat endpoint')
        result['d_'+name]=values
    return result,names


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--out',required=True,type=Path); args=parser.parse_args()
    if args.out.exists(): raise ValueError('output exists')
    heat_receipt=json.loads(HEAT_RECEIPT.read_text())
    if heat_receipt.get('output_sha256')!=sha256(HEAT): raise ValueError('heat input differs from receipt')
    independent=PROJECT/'data/provenance/us_competing_moisture_independent_audit_20260826.json'
    pins=json.loads(independent.read_text())['hash_audit']['sha256']
    folder=PROJECT/'data/interim/us_county/competing_moisture_predictive_v1'
    paths={'common':folder/'common_outcomes_controls_folds.parquet','direct_input':folder/'direct_weather.parquet',
           'pdsi_input':folder/'pdsi.parquet','protocol':DEFAULT_PROTOCOL}
    if any(sha256(path)!=pins[name] for name,path in paths.items()): raise ValueError('retained predictive input differs from independent audit')
    common=pd.read_parquet(paths['common']).sort_values(KEYS).reset_index(drop=True)
    direct=pd.read_parquet(paths['direct_input']).sort_values(KEYS).reset_index(drop=True)
    pdsi=pd.read_parquet(paths['pdsi_input']).sort_values(KEYS).reset_index(drop=True)
    heat=pd.read_parquet(HEAT).sort_values(PAIR_KEYS).reset_index(drop=True)
    protocol=load_protocol(DEFAULT_PROTOCOL)
    results={}
    results['baseline']=evaluate_frames(common,direct,pdsi,protocol)
    added={}
    for threshold in (29,30):
        modified,names=add_heat(common,heat,threshold); added[str(threshold)]=names
        cfg=copy.deepcopy(protocol); cfg['features']['common_temperature_controls'] += names
        results[f'daily_heat_{threshold}c']=evaluate_frames(modified,direct,pdsi,cfg)
    for result in results.values(): result['exploratory_daily_heat_sensitivity_not_model_promotion']=True
    output={'schema':'us_daily_heat_moisture_sensitivity_v1','role':'aggregate_exploratory_prediction_not_causal_response',
            'input_sha256':{name:sha256(path) for name,path in paths.items()},'heat_sha256':sha256(HEAT),
            'heat_receipt_sha256':sha256(HEAT_RECEIPT),'protocol_sha256':sha256(PROTOCOL),
            'evaluator_sha256':sha256(Path(__file__).with_name('evaluate_us_competing_moisture.py')),
            'added_controls':added,'results':results,'coefficients_emitted':False,'row_predictions_emitted':False,
            'model_promotion_authorized':False,'causal_response_authorized':False,'damage_or_scc_authorized':False}
    temporary=args.out.with_suffix('.partial'); temporary.write_text(json.dumps(output,indent=2,allow_nan=False)+'\n'); temporary.replace(args.out)
    print(f"completed {sum(len(value['metrics']) for value in results.values())} aggregate metrics; no promotion, response, damage, or SCC")

if __name__=='__main__': main()
