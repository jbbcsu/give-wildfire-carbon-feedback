"""Bounded acquisition of a registered cutout under standing user authorization.

Only the registered source is requested, with no raw-global fallback or retry.
Run inside run_bounded_job.py. Source/request contracts remain distinct from
the user's standing acquisition authority. Partial failures are preserved.
"""
import argparse
import json
from pathlib import Path
import shutil
import urllib.parse
import urllib.request
import zipfile

from prepare_heat_subset_pilot import json_request,validate_and_prepare
from heat_cutout_dates import registered_years
from run_authorized_heat_subset_pilot import stream_copy,inspect_archive,validate_cutout,NoRedirect
from summarize_contiguous_climate_contrasts import ROOT,sha256

BUDGET=64*2**20

def check_archive_identity(url,job_id,length,etag):
    parsed=urllib.parse.urlparse(url)
    if (parsed.scheme!='https' or parsed.hostname!='files.isimip.org' or parsed.query or parsed.fragment
        or parsed.path!=f'/api/v2/output/isimip-download-{job_id}.zip'):
        raise ValueError('unexpected archive URL')
    if not isinstance(length,int) or not 0<length<=16*2**20 or not isinstance(etag,str) or not etag:
        raise ValueError('archive must have capped exact length and nonempty ETag')

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--config',type=Path,required=True)
    parser.add_argument('--request-receipt',type=Path,required=True)
    parser.add_argument('--out-dir',type=Path,required=True)
    args=parser.parse_args();out=args.out_dir.resolve();config_path=args.config.resolve()
    if not out.is_relative_to(ROOT/'data/interim') or out.exists() or not config_path.is_relative_to(ROOT/'config'):
        raise ValueError('new ignored directory and registered config required')
    config=json.loads(config_path.read_text());req=json.loads(args.request_receipt.read_text())
    if req['config_sha256']!=sha256(config_path) or req['source_checks_passed'] is not True:
        raise ValueError('request/config lineage differs')
    dataset,dataset_hash=json_request(f'https://data.isimip.org/api/v1/datasets/{config["dataset_id"]}/')
    if validate_and_prepare(config,dataset)!=req['payload']:raise ValueError('registered payload differs')
    job_id=req['service_response']['id'];job_url=req['service_response']['job_url']
    if job_url!=f'https://files.isimip.org/api/v2/{job_id}':raise ValueError('job URL differs')
    job,job_hash=json_request(job_url)
    if job['id']!=job_id:raise ValueError('job identity differs')
    if job['status']!='finished':
        print('No download: registered server job status',job['status']);return
    url=job['file_url'];opener=urllib.request.build_opener(NoRedirect)
    # Validate URL before sending HEAD, then bind GET to that response identity.
    check_archive_identity(url,job_id,1,'url-precheck')
    with opener.open(urllib.request.Request(url,method='HEAD',headers={'Accept-Encoding':'identity'}),timeout=30) as response:
        if response.status!=200:raise ValueError('HEAD status differs')
        length=int(response.headers.get('Content-Length','0'));etag=response.headers.get('ETag')
    check_archive_identity(url,job_id,length,etag)
    initial=shutil.disk_usage(ROOT).free
    if initial-BUDGET<130*2**30:raise ValueError('insufficient protected free space')
    out.mkdir()
    result=dict(status='registered_not_downloaded',config_path=str(config_path.relative_to(ROOT)),
        config_sha256=sha256(config_path),request_receipt_sha256=sha256(args.request_receipt),
        catalogue_response_sha256=dataset_hash,job_response_sha256=job_hash,job_id=job_id,
        job_response=job,archive_url=url,archive_bytes=length,archive_etag=etag,
        source_contract=config,initial_free_bytes=initial,additional_disk_budget_bytes=BUDGET,
        authorization='standing project data download authorization; user instruction September 8, 2026 UTC',
        source_request_gate_is_not_acquisition_authority=True,causal_or_scc_result=False,
        code_hashes={p:sha256(ROOT/'scripts'/p) for p in ('acquire_registered_heat_cutout.py','run_authorized_heat_subset_pilot.py','prepare_heat_subset_pilot.py','heat_cutout_dates.py')})
    def budget(incoming=0):
        used=sum(p.stat().st_size for p in out.iterdir() if p.is_file())
        if used+incoming>BUDGET-128*1024 or shutil.disk_usage(ROOT).free-incoming<max(initial-BUDGET+128*1024,130*2**30):
            raise ValueError('disk budget exceeded')
    def save():
        budget();(out/'receipt.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    save()
    try:
        with opener.open(urllib.request.Request(url,headers={'Accept-Encoding':'identity'}),timeout=30) as response:
            if response.status!=200 or int(response.headers.get('Content-Length','0'))!=length or response.headers.get('ETag')!=etag:
                raise ValueError('archive identity changed between HEAD and GET')
            result['archive_sha256']=stream_copy(response,out/'cutout.zip',length,budget)
        with zipfile.ZipFile(out/'cutout.zip') as archive:
            member=inspect_archive(archive,length);result['archive_member']=member.filename
            with archive.open(member) as stream:
                result['climate_sha256']=stream_copy(stream,out/'tasmax_cutout.nc',member.file_size,budget)
        result['content_validation']=validate_cutout(out/'tasmax_cutout.nc',*registered_years(config))
        result.update(status='climate_content_validated',artifact_hashes={p.name:sha256(p) for p in out.iterdir() if p.suffix in ('.nc','.zip')})
        save();print('registered cutout validated',length,'archive bytes; no yield/SCC result')
    except Exception as error:
        result.update(status='failed_preserved',error_type=type(error).__name__,error=str(error))
        (out/'failure.json').write_text(json.dumps(result,indent=2)+'\n');raise

if __name__=='__main__':main()
