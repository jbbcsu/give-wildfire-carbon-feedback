"""Reuse one authorized real cutout; no network or outcome estimation."""
import argparse
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

from allocate_irrigation_heat_basis import _validate_panel, _regime_heat_basis, heat_basis_feature_names
from allocate_outcome_exposures import allocate, KEYS
from build_future_weighted_precipitation import join_season_stages, WEIGHT_HASH
from summarize_contiguous_climate_contrasts import ROOT, checked, sha256

FEATURES = heat_basis_feature_names([29.], 3)
HEAT = [x for x in FEATURES if not x.endswith('tmean_c')]


def exact_join(rain, heat, threshold=29.):
    features=heat_basis_feature_names([threshold],3)
    heat_columns=[x for x in features if not x.endswith('tmean_c')]
    if rain.duplicated(KEYS).any() or heat.duplicated(KEYS).any():
        raise ValueError('duplicate climate key')
    a=rain.set_index(KEYS).sort_index(); b=heat.set_index(KEYS).sort_index()
    if not a.index.equals(b.index):
        raise ValueError('rain/heat key support differs')
    if not np.isfinite(b[features].to_numpy()).all():
        raise ValueError('nonfinite heat basis')
    for stage in (1,2,3):
        col=f'stage{stage}_tmean_c'
        if not np.array_equal(a[col].to_numpy(),b[col].to_numpy()):
            raise ValueError('weighted stage mean temperature differs')
    if set(heat_columns)&set(a.columns):
        raise ValueError('heat fields already present')
    return a.join(b[heat_columns],validate='one_to_one').reset_index()


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--pilot',type=Path,required=True)
    parser.add_argument('--out-dir',type=Path,required=True)
    parser.add_argument('--crops',nargs='+',choices=['mai','soy'],default=['mai','soy'])
    parser.add_argument('--threshold-c',type=int,choices=[29,30],default=29)
    parser.add_argument('--scenario',choices=['ssp126','ssp585'],default='ssp126')
    parser.add_argument('--accounted-dir',type=Path,action='append',default=[])
    args=parser.parse_args(); pilot=args.pilot.resolve(); out=args.out_dir.resolve()
    if len(set(args.crops))!=len(args.crops):raise ValueError('duplicate crop')
    features=heat_basis_feature_names([args.threshold_c],3)
    accounted=[p.resolve() for p in args.accounted_dir]
    if any(not p.is_relative_to(ROOT/'data/interim') or not p.is_dir() for p in accounted):
        raise ValueError('accounted directories must be existing project intermediates')
    if len(set([pilot,out]+accounted))!=len([pilot,out]+accounted):raise ValueError('duplicate accounted directory')
    if not pilot.is_relative_to(ROOT/'data/interim') or not out.is_relative_to(ROOT/'data/interim') or out.exists():
        raise ValueError('use existing ignored pilot and new ignored output directory')
    receipt_path=pilot/'receipt.json'; pilot_receipt=json.loads(receipt_path.read_text())
    if pilot_receipt['status'] not in ('heat_pilot_reconciled_exact_retained_calendar_support','climate_content_validated'):
        raise ValueError('pilot not validated')
    config_path=ROOT/pilot_receipt.get('config_path','config/isimip3b_heat_subset_pilot_20260907.json')
    if sha256(config_path)!=pilot_receipt['config_sha256']:raise ValueError('cutout config changed')
    climate_config=json.loads(config_path.read_text())
    identity=climate_config['specifiers']
    if (identity['climate_scenario'],identity['climate_forcing'],identity['ensemble_member'])!=(args.scenario,'gfdl-esm4','r1i1p1f1'):
        raise ValueError('requested future realization differs from cutout lineage')
    for name,digest in pilot_receipt['artifact_hashes'].items():
        if sha256(pilot/name)!=digest: raise ValueError('pilot artifact changed')
    manifest_path=ROOT/'data/provenance/isimip_crop_calendar_2015soc.toml'
    manifest=tomllib.loads(manifest_path.read_text())
    future_path=ROOT/'data/provenance/future_weighted_precipitation_20260907.json'
    future=json.loads(future_path.read_text())
    weights_path=checked(dict(path='data/interim/mirca_os_v2/irrigation_shares_2000.parquet',sha256=WEIGHT_HASH))
    weights=pq.read_table(weights_path,filters=[('lat','in',[39.25,39.75]),('crop','in',['mai','soy'])],use_threads=False).to_pandas()
    result=dict(status='started',role='joint_climate_inputs_only',crop_yield_estimated=False,
                causal_or_scc_result=False,new_downloads=0,threshold_c=args.threshold_c,
                requested_crops=args.crops,pilot_receipt_sha256=sha256(receipt_path),
                future_receipt_sha256=sha256(future_path),weight_sha256=WEIGHT_HASH,
                calendar_manifest_sha256=sha256(manifest_path),products=[],calendars={},
                code_hashes={p:sha256(ROOT/'scripts'/p) for p in (
                    'extend_heat_cutout_two_crops.py','allocate_irrigation_heat_basis.py',
                    'allocate_outcome_exposures.py','build_future_weighted_precipitation.py',
                    'build_crop_heat_features.py','build_crop_stage_heat_features.py')})
    def budget():
        used=sum(p.stat().st_size for d in [pilot,out]+accounted for p in d.rglob('*') if p.is_file())
        if used>64*2**20-128*1024 or shutil.disk_usage(ROOT).free<pilot_receipt['initial_free_bytes']-64*2**20:
            raise ValueError('original 64 MiB combined disk ceiling breached')
        return used
    def save():
        result['combined_pilot_output_bytes']=budget()
        (out/'receipt.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    out.mkdir()
    try:
        save()
        for crop in args.crops:
            product=[p for p in future['products'] if (p['crop'],p['esm'],p['scenario'])==(crop,'GFDL-ESM4',args.scenario)]
            if len(product)!=1 or product[0]['member']!='r1i1p1f1':raise ValueError('realization differs')
            product=product[0]; bases=[]; source_hashes=[]
            for regime in ('noirr','firr'):
                name=f'ggcmi-crop-calendar-phase3_2015soc_{crop}_{regime}.nc'
                calendar=ROOT/'data/raw/crop_calendars'/name
                expected=[r for r in manifest['files'] if r['name']==name]
                if len(expected)!=1 or hashlib.sha512(calendar.read_bytes()).hexdigest()!=expected[0]['sha512']:
                    raise ValueError('calendar hash differs')
                result['calendars'][name]=expected[0]['sha512']
                inputs=[r for r in product['inputs'] if f'/{crop}_{regime}/' in r['season']['path']]
                if len(inputs)!=1:raise ValueError('rainfall calendar mapping differs')
                inputs=inputs[0]; source_hashes.append(inputs)
                tables={k:pd.read_parquet(checked(inputs[k])) for k in ('season','stages')}
                tables={k:v.loc[v.harvest_year.between(2042,2049)].copy() for k,v in tables.items()}
                panel=join_season_stages(tables['season'],tables['stages'])
                reuse=(crop,regime,args.threshold_c)==('mai','noirr',29) and pilot_receipt['status']=='heat_pilot_reconciled_exact_retained_calendar_support'
                dest=pilot if reuse else out/f'{crop}_{regime}'
                if dest!=pilot:
                    dest.mkdir(); common=['--tasmax',str(pilot/'tasmax_cutout.nc'),'--calendar',str(calendar),
                        '--crop',crop,'--irrigation',regime,'--year-start','2042','--year-end','2049',
                        '--lat-start','0','--lat-stop','2','--calendar-by-coordinates','--threshold-c',str(args.threshold_c)]
                    for script,filename in [('build_crop_heat_features.py','season_heat.parquet'),
                                            ('build_crop_stage_heat_features.py','stage_heat.parquet')]:
                        budget();subprocess.run([sys.executable,str(ROOT/'scripts'/script),*common,'--out',str(dest/filename)],check=True);budget()
                season=pd.read_parquet(dest/'season_heat.parquet'); stage=pd.read_parquet(dest/'stage_heat.parquet')
                for frame in (season,stage):
                    if set(pd.MultiIndex.from_frame(frame[KEYS]))!=set(pd.MultiIndex.from_frame(panel[KEYS])):
                        raise ValueError('incomplete heat/calendar coverage')
                scope=dict(crop=crop,irrigation=regime,year_start=2042,year_end=2049,stages=3)
                panel=_validate_panel(panel,**scope)
                basis,fractions,audit=_regime_heat_basis(panel,season,stage,thresholds=[args.threshold_c],**scope)
                if fractions!='0,0.3,0.7,1':raise ValueError('stage fractions differ')
                bases.append(basis)
            weighted,allocation=allocate(pd.concat(bases,ignore_index=True),weights,features,['noirr','firr'],exclude_missing_weight_cells=True)
            if weighted.yield_observed.any() or weighted.yield_t_ha.notna().any():raise ValueError('future outcomes present')
            rain=pd.read_parquet(checked(product));rain=rain.loc[rain.harvest_year.between(2042,2049)]
            joined=exact_join(rain,weighted,args.threshold_c)
            path=out/f'{crop}_GFDL-ESM4_{args.scenario}_joint_climate.parquet'; budget();joined.to_parquet(path,index=False);budget()
            result['products'].append(dict(crop=crop,esm='GFDL-ESM4',member='r1i1p1f1',scenario=args.scenario,
                years=list(range(2042,2050)),rows=len(joined),cells=len(joined[['lat','lon_360']].drop_duplicates()),
                path=str(path.relative_to(ROOT)),sha256=sha256(path),bytes=path.stat().st_size,
                rainfall_sha256=product['sha256'],regime_sources=source_hashes,allocation=allocation))
            save()
        result['artifacts']={str(p.relative_to(out)):sha256(p) for p in out.rglob('*.parquet')}
        result['status']='two_crop_joint_climate_inputs_validated' if set(args.crops)=={'mai','soy'} else 'joint_climate_inputs_validated';save()
        print(result['status'],[(p['crop'],p['rows']) for p in result['products']])
    except Exception as error:
        result.update(status='failed_preserved',error_type=type(error).__name__,error=str(error));save();raise


if __name__=='__main__':main()
