"""Source-bound regional extension of NASS-calendar climate feature inputs."""
import argparse
import gc
import json
from pathlib import Path

import numpy as np
import pandas as pd
from pyproj import CRS, Transformer
import shapefile
from shapely.geometry import box, shape
from shapely.ops import transform, unary_union
import xarray as xr

from build_us_paired_county_climate import county_weights, features, validate_dates, base
from inventory_us_paired_climate_overlap import PAIR, SHAPEFILE, coverage, identity
from prepare_us_paired_regional_cutout import BANDS, parent_and_payload
from summarize_contiguous_climate_contrasts import ROOT, checked, sha256

PROTOCOL = 'US_REGIONAL_COUNTY_FEATURE_PROTOCOL_20260908.md'
BAND_ORDER = ['north', 'central', 'south']


def candidate_cells(geometry, centers):
    x0, y0, x1, y1 = geometry.bounds
    a = np.asarray(centers)
    return np.flatnonzero((a[:, 1]+.25 > x0)&(a[:, 1]-.25 < x1)&
                         (a[:, 0]+.25 > y0)&(a[:, 0]-.25 < y1)).tolist()


def regional_sources():
    records = {}
    masks = {}
    centers = []
    for band in BAND_ORDER:
        west, east, south, north = BANDS[band]
        for scenario in ('obsclim', 'counterclim'):
            for var in ('pr', 'tas', 'tasmax'):
                for first in (1981, 1991, 2001):
                    config_path = ROOT/f'config/isimip3a_us_{band}_{scenario}_{var}_{first}_20260908.json'
                    config = json.loads(config_path.read_text())
                    parent, _ = parent_and_payload(config)
                    directory = ROOT/f'data/interim/us_{band}_{scenario}_{var}_{first}_20260908'
                    receipt_path = directory/'receipt.json'
                    if not receipt_path.exists() or (directory/'failure.json').exists():
                        raise ValueError('all54regional acquisitions required: '+str(directory))
                    receipt = json.loads(receipt_path.read_text())
                    if receipt['status'] != 'regional_paired_climate_content_validated' or receipt['config_sha256'] != sha256(config_path) or receipt['source_contract'] != parent:
                        raise ValueError('regional acquisition/source identity differs')
                    if receipt['helper_hashes']['validate_us_paired_regional_cutout.py'] != sha256(ROOT/'scripts/validate_us_paired_regional_cutout.py'):
                        raise ValueError('regional validator implementation changed')
                    content = receipt['content_validation']
                    if (content['band'], content['scenario'], content['variable'], content['first_date']) != (band, scenario, var, f'{first}-01-01'):
                        raise ValueError('regional validation identity differs')
                    if content['valid_domain_missing_values'] != 0:
                        raise ValueError('regional finite domain not fully validated')
                    if scenario == 'counterclim':
                        if band in masks and masks[band] != content['mask_sha256']:
                            raise ValueError('regional masks differ by variable or decade')
                        masks[band] = content['mask_sha256']
                    records[(band, scenario, var, first)] = dict(receipt=identity(receipt_path),
                        climate_path=str((directory/f'{var}_cutout.nc').relative_to(ROOT)), climate_sha256=receipt['climate_sha256'])
        centers.extend((float(a), float(b)) for a in np.arange(north-.25, south, -.5) for b in np.arange(west+.25, east, .5))
    if len(centers) != 3360 or len(set(centers)) != 3360:
        raise ValueError('regional grid partition differs')
    valid = []
    import hashlib
    for band in BAND_ORDER:
        record = records[(band, 'counterclim', 'pr', 1981)]
        path = ROOT/record['climate_path']
        if sha256(path) != record['climate_sha256']:
            raise ValueError('regional mask payload changed')
        with xr.open_dataset(path, engine='h5netcdf') as ds:
            mask = np.isfinite(ds.pr.isel(time=0).transpose('lat', 'lon').values)
        if hashlib.sha256(mask.tobytes()).hexdigest() != masks[band]:
            raise ValueError('regional mask snapshot differs from all-day validation')
        valid.extend(mask.ravel().tolist())
    return records, centers, np.asarray(valid, dtype=bool)


