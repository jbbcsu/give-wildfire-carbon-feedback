"""Exact same-model scenario contrasts; no yield-response/SCC calculation."""
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd
from allocate_outcome_exposures import KEYS
from allocate_irrigation_heat_basis import heat_basis_feature_names
from summarize_contiguous_climate_contrasts import ROOT,checked,sha256

GRID=['crop','lat','lon_360']

def compare(base,candidate,threshold):
    columns=['precip_mm','log1p_precip_mm','cdd_max_days','rx5day_mm']+heat_basis_feature_names([threshold],3)
    for frame in (base,candidate):
        if frame.empty or frame.duplicated(KEYS).any():raise ValueError('empty/duplicate scenario keys')
        if not np.isfinite(frame[columns].to_numpy()).all():raise ValueError('nonfinite climate feature')
        if not frame.groupby(GRID).harvest_year.agg(set).map(lambda x:x==set(range(2042,2050))).all():
            raise ValueError('scenario years incomplete')
    a=base.set_index(KEYS).sort_index();b=candidate.set_index(KEYS).sort_index()
    if not a.index.equals(b.index):raise ValueError('scenario supports differ')
    means=(b[columns]-a[columns]).groupby(GRID).mean()
    return dict(paired_crop_years=len(a),cells=len(means),features={c:dict(
        equal_cell_mean=float(means[c].mean()),cell_p10=float(means[c].quantile(.1)),
        cell_p90=float(means[c].quantile(.9)),cells_positive=int(means[c].gt(0).sum()),
        cells_negative=int(means[c].lt(0).sum()),cells_zero=int(means[c].eq(0).sum())) for c in columns})

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    if args.out.exists():raise ValueError('new output receipt required')
    mapping=[('mai',29,'two_crop_heat_real_20260908','ssp585_maize_heat29_20260908'),
             ('soy',30,'soy_heat30_real_20260908','ssp585_soy_heat30_20260908')]
    result=dict(role='matched_SSP585_minus_SSP126_climate_inputs_only',
        causal_or_scc_result=False,crop_yield_estimated=False,
        geographic_scope='39.25/39.75N only; not global or country-representative',
        dispersion_is_not_confidence_interval=True,years=list(range(2042,2050)),comparisons=[],
        protocol_sha256=sha256(ROOT/'PAIRED_HEAT_CLIMATE_PROTOCOL_20260908.md'),
        code_sha256=sha256(Path(__file__)))
    for crop,threshold,base_dir,candidate_dir in mapping:
        tables=[];sources=[];weights=[]
        for scenario,directory in [('ssp126',base_dir),('ssp585',candidate_dir)]:
            path=ROOT/'data/interim'/directory/'receipt.json';r=json.loads(path.read_text())
            if r['status'] not in ('joint_climate_inputs_validated','two_crop_joint_climate_inputs_validated'):
                raise ValueError('unvalidated joint inputs')
            if r.get('threshold_c',29)!=threshold:raise ValueError('crop heat threshold differs')
            products=[p for p in r['products'] if p['crop']==crop]
            if len(products)!=1:raise ValueError('crop missing/duplicate')
            product=products[0]
            if (product['esm'],product['member'],product['scenario'])!=('GFDL-ESM4','r1i1p1f1',scenario):
                raise ValueError('scenario/model/member mismatch')
            frame=pd.read_parquet(checked(product))
            if set(frame.crop)!={crop} or set(frame.lat)!={39.25,39.75}:raise ValueError('spatial/crop scope differs')
            tables.append(frame);weights.append(r['weight_sha256'])
            sources.append(dict(receipt_path=str(path.relative_to(ROOT)),receipt_sha256=sha256(path),
                product_path=product['path'],product_sha256=product['sha256']))
        if len(set(weights))!=1:raise ValueError('irrigation weights differ')
        result['comparisons'].append(dict(crop=crop,threshold_c=threshold,source_receipts=sources,
            weight_sha256=weights[0],**compare(*tables,threshold)))
    args.out.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print([(r['crop'],r['paired_crop_years'],r['features']['precip_mm']['equal_cell_mean']) for r in result['comparisons']])

if __name__=='__main__':main()
