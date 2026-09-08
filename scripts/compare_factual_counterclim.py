"""Paired factual-minus-published-counterclim inputs; not anthropogenic SCC."""
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd
import xarray as xr
from allocate_outcome_exposures import KEYS
from allocate_irrigation_heat_basis import heat_basis_feature_names
from build_future_weighted_precipitation import FEATURES,SHAPES,ZERO,WEIGHT_HASH
from compare_historical_climate_sources import observed,distribution_difference,GRID
from summarize_contiguous_climate_contrasts import ROOT,checked,sha256
from validate_counterclim_crop_domain import AMENDMENT


def aligned_pair(factual,counter,columns):
    for f in (factual,counter):
        if f.empty or f.duplicated(KEYS).any() or not np.isfinite(f[columns].to_numpy()).all():
            raise ValueError('empty, duplicate or nonfinite paired input')
    a=factual.set_index(KEYS).sort_index();b=counter.set_index(KEYS).sort_index()
    if not a.index.equals(b.index):raise ValueError('paired factual/counterclim keys differ')
    return a,b


def paired_summary(factual,counter,columns):
    a,b=aligned_pair(factual,counter,columns);delta=(a[columns]-b[columns]).reset_index()
    cell=delta.groupby(GRID)[columns].mean()
    return dict(rows=len(delta),cells=len(cell),
        paired_difference={c:dict(equal_cell_mean=float(cell[c].mean()),cell_p10=float(cell[c].quantile(.1)),
            cell_p90=float(cell[c].quantile(.9)),equal_cell_year_mean=float(delta[c].mean())) for c in columns},
        annual_equal_cell_means=[dict(year=int(y),**{c:float(v) for c,v in row.items()})
            for y,row in delta.groupby('harvest_year')[columns].mean().iterrows()],
        distribution_differences=distribution_difference(counter,factual,columns))


def factual_parity(old,new,columns):
    if old.duplicated(KEYS).any() or new.duplicated(KEYS).any():raise ValueError('duplicate parity keys')
    a=old.set_index(KEYS).sort_index();b=new.set_index(KEYS).sort_index()
    if not a.index.isin(b.index).all():raise ValueError('retained factual keys missing in rebuilt product')
    b=b.loc[a.index];residuals={}
    for c in columns:
        x=a[c].to_numpy();y=b[c].to_numpy()
        if c==ZERO:
            if not np.array_equal(x,y):raise ValueError('factual zero-rain flags differ')
            residuals[c]=0.0
            continue
        elif not np.allclose(x,y,rtol=1e-10,atol=1e-8,equal_nan=True):
            raise ValueError('factual numeric parity failed: '+c)
        finite=np.isfinite(x)&np.isfinite(y)
        residuals[c]=float(np.abs(x[finite]-y[finite]).max()) if finite.any() else None
    return dict(rows=len(a),cells=len(a.reset_index()[GRID].drop_duplicates()),
        atol=1e-8,rtol=1e-10,maximum_absolute_residual_by_feature=residuals)


def validate_precision_evidence(entry,crop,new_source,old_sources):
    if entry.get('crop')!=crop or entry.get('new_source')!=new_source or entry.get('old_sources')!=old_sources:
        raise ValueError('precision evidence source identity differs')
    if entry.get('compared_features')!=FEATURES+[ZERO]:raise ValueError('precision evidence feature coverage differs')
    parity=entry['legacy_reference_parity']
    if parity.get('atol')!=1e-8 or parity.get('rtol')!=1e-10 or set(parity['maximum_absolute_residual_by_feature'])!=set(FEATURES+[ZERO]):
        raise ValueError('precision evidence tolerance/coverage differs')
    if any(v!=0 for v in parity['maximum_absolute_residual_by_feature'].values()):raise ValueError('legacy reconstruction is not exact')
    audits=entry['primitive_audits']
    if len(audits)!=2 or {a['regime'] for a in audits}!={'noirr','firr'}:raise ValueError('precision regime evidence incomplete')
    for a in audits:
        if a['new_float64_primitives_exact'] is not True or (a['season_rows'],a['stage_rows'])!=(19894,59682):
            raise ValueError('raw-daily float64 reproduction incomplete')
        counts=a['primitive_precision_counts']
        if set(counts)!={'precip_mm','stage1_precip_mm','stage2_precip_mm','stage3_precip_mm'}:raise ValueError('primitive coverage incomplete')
        for values in counts.values():
            if set(values)!={'both','float32_only','float64_only'} or any(type(v)!=int or v<0 for v in values.values()) or sum(values.values())!=5488:
                raise ValueError('primitive precision counts differ')


