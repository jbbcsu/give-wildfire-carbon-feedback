"""Exact, fully observed crop support; never imputes static noncrop missing data."""
import hashlib
import tomllib
import numpy as np
import pandas as pd
import xarray as xr
from align_cutout_calendar import align_calendar
from build_crop_year_features import normalize_precip,normalize_temperature
from climate_inputs import validate_daily_units
from heat_cutout_dates import registered_years,date_contract
from summarize_contiguous_climate_contrasts import ROOT,sha256

IDS={'pr':'0cf6af1f-14c6-4625-b89a-68352da58765','tas':'efcda79c-cf3f-428f-9ca2-45481cd13631',
     'tasmax':'db109b0d-5f70-489d-9ae9-36a0c343279f'}
AMENDMENT='FACTUAL_COUNTERCLIM_DOMAIN_AMENDMENT_20260908.md'


def validate_static_domain(values,mask):
    values=np.asarray(values);mask=np.asarray(mask)
    if mask.dtype!=bool or values.ndim!=3 or values.shape[1:]!=mask.shape or not mask.any():
        raise ValueError('invalid crop-domain dimensions')
    if not np.isfinite(values[:,mask]).all():raise ValueError('missing or infinite crop weather')
    if not np.isnan(values[:,~mask]).all():raise ValueError('noncrop domain is not the registered static missing mask')
    return int(np.isnan(values).sum())


def validate_counterclim(path,config):
    s=config['specifiers'];var=s['climate_variable'];a,b=registered_years(config)
    identity=dict(simulation_round='ISIMIP3a',product='InputData',region='global',time_step='daily',
        climate_forcing='gswp3-w5e5',climate_scenario='counterclim')
    if any(s.get(k)!=v for k,v in identity.items()) or config['dataset_id']!=IDS.get(var) or config['dataset_version']!='20220506':
        raise ValueError('crop-domain exception is restricted to registered counterclim sources')
    first,last,count=date_contract(a,b);manifest_path=ROOT/'data/provenance/isimip_crop_calendar_2015soc.toml'
    manifest=tomllib.loads(manifest_path.read_text());mask=None;calendars={}
    with xr.open_dataset(path,engine='h5netcdf') as ds:
        if var not in ds or ds[var].dims!=('time','lat','lon'):raise ValueError('counterclim dimensions differ')
        if not np.array_equal(np.sort(ds.lat),[39.25,39.75]) or not np.array_equal(np.sort(ds.lon),np.arange(-179.75,180.,.5)):
            raise ValueError('counterclim exact grid differs')
        dates=pd.DatetimeIndex(ds.time.values);calendar=str(ds.time.encoding.get('calendar','standard'))
        if calendar not in ('standard','gregorian','proleptic_gregorian') or not dates.normalize().equals(pd.date_range(first,last)) or not np.all(np.diff(dates.values)==np.timedelta64(1,'D')):
            raise ValueError('counterclim exact daily dates differ')
        units=str(ds[var].attrs.get('units',''));validate_daily_units(var,units)
        for crop in ('mai','soy'):
            for regime in ('noirr','firr'):
                name=f'ggcmi-crop-calendar-phase3_2015soc_{crop}_{regime}.nc';cp=ROOT/'data/raw/crop_calendars'/name
                records=[r for r in manifest['files'] if r['name']==name]
                if len(records)!=1 or hashlib.sha512(cp.read_bytes()).hexdigest()!=records[0]['sha512']:
                    raise ValueError('crop-domain calendar hash differs')
                calendars[name]=records[0]['sha512']
                with xr.open_dataset(cp,engine='h5netcdf',decode_timedelta=False) as cal:
                    c=align_calendar(cal,ds);p=c.planting_day.values;m=c.maturity_day.values
                    current=np.isfinite(p)&np.isfinite(m)&(p>=1)&(m>=1)
                if int(current.sum())!=686 or current.size!=1440:raise ValueError('registered crop support differs')
                if mask is not None and not np.array_equal(mask,current):raise ValueError('calendar masks differ')
                mask=current
        missing=0;minimum=np.inf;maximum=-np.inf;normalizer=normalize_precip if var=='pr' else normalize_temperature
        for start in range(0,len(dates),365):
            values=normalizer(ds[var].isel(time=slice(start,start+365)).values,units)
            missing+=validate_static_domain(values,mask);crop_values=values[:,mask]
            if var=='pr' and (crop_values<0).any():raise ValueError('negative crop precipitation; no clipping')
            minimum=min(minimum,float(crop_values.min()));maximum=max(maximum,float(crop_values.max()))
        extrema=({'minimum_mm_day':minimum,'maximum_mm_day':maximum} if var=='pr' else {'minimum_c':minimum,'maximum_c':maximum})
        return dict(variable=var,days=count,first_date=first,last_date=last,latitudes=ds.lat.values.tolist(),
            longitude_count=len(ds.lon),calendar=calendar,source_units=units,**extrema,missing_values=missing,
            crop_missing_values=0,crop_cells=686,static_missing_noncrop_cells=754,imputation_performed=False,
            validation_domain='exact_four_calendar_crop_support',calendar_hashes=calendars,
            calendar_manifest_sha256=sha256(manifest_path),domain_amendment_sha256=sha256(ROOT/AMENDMENT),
            all_parent_payload_bytes_verified=False)
