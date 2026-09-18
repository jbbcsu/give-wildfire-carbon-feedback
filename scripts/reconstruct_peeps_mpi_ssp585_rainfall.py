#!/usr/bin/env python3
"""Bounded in-sample PEEPS versus source-ensemble rainfall diagnostic."""
import argparse
import base64
import calendar
import hashlib
import json
import math
from pathlib import Path
import shutil
import ssl
import struct
import sys
import urllib.request

import certifi


HASHES = {
    'author': 'fafe91fafb0f64b1448501bb49b623e21ad86e3c882a6b65b5fb337d8b6fa753',
    'gmst': 'cd632ffb21d171c48787f5d4766a2ae29f22d657db56a074738a7dc2c9a2bad3',
    'metadata': '96d0057abb0776eec9dc55aa137fa5c3313622404e6afb3ce3045c77432113c0',
    'coordinates': '0c77d5a44c35f5aec0d6fc14a8630e28177d038c1e81af1833a64464d955092b',
    'mirca': '7512ffc580928a03f75bbce5f3d4263c9bb2c631a8ff04075973acb4b149e4ba',
}
YEARS = (2015, 2100)
MEMBERS = ('r1i1p1f1', 'r2i1p1f1')
MAX_COMPRESSED = 160 * 2**20


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def crc32c(data):
    """GCS Castagnoli CRC32C, big-endian base64; verified by test vector."""
    polynomial = 0x82F63B78
    table = []
    for value in range(256):
        remainder = value
        for _ in range(8):
            remainder = (remainder >> 1) ^ (polynomial if remainder & 1 else 0)
        table.append(remainder)
    value = 0xffffffff
    for octet in data:
        value = table[(value ^ octet) & 0xff] ^ (value >> 8)
    return base64.b64encode((value ^ 0xffffffff).to_bytes(4, 'big')).decode()


