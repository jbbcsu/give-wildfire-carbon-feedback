"""Exploratory window sensitivity using retained rainfall inputs only."""
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd
from build_future_weighted_precipitation import contrasts
from summarize_contiguous_climate_contrasts import ROOT,checked,sha256

WINDOWS=[(2032,2039),(2042,2049),(2052,2059)]
METRICS=['precip_mm','log1p_precip_mm','cdd_max_days','rx5day_mm']

def windows(base,candidate):
    result=[]
    for first,last in WINDOWS:
        a=base.loc[base.harvest_year.between(first,last)]
        b=candidate.loc[candidate.harvest_year.between(first,last)]
        r=contrasts(a,b,list(range(first,last+1)))
        result.append(dict(year_start=first,year_end=last,cells=r['cells'],features={k:r['features'][k] for k in METRICS}))
    return result

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    if args.out.exists():raise ValueError('receipt exists')
    path=ROOT/'data/provenance/future_weighted_precipitation_20260907.json';parent=json.loads(path.read_text())
    joint={}
    for model,d in [('GFDL-ESM4','ssp585_heat_cutout_20260908'),('IPSL-CM6A-LR','ipsl_ssp585_heat_cutout_20260908')]:
        p=ROOT/'data/interim'/d/'paired_climate_comparison.json'
        joint[model]=(json.loads(p.read_text()),str(p.relative_to(ROOT)),sha256(p))
    result=dict(role='post_disagreement_exploratory_window_sensitivity',causal_or_scc_result=False,
        parent_sha256=sha256(path),protocol_sha256=sha256(ROOT/'PRECIPITATION_WINDOW_SENSITIVITY_PROTOCOL_20260908.md'),
        code_sha256=sha256(Path(__file__)),comparisons=[],maximum_joint_overlap_difference=0.)
    for crop in ('mai','soy'):
        for model in ('GFDL-ESM4','IPSL-CM6A-LR','MPI-ESM1-2-HR'):
            products=[next(p for p in parent['products'] if (p['crop'],p['esm'],p['scenario'])==(crop,model,s)) for s in ('ssp126','ssp585')]
            tables=[pd.read_parquet(checked(p)) for p in products]
            calculated=windows(*tables)
            references=[r for r in parent['comparisons'] if (r['crop'],r['esm'],r['candidate_scenario'])==(crop,model,'ssp585')]
            if len(references)!=1:raise ValueError('full-period reference missing/duplicate')
            entry=dict(crop=crop,esm=model,input_hashes=[p['sha256'] for p in products],windows=calculated,
                       retained_28year_reference=references[0])
            if model in joint:
                previous,source,source_hash=joint[model];old=next(x for x in previous['comparisons'] if x['crop']==crop)
                mid=calculated[1]
                if mid['cells']!=old['cells']:raise ValueError('joint cells differ')
                differences=[abs(mid['features'][k]['mean']-old['features'][k]['equal_cell_mean']) for k in METRICS]
                if max(differences)>1e-10:raise ValueError('midperiod rainfall overlap differs')
                result['maximum_joint_overlap_difference']=max(result['maximum_joint_overlap_difference'],max(differences))
                entry['joint_reference']=dict(path=source,sha256=source_hash)
            result['comparisons'].append(entry)
    args.out.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print('18window comparisons; maximum joint overlap difference',result['maximum_joint_overlap_difference'])

if __name__=='__main__':main()
