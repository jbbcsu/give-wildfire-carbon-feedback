"""Paired 28-year retained-feature contrasts, not impacts or SCC."""
import argparse
import gc
import json
from pathlib import Path
import tomllib

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from global_continuous_geographic_cluster_audit import ROOT, sha256
from summarize_climate_scenario_contrasts import FEATURES, describe
from evaluate_isimip3b_five_esm_holdout_smoke import _timing_features

RAW_KEYS = ['harvest_year','lat','lon_360','crop','irrigation']
YEARS = list(range(2032,2060))
COMMON_ESMS = ['GFDL-ESM4','IPSL-CM6A-LR','MPI-ESM1-2-HR']
MATRIX = 'data/provenance/isimip3b_rimex_contiguous_completed_matrix_audit_20260903.json'


def local_path(relative):
    path = ROOT/relative
    info = path.stat()
    if not path.is_file() or getattr(info,'st_flags',0) & 0x40000000:
        raise ValueError(f'not a locally available regular file: {relative}')
    return path


def checked(record):
    path = local_path(record['path'])
    if sha256(path)!=record['sha256']:
        raise ValueError(f'source hash mismatch: {path}')
    return path


def annual_features(season, stages):
    if season.duplicated(RAW_KEYS).any() or stages.duplicated(RAW_KEYS+['stage_id']).any():
        raise ValueError('duplicate season or stage identity')
    season_index = pd.MultiIndex.from_frame(season[RAW_KEYS]).sort_values()
    stage_index = pd.MultiIndex.from_frame(stages[RAW_KEYS].drop_duplicates()).sort_values()
    if not season_index.equals(stage_index) or len(stages)!=3*len(season):
        raise ValueError('stage and season support differ')
    if set(season.wet_day_threshold_mm)!={1.0} or set(stages.stage_fractions)!={'0,0.3,0.7,1'}:
        raise ValueError('unregistered wet-day threshold or stage fractions')
    for frame,days in ((season,'season_days'),(stages,'stage_days')):
        if not np.isfinite(frame[['tmean_c','precip_mm',days]].to_numpy()).all() or (frame[days]<=0).any():
            raise ValueError('nonfinite or empty climate window')
    weighted = stages.assign(temperature_day_sum=stages.tmean_c*stages.stage_days).groupby(RAW_KEYS).agg(
        stage_days=('stage_days','sum'),temperature_day_sum=('temperature_day_sum','sum'))
    joined = season.set_index(RAW_KEYS).join(weighted,validate='one_to_one')
    temperature_residual=float(np.abs(joined.tmean_c-joined.temperature_day_sum/joined.stage_days).max())
    if not joined.season_days.eq(joined.stage_days).all() or temperature_residual>1e-4:
        raise ValueError('stage-day temperature reconciliation failed: '
                         f'max days={np.abs(joined.season_days-joined.stage_days).max()}, '
                         f'max temperature={np.abs(joined.tmean_c-joined.temperature_day_sum/joined.stage_days).max()}')
    timing = _timing_features(season,stages,'contiguous pair')
    result = season.merge(timing,on=RAW_KEYS,validate='one_to_one').rename(columns={'harvest_year':'year'})
    result=result[['year','lat','lon_360']+FEATURES]
    result.attrs['stage_temperature_max_residual_c']=temperature_residual
    return result


