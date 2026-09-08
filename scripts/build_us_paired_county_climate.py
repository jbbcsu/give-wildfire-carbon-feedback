"""NASS-calendar county climate inputs from validated paired daily cutouts."""
import argparse
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd
from pyproj import CRS, Transformer
import shapefile
from shapely.geometry import box, shape
from shapely.ops import transform, unary_union
import xarray as xr

from summarize_contiguous_climate_contrasts import ROOT, checked, sha256
from compare_factual_counterclim import load_product
from inventory_us_paired_climate_overlap import PAIR, SHAPEFILE, identity

sys.path.insert(0, str(ROOT / 'us_county_validation/scripts'))
import estimate_us_direct_practice_precipitation_association as base
from build_us_national_nclimgrid_features import _maximum_run_by_cell, _rolling_max_by_cell

PROTOCOL = 'US_PAIRED_COUNTY_CLIMATE_PROTOCOL_20260908.md'
INVENTORY = 'data/interim/us_paired_overlap_20260908/result.json'


def county_weights(geometry, centers, valid, project):
    pieces = []
    source_cells = []
    for i, (lat, lon) in enumerate(centers):
        cell = box(lon-.25, lat-.25, lon+.25, lat+.25)
        part = geometry.intersection(cell)
        if part.is_empty or part.area <= 0:
            continue
        if not valid[i]:
            raise ValueError('county intersects missing climate cell')
        pieces.append((i, float(transform(project, part).area)))
        source_cells.append(cell)
    if not pieces or not unary_union(source_cells).covers(geometry):
        raise ValueError('whole county is not covered by available cells')
    area = sum(value for _, value in pieces)
    original_area = float(transform(project, geometry).area)
    if area <= 0 or original_area <= 0 or abs(area/original_area-1) > .03:
        raise ValueError('projected county partition area differs')
    return [(i, a/area) for i, a in pieces], dict(projected_partition_area_m2=area,
        projected_original_area_m2=original_area, partition_relative_difference=area/original_area-1)


def features(rain, tmean, tmax, weights):
    rain, tmean, tmax, weights = [np.asarray(v, dtype=float) for v in (rain, tmean, tmax, weights)]
    if rain.ndim != 2 or rain.shape != tmean.shape or rain.shape != tmax.shape or rain.shape[0] < 20:
        raise ValueError('invalid daily weather dimensions')
    if weights.shape != (rain.shape[1],) or (weights < 0).any() or not np.isclose(weights.sum(), 1, rtol=0, atol=1e-10):
        raise ValueError('invalid area weights')
    if not all(np.isfinite(v).all() for v in (rain, tmean, tmax, weights)) or (rain < 0).any() or (tmean > tmax+1e-5).any():
        raise ValueError('missing or physically inconsistent daily weather')
    total = rain.sum(axis=0, dtype=np.float64)
    cell = dict(precip_mm=total, cdd_max_days=_maximum_run_by_cell(rain < 1),
                rx5day_mm=_rolling_max_by_cell(rain, 5),
                zero_precipitation_season=(total == 0).astype(float))
    bounds = np.floor(np.array([0, .3, .7, 1])*len(rain)).astype(int)
    stage_amounts, shares = [], []
    for s, (left, right) in enumerate(zip(bounds[:-1], bounds[1:]), 1):
        amount = rain[left:right].sum(axis=0, dtype=np.float64)
        stage_amounts.append(amount)
        share = np.divide(amount, total, out=np.zeros_like(total), where=total > 0)
        shares.append(share)
        cell[f'stage{s}_precip_share'] = share
        cell[f'stage{s}_tmean_c'] = tmean[left:right].mean(axis=0)
        for threshold in (29, 30):
            cell[f'stage{s}_tmax_exceedance_{threshold}c_c_days'] = np.maximum(tmax[left:right]-threshold, 0).sum(axis=0)
            cell[f'stage{s}_tmax_days_gt_{threshold}c'] = (tmax[left:right] > threshold).sum(axis=0).astype(float)
    if not np.allclose(np.sum(stage_amounts, axis=0), total, rtol=0, atol=1e-8):
        raise ValueError('stage precipitation does not sum to season')
    for threshold in (29, 30):
        for stem, season in [('tmax_exceedance', np.maximum(tmax-threshold, 0).sum(axis=0)),
                             ('tmax_days_gt', (tmax > threshold).sum(axis=0))]:
            suffix = f'_{threshold}c' + ('_c_days' if stem == 'tmax_exceedance' else '')
            if not np.allclose(sum(cell[f'stage{s}_{stem}{suffix}'] for s in (1, 2, 3)), season, rtol=0, atol=1e-8):
                raise ValueError('stage heat does not sum to season')
    cell['precipitation_concentration_hhi'] = np.square(shares).sum(axis=0)
    return {name: float(np.sum(value*weights, dtype=np.float64)) for name, value in cell.items()}