def parity_with_verified_precision(old,new,columns,crop,new_source,old_sources):
    try:
        return factual_parity(old,new,columns)
    except ValueError as error:
        if not str(error).startswith('factual numeric parity failed: '):raise
        initial_error=str(error)
    path=ROOT/'data/interim/obsclim_soy_joint_20260908/precision_reconciliation.json';proof=json.loads(path.read_text())
    if proof['status']!='legacy_precision_reproduced_at_original_tolerance' or proof['tolerance_changed'] is not False:
        raise ValueError('precision reconciliation not validated')
    if proof['code_sha256']!=sha256(ROOT/'scripts/reconcile_factual_precision.py') or proof['protocol_sha256']!=sha256(ROOT/'FACTUAL_PARITY_PRECISION_RECONCILIATION_20260908.md'):
        raise ValueError('precision reconstruction method changed')
    entries=[e for e in proof['comparisons'] if e['crop']==crop]
    if len(entries)!=1:raise ValueError('precision crop evidence not unique')
    validate_precision_evidence(entries[0],crop,new_source,old_sources)
    explained=set(SHAPES)|{'precip_mm','log1p_precip_mm'}
    unchanged=factual_parity(old,new,[c for c in columns if c not in explained])
    if (unchanged['rows'],unchanged['cells'])!=(entries[0]['legacy_reference_parity']['rows'],entries[0]['legacy_reference_parity']['cells']):
        raise ValueError('precision reference support differs')
    unchanged.update(status='matched_with_exact_legacy_precision_reproduction',original_strict_parity_passed=False,
        original_error=initial_error,reconciliation=dict(path=str(path.relative_to(ROOT)),sha256=sha256(path)),
        explained_features=sorted(explained),tolerance_changed=False,both_comparison_paths_use_float64=True)
    return unchanged


def load_product(crop,scenario):
    rp=ROOT/f'data/interim/{scenario}_{crop}_joint_20260908/receipt.json';r=json.loads(rp.read_text())
    if r['status']!='observational_joint_climate_inputs_validated' or r['weight_sha256']!=WEIGHT_HASH:
        raise ValueError('observational input not validated')
    if len(r['products'])!=1:raise ValueError('observational product count differs')
    p=r['products'][0]
    expected=dict(crop=crop,climate_forcing='GSWP3-W5E5',scenario=scenario,years=list(range(1982,2011)))
    if any(p.get(k)!=v for k,v in expected.items()):raise ValueError('observational product identity differs')
    if r['protocol_sha256']!=sha256(ROOT/'FACTUAL_COUNTERCLIM_PILOT_PROTOCOL_20260908.md'):
        raise ValueError('paired protocol changed')
    if r['domain_amendment_sha256']!=sha256(ROOT/AMENDMENT):raise ValueError('domain amendment changed')
    f=pd.read_parquet(checked(p))
    if len(f)!={'mai':500,'soy':327}[crop]*29 or not f.groupby(GRID).harvest_year.agg(set).map(lambda s:s==set(range(1982,2011))).all():
        raise ValueError('incomplete paired crop-year coverage')
    return f,r,dict(path=str(rp.relative_to(ROOT)),sha256=sha256(rp))


