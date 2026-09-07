"""Marginal historical-range diagnostics; no response fitting or projection."""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from build_future_weighted_precipitation import FEATURES, SHAPES, ZERO
from summarize_contiguous_climate_contrasts import ROOT, checked, local_path, sha256

GRID=['crop','lat','lon_360']
KEYS=GRID+['harvest_year']
TOLERANCE=1e-10


def historical_ranges(frame):
    if frame.empty or frame.duplicated(KEYS).any():
        raise ValueError('empty/duplicate historical exposures')
    if not frame.harvest_year.between(1982,2010).all() or not frame.yield_t_ha.gt(0).all():
        raise ValueError('historical range scope differs')
    if not np.isfinite(frame[FEATURES+[ZERO]].to_numpy()).all():
        raise ValueError('nonfinite historical basis')
    ranges=frame.groupby(GRID).size().rename('observed_years').to_frame()
    for feature in FEATURES:
        selected=frame.loc[frame[ZERO].eq(0)] if feature in SHAPES else frame
        stats=selected.groupby(GRID)[feature].agg(['min','max','count'])
        stats.loc[stats['count']<2,['min','max']]=np.nan
        ranges=ranges.join(stats.rename(columns={x:f'{feature}__{x}' for x in stats}))
    return ranges.reset_index()


def compare(future,ranges):
    if future.empty or future.duplicated(KEYS).any() or ranges.duplicated(GRID).any():
        raise ValueError('empty/duplicate range comparison keys')
    if not np.isfinite(future[FEATURES+[ZERO]].to_numpy()).all():
        raise ValueError('nonfinite future basis')
    frame=future.merge(ranges,on=GRID,how='left',validate='many_to_one')
    out=dict(future_rows=len(frame),future_cells=len(frame[GRID].drop_duplicates()),features={})
    all_evaluable=np.ones(len(frame),dtype=bool)
    any_outside=np.zeros(len(frame),dtype=bool)
    for feature in FEATURES:
        lo,hi=frame[f'{feature}__min'],frame[f'{feature}__max']
        range_available=lo.notna() & hi.notna()
        shape_valid=frame[ZERO].eq(0) if feature in SHAPES else pd.Series(True,index=frame.index)
        valid=range_available & shape_valid
        below=valid & frame[feature].lt(lo-TOLERANCE)
        above=valid & frame[feature].gt(hi+TOLERANCE)
        n=int(valid.sum());outside=int((below|above).sum())
        out['features'][feature]=dict(evaluated_rows=n,range_unavailable_rows=int((~range_available).sum()),
            undefined_future_shape_rows=int((~shape_valid).sum()),
            below_range_rows=int(below.sum()),above_range_rows=int(above.sum()),
            outside_range_fraction=outside/n if n else None)
        all_evaluable &= valid.to_numpy()
        any_outside |= (below|above).to_numpy()
    n=int(all_evaluable.sum());outside=int((all_evaluable & any_outside).sum())
    out['common_evaluable_rows']=n
    out['any_feature_outside_rows']=outside
    out['any_feature_outside_fraction']=outside/n if n else None
    return out


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--out-dir',required=True,type=Path)
    parser.add_argument('--receipt',required=True,type=Path)
    args=parser.parse_args()
    if args.out_dir.exists() or args.receipt.exists():
        raise ValueError('new output paths required')
    parent_path=local_path('data/provenance/future_weighted_precipitation_20260907.json')
    parent=json.loads(parent_path.read_text())
    if parent['crop_yield_estimated'] is not False or parent['causal_or_scc_result'] is not False:
        raise ValueError('parent use gate changed')
    result=dict(role='marginal_historical_range_diagnostic_only',causal_or_scc_result=False,
        crop_yield_estimated=False,inside_range_is_not_joint_transport_validation=True,
        historical_years=[1982,2010],minimum_usable_years=2,absolute_boundary_tolerance=TOLERANCE,
        parent_receipt_sha256=sha256(parent_path),
        protocol_sha256=sha256(ROOT/'FUTURE_PRECIPITATION_RANGE_PROTOCOL_20260907.md'),
        code_hashes={p:sha256(ROOT/p) for p in ('scripts/compare_future_precipitation_ranges.py',
                    'scripts/build_future_weighted_precipitation.py')},historical_sources=[],comparisons=[])
    args.out_dir.mkdir(parents=True)
    for crop,label in [('mai','maize'),('soy','soy')]:
        receipt_path=local_path(f'outputs/continuous_global_panel_1982_2016_v1/{label}_1982_2016_direct_assembly_receipt.json')
        receipt=json.loads(receipt_path.read_text())
        source=checked(receipt['output'])
        pieces=[]
        for batch in pq.ParquetFile(source).iter_batches(batch_size=8192,
                columns=KEYS+['yield_t_ha']+FEATURES+[ZERO],use_threads=False):
            frame=batch.to_pandas()
            mask=(frame.lat.isin([39.25,39.75]) & frame.harvest_year.between(1982,2010)
                  & frame.yield_t_ha.gt(0))
            if mask.any():pieces.append(frame.loc[mask].copy())
        history=pd.concat(pieces,ignore_index=True)
        if set(history.crop)!={crop}:
            raise ValueError('historical crop differs')
        ranges=historical_ranges(history)
        output=args.out_dir/f'{crop}_historical_ranges.parquet'
        ranges.to_parquet(output,index=False)
        result['historical_sources'].append(dict(crop=crop,input=receipt['output'],
            input_receipt_sha256=sha256(receipt_path),observed_rows=len(history),cells=len(ranges),
            years_per_cell_min=int(ranges.observed_years.min()),
            years_per_cell_median=float(ranges.observed_years.median()),
            years_per_cell_max=int(ranges.observed_years.max()),
            range_output=dict(path=str(output.relative_to(ROOT)),sha256=sha256(output),bytes=output.stat().st_size)))
        for product in parent['products']:
            if product['crop']!=crop:continue
            future=pq.read_table(checked(product),use_threads=False).to_pandas()
            result['comparisons'].append(dict(crop=crop,esm=product['esm'],scenario=product['scenario'],
                **compare(future,ranges)))
        print(crop,len(history),'observed historical exposures;',len(ranges),'range cells',flush=True)
    args.receipt.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')


if __name__=='__main__':main()
