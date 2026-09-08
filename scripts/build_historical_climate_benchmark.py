"""Historical simulated-climate inputs only; no observed-year weather pairing."""
import argparse
from contextlib import ExitStack
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tomllib
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import xarray as xr
from allocate_irrigation_heat_basis import _validate_panel,_regime_heat_basis,heat_basis_feature_names
from allocate_outcome_exposures import allocate,KEYS
from build_future_weighted_precipitation import join_season_stages,weighted_climate,WEIGHT_HASH
from build_crop_year_features import normalize_temperature
from extend_heat_cutout_two_crops import exact_join
from heat_cutout_dates import registered_years
from run_authorized_heat_subset_pilot import validate_cutout
from summarize_contiguous_climate_contrasts import ROOT,sha256,checked

DATASETS={'pr':'3b37bbd1-d18d-4283-9e96-bf429c02479c','tas':'ecf92220-2f67-41d9-a427-a3ebef1255e9',
          'tasmax':'ad8ae7de-b41e-4f69-b683-daa5c0f21509'}
YEARS=list(range(1982,2011))


def validate_contracts(configs):
    expected={(v,a) for v in DATASETS for a in (1981,1991,2001)};seen=set()
    for c in configs:
        s=c['specifiers'];v=s['climate_variable'];a,b=registered_years(c)
        identity=dict(simulation_round='ISIMIP3b',product='InputData',region='global',time_step='daily',
            climate_forcing='gfdl-esm4',ensemble_member='r1i1p1f1',climate_scenario='historical',bias_adjustment='w5e5')
        if any(s.get(k)!=x for k,x in identity.items()) or v not in DATASETS:
            raise ValueError('historical realization differs')
        if c['dataset_id']!=DATASETS[v] or c['dataset_version']!='20210512' or c['resource_doi']!='10.48364/ISIMIP.842396.1':
            raise ValueError('historical dataset lineage differs')
        if (v,a) not in expected or b!=a+9 or (v,a) in seen:raise ValueError('historical blocks missing or duplicated')
        seen.add((v,a))
    if seen!=expected:raise ValueError('historical blocks incomplete')


