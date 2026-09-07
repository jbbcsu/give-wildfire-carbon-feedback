"""Direct, bounded scenario comparisons; not a climate emulator or SCC input."""
import argparse
import gc
import json
from pathlib import Path
import tomllib

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from global_continuous_geographic_cluster_audit import ROOT, sha256

FEATURES = ['tmean_c','precip_mm','wet_days_n','cdd_max_days','rx1day_mm','rx5day_mm',
            'stage1_precip_share','stage2_precip_share','stage3_precip_share',
            'precipitation_timing_centroid','precipitation_concentration_hhi']
SHAPE = FEATURES[6:]
KEYS = ['year','lat','lon_360']
PERIODS = {'midcentury':list(range(2042,2050)), 'endcentury':list(range(2092,2100))}


def validate_values(frame):
    if not np.isfinite(frame[FEATURES].to_numpy()).all():
        raise ValueError('nonfinite climate features')
    if (frame[FEATURES[1:6]] < 0).any().any():
        raise ValueError('negative physical feature')
    if ((frame[SHAPE] < -1e-12) | (frame[SHAPE] > 1+1e-12)).any().any():
        raise ValueError('shape feature outside unit interval')
    shares = frame[SHAPE[:3]].sum(axis=1).to_numpy()
    expected = frame.precip_mm.gt(0).astype(float).to_numpy()
    if not np.allclose(shares,expected,rtol=0,atol=1e-10):
        raise ValueError('stage composition inconsistent with rain state')


def pair_frames(reference, candidate, years):
    for frame in (reference,candidate):
        if frame.duplicated(KEYS).any() or set(frame.year) != set(years):
            raise ValueError('duplicate paired key or incomplete year support')
        if not frame.groupby(['lat','lon_360']).year.nunique().eq(len(years)).all():
            raise ValueError('a cell lacks a required year')
        validate_values(frame)
    left, right = (f.set_index(KEYS).sort_index() for f in (reference,candidate))
    if not left.index.equals(right.index):
        raise ValueError('scenario supports differ')
    return left,right


