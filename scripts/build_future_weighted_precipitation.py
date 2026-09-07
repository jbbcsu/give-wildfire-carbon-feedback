"""Real retained climate to fixed-weight nonlinear inputs; no yield estimates."""
import argparse
import gc
import json
from pathlib import Path
import tomllib

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from allocate_irrigation_distribution_basis import build_regime_candidate_basis
from allocate_outcome_exposures import allocate, KEYS
from summarize_contiguous_climate_contrasts import (
    ROOT, MATRIX, YEARS, COMMON_ESMS, checked, local_path, sha256, annual_features,
)

FEATURES = ['log1p_precip_mm', 'stage1_precip_share', 'stage2_precip_share',
            'cdd_max_days', 'rx5day_mm', 'precipitation_concentration_hhi',
            'stage3_precip_share', 'precip_mm'] + [f'stage{i}_tmean_c' for i in (1,2,3)]
SHAPES = {'stage1_precip_share','stage2_precip_share','stage3_precip_share',
          'precipitation_concentration_hhi'}
ZERO = 'zero_precipitation_season'
WEIGHT_HASH = '7512ffc580928a03f75bbce5f3d4263c9bb2c631a8ff04075973acb4b149e4ba'
PROTOCOL = 'FUTURE_WEIGHTED_PRECIPITATION_PROTOCOL_20260907.md'


def join_season_stages(season, stages):
    annual_features(season, stages)  # Existing chronology, totals and temperature checks.
    if set(stages.stage_id) != {1,2,3}:
        raise ValueError('stage IDs differ')
    stage_metrics = ['stage_days','tmean_c','precip_mm','wet_days_n',
                     'cdd_max_days','rx1day_mm','rx5day_mm']
    result = season.copy()
    for stage in (1,2,3):
        part = stages.loc[stages.stage_id.eq(stage), KEYS+['irrigation']+stage_metrics]
        part = part.rename(columns={c:f'stage{stage}_{c}' for c in stage_metrics})
        result = result.merge(part, on=KEYS+['irrigation'], validate='one_to_one')
    if len(result) != len(season):
        raise ValueError('stage merge lost seasons')
    # Explicitly absent future outcomes, solely for the existing schema API.
    result['yield_observed'] = False
    result['yield_t_ha'] = np.nan
    return result


def weighted_climate(panel, weights):
    if panel.yield_observed.any() or panel.yield_t_ha.notna().any():
        raise ValueError('future climate must not contain outcomes')
    basis, _, threshold = build_regime_candidate_basis(panel)
    if threshold != 1.:
        raise ValueError('wet-day threshold changed')
    output, audit = allocate(basis, weights, FEATURES+[ZERO], ['noirr','firr'],
                             exclude_missing_weight_cells=True)
    if output.yield_observed.any() or output.yield_t_ha.notna().any():
        raise ValueError('allocation produced a future outcome')
    output = output[KEYS+FEATURES+[ZERO]].copy()
    gap = np.log1p(output.precip_mm) - output.log1p_precip_mm
    if (gap < -1e-12).any():
        raise ValueError('nonlinear allocation violates Jensen inequality')
    audit.update(jensen_gap_min=float(gap.min()), jensen_gap_mean=float(gap.mean()),
                 jensen_gap_max=float(gap.max()), future_outcomes_present=False)
    return output, audit