def read_cell(audit, cell_id):
    cells = {c['id']:c for c in audit['cells']}
    record = cells[cell_id]
    paths = {kind:checked(record['inputs'][kind]) for kind in ('season','stages')}
    season,stages = (pq.read_table(paths[k],use_threads=False).to_pandas() for k in ('season','stages'))
    crop,regime = cell_id.split('_')
    for frame in (season,stages):
        if set(frame.crop)!={crop} or set(frame.irrigation)!={regime} or set(frame.lat)!={39.25,39.75}:
            raise ValueError('crop/regime/latitude identity mismatch')
    if len(season)!=record['row_counts']['season'] or len(stages)!=record['row_counts']['stages']:
        raise ValueError('row count differs from source receipt')
    try:
        features=annual_features(season,stages)
    except ValueError as error:
        raise ValueError(f'{paths["season"]}: {error}') from error
    return features, dict(
        inputs={k:record['inputs'][k] for k in ('season','stages')},
        stage_temperature_max_residual_c=features.attrs['stage_temperature_max_residual_c'],
        stage_temperature_tolerance_c=1e-4,
        stage_mean_temperature_available='tmean_c' in stages.columns,
        stage_tmax_integral_columns=[c for c in stages.columns if 'tmax' in c or 'tasmax' in c])


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--out',required=True,type=Path)
    args=parser.parse_args()
    if args.out.exists():
        raise ValueError('output already exists')
    matrix_path=local_path(MATRIX)
    matrix=json.loads(matrix_path.read_text())
    audits={}
    for row in matrix['cells']:
        audit_path=checked(dict(path=row['audit'],sha256=row['audit_sha256']))
        config_path=checked(dict(path=row['config'],sha256=row['config_sha256']))
        audit=json.loads(audit_path.read_text())
        config=tomllib.loads(config_path.read_text())
        if audit['result']!='passed' or audit['realization']!={k:config[k] for k in ('esm','member','scenario')}:
            raise ValueError('audit status or realization mismatch')
        if (config['feature_year_start'],config['feature_year_end'])!=(2032,2059):
            raise ValueError('source period mismatch')
        key=(row['esm'],row['scenario'])
        if key in audits or key!=(config['esm'],config['scenario']):
            raise ValueError('duplicate or inconsistent matrix identity')
        audits[key]=audit
    expected={(e,s) for e in COMMON_ESMS for s in ('ssp126','ssp370','ssp585')}|{('MRI-ESM2-0',s) for s in ('ssp126','ssp370')}
    if set(audits)!=expected:
        raise ValueError('registered available ESM/scenario matrix changed')
    mapping_receipt=local_path('data/provenance/global_country_proxy_20260907.json')
    mapping_path=checked(json.loads(mapping_receipt.read_text())['output'])
    mapping={(r['lat'],r['lon_360']):r['country_label'] for r in pq.read_table(mapping_path,use_threads=False).to_pylist()}
    cells=[f'{c}_{r}' for c in ('mai','soy','ri1','ri2','swh','wwh') for r in ('noirr','firr')]
    for audit in audits.values():
        if len(audit['cells'])!=12 or {c['id'] for c in audit['cells']}!=set(cells):
            raise ValueError('crop/calendar matrix incomplete')
    result=dict(role='direct_28_year_climate_contrasts_not_crop_impacts',
                global_projection=False,marginal_co2_effect=False,causal_or_scc_result=False,
                years=YEARS,latitudes=[39.25,39.75],common_comparison_esm_ids=COMMON_ESMS,
                additional_ssp370_esm='MRI-ESM2-0',matrix_path=MATRIX,matrix_sha256=sha256(matrix_path),
                country_proxy_receipt_sha256=sha256(mapping_receipt),
                code_hashes={p:sha256(ROOT/p) for p in (
                    'scripts/summarize_contiguous_climate_contrasts.py',
                    'scripts/summarize_climate_scenario_contrasts.py',
                    'scripts/evaluate_isimip3b_five_esm_holdout_smoke.py')},
                protocol_sha256=sha256(ROOT/'CLIMATE_CONTIGUOUS_CONTRAST_PROTOCOL_20260907.md'),
                comparisons=[],sources=[])
    for esm in COMMON_ESMS+['MRI-ESM2-0']:
        for cell in cells:
            base,source=read_cell(audits[(esm,'ssp126')],cell)
            result['sources'].append(dict(esm=esm,scenario='ssp126',cell=cell,**source))
            for scenario in ('ssp370','ssp585'):
                if (esm,scenario) not in audits:
                    continue
                if audits[(esm,scenario)]['realization']['member']!=audits[(esm,'ssp126')]['realization']['member']:
                    raise ValueError('paired realization differs')
                candidate,source=read_cell(audits[(esm,scenario)],cell)
                result['sources'].append(dict(esm=esm,scenario=scenario,cell=cell,**source))
                for region in ('full_calendar_band','USA_proxy_in_band','CHN_proxy_in_band'):
                    pair=[]
                    for frame in (base,candidate):
                        mask=np.ones(len(frame),dtype=bool) if region=='full_calendar_band' else np.array([
                            mapping.get(k)==region[:3] for k in zip(frame.lat,frame.lon_360)])
                        pair.append(frame.loc[mask])
                    record=dict(esm_id=esm,member_id=audits[(esm,scenario)]['realization']['member'],
                                crop_calendar=cell,region=region,reference_scenario='ssp126',
                                candidate_scenario=scenario,common_ensemble=esm in COMMON_ESMS)
                    if any(f.empty for f in pair):
                        record['status']='unavailable_subset'
                    else:
                        record.update(status='completed',**describe(*pair,YEARS))
                    result['comparisons'].append(record)
                del candidate
            del base
            gc.collect()
        print(esm,'all 12 crop/calendar contrasts complete',flush=True)
    temporary=args.out.with_suffix('.partial')
    temporary.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    temporary.replace(args.out)


if __name__=='__main__':
    main()
