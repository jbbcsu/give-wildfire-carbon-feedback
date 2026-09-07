"""Real daily heat measurement pilot; no yield response or SCC calculation."""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from build_county_nclimgrid_feature_smoke import (
    load_daily_cells, validate_polygon_weights, STAGE_FRACTIONS,
)
from us_national_nclimgrid_common import validate_acquired_months, sha256_file

ROOT=Path(__file__).resolve().parents[2]


def heat_metrics(values, weights, threshold):
    values=np.asarray(values,dtype=float)
    weights=np.asarray(weights,dtype=float)
    if values.ndim!=2 or values.shape[1]!=len(weights) or not len(values):
        raise ValueError('invalid day/cell dimensions')
    if not np.isfinite(values).all() or not np.isfinite(weights).all():
        raise ValueError('nonfinite input')
    if np.any(weights<0) or not np.isclose(weights.sum(),1,rtol=0,atol=1e-10):
        raise ValueError('invalid weights')
    cell_degree=np.maximum(values-threshold,0).sum(axis=0)
    cell_days=(values>threshold).sum(axis=0)
    average=np.einsum('dc,c->d',values,weights,optimize=False)
    primary=float(np.dot(cell_degree,weights))
    alternative=float(np.maximum(average-threshold,0).sum())
    if alternative > primary + 1e-9:
        raise ValueError('convexity check failed')
    return dict(cell_first_tmax_exceedance_c_days=primary,
                cell_first_above_threshold_days=float(np.dot(cell_days,weights)),
                county_mean_first_exceedance_c_days=alternative,
                spatial_aggregation_gap_c_days=primary-alternative,
                tmax_mean_c=float(average.mean()))


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--out',required=True,type=Path)
    args=parser.parse_args()
    if args.out.exists():
        raise ValueError('output already exists')
    weight_path=ROOT/'data/interim/us_county/cuming_ne_nclimgrid_polygon_weights.parquet'
    panel_path=ROOT/'data/interim/us_county/cuming_ne_1981_nass_nclimgrid_feature_smoke.parquet'
    weights=validate_polygon_weights(pd.read_parquet(weight_path))
    panel=pd.read_parquet(panel_path)
    if set(panel.county_geoid.astype(str))!={'31039'} or set(panel.harvest_year)!={1981}:
        raise ValueError('pilot support changed')
    paths,identities=validate_acquired_months([(1981,m) for m in range(5,11)],revalidate_netcdf=False)
    dates,climate=load_daily_cells(paths,weights)
    records=[]
    for row in panel.itertuples(index=False):
        start,end=pd.Timestamp(row.season_start),pd.Timestamp(row.season_end)
        use=(dates>=start)&(dates<=end)
        values=climate['tmax'][use]
        n=len(values)
        if n!=(end-start).days+1:
            raise ValueError('incomplete crop season')
        bounds=[int(np.floor(f*n)) for f in STAGE_FRACTIONS]
        for threshold in [29,30]:
            stage=[]
            for i,(left,right) in enumerate(zip(bounds,bounds[1:]),start=1):
                result=heat_metrics(values[left:right],weights.spatial_weight,threshold)
                if not np.isclose(result['tmax_mean_c'],getattr(row,f'stage{i}_tmax_mean_c'),rtol=0,atol=1e-8):
                    raise ValueError('stage mean differs from original feature panel')
                if right-left!=getattr(row,f'stage{i}_days'):
                    raise ValueError('stage day count differs')
                stage.append(dict(stage=i,days=right-left,**result))
            season=heat_metrics(values,weights.spatial_weight,threshold)
            for key in ['cell_first_tmax_exceedance_c_days','cell_first_above_threshold_days',
                        'county_mean_first_exceedance_c_days']:
                if not np.isclose(sum(s[key] for s in stage),season[key],rtol=0,atol=1e-8):
                    raise ValueError('stage/season reconciliation failed')
            records.append(dict(county_geoid='31039',crop=row.outcome_crop,
                practice=row.irrigation_practice,harvest_year=1981,threshold_c=threshold,
                season_start=str(start.date()),season_end=str(end.date()),season=season,stages=stage))
    result=dict(role='daily_heat_measurement_pilot_not_response',causal_or_scc_result=False,
                code_sha256=sha256_file(Path(__file__)),
                protocol_sha256=sha256_file(ROOT/'us_county_validation/US_DAILY_HEAT_PILOT_PROTOCOL_20260907.md'),
                weights_sha256=sha256_file(weight_path),panel_sha256=sha256_file(panel_path),
                climate_input_receipts=identities,records=records)
    temporary=args.out.with_suffix('.partial')
    temporary.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    temporary.replace(args.out)
    print('Completed eight crop/practice/threshold records; no response estimated')


if __name__=='__main__':
    main()
