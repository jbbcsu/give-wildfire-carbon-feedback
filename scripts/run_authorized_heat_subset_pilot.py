"""Single-cutout acquisition/heat pipeline; requires recorded user authorization.

Do not create an authorization record or invoke this CLI until the user has
approved the pending 64 MiB exception. Unit tests use synthetic in-memory input
only. A partial failure preserves its files and receipt for inspection.
"""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import stat
import subprocess
import sys
import tomllib
import urllib.request
import zipfile

import numpy as np
import pandas as pd
import xarray as xr

from prepare_heat_subset_pilot import json_request, validate_and_prepare
from build_crop_year_features import normalize_temperature
from climate_inputs import validate_daily_units
from summarize_contiguous_climate_contrasts import checked, local_path, sha256

ROOT=Path(__file__).resolve().parents[1]
CONFIG=ROOT/'config/isimip3b_heat_subset_pilot_20260907.json'
COMPLETION=ROOT/'data/provenance/heat_subset_server_completion_20260907.json'
BUDGET=64*2**20
ARCHIVE_CAP=16*2**20
OUTPUT_RESERVE=8*2**20
CHUNK=256*1024


def validate_authorization(record, config_hash, job_id):
    expected=dict(scope='one_isimip_heat_cutout_pilot',additional_disk_budget_bytes=BUDGET,
                  config_sha256=config_hash,job_id=job_id,user_approved=True)
    if record.get('user_approved') is not True or any(record.get(k)!=v for k,v in expected.items()):
        raise ValueError('explicit authorization does not match the registered pilot')
    if not isinstance(record.get('user_approval_quote'),str) or not record['user_approval_quote'].strip():
        raise ValueError('record the actual user approval; do not infer it')
    date=datetime.fromisoformat(record['approved_at_iso'])
    if date.tzinfo is None:
        raise ValueError('approval timestamp requires timezone')


def stream_copy(source,target,expected_bytes,check_budget):
    """Bounded copy; reject overrun/truncation without automatic retries."""
    if not isinstance(expected_bytes,int) or expected_bytes<=0:
        raise ValueError('positive exact length required')
    digest=hashlib.sha256();total=0
    with target.open('xb') as output:
        while True:
            chunk=source.read(min(CHUNK,expected_bytes-total+1))
            if not chunk:break
            if total+len(chunk)>expected_bytes:
                raise ValueError('payload exceeds its declared exact size')
            check_budget(len(chunk))
            output.write(chunk);digest.update(chunk);total+=len(chunk)
    if total!=expected_bytes:
        raise ValueError('truncated payload; partial file retained for inspection')
    return digest.hexdigest()


def inspect_archive(archive,archive_bytes):
    infos=archive.infolist()
    if not infos or len(infos)>16:
        raise ValueError('unexpected archive member count')
    names=set();climate=[]
    for info in infos:
        path=PurePosixPath(info.filename)
        if (path.is_absolute() or '..' in path.parts or '\\' in info.filename
            or ':' in info.filename or info.filename in names):
            raise ValueError('unsafe/duplicate archive path')
        names.add(info.filename)
        mode=info.external_attr>>16
        if stat.S_ISLNK(mode) or (stat.S_IFMT(mode) not in (0,stat.S_IFREG,stat.S_IFDIR)):
            raise ValueError('archive contains a link or special file')
        if info.flag_bits & 1:
            raise ValueError('encrypted archive member')
        if info.is_dir():continue
        if path.suffix.lower()=='.nc':climate.append(info)
        elif path.suffix.lower() not in ('.txt','.json','.md') or info.file_size>2**20:
            raise ValueError('unregistered archive sidecar')
    if len(climate)!=1:
        raise ValueError('exactly one NetCDF member required')
    member=climate[0]
    if member.file_size<=0 or archive_bytes+member.file_size+OUTPUT_RESERVE>BUDGET:
        raise ValueError('archive plus climate plus output reserve exceeds 64 MiB')
    return member