def validate_dates(dates, first, last):
    if not dates.equals(pd.date_range(first, last, freq='D')):
        raise ValueError('daily chronology differs')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--outdir', type=Path, required=True)
    args = parser.parse_args()
    if args.outdir.exists():
        raise ValueError('fresh climate directory required')
    inv_path = ROOT / INVENTORY
    inv = json.loads(inv_path.read_text())
    if inv['status'] != 'existing_us_paired_climate_overlap_inventoried' or inv['code_sha256'] != sha256(ROOT / 'scripts/inventory_us_paired_climate_overlap.py'):
        raise ValueError('inventory is not source bound')
    for record in inv['input_sources']+inv['tiger_components']:
        checked(record)
    cfg = base.load_config(base.DEFAULT_CONFIG)
    frame, source = base.validate_panel(cfg)
    if source != inv['association_input']:
        raise ValueError('NASS/weather source changed')
    selected = []
    for entry in inv['comparisons']:
        part = frame.loc[frame.outcome_crop.eq(entry['crop']) & frame.county_geoid.isin(entry['full_climate_county_geoids']) & frame.harvest_year.between(1982, 2010)].copy()
        if len(part) != 2*entry['classifications']['finite_climate_coverage']['full']['crop_county_years']:
            raise ValueError('full-coverage outcome keys changed')
        selected.append(part)
    support = pd.concat(selected, ignore_index=True)
    meta = PAIR + ['season_start', 'season_end', 'season_days', 'calendar_source_id', 'calendar_vintage',
                  'calendar_role', 'calendar_boundary_rule', 'stage_definition']
    seasons = support[meta].drop_duplicates()
    if seasons.duplicated(PAIR).any() or len(seasons) != 573:
        raise ValueError('practice calendar agreement/support differs')
    if not seasons.calendar_source_id.eq('usda_nass_field_crops_usual_dates_2010').all() or not seasons.calendar_role.eq('fixed_primary').all():
        raise ValueError('NASS calendar identity changed')
    for col in ['season_start', 'season_end']:
        seasons[col] = pd.to_datetime(seasons[col]).dt.normalize()
    if not ((seasons.season_end-seasons.season_start).dt.days+1).eq(seasons.season_days).all():
        raise ValueError('season day counts changed')
    if not seasons.season_start.dt.year.eq(seasons.harvest_year).all() or not seasons.season_end.dt.year.eq(seasons.harvest_year).all():
        raise ValueError('unregistered cross-year county season')

    receipts = {}
    for scenario in ('obsclim', 'counterclim'):
        _, r, rs = load_product('mai', scenario)
        receipts[scenario] = (r, rs)
    if receipts['counterclim'][1] != inv['climate_receipt']:
        raise ValueError('inventory climate identity changed')
    raw = checked(inv['daily_source']).parent / 'pr_cutout.nc'
    if sha256(raw) != inv['daily_source']['daily_sha256']:
        raise ValueError('mask source changed')
    with xr.open_dataset(raw, engine='h5netcdf') as ds:
        lat, lon = ds.lat.values, ds.lon.values
        valid = np.isfinite(ds.pr.isel(time=0).transpose('lat', 'lon').values).ravel()
    centers = [(float(a), float(b)) for a in lat for b in lon]
    geographic = Transformer.from_crs(CRS.from_wkt((ROOT/SHAPEFILE).with_suffix('.prj').read_text()), 4326, always_xy=True)
    project = Transformer.from_crs(4326, 5070, always_xy=True)
    weights, area_audits = {}, {}
    with shapefile.Reader(str(ROOT/SHAPEFILE)) as reader:
        names = [f[0] for f in reader.fields[1:]]
        for rec in reader.iterRecords():
            geoid = str(rec[names.index('GEOID')])
            if geoid not in set(seasons.county_geoid):
                continue
            geom = transform(geographic.transform, shape(reader.shape(rec.oid).__geo_interface__))
            weights[geoid], area = county_weights(geom, centers, valid, project.transform)
            declared = int(rec[names.index('ALAND')])+int(rec[names.index('AWATER')])
            if declared <= 0 or abs(area['projected_partition_area_m2']/declared-1) > .03:
                raise ValueError('declared county area audit failed')
            area.update(declared_area_m2=declared, declared_relative_difference=area['projected_partition_area_m2']/declared-1)
            area_audits[geoid] = area
    if set(weights) != set(seasons.county_geoid):
        raise ValueError('county weights incomplete')
    cells = sorted({i for w in weights.values() for i, _ in w})
    index = {old: new for new, old in enumerate(cells)}
    products, sources = [], []
    args.outdir.mkdir(parents=True)
    for scenario in ('obsclim', 'counterclim'):
        rows = []
        r, rs = receipts[scenario]
        for first in (1981, 1991, 2001):
            values = {}
            dates = None
            for var in ('pr', 'tas', 'tasmax'):
                records = [s for s in r['sources'] if s['content']['variable'] == var and int(s['content']['first_date'][:4]) == first]
                if len(records) != 1:
                    raise ValueError('daily source identity missing')
                record = records[0]
                path = checked(record).parent / f'{var}_cutout.nc'
                if sha256(path) != record['daily_sha256']:
                    raise ValueError('daily payload changed')
                with xr.open_dataset(path, engine='h5netcdf') as ds:
                    if not np.array_equal(ds.lat.values, lat) or not np.array_equal(ds.lon.values, lon):
                        raise ValueError('daily grid axes differ')
                    observed_dates = pd.DatetimeIndex(ds.time.values)
                    validate_dates(observed_dates, f'{first}-01-01', f'{first+9}-12-31')
                    if dates is not None and not dates.equals(observed_dates):
                        raise ValueError('daily variable date alignment differs')
                    dates = observed_dates
                    if ds[var].attrs['units'] != ('kg m-2 s-1' if var == 'pr' else 'K'):
                        raise ValueError('daily units differ')
                    array = ds[var].isel(lat=xr.DataArray(np.array(cells)//len(lon), dims='cell'),
                                         lon=xr.DataArray(np.array(cells)%len(lon), dims='cell')).transpose('time', 'cell').values.astype(float)
                values[var] = array*86400 if var == 'pr' else array-273.15
                if not np.isfinite(values[var]).all():
                    raise ValueError('nonfinite selected daily weather')
                sources.append(dict(scenario=scenario, variable=var, first_year=first, receipt=record, climate_sha256=record['daily_sha256']))
            for row in seasons.loc[seasons.harvest_year.between(first, first+9)].itertuples(index=False):
                where = (dates >= row.season_start) & (dates <= row.season_end)
                validate_dates(dates[where], row.season_start, row.season_end)
                idx = [index[i] for i, _ in weights[row.county_geoid]]
                w = [value for _, value in weights[row.county_geoid]]
                feats = features(*(values[v][where][:, idx] for v in ('pr', 'tas', 'tasmax')), w)
                rows.append({**{k: getattr(row, k) for k in PAIR}, 'scenario': scenario,
                             'season_start': row.season_start, 'season_end': row.season_end,
                             'season_days': int(row.season_days), **feats})
        table = pd.DataFrame(rows).sort_values(PAIR).reset_index(drop=True)
        if len(table) != 573 or table.duplicated(PAIR).any():
            raise ValueError('built climate key count differs')
        path = args.outdir/f'{scenario}_county_climate.parquet'
        table.to_parquet(path, index=False)
        products.append({**identity(path.resolve()), 'scenario': scenario, 'rows': len(table)})
    weight_rows = [dict(county_geoid=g, lat=centers[i][0], lon=centers[i][1], spatial_weight=w)
                   for g, records in sorted(weights.items()) for i, w in records]
    result = dict(status='us_paired_county_climate_inputs_validated', crop_yield_estimated=False, causal_or_scc_result=False,
                  inventory=identity(inv_path), input=source, protocol_sha256=sha256(ROOT/PROTOCOL),
                  code_sha256=sha256(Path(__file__)), helper_sha256=sha256(ROOT/'us_county_validation/scripts/build_us_national_nclimgrid_features.py'),
                  selected_daily_cells=len(cells), county_weights=weight_rows, area_audits=area_audits,
                  sources=sources, products=products,
                  calendar_role='fixed_NASS_2010_not_GGCMI', weight_role='county_polygon_proxy_including_water_not_crop_area')
    (args.outdir/'receipt.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print('Validated paired county climate:', len(weights), 'counties;', len(cells), 'daily cells; 573 rows per path')


if __name__ == '__main__':
    main()