def describe(reference,candidate,years):
    left,right = pair_frames(reference,candidate,years)
    cell_levels = ['lat','lon_360']
    always_positive = ((left.precip_mm>0)&(right.precip_mm>0)).groupby(level=cell_levels).all()
    lm,rm = (f[FEATURES].groupby(level=cell_levels).mean() for f in (left,right))
    results = {}
    for feature in FEATURES:
        mask = always_positive.to_numpy() if feature in SHAPE else np.ones(len(lm),dtype=bool)
        if not mask.any():
            results[feature] = dict(status='undefined_no_common_positive_rain_cells',cells=0)
            continue
        a,b = lm[feature].to_numpy()[mask],rm[feature].to_numpy()[mask]
        difference = b-a
        result = dict(status='completed',cells=len(a), reference_mean=float(a.mean()),
                      candidate_mean=float(b.mean()), mean_difference=float(difference.mean()),
                      spatial_difference_quantiles=np.quantile(difference,[.1,.5,.9]).tolist())
        if feature=='precip_mm':
            result['percent_change_of_mean'] = float(100*difference.mean()/a.mean()) if a.mean()>0 else None
        results[feature] = result
    return dict(cells=len(lm),years=years,cell_years=len(left),
                positive_rain_shape_cells=int(always_positive.sum()),
                shape_excluded_cells=int((~always_positive).sum()),
                reference_zero_rain_cell_years=int(left.precip_mm.eq(0).sum()),
                candidate_zero_rain_cell_years=int(right.precip_mm.eq(0).sum()),features=results)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out',required=True,type=Path)
    args = parser.parse_args()
    if args.out.exists():
        raise ValueError('output exists')
    config_path = ROOT/'config/isimip3b_physical_link_feature_response_v1.toml'
    config = tomllib.loads(config_path.read_text())
    path = ROOT/config['training_artifact']
    if sha256(path)!=config['training_artifact_sha256']:
        raise ValueError('climate table hash mismatch')
    receipt_path = ROOT/'data/provenance/isimip3b_expanded_fair_training_20260901.json'
    assembly = json.loads(receipt_path.read_text())
    if assembly['output']['sha256']!=sha256(path):
        raise ValueError('assembly receipt disagrees')
    mapping_receipt_path = ROOT/'data/provenance/global_country_proxy_20260907.json'
    mapping_receipt = json.loads(mapping_receipt_path.read_text())
    mapping_path = ROOT/mapping_receipt['output']['path']
    if sha256(mapping_path)!=mapping_receipt['output']['sha256']:
        raise ValueError('country-proxy hash mismatch')
    mapping = {(r['lat'],r['lon_360']):r['country_label'] for r in pq.read_table(mapping_path).to_pylist()}
    output = dict(role='bounded_direct_forcing_scenario_feature_contrasts',
                  causal_or_scc_result=False, marginal_co2_effect=False, global_projection=False,
                  code_sha256=sha256(Path(__file__)),
                  protocol_sha256=sha256(ROOT/'CLIMATE_SCENARIO_CONTRAST_PROTOCOL_20260907.md'),
                  input_sha256=sha256(path),assembly_receipt_sha256=sha256(receipt_path),
                  country_proxy_receipt_sha256=sha256(mapping_receipt_path),
                  crop='mai',irrigation_calendar='noirr',latitudes=[39.25,39.75],comparisons=[])
    columns = ['esm_id','member_id','scenario','year','lat','lon_360','crop','irrigation',
               'feature_family','feature_value','gmst_value_k','gmst_esm_id','gmst_member_id']
    for esm in config['required_esm_ids']:
        pieces = []
        for batch in pq.ParquetFile(path).iter_batches(batch_size=8192,columns=columns,use_threads=False):
            frame=batch.to_pandas()
            mask=frame.esm_id.eq(esm)&frame.year.isin(PERIODS['midcentury']+PERIODS['endcentury'])
            if mask.any():
                pieces.append(frame.loc[mask].copy())
        long=pd.concat(pieces,ignore_index=True)
        del pieces
        if set(long.crop)!={'mai'} or set(long.irrigation)!={'noirr'} or set(long.lat)!={39.25,39.75}:
            raise ValueError('unexpected spatial/crop/regime support')
        if long.member_id.nunique()!=1 or not (long.esm_id==long.gmst_esm_id).all() or not (long.member_id==long.gmst_member_id).all():
            raise ValueError('climate/GMST member identity mismatch')
        member=str(long.member_id.iloc[0])
        if set(long.feature_family)!=set(FEATURES) or long.duplicated(['scenario']+KEYS+['feature_family']).any():
            raise ValueError('feature identity or uniqueness failure')
        gmst_groups=long.groupby(['scenario','year']).gmst_value_k
        if not gmst_groups.nunique().eq(1).all():
            raise ValueError('GMST differs across repeated spatial/feature rows')
        gmst=gmst_groups.first()
        if not np.isfinite(gmst).all():
            raise ValueError('nonfinite GMST')
        wide=long.pivot(index=['scenario']+KEYS,columns='feature_family',values='feature_value').reset_index()
        del long
        wide['country_proxy']=[mapping.get(k) for k in zip(wide.lat,wide.lon_360)]
        for period,years in PERIODS.items():
            for candidate in ('ssp370','ssp585'):
                gmst_delta=float(gmst.loc[candidate].loc[years].mean()-gmst.loc['ssp126'].loc[years].mean())
                for region in ('full_calendar_band','USA_proxy_in_band','CHN_proxy_in_band'):
                    region_mask = np.ones(len(wide),dtype=bool) if region=='full_calendar_band' else wide.country_proxy.eq(region[:3]).to_numpy()
                    selected=wide.loc[region_mask&wide.year.isin(years)]
                    base=selected.loc[selected.scenario=='ssp126']
                    high=selected.loc[selected.scenario==candidate]
                    record=dict(esm_id=esm,member_id=member,period=period,region=region,
                                reference_scenario='ssp126',candidate_scenario=candidate,
                                gmst_mean_difference_k=gmst_delta)
                    if base.empty or high.empty:
                        record.update(status='unavailable_subset')
                    else:
                        record.update(status='completed',**describe(base,high,years))
                    output['comparisons'].append(record)
        del wide
        gc.collect()
        print(esm,'scenario contrasts complete',flush=True)
    temporary=args.out.with_suffix('.partial')
    temporary.write_text(json.dumps(output,indent=2,allow_nan=False)+'\n')
    temporary.replace(args.out)


if __name__=='__main__':
    main()
