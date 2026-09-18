#!/usr/bin/env python3
"""Stream four MPI precipitation chunks into small crop-center matrices."""
import argparse
import base64
import calendar
import hashlib
import json
from pathlib import Path
import shutil
import ssl
import struct
import sys
import urllib.request

import certifi

from reconstruct_peeps_mpi_ssp585_rainfall import crc32c


MANIFEST_SHA256 = '96d0057abb0776eec9dc55aa137fa5c3313622404e6afb3ce3045c77432113c0'
COORD_SHA256 = '0c77d5a44c35f5aec0d6fc14a8630e28177d038c1e81af1833a64464d955092b'
MAPPING_SHA256 = 'abd8058f696eca10c3c614bdc24db32830e38f41808ee1960234248c5ee2fa9c'
MAX_COMPRESSED = 160 * 2**20
MEMBERS = ('r1i1p1f1', 'r2i1p1f1')
YEARS = (2015, 2100)


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('metadata_manifest', type=Path)
    parser.add_argument('coordinate_manifest', type=Path)
    parser.add_argument('mapping_manifest', type=Path)
    parser.add_argument('--member', choices=MEMBERS, required=True)
    parser.add_argument('--chunk-index', type=int, required=True)
    parser.add_argument('--dependency-dir', type=Path, required=True)
    parser.add_argument('--out-dir', type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    metadata_path, coord_path, mapping_path, dependency, output = (
        x.resolve() for x in (args.metadata_manifest, args.coordinate_manifest,
                              args.mapping_manifest, args.dependency_dir, args.out_dir))
    if (any(not x.is_relative_to(root / 'data/interim') for x in
            (metadata_path, coord_path, mapping_path, dependency, output))
            or output.exists() or shutil.disk_usage(root).free < 130 * 2**30):
        parser.error('ignored inputs, fresh output, disk reserve required')
    if (sha(metadata_path) != MANIFEST_SHA256 or sha(coord_path) != COORD_SHA256
            or sha(mapping_path) != MAPPING_SHA256):
        raise ValueError('frozen source/coordinate/mapping hashes changed')
    sys.path.insert(0, str(dependency))
    import numpy as np
    import numcodecs
    from numcodecs.blosc import _cbuffer_sizes, set_nthreads
    set_nthreads(1)
    metadata, coordinates, mapping = (json.loads(path.read_text()) for path in
                                      (metadata_path, coord_path, mapping_path))
    if (coordinates['source_member_variable_axes_equal'] is not True
            or coordinates['metadata_sha256'] != MANIFEST_SHA256
            or mapping['status'] != 'verified_peeps_native_rainfed_maize_center_mapping_not_exposure'):
        raise ValueError('source coordinate or crop mapping gate differs')
    mapping_npz = mapping_path.parent / 'mapping.npz'
    if sha(mapping_npz) != mapping['mapping_sha256']:
        raise ValueError('crop mapping array changed')
    with np.load(mapping_npz) as saved:
        ii = saved['ii'].astype(int)
        jj = saved['jj'].astype(int)
        hectares = saved['hectares'].astype(float)
    if (len(ii) != 30821 or len(jj) != len(ii) or len(hectares) != len(ii)
            or not np.all((0 <= ii) & (ii < 192)) or not np.all((0 <= jj) & (jj < 384))):
        raise ValueError('mapped crop-center dimensions differ')
    chunk_records = []
    context = ssl.create_default_context(cafile=certifi.where())
    for member in (args.member,):
        matches = [x for x in metadata['records'] if x['variable'] == 'pr' and x['member_id'] == member]
        if len(matches) != 1:
            raise ValueError('source precipitation member not unique')
        record = matches[0]
        meta_file = metadata_path.parent / record['metadata_file']
        if sha(meta_file) != record['metadata_sha256']:
            raise ValueError('source store metadata changed')
        spec = json.loads(meta_file.read_text())['metadata']['pr/.zarray']
        if (spec['dtype'] != '<f4' or spec['filters'] is not None
                or spec['order'] != 'C' or spec['compressor']['id'] != 'blosc'
                or spec['chunks'][1:] != [192, 384] or spec['shape'] != [1032, 192, 384]):
            raise ValueError('source climate array layout differs')
        first = spec['chunks'][0]
        selected = sorted({((year - 2015) * 12 + month) // first
                           for year in YEARS for month in range(12)})
        frozen_chunks = [0, 1] if member == MEMBERS[0] else [0, 4]
        if selected != frozen_chunks or args.chunk_index not in frozen_chunks:
            raise ValueError('preregistered climate chunk indices changed')
        chunk_years = [year for year in YEARS
                       if all(((year - 2015) * 12 + month) // first == args.chunk_index
                              for month in range(12))]
        if len(chunk_years) != 1:
            raise ValueError('selected chunk not exactly one complete source year')
        direct = {year: np.empty((12, len(ii)), dtype=np.float64) for year in chunk_years}
        for chunk_index in (args.chunk_index,):
            key = f'{chunk_index}.0.0'
            url = record['metadata_url'].removesuffix('.zmetadata') + 'pr/' + key
            request = urllib.request.Request(url, headers={'User-Agent': 'GIVE-precipitation-research/1.0',
                                                           'Accept-Encoding': 'identity'})
            with urllib.request.urlopen(request, context=context, timeout=120) as response:
                if response.status != 200 or response.headers.get('Content-Encoding'):
                    raise ValueError('unexpected source-climate HTTP response')
                declared = response.headers.get('Content-Length')
                if declared is not None and int(declared) > MAX_COMPRESSED:
                    raise ValueError('compressed source chunk exceeds cap before read')
                content = response.read(MAX_COMPRESSED + 1)
                source_hash = ','.join(response.headers.get_all('x-goog-hash', []))
            if len(content) > MAX_COMPRESSED or (declared and len(content) != int(declared)):
                raise ValueError('compressed source chunk length differs')
            crc_header = [item.strip()[7:] for item in source_hash.split(',')
                          if item.strip().startswith('crc32c=')]
            if crc_header and crc_header != [crc32c(content)]:
                raise ValueError('GCS source CRC32C disagrees')
            md5_header = [item.strip()[4:] for item in source_hash.split(',')
                          if item.strip().startswith('md5=')]
            if md5_header and md5_header != [base64.b64encode(hashlib.md5(content).digest()).decode()]:
                raise ValueError('GCS source MD5 disagrees')
            compressed_sha = hashlib.sha256(content).hexdigest()
            decoded_bytes, compressed_bytes, _ = _cbuffer_sizes(content)
            edge = min(first, 1032 - chunk_index * first)
            plane_bytes = 192 * 384 * 4
            if compressed_bytes != len(content) or decoded_bytes not in (first * plane_bytes,
                                                                          edge * plane_bytes):
                raise ValueError('Blosc decoded allocation differs')
            decoded = numcodecs.get_codec(spec['compressor']).decode(content)
            del content
            if len(decoded) != decoded_bytes:
                raise ValueError('decoded source chunk length differs')
            count = decoded_bytes // plane_bytes
            data = np.frombuffer(decoded, dtype='<f4').reshape(count, 192, 384)
            plane_counts = []
            sentinels = []
            for year in chunk_years:
                for month in range(12):
                    index = (year - 2015) * 12 + month
                    if index // first != chunk_index:
                        continue
                    local = index - chunk_index * first
                    plane = data[local]
                    if not np.isfinite(plane).all() or np.any(plane == spec['fill_value']):
                        raise ValueError('source rainfall missing or nonfinite')
                    plane_counts.append({'year': year, 'month': month + 1,
                                         'native_negative_cells': int(np.count_nonzero(plane < 0)),
                                         'native_missing_cells': 0})
                    if month == 0:
                        for i, j in ((0, 0), (46, 96), (96, 192), (191, 383)):
                            byte_offset = 4 * (local * 192 * 384 + i * 384 + j)
                            scalar = struct.unpack_from('<f', decoded, byte_offset)[0]
                            if scalar != float(plane[i, j]):
                                raise ValueError('independent scalar byte unpack disagrees')
                            sentinels.append({'year': year, 'month': 1, 'i': i, 'j': j,
                                              'source_flux_kg_m2_s': scalar})
                    direct[year][month] = (plane[ii, jj].astype(np.float64)
                                           * 86400 * calendar.monthrange(year, month + 1)[1])
            chunk_records.append({'member': member, 'chunk_index': chunk_index,
                                  'url': url, 'compressed_bytes': compressed_bytes,
                                  'compressed_sha256': compressed_sha,
                                  'gcs_crc32c_verified': bool(crc_header),
                                  'gcs_md5_verified': bool(md5_header),
                                  'decoded_bytes': decoded_bytes,
                                  'selected_plane_counts': plane_counts,
                                  'scalar_buffer_sentinels': sentinels})
            del plane, data, decoded
            print('decoded', member, chunk_index, compressed_bytes, flush=True)
    output.mkdir(parents=True)
    arrays = {'hectares': hectares, 'ii': ii, 'jj': jj}
    for year in chunk_years:
        arrays[f'{member}_{year}_monthly_mm'] = direct[year]
    saved_path = output / 'direct_crop_center_monthly_mm.npz'
    np.savez_compressed(saved_path, **arrays)
    result = {'status': 'single_member_single_chunk_direct_mpi_crop_rainfall_not_scored',
              'years': chunk_years, 'members': [member], 'chunk_index': args.chunk_index,
              'metadata_manifest_sha256': MANIFEST_SHA256,
              'coordinate_manifest_sha256': COORD_SHA256,
              'mapping_manifest_sha256': MAPPING_SHA256,
              'direct_arrays_sha256': sha(saved_path),
              'crop_center_count': len(ii), 'total_rainfed_maize_area_ha': float(hectares.sum()),
              'chunks': chunk_records, 'yield_damage_scc_estimated': False}
    (output / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'status': result['status'], 'chunks':
                      [{k: row[k] for k in ('member', 'chunk_index', 'compressed_bytes', 'decoded_bytes',
                                             'gcs_crc32c_verified')}
                       for row in chunk_records]}))


if __name__ == '__main__':
    main()