def summarize(direct, predicted, hectares):
    """Compare 12xN monthly millimeters without hiding invalid levels."""
    import numpy as np
    if direct.shape != predicted.shape or direct.shape != (12, len(hectares)):
        raise ValueError('monthly geometry differs')
    if not (np.isfinite(direct).all() and np.isfinite(predicted).all()
            and np.isfinite(hectares).all() and np.all(hectares > 0)):
        raise ValueError('nonfinite climate or invalid area')
    monthly = []
    for m in range(12):
        delta = predicted[m] - direct[m]
        monthly.append({'month': m + 1,
                        'direct_negative_area_percent': 100 * float(hectares[direct[m] < 0].sum()) / hectares.sum(),
                        'predicted_negative_area_percent': 100 * float(hectares[predicted[m] < 0].sum()) / hectares.sum(),
                        'mean_direct_mm': float(np.average(direct[m], weights=hectares)),
                        'mean_predicted_mm': float(np.average(predicted[m], weights=hectares)),
                        'mean_bias_mm': float(np.average(delta, weights=hectares)),
                        'mae_mm': float(np.average(np.abs(delta), weights=hectares)),
                        'rmse_mm': float(np.sqrt(np.average(delta**2, weights=hectares)))})
    direct_total = direct.sum(axis=0)
    predicted_total = predicted.sum(axis=0)
    all_delta = predicted_total - direct_total
    valid = ((direct >= 0).all(axis=0) & (predicted >= 0).all(axis=0)
             & (direct_total > 0) & (predicted_total > 0))
    result = {'months': monthly,
              'direct_any_negative_area_percent': 100 * float(hectares[(direct < 0).any(axis=0)].sum()) / hectares.sum(),
              'predicted_any_negative_area_percent': 100 * float(hectares[(predicted < 0).any(axis=0)].sum()) / hectares.sum(),
              'all_area_annual_direct_mean_mm': float(np.average(direct_total, weights=hectares)),
              'all_area_annual_predicted_mean_mm': float(np.average(predicted_total, weights=hectares)),
              'all_area_annual_bias_mm': float(np.average(all_delta, weights=hectares)),
              'all_area_annual_rmse_mm': float(np.sqrt(np.average(all_delta**2, weights=hectares))),
              'common_valid_centers': int(valid.sum()),
              'common_valid_area_percent': 100 * float(hectares[valid].sum()) / hectares.sum()}
    if valid.any():
        share_direct = direct[:, valid] / direct_total[valid]
        share_pred = predicted[:, valid] / predicted_total[valid]
        tv = 0.5 * np.abs(share_direct - share_pred).sum(axis=0)
        result['common_valid_mean_month_share_tv_error'] = float(np.average(tv, weights=hectares[valid]))
        result['common_valid_annual_rmse_mm'] = float(np.sqrt(np.average(all_delta[valid]**2, weights=hectares[valid])))
    else:
        result['common_valid_mean_month_share_tv_error'] = None
        result['common_valid_annual_rmse_mm'] = None
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('author_receipt', type=Path)
    parser.add_argument('gmst_receipt', type=Path)
    parser.add_argument('metadata_manifest', type=Path)
    parser.add_argument('coordinate_manifest', type=Path)
    parser.add_argument('--dependency-dir', type=Path, required=True)
    parser.add_argument('--out-dir', type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    sources = {'author': args.author_receipt.resolve(), 'gmst': args.gmst_receipt.resolve(),
               'metadata': args.metadata_manifest.resolve(), 'coordinates': args.coordinate_manifest.resolve()}
    output = args.out_dir.resolve()
    dependency = args.dependency_dir.resolve()
    if (any(not x.is_relative_to(root / 'data/interim') for x in (*sources.values(), output, dependency))
            or output.exists() or shutil.disk_usage(root).free < 130 * 2**30):
        parser.error('ignored input, fresh output and disk reserve required')
    if any(sha(path) != HASHES[key] for key, path in sources.items()):
        raise ValueError('frozen source manifest hash changed')
    sys.path.insert(0, str(dependency))
    import numpy as np
    import pyarrow.parquet as pq
    import xarray as xr
    import numcodecs
    from numcodecs.blosc import _cbuffer_sizes, set_nthreads
    set_nthreads(1)
    author, gmst_meta, manifest, coords = (json.loads(path.read_text()) for path in sources.values())
    if (author['outer_archive_md5'] != 'eed1a0e8a43bf915c78ec68d0f37e357'
            or coords['source_member_variable_axes_equal'] is not True
            or len(manifest['records']) != 4):
        raise ValueError('source identity/coordinate gate changed')
    gmst_path = root / gmst_meta['output_relative_to_project']
    if sha(gmst_path) != gmst_meta['member_sha256']:
        raise ValueError('author GMST changed')
    with xr.open_dataset(gmst_path) as ds:
        gmst_years = ds.time.dt.year.values.astype(int)
        gmst_vals = ds.tas.values.astype(float)
    if not np.array_equal(gmst_years, np.arange(2015, 2101)):
        raise ValueError('author GMST year axis changed')
    temperatures = {year: float(gmst_vals[gmst_years == year][0]) for year in YEARS}
    if not all(250 < x < 330 for x in temperatures.values()):
        raise ValueError('author GMST absolute temperature invalid')
    weights_path = root / 'data/interim/mirca_os_v2/irrigation_shares_2000.parquet'
    if sha(weights_path) != HASHES['mirca']:
        raise ValueError('MIRCA source changed')
    area = pq.read_table(weights_path,
                         columns=['lat', 'lon_360', 'crop', 'irrigation', 'rainfed_area_ha'],
                         filters=[('crop', '=', 'mai'), ('irrigation', '=', 'noirr')],
                         use_threads=False).to_pandas()
    area = area.loc[area.rainfed_area_ha > 0]
    if len(area) != 30821 or area.duplicated(['lat', 'lon_360']).any():
        raise ValueError('MIRCA maize support changed')
    lat = area.lat.to_numpy(dtype=float)
    lon = area.lon_360.to_numpy(dtype=float)
    hectares = area.rainfed_area_ha.to_numpy(dtype=float)
    del area
    # Published January native grid is the mapping reference; all four
    # direct source grids already passed the 1e-10-degree gate.
    january = sources['author'].parent / 'MPI-ESM1-2-HR_ssp585_pr_monthly_patterns_jan.nc'
    january_entry = next(x for x in author['selected_members'] if x['name'] == january.name)
    if sha(january) != january_entry['sha256']:
        raise ValueError('published January coefficients changed')
    with xr.open_dataset(january) as ds:
        grid_lat, grid_lon = ds.lat.values.copy(), ds.lon.values.copy()
    ii = np.abs(lat[:, None] - grid_lat).argmin(axis=1)
    jj = np.abs(((lon[:, None] - grid_lon + 180) % 360) - 180).argmin(axis=1)
    if not np.isclose(hectares.sum(), np.bincount(ii * len(grid_lon) + jj, weights=hectares).sum(),
                      rtol=1e-12, atol=0):
        raise ValueError('crop area not conserved')
    predicted = {year: np.empty((12, len(hectares)), dtype=np.float64) for year in YEARS}
    for m, item in enumerate(author['selected_members'], 1):
        file = sources['author'].parent / item['name']
        if sha(file) != item['sha256']:
            raise ValueError('published monthly coefficient changed')
        with xr.open_dataset(file) as ds:
            beta = ds.slope.values[0, ii, jj]
            alpha = ds.intercept.values[0, ii, jj]
            for year in YEARS:
                predicted[year][m - 1] = (beta * temperatures[year] + alpha) * 86400 * calendar.monthrange(year, m)[1]
    direct = {member: {year: np.empty((12, len(hectares)), dtype=np.float64)
                       for year in YEARS} for member in MEMBERS}
    context = ssl.create_default_context(cafile=certifi.where())
    chunk_records = []
    for member in MEMBERS:
        record = next(x for x in manifest['records'] if x['variable'] == 'pr' and x['member_id'] == member)
        meta_file = sources['metadata'].parent / record['metadata_file']
        if sha(meta_file) != record['metadata_sha256']:
            raise ValueError('source precipitation metadata changed')
        spec = json.loads(meta_file.read_text())['metadata']['pr/.zarray']
        if (spec['dtype'] != '<f4' or spec['filters'] is not None
                or spec['order'] != 'C' or spec['compressor']['id'] != 'blosc'
                or spec['chunks'][1:] != [192, 384] or spec['shape'] != [1032, 192, 384]):
            raise ValueError('source climate chunk contract changed')
        first = spec['chunks'][0]
        selected_chunks = sorted({((year - 2015) * 12 + m) // first
                                  for year in YEARS for m in range(12)})
        expected_chunks = [0, 1] if member == MEMBERS[0] else [0, 4]
        if selected_chunks != expected_chunks:
            raise ValueError('frozen selected source chunk indices changed')
        for chunk_index in selected_chunks:
            key = f'{chunk_index}.0.0'
            url = record['metadata_url'].removesuffix('.zmetadata') + 'pr/' + key
            request = urllib.request.Request(url, headers={'User-Agent': 'GIVE-precipitation-research/1.0',
                                                           'Accept-Encoding': 'identity'})
            with urllib.request.urlopen(request, context=context, timeout=120) as response:
                if response.status != 200 or response.headers.get('Content-Encoding'):
                    raise ValueError('unexpected raw-climate response')
                declared = response.headers.get('Content-Length')
                if declared and int(declared) > MAX_COMPRESSED:
                    raise ValueError('compressed climate chunk exceeds cap before transfer')
                content = response.read(MAX_COMPRESSED + 1)
                hash_header = ','.join(response.headers.get_all('x-goog-hash', []))
            if len(content) > MAX_COMPRESSED or (declared and len(content) != int(declared)):
                raise ValueError('compressed chunk transfer size differs')
            crc_headers = [x.strip()[7:] for x in hash_header.split(',') if x.strip().startswith('crc32c=')]
            crc_verified = bool(crc_headers)
            if crc_headers and crc_headers != [crc32c(content)]:
                raise ValueError('GCS CRC32C compressed chunk differs')
            md5_headers = [x.strip()[4:] for x in hash_header.split(',') if x.strip().startswith('md5=')]
            if md5_headers and md5_headers != [base64.b64encode(hashlib.md5(content).digest()).decode()]:
                raise ValueError('GCS MD5 compressed chunk differs')
            compressed_sha = hashlib.sha256(content).hexdigest()
            decoded_bytes, compressed_bytes, _ = _cbuffer_sizes(content)
            remaining = spec['shape'][0] - chunk_index * first
            edge = min(first, remaining)
            plane_bytes = 192 * 384 * np.dtype('<f4').itemsize
            if compressed_bytes != len(content) or decoded_bytes not in (first * plane_bytes, edge * plane_bytes):
                raise ValueError('Blosc decoded allocation differs')
            decoded = numcodecs.get_codec(spec['compressor']).decode(content)
            del content
            if len(decoded) != decoded_bytes:
                raise ValueError('decoded climate chunk byte count differs')
            count = decoded_bytes // plane_bytes
            data = np.frombuffer(decoded, dtype='<f4').reshape(count, 192, 384)
            chunk_sentinels = []
            selected_plane_counts = []
            for year in YEARS:
                for m in range(12):
                    index = (year - 2015) * 12 + m
                    if index // first != chunk_index:
                        continue
                    plane = data[index - chunk_index * first]
                    if not np.isfinite(plane).all() or np.any(plane == spec['fill_value']):
                        raise ValueError('source climate missing or nonfinite values')
                    selected_plane_counts.append({'year': year, 'month': m + 1,
                                                  'native_negative_cells': int(np.count_nonzero(plane < 0)),
                                                  'native_missing_cells': 0})
                    if m == 0:
                        local = index - chunk_index * first
                        for i, j in ((0, 0), (46, 96), (96, 192), (191, 383)):
                            offset = 4 * (local * 192 * 384 + i * 384 + j)
                            independently_unpacked = struct.unpack_from('<f', decoded, offset)[0]
                            if independently_unpacked != float(plane[i, j]):
                                raise ValueError('scalar buffer sentinel disagrees')
                            chunk_sentinels.append({'year': year, 'month': 1,
                                                    'native_i': i, 'native_j': j,
                                                    'source_flux': independently_unpacked})
                    seconds = 86400 * calendar.monthrange(year, m + 1)[1]
                    direct[member][year][m] = plane[ii, jj].astype(np.float64) * seconds
            chunk_records.append({'member': member, 'chunk_index': chunk_index,
                                  'url': url, 'compressed_bytes': compressed_bytes,
                                  'compressed_sha256': compressed_sha,
                                  'gcs_crc32c_verified': crc_verified,
                                  'gcs_md5_verified': bool(md5_headers),
                                  'decoded_bytes': decoded_bytes,
                                  'selected_plane_counts': selected_plane_counts,
                                  'scalar_buffer_sentinels': chunk_sentinels})
            del plane, data, decoded
            print('decoded', member, chunk_index, compressed_bytes, flush=True)
    source_mean = {year: (direct[MEMBERS[0]][year] + direct[MEMBERS[1]][year]) / 2
                   for year in YEARS}
    outputs = {'status': 'same_source_in_sample_published_rainfall_reconstruction_not_holdout_or_scc',
               'years': list(YEARS), 'members': list(MEMBERS),
               'source_manifest_sha256': HASHES,
               'rainfed_maize_centers': len(hectares),
               'rainfed_maize_area_ha': float(hectares.sum()),
               'chunk_records': chunk_records,
               'year_results': [{'year': year, 'author_absolute_gmst_K': temperatures[year],
                                 **summarize(source_mean[year], predicted[year], hectares)}
                                for year in YEARS],
               'yield_damage_scc_estimated': False}
    output.mkdir(parents=True)
    arrays = {'hectares': hectares, 'ii': ii, 'jj': jj}
    for year in YEARS:
        arrays[f'direct_mean_mm_{year}'] = source_mean[year]
        arrays[f'published_mm_{year}'] = predicted[year]
        for member in MEMBERS:
            arrays[f'direct_{member}_mm_{year}'] = direct[member][year]
    npz = output / 'crop_center_monthly_arrays.npz'
    np.savez_compressed(npz, **arrays)
    outputs['crop_center_arrays_sha256'] = sha(npz)
    (output / 'result.json').write_text(json.dumps(outputs, indent=2) + '\n')
    print(json.dumps({'status': outputs['status'], 'year_results':
                      [{k: value for k, value in item.items() if k != 'months'}
                       for item in outputs['year_results']]}))


if __name__ == '__main__':
    main()
