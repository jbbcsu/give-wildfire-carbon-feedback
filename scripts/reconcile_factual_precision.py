"""Independent raw-daily reduction audit; never loosens the parity tolerance."""
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import xarray as xr
from build_crop_year_features import normalize_precip,date_from_doy
from build_future_weighted_precipitation import join_season_stages,weighted_climate,FEATURES,ZERO,WEIGHT_HASH
from compare_factual_counterclim import load_product,observed,factual_parity,KEYS
from summarize_contiguous_climate_contrasts import ROOT,checked,sha256


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);args=p.parse_args()
    if args.out.exists():raise ValueError('new precision audit required')
    arrays=[];times=[];sources=[];latitude=None;longitude=None
    for year in (1981,1991,2001):
        d=ROOT/f'data/interim/obsclim_pr_{year}_20260908';rp=d/'receipt.json';r=json.loads(rp.read_text());file=d/'pr_cutout.nc'
        if r['status']!='climate_content_validated' or sha256(file)!=r['climate_sha256']:raise ValueError('factual source differs')
        with xr.open_dataset(file,engine='h5netcdf') as ds:
            if latitude is not None and not all(np.array_equal(a,ds[k]) for a,k in ((latitude,'lat'),(longitude,'lon'))):raise ValueError('daily grid differs')
            latitude=ds.lat.values;longitude=ds.lon.values;arrays.append(normalize_precip(ds.pr.values,ds.pr.attrs['units']));times.extend(ds.time.values)
        sources.append(dict(path=str(rp.relative_to(ROOT)),sha256=sha256(rp),daily_sha256=sha256(file)))
    rain=np.concatenate(arrays);del arrays
    if rain.dtype!=np.float32:raise ValueError('legacy reproduction requires the original float32 daily representation')
    dates=pd.DatetimeIndex(times).normalize();lats={float(x):i for i,x in enumerate(latitude)};lons={float(x):i for i,x in enumerate(longitude)}
    weights=pq.read_table(checked(dict(path='data/interim/mirca_os_v2/irrigation_shares_2000.parquet',sha256=WEIGHT_HASH)),
        filters=[('lat','in',[39.25,39.75])],use_threads=False).to_pandas()
    result=dict(role='legacy_float32_factual_precision_reproduction',status='started',tolerance_changed=False,
        legacy_years=[1982,1989],raw_daily_sources=sources,code_sha256=sha256(Path(__file__)),
        protocol_sha256=sha256(ROOT/'FACTUAL_PARITY_PRECISION_RECONCILIATION_20260908.md'),comparisons=[])
    for crop,label,threshold in [('mai','maize',29),('soy','soy',30)]:
        new,r,new_source=load_product(crop,'obsclim');old,old_sources=observed(crop,label,threshold)
        panels=[];audits=[]
        allocation_path=ROOT/f'outputs/irrigation_basis/{label}_mirca2000_1982_1989_distribution_candidate_audit.json'
        allocation=json.loads(allocation_path.read_text())
        for regime in ('noirr','firr'):
            d=ROOT/f'data/interim/obsclim_{crop}_joint_20260908'/regime
            season_path=d/'season.parquet';stage_path=d/'stages.parquet'
            for path in (season_path,stage_path):
                if sha256(path)!=r['artifacts'][str(path.relative_to(d.parent))]:raise ValueError('factual primitives changed')
            season=pd.read_parquet(season_path);stages=pd.read_parquet(stage_path)
            sources_old=[dict(path=p,sha256=h) for p,h in zip(allocation['input_panel_files'],allocation['input_panel_sha256']) if f'_{regime}_' in p]
            if len(sources_old)!=1:raise ValueError('nonunique retained regime source')
            old_path=checked(sources_old[0]);parts=[]
            for batch in pq.ParquetFile(old_path).iter_batches(batch_size=8192,columns=KEYS+['precip_mm','stage1_precip_mm','stage2_precip_mm','stage3_precip_mm'],use_threads=False):
                piece=batch.to_pandas();part=piece.loc[piece.lat.isin([39.25,39.75])&piece.harvest_year.between(1982,1989)]
                if len(part):parts.append(part)
            original=pd.concat(parts,ignore_index=True).set_index(KEYS)
            if original.index.duplicated().any():raise ValueError('duplicate retained primitive keys')
            legacy_totals={};current_totals={};legacy_stages={};current_stages={}
            for row in season.itertuples(index=False):
                start=pd.Timestamp(date_from_doy(row.plant_year,row.plant_doy));end=pd.Timestamp(date_from_doy(row.harvest_year,row.maturity_doy))
                i0=dates.get_loc(start);i1=dates.get_loc(end)+1
                daily=np.ascontiguousarray(rain[i0:i1,lats[row.lat],lons[row.lon]])
                if len(daily)!=row.season_days or not np.isfinite(daily).all():raise ValueError('raw crop window differs')
                key=tuple(getattr(row,k) for k in KEYS)
                current_totals[key]=float(np.sum(daily,dtype=np.float64))
                legacy_totals[key]=float(daily.sum()) if row.harvest_year<=1989 else current_totals[key]
                for stage,(left,right) in enumerate(zip((0.,.3,.7),(.3,.7,1.)),1):
                    v=daily[int(np.floor(left*len(daily))):int(np.floor(right*len(daily)))]
                    current_stages[key+(stage,)]=float(np.sum(v,dtype=np.float64))
                    legacy_stages[key+(stage,)]=float(v.sum()) if row.harvest_year<=1989 else current_stages[key+(stage,)]
            precision_counts={}
            for f,current,legacy,keys in ((season,current_totals,legacy_totals,KEYS),(stages,current_stages,legacy_stages,KEYS+['stage_id'])):
                keylist=list(f[keys].itertuples(index=False,name=None));expected=np.array([current[k] for k in keylist])
                if not np.array_equal(f.precip_mm.to_numpy(),expected):raise ValueError('new float64 primitive is not exactly reproduced')
                verified=[]
                for k in keylist:
                    year=k[KEYS.index('harvest_year')]
                    if year>1989:verified.append(current[k]);continue
                    stage=k[-1] if len(keys)>len(KEYS) else None
                    col=f'stage{stage}_precip_mm' if stage is not None else 'precip_mm'
                    original_key=k[:-1] if stage is not None else k
                    value=float(original.loc[original_key,col]);match32=value==legacy[k];match64=value==current[k]
                    if not (match32 or match64):raise ValueError('retained primitive matches neither exact reduction: '+regime+'/'+col)
                    category='both' if match32 and match64 else ('float32_only' if match32 else 'float64_only')
                    counts=precision_counts.setdefault(col,dict(both=0,float32_only=0,float64_only=0));counts[category]+=1
                    verified.append(value)
                f['precip_mm']=verified
            panels.append(join_season_stages(season,stages))
            audits.append(dict(regime=regime,season_rows=len(season),stage_rows=len(stages),new_float64_primitives_exact=True,
                original_source=sources_old[0],primitive_precision_counts=precision_counts,
                allocation_audit=dict(path=str(allocation_path.relative_to(ROOT)),sha256=sha256(allocation_path))))
        legacy,_=weighted_climate(pd.concat(panels,ignore_index=True),weights.loc[weights.crop.eq(crop)])
        parity=factual_parity(old,legacy,FEATURES+[ZERO])
        # The current daily reconstruction explained the primitive differences;
        # historical-reference acceptance still uses the original numerical gate.
        result['comparisons'].append(dict(crop=crop,new_source=new_source,old_sources=old_sources,
            primitive_audits=audits,legacy_reference_parity=parity,compared_features=FEATURES+[ZERO],
            legacy_basis_sha256=sha256_data(legacy[KEYS+FEATURES+[ZERO]])))
    result['status']='legacy_precision_reproduced_at_original_tolerance'
    args.out.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');print(json.dumps(result,indent=2))


def sha256_data(frame):
    import hashlib
    return hashlib.sha256(pd.util.hash_pandas_object(frame.sort_values(KEYS),index=False).values.tobytes()).hexdigest()


if __name__=='__main__':main()