def load_selected(records, centers, cells, scenario, first):
    values, dates = {}, None
    # The concatenation order is fixed north,central,south and row-major within each.
    for var in ('pr', 'tas', 'tasmax'):
        parts = []
        for band_no, band in enumerate(BAND_ORDER):
            local = [c-band_no*1120 for c in cells if band_no*1120 <= c < (band_no+1)*1120]
            record = records[(band, scenario, var, first)]
            path = ROOT/record['climate_path']
            if sha256(path) != record['climate_sha256']:
                raise ValueError('regional daily payload changed')
            with xr.open_dataset(path, engine='h5netcdf') as ds:
                west, east, south, north = BANDS[band]
                if not np.array_equal(ds.lat.values, np.arange(north-.25, south, -.5)) or not np.array_equal(ds.lon.values, np.arange(west+.25, east, .5)):
                    raise ValueError('regional daily coordinates changed')
                observed_dates = pd.DatetimeIndex(ds.time.values)
                validate_dates(observed_dates, f'{first}-01-01', f'{first+9}-12-31')
                if dates is not None and not dates.equals(observed_dates):
                    raise ValueError('regional daily axes do not pair')
                dates = observed_dates
                if ds[var].attrs['units'] != ('kg m-2 s-1' if var == 'pr' else 'K'):
                    raise ValueError('regional daily units changed')
                if local:
                    local = np.array(local)
                    array = ds[var].isel(lat=xr.DataArray(local//70, dims='cell'), lon=xr.DataArray(local%70, dims='cell')).transpose('time', 'cell').values.astype(float)
                    parts.append(array)
        array = np.concatenate(parts, axis=1)
        values[var] = array*86400 if var == 'pr' else array-273.15
        del parts, array
        if values[var].shape != (len(dates), len(cells)) or not np.isfinite(values[var]).all():
            raise ValueError('regional selected-cell shape/finite coverage differs')
    return dates, values


def pilot_parity(table, reference):
    if table.duplicated(PAIR).any() or reference.duplicated(PAIR).any():
        raise ValueError('pilot parity duplicate keys')
    a = reference.set_index(PAIR).sort_index()
    b = table.set_index(PAIR).sort_index()
    if not a.index.isin(b.index).all():
        raise ValueError('pilot parity keys absent')
    b = b.loc[a.index]
    numeric = [c for c in a.columns if c not in ('scenario', 'season_start', 'season_end')]
    pd.testing.assert_frame_equal(a[['scenario', 'season_start', 'season_end']], b[['scenario', 'season_start', 'season_end']], check_dtype=False)
    if not np.array_equal(a.zero_precipitation_season, b.zero_precipitation_season):
        raise ValueError('pilot zero-rain flags differ')
    residuals = {}
    for c in numeric:
        if not np.isfinite(a[c]).all() or not np.isfinite(b[c]).all() or not np.allclose(a[c], b[c], atol=1e-8, rtol=1e-10):
            raise ValueError('regional pilot numerical parity failed: '+c)
        residuals[c] = float(np.max(np.abs(a[c]-b[c])))
    return dict(rows=len(a), atol=1e-8, rtol=1e-10, maximum_absolute_residual_by_feature=residuals)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--outdir', type=Path, required=True)
    args = p.parse_args()
    if args.outdir.exists():
        raise ValueError('fresh regional feature directory required')
    sources, centers, valid = regional_sources()
    inv_path = ROOT/'data/interim/us_paired_overlap_20260908/result.json'
    inv = json.loads(inv_path.read_text())
    for record in inv['input_sources']+inv['tiger_components']:
        checked(record)
    frame, source = base.validate_panel(base.load_config(base.DEFAULT_CONFIG))
    if source != inv['association_input']:
        raise ValueError('validated NASS/weather source differs')
    frame = frame.loc[frame.harvest_year.between(1982, 2010)].copy()
    meta = PAIR+['season_start', 'season_end', 'season_days', 'calendar_source_id', 'calendar_role',
                 'calendar_vintage', 'calendar_boundary_rule', 'stage_definition']
    seasons = frame[meta].drop_duplicates()
    if seasons.duplicated(PAIR).any() or len(seasons) != 10402:
        raise ValueError('registered NASS overlap/calendar pairing differs')
    for c in ('season_start', 'season_end'):
        seasons[c] = pd.to_datetime(seasons[c]).dt.normalize()
    if not ((seasons.season_end-seasons.season_start).dt.days+1).eq(seasons.season_days).all() or not seasons.season_start.dt.year.eq(seasons.harvest_year).all() or not seasons.season_end.dt.year.eq(seasons.harvest_year).all():
        raise ValueError('NASS season chronology changed')
    if not seasons.calendar_source_id.eq('usda_nass_field_crops_usual_dates_2010').all() or not seasons.calendar_role.eq('fixed_primary').all():
        raise ValueError('NASS calendar lineage changed')
    domain = unary_union([box(b-.25, a-.25, b+.25, a+.25) for (a, b), keep in zip(centers, valid) if keep])
    shp = ROOT/SHAPEFILE
    to_geo = Transformer.from_crs(CRS.from_wkt(shp.with_suffix('.prj').read_text()), 4326, always_xy=True)
    to_area = Transformer.from_crs(4326, 5070, always_xy=True)
    required = set(seasons.county_geoid)
    coverage_rows, weights, areas = [], {}, {}
    with shapefile.Reader(str(shp)) as reader:
        names = [f[0] for f in reader.fields[1:]]
        for rec in reader.iterRecords():
            geoid = str(rec[names.index('GEOID')])
            if geoid not in required:
                continue
            geometry = transform(to_geo.transform, shape(reader.shape(rec.oid).__geo_interface__))
            status = coverage(geometry, domain)
            coverage_rows.append(dict(county_geoid=geoid, finite_climate_coverage=status))
            if status != 'full':
                continue
            selected = candidate_cells(geometry, centers)
            local, area = county_weights(geometry, [centers[i] for i in selected], valid[selected], to_area.transform)
            weights[geoid] = [(selected[i], weight) for i, weight in local]
            declared = int(rec[names.index('ALAND')])+int(rec[names.index('AWATER')])
            if declared <= 0 or abs(area['projected_partition_area_m2']/declared-1) > .03:
                raise ValueError('regional declared county area audit failed')
            area.update(declared_area_m2=declared, declared_relative_difference=area['projected_partition_area_m2']/declared-1)
            areas[geoid] = area
    if {r['county_geoid'] for r in coverage_rows} != required or len(coverage_rows) != len(required):
        raise ValueError('regional county geography incomplete')
    all_seasons = seasons.merge(pd.DataFrame(coverage_rows), on='county_geoid', validate='many_to_one')
    seasons = all_seasons.loc[all_seasons.finite_climate_coverage == 'full'].copy()
    if seasons.empty:
        raise ValueError('no wholly covered finite-weather counties')
    cells = sorted({i for records in weights.values() for i, _ in records})
    index = {c: i for i, c in enumerate(cells)}
    args.outdir.mkdir(parents=True)
    products, parities = [], []
    pilot_path = ROOT/'data/interim/us_paired_county_climate_20260908/receipt.json'
    pilot = json.loads(pilot_path.read_text())
    if pilot['status'] != 'us_paired_county_climate_inputs_validated':
        raise ValueError('pilot comparison reference not validated')
    for scenario in ('obsclim', 'counterclim'):
        rows = []
        for first in (1981, 1991, 2001):
            dates, values = load_selected(sources, centers, cells, scenario, first)
            for row in seasons.loc[seasons.harvest_year.between(first, first+9)].itertuples(index=False):
                where = (dates >= row.season_start)&(dates <= row.season_end)
                validate_dates(dates[where], row.season_start, row.season_end)
                columns = [index[c] for c, _ in weights[row.county_geoid]]
                w = [weight for _, weight in weights[row.county_geoid]]
                selection = np.ix_(np.flatnonzero(where), columns)
                feat = features(*(values[var][selection] for var in ('pr', 'tas', 'tasmax')), w)
                rows.append({**{k: getattr(row, k) for k in PAIR}, 'scenario': scenario,
                    'season_start': row.season_start, 'season_end': row.season_end, 'season_days': int(row.season_days), **feat})
            del values
            gc.collect()
        table = pd.DataFrame(rows).sort_values(PAIR).reset_index(drop=True)
        if len(table) != len(seasons) or table.duplicated(PAIR).any():
            raise ValueError('regional climate keys differ')
        matches = [p for p in pilot['products'] if p['scenario'] == scenario]
        if len(matches) != 1:
            raise ValueError('pilot source count differs')
        parities.append(dict(scenario=scenario, source=matches[0],
                             comparison=pilot_parity(table, pd.read_parquet(checked(matches[0])))))
        path = args.outdir/f'{scenario}_county_climate.parquet'
        table.to_parquet(path, index=False)
        products.append({**identity(path.resolve()), 'scenario': scenario, 'rows': len(table)})
    result = dict(status='us_regional_county_climate_inputs_validated', input=source, inventory=identity(inv_path),
        protocol_sha256=sha256(ROOT/PROTOCOL), code_sha256=sha256(Path(__file__)),
        feature_helper_sha256=sha256(ROOT/'scripts/build_us_paired_county_climate.py'),
        crop_yield_estimated=False, causal_or_scc_result=False, selected_daily_cells=len(cells),
        observed_county_years_before_climate_coverage=len(all_seasons), retained_county_years=len(seasons),
        coverage=coverage_rows, area_audits=areas, products=products, pilot_parity=parities,
        pilot_receipt=identity(pilot_path),
        county_weights=[dict(county_geoid=g, grid_cell=i, lat=centers[i][0], lon=centers[i][1], spatial_weight=w)
                        for g, records in weights.items() for i, w in records],
        sources=[dict(band=k[0], scenario=k[1], variable=k[2], first_year=k[3], **v) for k, v in sources.items()],
        coverage_counts=[dict(crop=crop, status=status, counties=int(group.county_geoid.nunique()), county_years=len(group))
                         for (crop, status), group in all_seasons.groupby(['outcome_crop', 'finite_climate_coverage'])])
    (args.outdir/'receipt.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print('Regional county climate validated:', result['coverage_counts'], '; daily cells:', len(cells))


if __name__ == '__main__':
    main()
