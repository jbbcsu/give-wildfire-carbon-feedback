#!/usr/bin/env python3
"""Boundedly decode PEEPS-source MPI coordinates, not climate payload."""
import argparse
import base64
import hashlib
import json
import math
from pathlib import Path
import shutil
import ssl
import sys
import urllib.request

import certifi


METADATA_SHA256 = '96d0057abb0776eec9dc55aa137fa5c3313622404e6afb3ce3045c77432113c0'
MAX_CHUNK = 2 * 2**20


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('metadata_manifest', type=Path)
    parser.add_argument('peeps_monthly_receipt', type=Path)
    parser.add_argument('--dependency-dir', type=Path, required=True)
    parser.add_argument('--out-dir', type=Path, required=True)
    args = parser.parse_args()
    project = Path(__file__).resolve().parents[1]
    metadata_path, peeps_path, output = (path.resolve() for path in
                                         (args.metadata_manifest, args.peeps_monthly_receipt, args.out_dir))
    dependency_dir = args.dependency_dir.resolve()
    if (any(not path.is_relative_to(project / 'data/interim') for path in (metadata_path, peeps_path, output))
            or not dependency_dir.is_relative_to(project / 'data/interim')
            or output.exists() or sha(metadata_path) != METADATA_SHA256
            or shutil.disk_usage(project).free < 130 * 2**30):
        parser.error('unexpected input, output or disk reserve')
    sys.path.insert(0, str(dependency_dir))
    import cftime
    import numcodecs
    import numpy as np
    import xarray as xr
    from numcodecs.blosc import _cbuffer_sizes, set_nthreads
    set_nthreads(1)
    metadata = json.loads(metadata_path.read_text())
    if metadata['status'] != 'four_source_matched_mpi_store_metadata_validated_no_climate_payload' or len(metadata['records']) != 4:
        raise ValueError('wrong source-matched metadata manifest')
    author = json.loads(peeps_path.read_text())
    if (author['outer_archive_md5'] != 'eed1a0e8a43bf915c78ec68d0f37e357'
            or author['model'] != 'MPI-ESM1-2-HR' or author['scenario'] != 'ssp585'):
        raise ValueError('wrong published author coefficient source')
    coefficient = peeps_path.parent / 'MPI-ESM1-2-HR_ssp585_pr_monthly_patterns_jan.nc'
    january = next((item for item in author['selected_members'] if item['name'] == coefficient.name), None)
    if january is None or sha(coefficient) != january['sha256']:
        raise ValueError('published January coefficient changed')
    with xr.open_dataset(coefficient) as dataset:
        peeps_lat, peeps_lon = dataset.lat.values.copy(), dataset.lon.values.copy()
    output.mkdir(parents=True)
    context = ssl.create_default_context(cafile=certifi.where())
    records = []
    reference = None
    for record in metadata['records']:
        path = metadata_path.parent / record['metadata_file']
        if sha(path) != record['metadata_sha256']:
            raise ValueError('source metadata file changed')
        document = json.loads(path.read_text())['metadata']
        bound_name = document['time/.zattrs'].get('bounds')
        if not bound_name or bound_name in ('pr', 'tas'):
            raise ValueError('invalid time bounds name')
        arrays = {}
        chunks = []
        for variable in ('lat', 'lon', 'time', bound_name):
            spec = document[f'{variable}/.zarray']
            expected_bytes = math.prod(spec['chunks']) * np.dtype(spec['dtype']).itemsize
            if (spec['chunks'] != spec['shape'] or expected_bytes > MAX_CHUNK
                    or spec['zarr_format'] != 2 or spec['order'] != 'C'
                    or spec['filters'] is not None or spec['compressor']['id'] != 'blosc'):
                raise ValueError(f'unsupported coordinate allocation: {variable}')
            key = '.'.join('0' for _ in spec['shape'])
            url = record['metadata_url'].removesuffix('.zmetadata') + variable + '/' + key
            request = urllib.request.Request(url, headers={'User-Agent': 'GIVE-precipitation-research/1.0',
                                                           'Accept-Encoding': 'identity'})
            with urllib.request.urlopen(request, context=context, timeout=60) as response:
                if response.status != 200 or response.headers.get('Content-Encoding'):
                    raise ValueError('unexpected coordinate HTTP response')
                content = response.read(MAX_CHUNK + 1)
                server_hash = ','.join(response.headers.get_all('x-goog-hash', []))
            if not 16 <= len(content) <= MAX_CHUNK:
                raise ValueError('coordinate chunk size invalid')
            md5s = [part.strip()[4:] for part in server_hash.split(',') if part.strip().startswith('md5=')]
            if md5s and md5s != [base64.b64encode(hashlib.md5(content).digest()).decode()]:
                raise ValueError('coordinate server MD5 differs')
            uncompressed, compressed, _ = _cbuffer_sizes(content)
            if uncompressed != expected_bytes or compressed != len(content):
                raise ValueError('coordinate chunk header differs')
            decoded = numcodecs.get_codec(spec['compressor']).decode(content)
            if len(decoded) != expected_bytes:
                raise ValueError('coordinate decoded bytes differ')
            array = np.frombuffer(decoded, dtype=spec['dtype']).reshape(spec['shape'])
            if not np.isfinite(array).all():
                raise ValueError('nonfinite coordinate or bounds')
            arrays[variable] = array.copy()
            name = f"{record['variable']}_{record['member_id']}_{variable}.blosc"
            saved = output / name
            saved.write_bytes(content)
            chunks.append({'variable': variable, 'url': url, 'file': name,
                           'bytes': len(content), 'sha256': sha(saved),
                           'server_md5_verified': bool(md5s)})
        lat, lon, times, bounds = (arrays[x] for x in ('lat', 'lon', 'time', bound_name))
        if (not np.all(np.diff(lat) > 0) or not np.all(np.diff(lon) > 0)
                or lat.min() < -90 or lat.max() > 90 or lon.min() < 0 or lon.max() >= 360):
            raise ValueError('native spatial coordinates invalid')
        time_attrs = document['time/.zattrs']
        bounds_attrs = document[f'{bound_name}/.zattrs']
        cal = time_attrs['calendar']
        if bounds_attrs.get('calendar', cal) != cal:
            raise ValueError('time and bounds calendars differ')
        date = cftime.num2date(times, time_attrs['units'], calendar=cal)
        edge = cftime.num2date(bounds, bounds_attrs.get('units', time_attrs['units']), calendar=cal)
        ids = np.array([12 * item.year + item.month - 1 for item in date])
        expected = np.arange(12 * 2015, 12 * 2101)
        if not np.array_equal(ids, expected):
            raise ValueError('time axis has missing/duplicate months or endpoints')
        for middle, (lo, hi) in zip(date, edge):
            if ((lo.year, lo.month) != (middle.year, middle.month)
                    or lo.day != 1 or hi.day != 1
                    or 12 * hi.year + hi.month - (12 * lo.year + lo.month) != 1
                    or any(getattr(x, part) != 0 for x in (lo, hi)
                           for part in ('hour', 'minute', 'second', 'microsecond'))
                    or not lo < middle < hi):
                raise ValueError('time bounds not full aligned calendar months')
        if any(edge[j, 1] != edge[j + 1, 0] for j in range(len(edge) - 1)):
            raise ValueError('time bounds not contiguous')
        equal_peeps = bool(np.array_equal(lat, peeps_lat) and np.array_equal(lon, peeps_lon))
        close_peeps = bool(np.allclose(lat, peeps_lat, rtol=0, atol=1e-10)
                           and np.allclose(lon, peeps_lon, rtol=0, atol=1e-10))
        if not close_peeps:
            raise ValueError('author coefficient grid differs from direct source')
        if reference is None:
            reference = (lat.copy(), lon.copy(), ids.copy())
        ref_lat, ref_lon, ref_ids = reference
        member_grid_exact = bool(np.array_equal(ref_lat, lat) and np.array_equal(ref_lon, lon))
        max_member_grid_difference = max(float(np.max(np.abs(ref_lat - lat))),
                                         float(np.max(np.abs(ref_lon - lon))))
        if (not np.allclose(ref_lat, lat, rtol=0, atol=1e-10)
                or not np.allclose(ref_lon, lon, rtol=0, atol=1e-10)
                or not np.array_equal(ref_ids, ids)):
            raise ValueError('source members/variables coordinate mismatch beyond frozen tolerance')
        records.append({'variable': record['variable'], 'member_id': record['member_id'],
                        'calendar': cal, 'first_timestamp': str(date[0]),
                        'last_timestamp': str(date[-1]), 'months': len(ids),
                        'bounds_contiguous': True, 'peeps_grid_exact_bit_equal': equal_peeps,
                        'peeps_grid_within_1e_10_degree': close_peeps,
                        'member_grid_exact_bit_equal_to_first': member_grid_exact,
                        'max_member_grid_difference_degree': max_member_grid_difference,
                        'chunks': chunks})
    result = {'status': 'four_mpi_source_coordinate_axes_and_peeps_grid_passed_no_climate_payload',
              'metadata_sha256': METADATA_SHA256, 'records': records,
              'source_member_variable_axes_equal': True,
              'climate_payload_read': False, 'yield_damage_scc_estimated': False}
    (output / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'status': result['status'], 'records':
                      [{k: row[k] for k in ('variable', 'member_id', 'first_timestamp',
                                            'last_timestamp', 'months', 'peeps_grid_exact_bit_equal')}
                       for row in records]}))


if __name__ == '__main__':
    main()
