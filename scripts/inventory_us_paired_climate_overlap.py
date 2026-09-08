"""Existing-input geographic/time feasibility; no crop response estimation."""
import argparse
import json
from pathlib import Path
import sys
import tomllib

import numpy as np
import pandas as pd
from pyproj import CRS, Transformer
import shapefile
from shapely.geometry import box, shape
from shapely.ops import transform, unary_union
import xarray as xr

from compare_factual_counterclim import load_product
from summarize_contiguous_climate_contrasts import ROOT, checked, sha256

sys.path.insert(0, str(ROOT / 'us_county_validation/scripts'))
import estimate_us_direct_practice_precipitation_association as base

PROTOCOL = 'US_PAIRED_CLIMATE_OVERLAP_PROTOCOL_20260908.md'
PREDICTIVE = 'us_county_validation/us_competing_moisture_predictive_v1.toml'
SHAPEFILE = 'data/raw/us_county/tigerline/tl_2019_us_county/tl_2019_us_county.shp'
WEIGHT_REFERENCE = 'data/interim/us_county/nclimgrid_polygon_weights_national_v1/county_geoid=20199/receipt.json'
PAIR = ['county_geoid', 'outcome_crop', 'harvest_year']


def coverage(geometry, domain):
    if geometry.is_empty or not geometry.is_valid or domain.is_empty or not domain.is_valid:
        raise ValueError('invalid geographic support geometry')
    if domain.covers(geometry):
        return 'full'
    return 'partial' if geometry.intersection(domain).area > 0 else 'none'


def paired_keys(frame):
    keys = PAIR + ['irrigation_practice']
    if frame.empty or frame.duplicated(keys).any():
        raise ValueError('empty or duplicated practice keys')
    practices = frame.groupby(PAIR).irrigation_practice.agg(set)
    if not practices.map(lambda p: p == {'irrigated', 'non_irrigated'}).all():
        raise ValueError('irrigation practices are not paired')
    return frame[PAIR].drop_duplicates().sort_values(PAIR).reset_index(drop=True)


