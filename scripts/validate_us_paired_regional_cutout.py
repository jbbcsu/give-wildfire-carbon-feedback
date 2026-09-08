"""Source-bound regional daily validation, distinct from old strip validators."""
import hashlib
import tomllib
import numpy as np
import pandas as pd
import xarray as xr
from align_cutout_calendar import align_calendar
from climate_inputs import validate_daily_units
from heat_cutout_dates import registered_years, date_contract
from validate_counterclim_crop_domain import IDS, validate_static_domain
from prepare_us_paired_regional_cutout import parent_and_payload, BANDS, PROTOCOL
from summarize_contiguous_climate_contrasts import ROOT, sha256


def validate(path, config):
    parent, _ = parent_and_payload(config)
    variable = parent['specifiers']['climate_variable']
    scenario = parent['specifiers']['climate_scenario']
    if variable not in ('pr', 'tas', 'tasmax'):
        raise ValueError('unregistered daily variable')
    if scenario == 'counterclim' and (parent['dataset_id'] != IDS[variable] or parent['dataset_version'] != '20220506'):
        raise ValueError('counterclim identity differs')
    west, east, south, north = BANDS[config['band']]
    first, last, count = date_contract(*registered_years(parent))
    manifest_path = ROOT/'data/provenance/isimip_crop_calendar_2015soc.toml'
    manifest = tomllib.loads(manifest_path.read_text())
    with xr.open_dataset(path, engine='h5netcdf') as ds:
        if ds[variable].dims != ('time', 'lat', 'lon') or not np.array_equal(ds.lat.values, np.arange(north-.25, south, -.5)) or not np.array_equal(ds.lon.values, np.arange(west+.25, east, .5)):
            raise ValueError('regional daily grid differs')
        dates = pd.DatetimeIndex(ds.time.values)
        if not dates.equals(pd.date_range(first, last)):
            raise ValueError('regional exact daily chronology differs')
        calendar = str(ds.time.encoding.get('calendar', 'standard'))
        if calendar not in ('standard', 'gregorian', 'proleptic_gregorian'):
            raise ValueError('regional calendar differs')
        units = str(ds[variable].attrs.get('units', ''))
        validate_daily_units(variable, units)
        if units != ('kg m-2 s-1' if variable == 'pr' else 'K'):
            raise ValueError('regional conversion units differ')
        mask = np.ones((16, 70), dtype=bool)
        calendars = {}
        if scenario == 'counterclim':
            mask = None
            for crop in ('mai', 'soy'):
                for regime in ('noirr', 'firr'):
                    name = f'ggcmi-crop-calendar-phase3_2015soc_{crop}_{regime}.nc'
                    cp = ROOT/'data/raw/crop_calendars'/name
                    matches = [m for m in manifest['files'] if m['name'] == name]
                    if len(matches) != 1 or hashlib.sha512(cp.read_bytes()).hexdigest() != matches[0]['sha512']:
                        raise ValueError('regional calendar source changed')
                    calendars[name] = matches[0]['sha512']
                    with xr.open_dataset(cp, engine='h5netcdf', decode_timedelta=False) as cal:
                        aligned = align_calendar(cal, ds)
                        p, m = aligned.planting_day.values, aligned.maturity_day.values
                        candidate = np.isfinite(p)&np.isfinite(m)&(p >= 1)&(m >= 1)
                    if mask is not None and not np.array_equal(mask, candidate):
                        raise ValueError('four regional source-domain masks differ')
                    mask = candidate
        missing, minimum, maximum = 0, np.inf, -np.inf
        for start in range(0, len(dates), 365):
            values = ds[variable].isel(time=slice(start, start+365)).values.astype(float)
            values = values*86400 if variable == 'pr' else values-273.15
            if scenario == 'counterclim':
                missing += validate_static_domain(values, mask)
            elif not np.isfinite(values).all():
                raise ValueError('nonfinite factual regional weather')
            selected = values[:, mask]
            if variable == 'pr' and (selected < 0).any():
                raise ValueError('negative precipitation')
            minimum, maximum = min(minimum, float(selected.min())), max(maximum, float(selected.max()))
    return dict(variable=variable, scenario=scenario, band=config['band'], bbox=BANDS[config['band']],
        days=count, first_date=first, last_date=last, calendar=calendar, source_units=units,
        latitude_count=16, longitude_count=70, finite_cells=int(mask.sum()), missing_values=missing,
        missing_domain_static=True, valid_domain_missing_values=0, mask_sha256=hashlib.sha256(mask.tobytes()).hexdigest(),
        minimum=minimum, maximum=maximum, normalized_units='mm/day' if variable == 'pr' else 'C',
        calendar_hashes=calendars, calendar_manifest_sha256=sha256(manifest_path),
        protocol_sha256=sha256(ROOT/PROTOCOL), imputation=False)
