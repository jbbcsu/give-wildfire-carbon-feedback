"""Distributional source offsets and future changes; never weather-year pairs."""
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from allocate_outcome_exposures import KEYS
from allocate_irrigation_heat_basis import heat_basis_feature_names
from build_future_weighted_precipitation import FEATURES,SHAPES,ZERO,WEIGHT_HASH
from extend_heat_cutout_two_crops import exact_join
from summarize_contiguous_climate_contrasts import ROOT,checked,sha256

GRID=['crop','lat','lon_360']


def distribution_difference(reference,candidate,columns):
    """Each cell gets equal weight; year realizations are never subtracted."""
    for frame in (reference,candidate):
        if frame.empty or frame.duplicated(KEYS).any() or not np.isfinite(frame[columns].to_numpy()).all():
            raise ValueError('empty, duplicate or nonfinite distribution inputs')
    a=reference.groupby(GRID)[columns];b=candidate.groupby(GRID)[columns]
    if not a.size().index.equals(b.size().index):raise ValueError('distribution cell supports differ')
    result={}
    for column in columns:
        differences={'mean':b.mean()[column]-a.mean()[column]}
        for q in (.1,.5,.9):differences[f'q{int(q*100)}']=b.quantile(q)[column]-a.quantile(q)[column]
        result[column]={k:dict(equal_cell_mean=float(v.mean()),cell_p10=float(v.quantile(.1)),
            cell_p90=float(v.quantile(.9)),cells=len(v)) for k,v in differences.items()}
    return result


def model_heat_ranges(reference,future,columns):
    if reference.duplicated(KEYS).any() or future.duplicated(KEYS).any():raise ValueError('duplicate range keys')
    grouped=reference.groupby(GRID);lo=grouped[columns].min();hi=grouped[columns].max()
    keys=pd.MultiIndex.from_frame(future[GRID]);lower=lo.reindex(keys).to_numpy();upper=hi.reindex(keys).to_numpy()
    values=future[columns].to_numpy()
    if not np.isfinite(np.concatenate([lower,upper,values])).all():raise ValueError('range support missing')
    outside=(values<lower-1e-10)|(values>upper+1e-10)
    return dict(evaluated_rows=len(future),outside_any_rows=int(outside.any(axis=1).sum()),
        outside_any_fraction=float(outside.any(axis=1).mean()),
        by_feature={c:float(outside[:,i].mean()) for i,c in enumerate(columns)})


