#!/usr/bin/env python3
"""Validate aggregate daily-heat sensitivity arithmetic without refitting."""
import argparse
import json
from pathlib import Path
import numpy as np
from build_us_competing_moisture_inputs import sha256

PROJECT=Path(__file__).resolve().parents[2]
ARTIFACT=PROJECT/'data/provenance/us_daily_heat_moisture_sensitivity_20260907.json'
OLD=PROJECT/'data/provenance/us_moisture_tmax_sensitivity_verified_20260905.json'
HEAT=PROJECT/'data/interim/us_county/nass_direct_practice_daily_heat_1981_2019.parquet'
HEAT_RECEIPT=PROJECT/'data/provenance/us_daily_heat_expansion_20260907.json'
PROTOCOL=PROJECT/'us_county_validation/US_DAILY_HEAT_MOISTURE_SENSITIVITY_PROTOCOL_20260907.md'

def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--out',required=True,type=Path); args=parser.parse_args()
    if args.out.exists(): raise ValueError('validation output exists')
    data=json.loads(ARTIFACT.read_text()); old=json.loads(OLD.read_text())
    if data.get('schema')!='us_daily_heat_moisture_sensitivity_v1': raise ValueError('schema changed')
    if data.get('heat_sha256')!=sha256(HEAT) or data.get('heat_receipt_sha256')!=sha256(HEAT_RECEIPT): raise ValueError('heat binding changed')
    if data.get('protocol_sha256')!=sha256(PROTOCOL): raise ValueError('protocol binding changed')
    for gate in ('coefficients_emitted','row_predictions_emitted','model_promotion_authorized','causal_response_authorized','damage_or_scc_authorized'):
        if data.get(gate) is not False: raise ValueError(f'closed gate changed: {gate}')
    if set(data['results'])!={'baseline','daily_heat_29c','daily_heat_30c'}: raise ValueError('result variants changed')
    baseline={k:v for k,v in data['results']['baseline'].items() if k!='exploratory_daily_heat_sensitivity_not_model_promotion'}
    old_baseline={k:v for k,v in old['results']['baseline'].items() if k!='exploratory_sensitivity_not_new_registered_validation'}
    if baseline!=old_baseline: raise ValueError('registered baseline did not reproduce exactly')
    baseline_index={(r['crop'],r['irrigation_practice'],r['split'],r['split_id'],r['model']):r for r in baseline['metrics']}
    decisions={}; summaries={}
    for label,result in data['results'].items():
        if len(result['metrics'])!=120 or len(result['comparison_summaries'])!=4: raise ValueError(f'{label} support changed')
        index={(r['crop'],r['irrigation_practice'],r['split'],r['split_id'],r['model']):r for r in result['metrics']}
        if set(index)!=set(baseline_index): raise ValueError(f'{label} metric keys changed')
        if label!='baseline':
            for key,row in index.items():
                if row['feature_count_excluding_year_terms']!=baseline_index[key]['feature_count_excluding_year_terms']+6: raise ValueError(f'{label} does not add six controls')
        decisions[label]={}; summaries[label]={}
        for summary in result['comparison_summaries']:
            key=f"{summary['crop']}/{summary['irrigation_practice']}"
            improvements=summary['direct_distribution_rmse_improvement_each_eligible_state']; floors=summary['direct_distribution_required_material_rmse_floor_each_eligible_state']; excess=summary['direct_distribution_rmse_excess_over_material_floor_each_eligible_state']
            if set(improvements)!=set(floors) or set(floors)!=set(excess): raise ValueError('state support differs')
            for state in improvements:
                if not np.isclose(improvements[state]-floors[state],excess[state],rtol=0,atol=1e-14): raise ValueError('materiality arithmetic changed')
            selected=all(value>=0 for value in excess.values())
            if summary['direct_distribution_selected_on_development_leave_state_out'] is not selected: raise ValueError('selection arithmetic changed')
            decisions[label][key]=selected
            summaries[label][key]={'mean_leave_state_out_improvement':summary['direct_distribution_mean_leave_state_out_rmse_improvement'],'terminal_improvement':summary['direct_distribution_terminal_rmse_improvement_not_used_for_selection'],'direct_quantity_minus_pdsi_terminal':summary['direct_quantity_minus_pdsi_season_terminal_rmse']}
    expected={'corn_grain/irrigated':False,'corn_grain/non_irrigated':False,'soybeans/irrigated':False,'soybeans/non_irrigated':False}
    if decisions['daily_heat_29c']!=expected or decisions['daily_heat_30c']!=expected: raise ValueError('daily-heat qualitative result changed')
    result={'schema':'us_daily_heat_moisture_sensitivity_validation_v1','status':'validated_daily_heat_controls_remove_soybean_diagnostic_promotion','artifact_sha256':sha256(ARTIFACT),'baseline_reproduced_exactly':True,'metric_rows_reconciled':360,'selection_decisions':decisions,'comparison_summaries':summaries,'coefficients_checked':False,'refit_performed':False,'causal_response_authorized':False,'damage_or_scc_authorized':False}
    temporary=args.out.with_suffix('.partial'); temporary.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n'); temporary.replace(args.out)
    print('validated 360 metrics and 12 summaries; both daily-heat variants reject all promotions')

if __name__=='__main__': main()
