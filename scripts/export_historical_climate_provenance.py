"""Aggregate historical-climate source/validation evidence; no raw rows."""
import argparse
import json
from pathlib import Path
import shutil
from summarize_contiguous_climate_contrasts import ROOT,sha256
from build_historical_climate_benchmark import MODELS


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--model',choices=sorted(MODELS),default='gfdl');args=parser.parse_args()
    prefix='' if args.model=='gfdl' else args.model+'_'
    out=ROOT/f'data/provenance/{prefix}historical_climate_benchmark_20260908.json'
    if out.exists():raise ValueError('new provenance path required')
    files=[];jobs=[];directories=[]
    for var in ('pr','tas','tasmax'):
        for first in (1981,1991,2001):
            stem=f'{args.model}_historical_{var}_{first}_20260908';directory='data/interim/'+stem
            directories.append(directory);files.append(directory+'/receipt.json')
            jobs += [stem+'_request',stem+'_acquisition']
    for crop in ('mai','soy'):
        stem=f'{args.model}_historical_{crop}_joint_20260908';directory='data/interim/'+stem
        directories.append(directory);files.append(directory+'/receipt.json');jobs.append(stem)
    files.append(f'data/interim/{args.model}_historical_soy_joint_20260908/source_comparison.json')
    jobs += (['historical_historical_climate_cutouts_20260908','historical_heat_cutout_dates_20260908',
        'historical_authorized_heat_subset_pilot_20260908','historical_climate_inputs_20260908',
        'historical_benchmark_contract_20260908','historical_source_comparison_tests_20260908',
        'gfdl_historical_source_comparison_20260908'] if args.model=='gfdl' else [
        'ipsl_historical_benchmark_contract_20260908','ipsl_historical_source_comparison_20260908',
        'ipsl_historical_climate_cutouts_20260908','ipsl_historical_source_comparison_real_20260908'])
    resources=['outputs/'+j+'_resource.json' for j in jobs];receipts=[]
    for name in files+resources:
        path=ROOT/name;r=json.loads(path.read_text())
        if name in resources and r.get('status')!='completed':raise ValueError('bounded job did not complete')
        if name.endswith('/receipt.json'):
            for key in ('artifacts','artifact_hashes'):
                for artifact,digest in r.get(key,{}).items():
                    if sha256(path.parent/artifact)!=digest:raise ValueError('local climate artifact changed')
            for p in r.get('products',[]):
                if sha256(ROOT/p['path'])!=p['sha256']:raise ValueError('joint product changed')
        receipts.append(dict(path=name,sha256=sha256(path),content=r))
    retained={d:sum(p.stat().st_size for p in (ROOT/d).rglob('*') if p.is_file()) for d in directories}
    result=dict(role=MODELS[args.model]['esm']+'_historical_distribution_source_benchmark',causal_or_scc_result=False,
        observed_weather_years_paired=False,receipts=receipts,
        logs=[dict(path='outputs/'+j+'.log',sha256=sha256(ROOT/'outputs'/f'{j}.log')) for j in jobs],
        retained_new_input_output_bytes=retained,total_retained_bytes=sum(retained.values()),
        free_bytes_at_export=shutil.disk_usage(ROOT).free,
        previous_full_period_retained_bytes=json.loads((ROOT/'data/provenance/full_period_heat_20260908.json').read_text())['total_retained_bytes'],
        code_sha256=sha256(Path(__file__)))
    if args.model=='ipsl':
        previous=ROOT/'data/provenance/historical_climate_benchmark_20260908.json'
        result['previous_gfdl_historical_retained_bytes']=json.loads(previous.read_text())['total_retained_bytes']
        result['previous_gfdl_provenance_sha256']=sha256(previous)
    out.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print('historical aggregate provenance',out.stat().st_size,'bytes; retained',result['total_retained_bytes'])


if __name__=='__main__':main()