def observed(crop,label,threshold):
    frames={};receipts=[];heat=[c for c in heat_basis_feature_names([threshold],3) if not c.endswith('tmean_c')]
    for kind,features in [('direct',FEATURES+[ZERO]),('heat',heat_basis_feature_names([threshold],3))]:
        receipt=ROOT/f'outputs/continuous_global_panel_1982_2016_v1/{label}_1982_2016_{kind}_assembly_receipt.json'
        r=json.loads(receipt.read_text());path=checked(r['output']);parts=[]
        for batch in pq.ParquetFile(path).iter_batches(batch_size=8192,columns=KEYS+['yield_observed','yield_t_ha']+features,use_threads=False):
            f=batch.to_pandas();mask=f.lat.isin([39.25,39.75])&f.harvest_year.between(1982,2010)&f.yield_observed&f.yield_t_ha.gt(0)
            if mask.any():parts.append(f.loc[mask].copy())
        frames[kind]=pd.concat(parts,ignore_index=True)
        if set(frames[kind].crop)!={crop}:raise ValueError('observed crop differs')
        receipts.append(dict(path=str(receipt.relative_to(ROOT)),sha256=sha256(receipt),product=r['output']))
    a=frames['direct'].set_index(KEYS).sort_index();b=frames['heat'].set_index(KEYS).sort_index()
    pd.testing.assert_frame_equal(a[['yield_observed','yield_t_ha']],b[['yield_observed','yield_t_ha']],check_exact=True)
    return exact_join(frames['direct'],frames['heat'],threshold),receipts


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);args=p.parse_args()
    if args.out.exists():raise ValueError('new comparison receipt required')
    result=dict(role='historical_distribution_source_benchmark_not_causal_bias_correction',
        observed_weather_years_paired=False,crop_yield_estimated=False,causal_or_scc_result=False,
        periods=dict(historical=[1982,2010],future=[2032,2059]),comparisons=[],
        protocol_sha256=sha256(ROOT/'HISTORICAL_CLIMATE_BENCHMARK_PROTOCOL_20260908.md'),
        code_sha256=sha256(Path(__file__)))
    for crop,label,threshold in [('mai','maize',29),('soy','soy',30)]:
        obs,observed_sources=observed(crop,label,threshold)
        rp=ROOT/f'data/interim/gfdl_historical_{crop}_joint_20260908/receipt.json';r=json.loads(rp.read_text())
        if r['status']!='historical_joint_climate_inputs_validated' or r['weight_sha256']!=WEIGHT_HASH:raise ValueError('unvalidated historical climate')
        if len(r['products'])!=1 or r['products'][0]['crop']!=crop:raise ValueError('historical crop differs')
        model=pd.read_parquet(checked(r['products'][0]));common=pd.MultiIndex.from_frame(obs[GRID].drop_duplicates())
        model=model.loc[pd.MultiIndex.from_frame(model[GRID]).isin(common)].copy()
        if not pd.MultiIndex.from_frame(obs[KEYS]).isin(pd.MultiIndex.from_frame(model[KEYS])).all():raise ValueError('observed keys absent from model historical coverage')
        if not model.groupby(GRID).harvest_year.agg(set).map(lambda v:v==set(range(1982,2011))).all():raise ValueError('historical model years incomplete')
        sampled=model.set_index(KEYS).loc[pd.MultiIndex.from_frame(obs[KEYS])].reset_index()
        heat=[c for c in heat_basis_feature_names([threshold],3) if not c.endswith('tmean_c')]
        columns=FEATURES+heat;core=[c for c in columns if c not in SHAPES]
        entry=dict(crop=crop,observed_sources=observed_sources,model_receipt=dict(path=str(rp.relative_to(ROOT)),sha256=sha256(rp)),
            common_cells=len(common),observed_rows=len(obs),model_historical_rows=len(model),
            historical_model_minus_observed=distribution_difference(obs,model,core),
            availability_matched_model_minus_observed=distribution_difference(obs,sampled,core),scenarios=[])
        for scenario in ('ssp126','ssp585'):
            fp=ROOT/f'data/interim/gfdl_{scenario}_{crop}_full_heat_20260908/receipt.json';fr=json.loads(fp.read_text())
            if fr['status']!='joint_climate_inputs_validated' or fr['calendars']!=r['calendars'] or fr['weight_sha256']!=r['weight_sha256']:raise ValueError('future lineage differs')
            product=fr['products'][0]
            if (product['crop'],product['esm'],product['member'],product['scenario'])!=(crop,'GFDL-ESM4','r1i1p1f1',scenario):raise ValueError('future realization differs')
            future=pd.read_parquet(checked(product));future=future.loc[pd.MultiIndex.from_frame(future[GRID]).isin(common)].copy()
            if not future.groupby(GRID).harvest_year.agg(set).map(lambda v:v==set(range(2032,2060))).all():raise ValueError('future years incomplete')
            changes=distribution_difference(model,future,core);total=distribution_difference(obs,future,core)
            residual=max(abs(total[c]['mean']['equal_cell_mean']-changes[c]['mean']['equal_cell_mean']-entry['historical_model_minus_observed'][c]['mean']['equal_cell_mean']) for c in core)
            if residual>1e-10:raise ValueError('source/period mean arithmetic does not reconcile')
            zero=pd.concat([obs[GRID+[ZERO]],model[GRID+[ZERO]],future[GRID+[ZERO]]]).groupby(GRID)[ZERO].max()
            valid=zero.index[zero.eq(0)];shape_frames=[f.loc[pd.MultiIndex.from_frame(f[GRID]).isin(valid)] for f in (obs,model,future)]
            shapes=(dict(historical_model_minus_observed=distribution_difference(shape_frames[0],shape_frames[1],sorted(SHAPES)),
                future_minus_model_historical=distribution_difference(shape_frames[1],shape_frames[2],sorted(SHAPES))) if len(valid) else None)
            entry['scenarios'].append(dict(scenario=scenario,source=dict(path=str(fp.relative_to(ROOT)),sha256=sha256(fp)),
                future_rows=len(future),future_minus_model_historical=changes,future_minus_observed_historical=total,
                mean_decomposition_max_absolute_residual=residual,model_historical_heat_ranges=model_heat_ranges(model,future,heat),
                shape_common_cells=len(valid),shape_excluded_cells=len(common)-len(valid),shape_comparisons=shapes))
        result['comparisons'].append(entry)
    args.out.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print([(c['crop'],c['common_cells'],[(s['scenario'],s['model_historical_heat_ranges']['outside_any_fraction']) for s in c['scenarios']]) for c in result['comparisons']])


if __name__=='__main__':main()