def main():
    p=argparse.ArgumentParser();p.add_argument('--crop',choices=['mai','soy'],required=True)
    p.add_argument('--out-dir',type=Path,required=True);args=p.parse_args();out=args.out_dir.resolve()
    if out.exists() or not out.is_relative_to(ROOT/'data/interim'):raise ValueError('new ignored output required')
    threshold={'mai':29,'soy':30}[args.crop];sources={};configs=[];source_records=[]
    for var in DATASETS:
        sources[var]=[]
        for first in (1981,1991,2001):
            d=ROOT/f'data/interim/gfdl_historical_{var}_{first}_20260908'
            receipt=d/'receipt.json';r=json.loads(receipt.read_text())
            if r['status']!='climate_content_validated':raise ValueError('unvalidated daily source')
            cp=ROOT/r['config_path']
            if sha256(cp)!=r['config_sha256']:raise ValueError('source config changed')
            c=json.loads(cp.read_text());configs.append(c)
            file=d/f'{var}_cutout.nc'
            if sha256(file)!=r['artifact_hashes'][file.name]:raise ValueError('daily source changed')
            content=validate_cutout(file,*registered_years(c),variable=var)
            sources[var].append(file);source_records.append(dict(path=str(receipt.relative_to(ROOT)),
                sha256=sha256(receipt),daily_sha256=sha256(file),content=content))
    validate_contracts(configs)
    # Simultaneous variables must refer to the same grid/instant; no nearest matching.
    previous_last=None;mean_above_max=0
    for index in range(3):
        with ExitStack() as stack:
            ds={v:stack.enter_context(xr.open_dataset(sources[v][index],engine='h5netcdf')) for v in DATASETS}
            ref=ds['pr']
            for other in ('tas','tasmax'):
                if not all(np.array_equal(ref[k],ds[other][k]) for k in ('time','lat','lon')):
                    raise ValueError('cross-variable axes differ')
            if previous_last is not None and ref.time.values[0]-previous_last!=np.timedelta64(1,'D'):
                raise ValueError('historical decade timestamps not contiguous')
            previous_last=ref.time.values[-1]
            for start in range(0,len(ref.time),365):
                arrays={v:normalize_temperature(ds[v][v].isel(time=slice(start,start+365)).values,ds[v][v].attrs['units']) for v in ('tas','tasmax')}
                mean_above_max+=int((arrays['tas']>arrays['tasmax']+1e-5).sum())
    if mean_above_max:raise ValueError('daily mean temperature exceeds maximum temperature')
    manifest_path=ROOT/'data/provenance/isimip_crop_calendar_2015soc.toml'
    manifest=tomllib.loads(manifest_path.read_text())
    weights_path=checked(dict(path='data/interim/mirca_os_v2/irrigation_shares_2000.parquet',sha256=WEIGHT_HASH))
    weights=pq.read_table(weights_path,filters=[('lat','in',[39.25,39.75]),('crop','=',args.crop)],use_threads=False).to_pandas()
    initial=shutil.disk_usage(ROOT).free
    result=dict(status='started',role='historical_simulated_climate_inputs_only',crop_yield_estimated=False,
        causal_or_scc_result=False,observed_weather_years_paired=False,threshold_c=threshold,
        sources=source_records,weight_sha256=WEIGHT_HASH,calendar_manifest_sha256=sha256(manifest_path),
        calendars={},products=[],initial_free_bytes=initial,daily_mean_above_max_count=0,
        daily_mean_max_tolerance_c=1e-5,construction_latitude_rows_per_child=1,
        protocol_sha256=sha256(ROOT/'HISTORICAL_CLIMATE_BENCHMARK_PROTOCOL_20260908.md'),
        code_hashes={n:sha256(ROOT/'scripts'/n) for n in ('build_historical_climate_benchmark.py','build_crop_year_features.py',
            'build_crop_stage_features.py','build_crop_heat_features.py','build_crop_stage_heat_features.py',
            'build_future_weighted_precipitation.py','extend_heat_cutout_two_crops.py','climate_inputs.py',
            'allocate_irrigation_heat_basis.py','allocate_irrigation_distribution_basis.py','allocate_outcome_exposures.py',
            'run_authorized_heat_subset_pilot.py','heat_cutout_dates.py','align_cutout_calendar.py')})
    def budget():
        used=sum(p.stat().st_size for p in out.rglob('*') if p.is_file())
        if used>64*2**20-128*1024 or shutil.disk_usage(ROOT).free<max(130*2**30,initial-64*2**20):
            raise ValueError('historical batch disk budget breached')
        return used
    def save():
        result['output_bytes_before_receipt_write']=budget();(out/'receipt.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    out.mkdir();panels=[];bases=[];features=heat_basis_feature_names([threshold],3)
    try:
        save()
        for regime in ('noirr','firr'):
            name=f'ggcmi-crop-calendar-phase3_2015soc_{args.crop}_{regime}.nc';calendar=ROOT/'data/raw/crop_calendars'/name
            entries=[r for r in manifest['files'] if r['name']==name]
            if len(entries)!=1 or hashlib.sha512(calendar.read_bytes()).hexdigest()!=entries[0]['sha512']:raise ValueError('calendar hash differs')
            result['calendars'][name]=entries[0]['sha512'];dest=out/regime;dest.mkdir();tables={}
            for kind,script in [('season','build_crop_year_features.py'),('stages','build_crop_stage_features.py'),
                                ('season_heat','build_crop_heat_features.py'),('stage_heat','build_crop_stage_heat_features.py')]:
                parts=[]
                for lat in (0,1):
                    path=dest/f'{kind}_lat{lat}.parquet'
                    climate=(['--tasmax',*map(str,sources['tasmax']),'--threshold-c',str(threshold)] if 'heat' in kind
                             else ['--precip',*map(str,sources['pr']),'--temperature',*map(str,sources['tas'])])
                    cmd=[sys.executable,str(ROOT/'scripts'/script),*climate,'--calendar',str(calendar),'--crop',args.crop,
                        '--irrigation',regime,'--year-start','1982','--year-end','2010','--lat-start',str(lat),'--lat-stop',str(lat+1),
                        '--calendar-by-coordinates','--out',str(path)]
                    budget();subprocess.run(cmd,check=True);budget();parts.append(pd.read_parquet(path))
                tables[kind]=pd.concat(parts,ignore_index=True);tables[kind].to_parquet(dest/f'{kind}.parquet',index=False);budget()
            panel=join_season_stages(tables['season'],tables['stages'])
            if len(panel)!=686*29 or not panel.groupby(['lat','lon_360']).harvest_year.agg(set).map(lambda x:x==set(YEARS)).all():
                raise ValueError('historical complete-calendar support differs')
            scope=dict(crop=args.crop,irrigation=regime,year_start=1982,year_end=2010,stages=3)
            panel=_validate_panel(panel,**scope);basis,fractions,audit=_regime_heat_basis(panel,tables['season_heat'],tables['stage_heat'],thresholds=[threshold],**scope)
            if fractions!='0,0.3,0.7,1':raise ValueError('stage fractions differ')
            panels.append(panel);bases.append(basis);save()
        rain,rain_audit=weighted_climate(pd.concat(panels,ignore_index=True),weights)
        heat,heat_audit=allocate(pd.concat(bases,ignore_index=True),weights,features,['noirr','firr'],exclude_missing_weight_cells=True)
        joint=exact_join(rain,heat,threshold)
        if len(joint)!={'mai':500,'soy':327}[args.crop]*29:raise ValueError('weighted historical support differs')
        path=out/f'{args.crop}_GFDL-ESM4_historical_joint_climate.parquet';joint.to_parquet(path,index=False);budget()
        result['products']=[dict(crop=args.crop,esm='GFDL-ESM4',member='r1i1p1f1',scenario='historical',years=YEARS,
            rows=len(joint),cells=len(joint[['lat','lon_360']].drop_duplicates()),path=str(path.relative_to(ROOT)),sha256=sha256(path),
            rainfall_allocation=rain_audit,heat_allocation=heat_audit)]
        result.update(status='historical_joint_climate_inputs_validated',artifacts={str(p.relative_to(out)):sha256(p) for p in out.rglob('*.parquet')})
        save();print('historical joint climate validated',args.crop,len(joint),flush=True)
    except Exception as e:
        result.update(status='failed_preserved',error_type=type(e).__name__,error=str(e));save();raise


if __name__=='__main__':main()
