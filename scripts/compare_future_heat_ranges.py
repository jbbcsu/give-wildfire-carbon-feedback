"""Six marginal heat-range diagnostics; no response fitting or causal claims."""
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from extend_heat_cutout_two_crops import HEAT
from allocate_irrigation_heat_basis import heat_basis_feature_names
from summarize_contiguous_climate_contrasts import ROOT, checked, sha256

GRID=['crop','lat','lon_360']
KEYS=GRID+['harvest_year']
TOL=1e-10

def diagnose(history,future,features=None):
    features=HEAT if features is None else features
    if history.empty or future.empty or history.duplicated(KEYS).any() or future.duplicated(KEYS).any():
        raise ValueError('empty/duplicate heat keys')
    if not history.harvest_year.between(1982,2010).all() or not history.yield_t_ha.gt(0).all():
        raise ValueError('historical scope differs')
    if not np.isfinite(history[features].to_numpy()).all() or not np.isfinite(future[features].to_numpy()).all():
        raise ValueError('nonfinite heat')
    groups=history.groupby(GRID)
    lo=groups[features].min();hi=groups[features].max();count=groups.size()
    lo.loc[count<2,:]=np.nan;hi.loc[count<2,:]=np.nan
    frame=future.merge(lo.add_suffix('__min'),on=GRID,how='left',validate='many_to_one')
    frame=frame.merge(hi.add_suffix('__max'),on=GRID,how='left',validate='many_to_one')
    out=dict(historical_observed_rows=len(history),historical_cells=len(count),
        years_per_cell_min=int(count.min()),years_per_cell_max=int(count.max()),
        future_rows=len(future),future_cells=len(future[GRID].drop_duplicates()),features={})
    common=np.ones(len(frame),dtype=bool);any_out=np.zeros(len(frame),dtype=bool)
    for col in features:
        valid=frame[col+'__min'].notna() & frame[col+'__max'].notna()
        below=valid & frame[col].lt(frame[col+'__min']-TOL)
        above=valid & frame[col].gt(frame[col+'__max']+TOL)
        n=int(valid.sum());outside=int((below|above).sum())
        out['features'][col]=dict(evaluated_rows=n,range_unavailable_rows=int((~valid).sum()),
            below_range_rows=int(below.sum()),above_range_rows=int(above.sum()),
            outside_range_fraction=outside/n if n else None)
        common &= valid.to_numpy();any_out |= (below|above).to_numpy()
    n=int(common.sum());outside=int((common&any_out).sum())
    out.update(common_evaluable_rows=n,any_heat_outside_rows=outside,any_heat_outside_fraction=outside/n if n else None)
    return out

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--parent',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    if args.out.exists():raise ValueError('new receipt required')
    parent=json.loads(args.parent.read_text())
    if parent['status'] not in ('two_crop_joint_climate_inputs_validated','joint_climate_inputs_validated'):raise ValueError('unvalidated future inputs')
    threshold=parent.get('threshold_c',29)
    if threshold not in (29,30):raise ValueError('unregistered threshold')
    features=[x for x in heat_basis_feature_names([threshold],3) if not x.endswith('tmean_c')]
    result=dict(role='marginal_heat_ranges_not_transport_or_damages',crop_yield_estimated=False,
        causal_or_scc_result=False,soybean_29c_is_not_locked_30c_control=threshold==29,
        threshold_c=threshold,minimum_years=2,absolute_tolerance=TOL,
        parent_sha256=sha256(args.parent),code_sha256=sha256(Path(__file__)),
        protocol_sha256=sha256(ROOT/'FUTURE_HEAT_RANGE_PROTOCOL_20260908.md'),comparisons=[])
    for crop,label in [('mai','maize'),('soy','soy')]:
        if crop not in {p['crop'] for p in parent['products']}:continue
        source_receipt=ROOT/f'outputs/continuous_global_panel_1982_2016_v1/{label}_1982_2016_heat_assembly_receipt.json'
        source=json.loads(source_receipt.read_text());path=checked(source['output']);parts=[]
        for batch in pq.ParquetFile(path).iter_batches(batch_size=8192,columns=KEYS+['yield_t_ha']+features,use_threads=False):
            frame=batch.to_pandas();mask=frame.lat.isin([39.25,39.75])&frame.harvest_year.between(1982,2010)&frame.yield_t_ha.gt(0)
            if mask.any():parts.append(frame.loc[mask].copy())
        history=pd.concat(parts,ignore_index=True)
        products=[p for p in parent['products'] if p['crop']==crop]
        if len(products)!=1 or set(history.crop)!={crop}:raise ValueError('crop mismatch')
        product=products[0];future=pd.read_parquet(checked(product))
        result['comparisons'].append(dict(crop=crop,esm=product['esm'],scenario=product['scenario'],
            historical_input=source['output'],historical_receipt_sha256=sha256(source_receipt),
            future_sha256=product['sha256'],**diagnose(history,future,features)))
    args.out.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print([(r['crop'],r['any_heat_outside_fraction']) for r in result['comparisons']])

if __name__=='__main__':main()
