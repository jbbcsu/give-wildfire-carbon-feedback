#!/usr/bin/env python3
"""Validate the selected published PEEPS December rainfall coefficient file.

This checks file identity and internal structure, not predictive transfer,
physical nonnegative rainfall at every warming level, or SCC suitability.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

import numpy as np
import xarray as xr


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('receipt', type=Path)
    args = parser.parse_args()
    project = Path(__file__).resolve().parents[1]
    receipt_path = args.receipt.resolve()
    if not receipt_path.is_relative_to(project / 'data/interim'):
        parser.error('only ignored project interim data may be validated')
    if shutil.disk_usage(project).free < 130 * 2**30:
        raise RuntimeError('free disk below project reserve')
    source = json.loads(receipt_path.read_text())
    file_path = project / source['output_relative_to_project']
    if file_path.parent != receipt_path.parent or not file_path.is_file():
        raise ValueError('receipt/file directory mismatch')
    if file_path.stat().st_size != source['member_bytes']:
        raise ValueError('published member byte count differs from receipt')
    digest = hashlib.sha256()
    with file_path.open('rb') as stream:
        while block := stream.read(1024 * 1024):
            digest.update(block)
    if digest.hexdigest() != source['member_sha256']:
        raise ValueError('selected member SHA256 mismatch')
    with xr.open_dataset(file_path) as ds:
        if set(ds.data_vars) != {'slope', 'intercept'}:
            raise ValueError('unexpected PEEPS coefficient variables')
        if dict(ds.sizes) != {'param': 1, 'lat': 192, 'lon': 384}:
            raise ValueError('unexpected native coefficient grid')
        if str(ds.param.values[0]) != 'estimated_param':
            raise ValueError('unexpected coefficient parameter label')
        attrs = {k: str(ds.attrs.get(k, '')) for k in
                 ('source_id', 'experiment_id', 'variable_id', 'variable_units',
                  'grid_label', 'variant_label', 'pattern_info')}
        expected = {'source_id': source['model'],
                    'experiment_id': source['scenario'],
                    'variable_id': 'pr', 'variable_units': 'kg m-2 s-1',
                    'grid_label': 'gn', 'variant_label': 'ensemble_avg',
                    'pattern_info': 'pattern of dec gridded data'}
        if attrs != expected:
            raise ValueError(f'published file metadata mismatch: {attrs}')
        lat = ds.lat.values
        lon = ds.lon.values
        if not (np.all(np.diff(lat) > 0) and np.all(np.diff(lon) > 0)
                and np.all((-90 <= lat) & (lat <= 90))
                and np.all((0 <= lon) & (lon < 360))):
            raise ValueError('invalid coefficient grid coordinates')
        slope = ds.slope.values
        intercept = ds.intercept.values
        if not (np.isfinite(slope).all() and np.isfinite(intercept).all()):
            raise ValueError('nonfinite published coefficients')
        output = {'status': 'source_file_structure_validated_not_predictive_or_scc_validated',
                  'selected_member_sha256': digest.hexdigest(),
                  'selected_member_bytes': file_path.stat().st_size,
                  'source_metadata': attrs, 'grid_shape': [192, 384],
                  'finite_cells': int(slope.size),
                  'slope_range': [float(slope.min()), float(slope.max())],
                  'intercept_range': [float(intercept.min()), float(intercept.max())],
                  'outer_archive_checksum_verified': False,
                  'predictor_definition': 'author code: annual arithmetic mean of 12 monthly cosine-latitude-weighted absolute tas; predictor alignment still to be audited',
                  'yield_damage_scc_estimated': False}
    result_path = receipt_path.parent / 'structure_validation.json'
    if result_path.exists():
        raise FileExistsError('validation receipt already exists')
    result = json.dumps(output, indent=2) + '\n'
    if len(result.encode()) > 8192:
        raise ValueError('unexpected validation output size')
    result_path.write_text(result)
    print(json.dumps(output))


if __name__ == '__main__':
    main()
