"""Single public server-side subset request; never downloads climate output."""
import argparse
import hashlib
import json
from pathlib import Path
import urllib.parse
import urllib.request
from heat_cutout_dates import registered_years

ROOT=Path(__file__).resolve().parents[1]
CONFIG=ROOT/'config/isimip3b_heat_subset_pilot_20260907.json'
SERVICE='https://files.isimip.org/api/v2'


def json_request(url,payload=None):
    parsed=urllib.parse.urlparse(url)
    if parsed.scheme!='https' or parsed.hostname not in ('data.isimip.org','files.isimip.org'):
        raise ValueError('unexpected public API host')
    headers={'User-Agent':'GIVE-precipitation-subset-pilot/1'}
    body=None
    if payload is not None:
        if url!=SERVICE:
            raise ValueError('POST restricted to registered subset service')
        headers['Content-Type']='application/json'
        body=json.dumps(payload,sort_keys=True).encode()
    request=urllib.request.Request(url,data=body,headers=headers)
    with urllib.request.urlopen(request,timeout=30) as response:
        content=response.read(1048577)
        if len(content)>1048576:
            raise ValueError('metadata response exceeds 1 MiB cap')
    return json.loads(content),hashlib.sha256(content).hexdigest()


def validate_and_prepare(config,dataset):
    registered_years(config)
    for gate in ('local_download_authorized','local_feature_construction_authorized','damage_or_scc_authorized'):
        if config[gate] is not False:
            raise ValueError('pilot unexpectedly opens a local data or scientific gate')
    if dataset['id']!=config['dataset_id'] or dataset['version']!=config['dataset_version']:
        raise ValueError('dataset identity/version changed')
    if dataset['public'] is not True or dataset['restricted'] is not False or dataset['rights']['short']!='CC0 1.0':
        raise ValueError('source access or rights changed')
    if config['resource_doi'] not in {r['doi'] for r in dataset['resources']}:
        raise ValueError('resource DOI changed')
    if any(dataset['specifiers'].get(k)!=v for k,v in config['specifiers'].items()):
        raise ValueError('climate identity changed')
    files=[r for r in dataset['files'] if r['id']==config['file_id']]
    if len(files)!=1:
        raise ValueError('source file not unique')
    record=files[0]
    expected={'name':config['file_name'],'path':config['source_path'],'version':config['dataset_version'],
              'size':config['source_bytes'],'checksum':config['source_sha512'],'checksum_type':'sha512'}
    if any(record.get(k)!=v for k,v in expected.items()):
        raise ValueError('source file contract changed')
    bbox=config['bbox_west_east_south_north']
    if bbox!=[-180,180,39,40]:
        raise ValueError('pilot bounding box changed')
    return {'paths':[record['path']],'operations':[{'operation':'select_bbox','bbox':bbox,
              'compute_mean':False,'output_csv':False}]}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--submit',action='store_true')
    parser.add_argument('--config',type=Path,default=CONFIG)
    args=parser.parse_args()
    if args.out.exists() or args.out.with_suffix('.partial').exists():
        raise ValueError('receipt or partial receipt exists; inspect before any resubmission')
    config_path=args.config.resolve()
    if not config_path.is_relative_to(ROOT/'config'):
        raise ValueError('registered project config required')
    config=json.loads(config_path.read_text())
    url=f'https://data.isimip.org/api/v1/datasets/{config["dataset_id"]}/'
    dataset,digest=json_request(url)
    payload=validate_and_prepare(config,dataset)
    receipt=dict(role=config['role'],config_sha256=hashlib.sha256(config_path.read_bytes()).hexdigest(),
                 config_path=str(config_path.relative_to(ROOT)),
                 code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                 catalogue_url=url,catalogue_response_sha256=digest,
                 payload=payload,request_sha256=hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest(),
                 source_checks_passed=True,local_climate_bytes_downloaded=0,
                 local_download_authorized=False,status='prepared_not_submitted')
    partial=args.out.with_suffix('.partial')
    partial.write_text(json.dumps(receipt,indent=2)+'\n')
    if args.submit:
        result,response_hash=json_request(SERVICE,payload)
        receipt.update(status='server_request_returned',service_response=result,service_response_sha256=response_hash)
    partial.write_text(json.dumps(receipt,indent=2)+'\n')
    partial.replace(args.out)
    print(json.dumps({k:v for k,v in receipt.items() if k in ('status','service_response','local_climate_bytes_downloaded')}))


if __name__=='__main__':
    main()