def identity(path):
    return dict(path=str(path.relative_to(ROOT)), sha256=sha256(path), bytes=path.stat().st_size)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    if args.out.exists():
        raise ValueError('new inventory output required')
    cfg = base.load_config(base.DEFAULT_CONFIG)
    association, association_input = base.validate_panel(cfg)
    panel_path = ROOT / cfg['input']['panel']
    frame = pd.read_parquet(panel_path, columns=PAIR + ['irrigation_practice'])
    pairs = paired_keys(frame)
    if (len(frame), len(pairs), pairs.county_geoid.nunique()) != (23722, 11861, 419):
        raise ValueError('registered full U.S. support differs')
    common = pairs.loc[pairs.harvest_year.between(1982, 2010)].copy()
    counties = set(pairs.county_geoid)
    heat_receipt_path = ROOT / 'data/provenance/us_daily_heat_expansion_20260907.json'
    hr = json.loads(heat_receipt_path.read_text())
    heat_path = ROOT / 'data/interim/us_county/nass_direct_practice_daily_heat_1981_2019.parquet'
    if sha256(heat_path) != hr['output_sha256']:
        raise ValueError('daily heat source changed')
    heat = pd.read_parquet(heat_path, columns=PAIR).sort_values(PAIR).reset_index(drop=True)
    pd.testing.assert_frame_equal(pairs, heat, check_dtype=False)

    weight_path = ROOT / WEIGHT_REFERENCE
    wr = json.loads(weight_path.read_text())
    components = []
    for name, digest in wr['input_identity']['tiger_component_sha256'].items():
        path = (ROOT / SHAPEFILE).parent / name
        if sha256(path) != digest:
            raise ValueError('TIGER component changed')
        components.append(identity(path))
    if len(components) != 4:
        raise ValueError('TIGER source components incomplete')
    _, climate_receipt, climate_source = load_product('mai', 'counterclim')
    source = [s for s in climate_receipt['sources'] if s['content']['variable'] == 'pr'
              and s['content']['first_date'] == '1981-01-01']
    if len(source) != 1 or source[0]['content']['validation_domain'] != 'exact_four_calendar_crop_support':
        raise ValueError('validated static crop-domain source absent')
    daily = checked(source[0]).parent / 'pr_cutout.nc'
    if sha256(daily) != source[0]['daily_sha256']:
        raise ValueError('counterclim daily content changed')
    with xr.open_dataset(daily, engine='h5netcdf') as ds:
        lat, lon = ds.lat.values, ds.lon.values
        values = ds.pr.isel(time=0).transpose('lat', 'lon').values
    if not np.array_equal(lat, [39.75, 39.25]) or not np.array_equal(lon, np.arange(-179.75, 180, .5)):
        raise ValueError('counterclim grid centers changed')
    valid = np.isfinite(values)
    if int(valid.sum()) != 686 or int(np.isnan(values).sum()) != 754:
        raise ValueError('counterclim static mask changed')
    domain = unary_union([box(float(lon[j] - .25), float(lat[i] - .25),
                             float(lon[j] + .25), float(lat[i] + .25))
                          for i, j in zip(*np.where(valid))])
    strip = box(-180, 39, 180, 40)
    shp_path = ROOT / SHAPEFILE
    source_crs = CRS.from_wkt(shp_path.with_suffix('.prj').read_text())
    transformer = Transformer.from_crs(source_crs, CRS.from_epsg(4326), always_xy=True)
    records = []
    with shapefile.Reader(str(shp_path)) as reader:
        names = [f[0] for f in reader.fields[1:]]
        geoid_i, name_i = names.index('GEOID'), names.index('NAME')
        for rec in reader.iterRecords():
            geoid = str(rec[geoid_i])
            if geoid not in counties:
                continue
            geometry = transform(transformer.transform, shape(reader.shape(rec.oid).__geo_interface__))
            records.append(dict(county_geoid=geoid, county_name=str(rec[name_i]),
                                bounds_lonlat=list(geometry.bounds),
                                strip_coverage=coverage(geometry, strip),
                                finite_climate_coverage=coverage(geometry, domain)))
    geography = pd.DataFrame(records)
    if len(geography) != len(counties) or geography.county_geoid.duplicated().any() or set(geography.county_geoid) != counties:
        raise ValueError('county geometry mapping incomplete')
    joined = common.merge(geography, on='county_geoid', validate='many_to_one')
    comparisons = []
    for crop, group in joined.groupby('outcome_crop'):
        comparisons.append(dict(crop=crop, crop_county_years=len(group), counties=group.county_geoid.nunique(),
            classifications={field: {status: dict(crop_county_years=int((group[field] == status).sum()),
                counties=int(group.loc[group[field] == status, 'county_geoid'].nunique())) for status in ['full', 'partial', 'none']}
                for field in ['strip_coverage', 'finite_climate_coverage']},
            full_climate_county_geoids=sorted(group.loc[group.finite_climate_coverage == 'full', 'county_geoid'].unique())))
    predictive = tomllib.loads((ROOT / PREDICTIVE).read_text())
    result = dict(status='existing_us_paired_climate_overlap_inventoried',
        role='geographic_and_time_support_feasibility_not_response_fit',
        crop_yield_estimated=False, causal_or_scc_result=False, new_holdout_identified=False,
        climate_years=[1982, 2010], climate_valid_half_degree_cells=686,
        full_direct_weather_rows=len(frame), unique_crop_county_years=len(pairs), counties=len(counties),
        association_period=[cfg['input']['year_min'], cfg['input']['year_max']],
        association_input=association_input,
        previously_evaluated_predictive_period=[predictive['sample']['year_min'], predictive['sample']['year_max']],
        previously_evaluated_terminal_period=[2012, 2019],
        available_weather_years_not_in_evaluated_period=sorted(set(pairs.harvest_year) - set(range(1981, 2020))),
        years=[dict(harvest_year=int(y), crop=crop, crop_county_years=int(len(g)), counties=int(g.county_geoid.nunique()))
               for (y, crop), g in pairs.groupby(['harvest_year', 'outcome_crop'])],
        comparisons=comparisons, county_geography=records,
        input_sources=[identity(base.DEFAULT_CONFIG), identity(ROOT / cfg['input']['source_receipt']),
                       identity(panel_path), identity(heat_receipt_path), identity(heat_path),
                       identity(weight_path), identity(ROOT / PREDICTIVE),
                       identity(ROOT / 'data/provenance/nass_irrigation_practice_screen.toml')],
        tiger_components=components, climate_receipt=climate_source, daily_source=source[0],
        protocol_sha256=sha256(ROOT / PROTOCOL), code_sha256=sha256(Path(__file__)))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(json.dumps(comparisons, indent=2))


if __name__ == '__main__':
    main()