def contrasts(base, candidate, expected_years):
    if base.duplicated(KEYS).any() or candidate.duplicated(KEYS).any():
        raise ValueError('duplicate scenario key')
    b = base.set_index(KEYS).sort_index()
    c = candidate.set_index(KEYS).sort_index()
    if not b.index.equals(c.index):
        raise ValueError('scenario keys differ')
    grid = ['crop','lat','lon_360']
    for frame in (b,c):
        if not frame.reset_index().groupby(grid).harvest_year.agg(set).map(
                lambda v:v==set(expected_years)).all():
            raise ValueError('incomplete years')
        if not np.isfinite(frame[FEATURES+[ZERO]].to_numpy()).all():
            raise ValueError('nonfinite feature')
    delta = (c[FEATURES]-b[FEATURES]).groupby(grid).mean()
    valid_shape = (~((b[ZERO]>0)|(c[ZERO]>0))).groupby(grid).all()
    result = {'cells':len(delta),'shape_cells':int(valid_shape.sum()),
              'shape_excluded_cells':int((~valid_shape).sum()),'features':{}}
    for name in FEATURES:
        values=delta.loc[valid_shape,name] if name in SHAPES else delta[name]
        result['features'][name] = (dict(mean=float(values.mean()),
            cell_p10=float(values.quantile(.1)),cell_p90=float(values.quantile(.9)))
            if len(values) else None)
    return result


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--out-dir',required=True,type=Path)
    parser.add_argument('--receipt',required=True,type=Path)
    args=parser.parse_args()
    if args.out_dir.exists() or args.receipt.exists():
        raise ValueError('new output paths required')
    matrix_path=local_path(MATRIX)
    matrix=json.loads(matrix_path.read_text())
    audits={}
    for record in matrix['cells']:
        if record['esm'] not in COMMON_ESMS:
            continue
        audit=json.loads(checked({'path':record['audit'],'sha256':record['audit_sha256']}).read_text())
        config=tomllib.loads(checked({'path':record['config'],'sha256':record['config_sha256']}).read_text())
        if audit['result']!='passed' or audit['realization']!={k:config[k] for k in ('esm','member','scenario')}:
            raise ValueError('climate realization differs')
        if (config['feature_year_start'],config['feature_year_end'])!=(2032,2059):
            raise ValueError('climate period differs')
        key=(record['esm'],record['scenario'])
        if key in audits or key!=(config['esm'],config['scenario']):
            raise ValueError('duplicate/mismatched realization')
        audits[key]=audit
    if set(audits)!={(e,s) for e in COMMON_ESMS for s in ('ssp126','ssp370','ssp585')}:
        raise ValueError('balanced matrix missing')
    weight_path=checked({'path':'data/interim/mirca_os_v2/irrigation_shares_2000.parquet','sha256':WEIGHT_HASH})
    weights=pq.read_table(weight_path,filters=[('lat','in',[39.25,39.75]),('crop','in',['mai','soy'])],use_threads=False).to_pandas()
    if set(weights.weight_vintage)!={'fixed_2000'}:
        raise ValueError('weight vintage differs')
    result=dict(role='future_weighted_climate_inputs_not_yield_projection',
        crop_yield_estimated=False,causal_or_scc_result=False,local_raw_downloads=0,
        years=YEARS,latitudes=[39.25,39.75],weight_sha256=WEIGHT_HASH,
        matrix_sha256=sha256(matrix_path),protocol_sha256=sha256(ROOT/PROTOCOL),
        code_hashes={p:sha256(ROOT/p) for p in (
            'scripts/build_future_weighted_precipitation.py','scripts/allocate_irrigation_distribution_basis.py',
            'scripts/allocate_outcome_exposures.py','scripts/summarize_contiguous_climate_contrasts.py',
            'scripts/evaluate_isimip3b_five_esm_holdout_smoke.py')},
        products=[],comparisons=[])
    args.out_dir.mkdir(parents=True)
    for crop in ('mai','soy'):
        for esm in COMMON_ESMS:
            base=None
            for scenario in ('ssp126','ssp370','ssp585'):
                audit=audits[esm,scenario]
                if audit['realization']['member']!=audits[esm,'ssp126']['realization']['member']:
                    raise ValueError('paired member differs')
                inputs=[]; panels=[]
                for regime in ('noirr','firr'):
                    cells=[c for c in audit['cells'] if c['id']==f'{crop}_{regime}']
                    if len(cells)!=1:
                        raise ValueError('calendar missing/duplicate')
                    rec=cells[0]
                    paths={k:checked(rec['inputs'][k]) for k in ('season','stages')}
                    season,stages=(pq.read_table(paths[k],use_threads=False).to_pandas() for k in ('season','stages'))
                    for frame,kind in ((season,'season'),(stages,'stages')):
                        if (len(frame)!=rec['row_counts'][kind] or set(frame.crop)!={crop}
                            or set(frame.irrigation)!={regime} or set(frame.lat)!={39.25,39.75}
                            or set(frame.harvest_year)!=set(YEARS)):
                            raise ValueError('source scope changed')
                    panels.append(join_season_stages(season,stages))
                    inputs.append({k:rec['inputs'][k] for k in paths})
                panel=pd.concat(panels,ignore_index=True)
                output,allocation=weighted_climate(panel,weights)
                # Verify complete keys even for the reference path.
                contrasts(output,output,YEARS)
                path=args.out_dir/f'{crop}_{esm}_{scenario}.parquet'
                output.to_parquet(path,index=False)
                result['products'].append(dict(crop=crop,esm=esm,scenario=scenario,
                    member=audit['realization']['member'],path=str(path.relative_to(ROOT)),
                    sha256=sha256(path),bytes=path.stat().st_size,inputs=inputs,allocation=allocation))
                if scenario=='ssp126':
                    base=output
                else:
                    result['comparisons'].append(dict(crop=crop,esm=esm,
                        reference_scenario='ssp126',candidate_scenario=scenario,
                        **contrasts(base,output,YEARS)))
                del panel,panels,season,stages
                gc.collect()
                print(crop,esm,scenario,len(output),'climate rows',flush=True)
            del base
    result['output_parquet_bytes']=sum(p['bytes'] for p in result['products'])
    if result['output_parquet_bytes']>48*2**20:
        raise ValueError('climate feature products exceed registered small-output allowance')
    args.receipt.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')


if __name__=='__main__':
    main()