def paired_daily_axes(factual,counter):
    def records(r):
        if len(r['sources'])!=9:raise ValueError('paired daily source count differs')
        result={}
        for item in r['sources']:
            c=item['content'];key=(c['variable'],int(c['first_date'][:4]))
            if key in result:raise ValueError('duplicate paired daily source')
            rp=checked(item);path=rp.parent/f'{key[0]}_cutout.nc'
            if sha256(path)!=item['daily_sha256']:raise ValueError('paired daily payload changed')
            result[key]=path
        if set(result)!={(v,y) for v in ('pr','tas','tasmax') for y in (1981,1991,2001)}:
            raise ValueError('paired daily source blocks differ')
        return result
    a,b=records(factual),records(counter)
    for key in a:
        with xr.open_dataset(a[key],engine='h5netcdf') as x,xr.open_dataset(b[key],engine='h5netcdf') as y:
            if not all(np.array_equal(x[c],y[c]) for c in ('time','lat','lon')):
                raise ValueError('factual/counterclim daily axes differ')
    return dict(paired_daily_files=9,exact_time_lat_lon=True)


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);args=p.parse_args()
    if args.out.exists():raise ValueError('new comparison output required')
    result=dict(role='conditional_historical_trend_climate_input_comparison',
        sign='factual_minus_counterclim',climate_sequence_years_paired=True,
        anthropogenic_attribution=False,crop_yield_estimated=False,causal_or_scc_result=False,
        protocol_sha256=sha256(ROOT/'FACTUAL_COUNTERCLIM_PILOT_PROTOCOL_20260908.md'),
        domain_amendment_sha256=sha256(ROOT/AMENDMENT),
        code_sha256=sha256(Path(__file__)),comparisons=[])
    for crop,label,threshold in [('mai','maize',29),('soy','soy',30)]:
        f,fr,fs=load_product(crop,'obsclim');c,cr,cs=load_product(crop,'counterclim')
        if fr['calendars']!=cr['calendars'] or fr['weight_sha256']!=cr['weight_sha256']:
            raise ValueError('paired calendar/irrigation lineage differs')
        axes=paired_daily_axes(fr,cr)
        heat=[v for v in heat_basis_feature_names([threshold],3) if not v.endswith('tmean_c')]
        columns=FEATURES+heat;core=[v for v in columns if v not in SHAPES]
        retained,rs=observed(crop,label,threshold)
        parity=parity_with_verified_precision(retained,f,columns+[ZERO],crop,fs,rs)
        zero=pd.concat([f[GRID+[ZERO]],c[GRID+[ZERO]]]).groupby(GRID)[ZERO].max()
        valid=zero.index[zero.eq(0)]
        shape_f=f.loc[pd.MultiIndex.from_frame(f[GRID]).isin(valid)]
        shape_c=c.loc[pd.MultiIndex.from_frame(c[GRID]).isin(valid)]
        periods=[]
        for name,first,last in [('full',1982,2010),('early',1982,1991),('late',2001,2010)]:
            choose=lambda x:x.loc[x.harvest_year.between(first,last)]
            periods.append(dict(name=name,years=[first,last],core=paired_summary(choose(f),choose(c),core),
                shape=(paired_summary(choose(shape_f),choose(shape_c),sorted(SHAPES)) if len(valid) else None)))
        result['comparisons'].append(dict(crop=crop,sources=[fs,cs],retained_observed_sources=rs,
            factual_parity=parity,paired_axes=axes,shape_common_cells=len(valid),shape_excluded_cells=len(zero)-len(valid),periods=periods))
    result['status']='paired_climate_diagnostic_validated'
    args.out.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print([(c['crop'],c['factual_parity']['rows'],c['periods'][0]['core']['paired_difference']['precip_mm']) for c in result['comparisons']])


if __name__=='__main__':main()
