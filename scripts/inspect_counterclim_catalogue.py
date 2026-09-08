"""Metadata-only feasibility: no subset submission or climate data download."""
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
import re
import tomllib
from urllib.parse import urlencode
from prepare_heat_subset_pilot import json_request,ROOT
from summarize_contiguous_climate_contrasts import sha256


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);args=p.parse_args()
    if args.out.exists():raise ValueError('new metadata receipt required')
    manifest=ROOT/'data/provenance/isimip3a_daily_climate_plan.toml'
    original={f['name']:f for f in tomllib.loads(manifest.read_text())['files']}
    result=dict(role='public_counterclim_catalogue_feasibility_only',
        checked_utc=datetime.now(timezone.utc).isoformat(),climate_bytes_downloaded=0,
        subset_requests_submitted=0,crop_yield_estimated=False,causal_or_scc_result=False,
        factual_manifest_sha256=sha256(manifest),code_sha256=sha256(Path(__file__)),queries=[])
    for scenario in ('obsclim','counterclim'):
        for variable in ('pr','tas','tasmax'):
            spec=dict(simulation_round='ISIMIP3a',climate_forcing='gswp3-w5e5',
                climate_scenario=scenario,climate_variable=variable,time_step='daily')
            url='https://data.isimip.org/api/v1/datasets/?'+urlencode(spec)
            page,digest=json_request(url)
            if page.get('next'):raise ValueError('metadata pagination requires review')
            matches=[d for d in page['results'] if all(d['specifiers'].get(k)==v for k,v in spec.items())
                     and d['specifiers'].get('product')=='InputData' and d['specifiers'].get('region')=='global']
            if len(matches)!=1:raise ValueError(f'nonunique daily dataset: {scenario}/{variable}')
            dataset,ds_hash=json_request('https://data.isimip.org/api/v1/datasets/'+matches[0]['id']+'/')
            if dataset['id']!=matches[0]['id'] or dataset['specifiers']!=matches[0]['specifiers']:
                raise ValueError('catalogue identity changed between requests')
            if not dataset['public'] or dataset['restricted'] or dataset['rights']['short']!='CC0 1.0':
                raise ValueError('access or license needs review')
            files=[]
            for f in dataset['files']:
                match=re.search(r'_(1981_1990|1991_2000|2001_2010)\.nc$',f['name'])
                if not match:continue
                item={k:f[k] for k in ('id','name','path','size','version','checksum','checksum_type')}
                if scenario=='obsclim':
                    old=original.get(f['name'])
                    item['retained_manifest_exact_match']=bool(old and f['size']==old['size_bytes']
                        and f['checksum_type']=='sha512' and f['checksum']==old['sha512'])
                    if not item['retained_manifest_exact_match']:raise ValueError('factual manifest differs')
                files.append(item)
            if len(files)!=3:raise ValueError('three historical decades not resolved')
            result['queries'].append(dict(query_url=url,query_sha256=digest,dataset_sha256=ds_hash,
                dataset_id=dataset['id'],version=dataset['version'],specifiers=dataset['specifiers'],
                rights=dataset['rights']['short'],public=dataset['public'],restricted=dataset['restricted'],
                resources=[{k:r[k] for k in ('id','doi') if k in r} for r in dataset['resources']],files=files))
    args.out.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print([(q['specifiers']['climate_scenario'],q['specifiers']['climate_variable'],q['dataset_id'],q['version']) for q in result['queries']])


if __name__=='__main__':main()
