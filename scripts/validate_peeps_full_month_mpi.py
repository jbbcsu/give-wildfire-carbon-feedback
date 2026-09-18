#!/usr/bin/env python3
"""Validate twelve author PEEPS MPI monthly pr files after whole MD5 pass."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

import numpy as np
import xarray as xr

from extract_peeps_full_month_mpi import MONTHS, MODEL, SCENARIO, OUTER_MD5


PILOT_DEC_SHA256 = '13e17ee549adfe109356b765cc25a50c2adc539399b95c09eeae73ec0b237699'


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        while block := stream.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('receipt', type=Path)
    args = parser.parse_args()
    project = Path(__file__).resolve().parents[1]
    if shutil.disk_usage(project).free < 130 * 2**30:
        raise RuntimeError('disk reserve not met')
    receipt_path = args.receipt.resolve()
    if not receipt_path.is_relative_to(project / 'data/interim'):
        parser.error('only ignored project interim files accepted')
    source = json.loads(receipt_path.read_text())
    if source['status'] != 'whole_author_archive_md5_verified_selected_members_acquired':
        raise ValueError('whole-source acquisition not complete')
    if source['outer_archive_md5'] != OUTER_MD5 or source['selected_months'] != list(MONTHS):
        raise ValueError('published source hash or month set differs')
    if source['model'] != MODEL or source['scenario'] != SCENARIO:
        raise ValueError('wrong author model/scenario')
    records = source['selected_members']
    if len(records) != 12 or source['selected_total_bytes'] != sum(item['bytes'] for item in records):
        raise ValueError('selected source byte accounting differs')
    result = []
    first_lat = first_lon = None
    for month, item in zip(MONTHS, records, strict=True):
        expected_name = f'{MODEL}_{SCENARIO}_pr_monthly_patterns_{month}.nc'
        if item['name'] != expected_name:
            raise ValueError('wrong published monthly member')
        path = receipt_path.parent / expected_name
        if not path.is_file() or path.stat().st_size != item['bytes'] or sha256(path) != item['sha256']:
            raise ValueError(f'published member changed: {month}')
        with xr.open_dataset(path) as ds:
            expected_attrs = {'source_id': MODEL, 'experiment_id': SCENARIO,
                              'variable_id': 'pr', 'variable_units': 'kg m-2 s-1',
                              'grid_label': 'gn', 'variant_label': 'ensemble_avg',
                              'pattern_info': f'pattern of {month} gridded data'}
            if any(str(ds.attrs.get(k, '')) != v for k, v in expected_attrs.items()):
                raise ValueError(f'author metadata differs: {month}')
            if set(ds.data_vars) != {'slope', 'intercept'} or dict(ds.sizes) != {'param': 1, 'lat': 192, 'lon': 384}:
                raise ValueError(f'coefficient shape differs: {month}')
            if str(ds.param.values[0]) != 'estimated_param':
                raise ValueError('unexpected parameter label')
            lat, lon = ds.lat.values, ds.lon.values
            if first_lat is None:
                first_lat, first_lon = lat.copy(), lon.copy()
            elif not (np.array_equal(lat, first_lat) and np.array_equal(lon, first_lon)):
                raise ValueError('monthly native grids not identical')
            slope, intercept = ds.slope.values[0], ds.intercept.values[0]
            if not (np.isfinite(slope).all() and np.isfinite(intercept).all()):
                raise ValueError(f'nonfinite author coefficients: {month}')
            result.append({'month': month, 'sha256': item['sha256'], 'bytes': item['bytes'],
                           'finite_cells': int(slope.size),
                           'slope_min': float(slope.min()), 'slope_max': float(slope.max()),
                           'intercept_min': float(intercept.min()), 'intercept_max': float(intercept.max())})
    if result[-1]['sha256'] != PILOT_DEC_SHA256:
        raise ValueError('whole-source December differs from independent range pilot')
    report = {'status': 'published_twelve_month_source_structure_validated_not_prediction_or_scc',
              'outer_archive_md5': OUTER_MD5, 'model': MODEL, 'scenario': SCENARIO,
              'shared_grid_shape': [192, 384], 'source_units': 'kg m-2 s-1',
              'independent_december_range_sha256_matches': True,
              'months': result, 'yield_damage_scc_estimated': False}
    output_path = receipt_path.parent / 'all_month_structure_validation.json'
    if output_path.exists():
        raise FileExistsError('validation receipt exists')
    payload = json.dumps(report, indent=2) + '\n'
    if len(payload.encode()) > 32768:
        raise ValueError('unexpected validation output size')
    output_path.write_text(payload)
    print(json.dumps({'status': report['status'],
                      'independent_december_range_sha256_matches': True,
                      'months': [item['month'] for item in result]}))


if __name__ == '__main__':
    main()