def validate_cutout(path, start_year=2041, end_year=2050):
    from heat_cutout_dates import date_contract
    first_date,last_date,expected_days=date_contract(start_year,end_year)
    with xr.open_dataset(path,engine='h5netcdf') as dataset:
        if 'tasmax' not in dataset or dataset.tasmax.dims!=('time','lat','lon'):
            raise ValueError('cutout variable/dimension contract differs')
        field=dataset.tasmax
        if not np.array_equal(np.sort(field.lat.values),[39.25,39.75]):
            raise ValueError('cutout is not the two registered latitude centers')
        if not np.array_equal(np.sort(field.lon.values),np.arange(-179.75,180.,.5)):
            raise ValueError('cutout longitude centers differ; no regridding')
        calendar=str(field.time.encoding.get('calendar','standard'))
        if calendar not in ('standard','gregorian','proleptic_gregorian'):
            raise ValueError('unregistered time calendar')
        dates=pd.DatetimeIndex(field.time.values)
        expected=pd.date_range(first_date,last_date)
        if not dates.normalize().equals(expected) or not np.all(np.diff(dates.values)==np.timedelta64(1,'D')):
            raise ValueError(f'cutout must contain exact contiguous {start_year}–{end_year} daily dates')
        units=str(field.attrs.get('units',''))
        validate_daily_units('tasmax',units)
        missing=0;minimum=np.inf;maximum=-np.inf
        for first in range(0,len(dates),365):
            values=normalize_temperature(field.isel(time=slice(first,first+365)).values,units)
            missing+=int((~np.isfinite(values)).sum())
            finite=values[np.isfinite(values)]
            if len(finite):minimum=min(minimum,float(finite.min()));maximum=max(maximum,float(finite.max()))
        if missing:
            raise ValueError(f'cutout contains {missing} nonfinite daily values; no imputation')
        return dict(days=len(dates),first_date=first_date,last_date=last_date,
            latitudes=field.lat.values.tolist(),longitude_count=len(field.lon),
            calendar=calendar,source_units=units,minimum_c=minimum,maximum_c=maximum,
            missing_values=missing,all_parent_payload_bytes_verified=False)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        raise ValueError('unexpected archive redirect')


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--authorization-file',type=Path,required=True)
    parser.add_argument('--out-dir',type=Path,required=True)
    args=parser.parse_args()
    authorization=json.loads(args.authorization_file.read_text())
    config=json.loads(CONFIG.read_text());completion=json.loads(COMPLETION.read_text())
    validate_authorization(authorization,sha256(CONFIG),completion['job_id'])
    out=args.out_dir.resolve()
    if not out.is_relative_to(ROOT/'data/interim') or out.exists():
        raise ValueError('use a new directory inside this project data/interim; inspect any partial run')
    # Validate all existing prerequisites before any archive GET or directory write.
    calendar_manifest=local_path('data/provenance/isimip_crop_calendar_2015soc.toml')
    manifest=tomllib.loads(calendar_manifest.read_text())
    calendar_name='ggcmi-crop-calendar-phase3_2015soc_mai_noirr.nc'
    calendar=local_path('data/raw/crop_calendars/'+calendar_name)
    cal_record=[r for r in manifest['files'] if r['name']==calendar_name]
    if len(cal_record)!=1 or hashlib.sha512(calendar.read_bytes()).hexdigest()!=cal_record[0]['sha512']:
        raise ValueError('calendar hash differs')
    source_audit=local_path('data/provenance/isimip3b_rimex_contiguous_multicrop_regime_audit_20260902.json')
    audit=json.loads(source_audit.read_text())
    if audit['realization']!={'esm':'GFDL-ESM4','member':'r1i1p1f1','scenario':'ssp126'} or audit['result']!='passed':
        raise ValueError('retained rainfall realization differs')
    crop_record=[c for c in audit['cells'] if c['id']=='mai_noirr']
    if len(crop_record)!=1:raise ValueError('retained crop/calendar missing')
    season_path=checked(crop_record[0]['inputs']['season'])
    dataset,catalogue_hash=json_request(f'https://data.isimip.org/api/v1/datasets/{config["dataset_id"]}/')
    validate_and_prepare(config,dataset)
    job,job_hash=json_request(completion['job_url'])
    if job.get('status')!='finished' or job.get('id')!=completion['job_id'] or job.get('file_url')!=completion['file_url']:
        raise ValueError('server job is not the registered finished cutout')
    archive_length=completion['head_content_length_bytes']
    if not 0<archive_length<=ARCHIVE_CAP:raise ValueError('registered archive too large')
    initial_free=shutil.disk_usage(ROOT).free
    out.mkdir()
    def budget(incoming=0):
        occupied=sum(p.stat().st_size for p in out.iterdir() if p.is_file())
        # Keep a small journal allowance inside the total cap so even a
        # rejected write can leave a concise failure receipt without overshoot.
        if (occupied+incoming>BUDGET-128*1024
            or shutil.disk_usage(ROOT).free-incoming<initial_free-BUDGET+128*1024):
            raise ValueError('64 MiB disk occupancy/reserve limit reached')
    receipt=dict(status='authorized_not_downloaded',authorization_sha256=sha256(args.authorization_file),
        config_sha256=sha256(CONFIG),completion_sha256=sha256(COMPLETION),
        catalogue_response_sha256=catalogue_hash,job_response_sha256=job_hash,
        code_sha256=sha256(Path(__file__)),calendar_sha512=cal_record[0]['sha512'],
        implementation_hashes={p:sha256(ROOT/'scripts'/p) for p in (
            'prepare_heat_subset_pilot.py','build_crop_heat_features.py',
            'build_crop_stage_heat_features.py','align_cutout_calendar.py',
            'build_crop_year_features.py','climate_inputs.py',
            'validate_heat_partition.py','validate_stage_heat_partition.py',
            'heat_threshold_validation.py','reconcile_stage_heat_features.py')},
        retained_season_input=crop_record[0]['inputs']['season'],
        additional_disk_budget_bytes=BUDGET,initial_free_bytes=initial_free,
        scientific_use='heat_feature_pilot_only',crop_yield_estimated=False,causal_or_scc_result=False)
    def save():
        budget();(out/'receipt.json').write_text(json.dumps(receipt,indent=2,allow_nan=False)+'\n')
    save()
    try:
        request=urllib.request.Request(completion['file_url'],headers={'Accept-Encoding':'identity'})
        with urllib.request.build_opener(NoRedirect).open(request,timeout=30) as response:
            if (response.status!=200 or int(response.headers.get('Content-Length','0'))!=archive_length
                or response.headers.get('ETag')!=completion['head_etag']):
                raise ValueError('archive length or ETag changed; review before downloading')
            receipt['archive_sha256']=stream_copy(response,out/'cutout.zip',archive_length,budget)
        receipt['status']='archive_downloaded';save()
        with zipfile.ZipFile(out/'cutout.zip') as archive:
            member=inspect_archive(archive,archive_length)
            receipt['archive_member']=member.filename
            with archive.open(member) as stream:
                receipt['climate_sha256']=stream_copy(stream,out/'tasmax_cutout.nc',member.file_size,budget)
        receipt['content_validation']=validate_cutout(out/'tasmax_cutout.nc')
        receipt['status']='climate_content_validated';save()
        common=['--tasmax',str(out/'tasmax_cutout.nc'),'--calendar',str(calendar),
                '--crop','mai','--irrigation','noirr','--year-start','2042','--year-end','2049',
                '--lat-start','0','--lat-stop','2','--calendar-by-coordinates','--threshold-c','29']
        commands=[['build_crop_heat_features.py',*common,'--out',str(out/'season_heat.parquet')],
            ['validate_heat_partition.py',str(out/'season_heat.parquet'),'--threshold-c','29'],
            ['build_crop_stage_heat_features.py',*common,'--out',str(out/'stage_heat.parquet')],
            ['validate_stage_heat_partition.py',str(out/'stage_heat.parquet'),'--threshold-c','29'],
            ['reconcile_stage_heat_features.py','--season',str(out/'season_heat.parquet'),
             '--stages',str(out/'stage_heat.parquet'),'--out-audit',str(out/'reconciliation.json')]]
        for script,*arguments in commands:
            budget();subprocess.run([sys.executable,str(ROOT/'scripts'/script),*arguments],check=True);budget()
        source=pd.read_parquet(season_path);source=source.loc[source.harvest_year.between(2042,2049)]
        heat=pd.read_parquet(out/'season_heat.parquet')
        keys=['harvest_year','lat','lon_360','crop','irrigation']
        cols=keys+['plant_year','cross_year','plant_doy','maturity_doy','season_days']
        pd.testing.assert_frame_equal(source[cols].sort_values(keys).reset_index(drop=True),
            heat[cols].sort_values(keys).reset_index(drop=True),check_dtype=False,check_exact=True)
        receipt.update(status='heat_pilot_reconciled_exact_retained_calendar_support',rows=len(heat),
            artifact_hashes={p.name:sha256(p) for p in out.iterdir() if p.suffix in ('.parquet','.nc','.zip')},
            output_bytes_before_final_receipt=sum(p.stat().st_size for p in out.iterdir() if p.is_file()))
        save();print(receipt['status'],len(heat),'rows; no yield or SCC estimate')
    except Exception as error:
        receipt.update(status='failed_preserved_for_inspection',error_type=type(error).__name__,error=str(error))
        # Preserve failure context even when an occupancy guard has fired.
        (out/'failure.json').write_text(json.dumps(receipt,indent=2,allow_nan=False)+'\n')
        raise


if __name__=='__main__':main()
