#!/usr/bin/env python3
"""Validate four source-matched raw-CMIP6 store metadata documents."""
import argparse
import base64
import hashlib
import json
import math
from pathlib import Path
import shutil
import ssl
import urllib.request

import certifi
import numpy as np


CATALOG_SHA256 = '518d0abae7c3257a34ed0e4b9ad3e513d7d5d2aa0b1afebe46cb6658380efff0'
MAX_META = 2 * 2**20


def checked_metadata(document, row):
    """Return a small validated source contract, without decoding payload."""
    meta = document['metadata']
    attrs = meta['.zattrs']
    expected = {'source_id': 'MPI-ESM1-2-HR', 'experiment_id': 'ssp585',
                'variant_label': row['ensemble'], 'grid_label': 'gn',
                'table_id': 'Amon'}
    if any(str(attrs.get(key, '')) != value for key, value in expected.items()):
        raise ValueError('source member/grid/table attributes differ')
    variable = row['variable']
    vattrs = meta[f'{variable}/.zattrs']
    array = meta[f'{variable}/.zarray']
    expected_units = {'pr': 'kg m-2 s-1', 'tas': 'K'}[variable]
    if vattrs.get('_ARRAY_DIMENSIONS') != ['time', 'lat', 'lon'] or vattrs.get('units') != expected_units:
        raise ValueError('variable dimensions or units differ')
    if len(array['shape']) != 3 or len(array['chunks']) != 3 or any(x <= 0 for x in array['shape'] + array['chunks']):
        raise ValueError('invalid source array shape/chunk')
    if array['shape'][1] != meta['lat/.zarray']['shape'][0] or array['shape'][2] != meta['lon/.zarray']['shape'][0]:
        raise ValueError('climate and coordinates dimension mismatch')
    if array['shape'][1:] != [192, 384]:
        raise ValueError('native grid not expected 192x384')
    if array['chunks'][1:] != [192, 384]:
        raise ValueError('spatially partial chunk requires different reader')
    calendar = meta['time/.zattrs'].get('calendar')
    if not calendar or not attrs.get('license'):
        raise ValueError('source calendar or license absent')
    chunk_bytes = math.prod(array['chunks']) * np.dtype(array['dtype']).itemsize
    if chunk_bytes > 192 * 2**20:
        raise ValueError('uncompressed chunk exceeds bounded reader design')
    return {'source_id': attrs['source_id'], 'experiment_id': attrs['experiment_id'],
            'member_id': attrs['variant_label'], 'grid_label': attrs['grid_label'],
            'variable': variable, 'units': expected_units, 'calendar': calendar,
            'shape': array['shape'], 'chunks': array['chunks'], 'dtype': array['dtype'],
            'uncompressed_chunk_bytes': chunk_bytes,
            'license': attrs['license'], 'institution_id': attrs.get('institution_id'),
            'time_units': meta['time/.zattrs'].get('units')}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('catalog', type=Path)
    parser.add_argument('--out-dir', type=Path, required=True)
    args = parser.parse_args()
    project = Path(__file__).resolve().parents[1]
    catalog_path, out_dir = args.catalog.resolve(), args.out_dir.resolve()
    if (not catalog_path.is_relative_to(project / 'data/interim')
            or not out_dir.is_relative_to(project / 'data/interim')
            or out_dir.exists() or shutil.disk_usage(project).free < 130 * 2**30):
        parser.error('ignored project input, fresh output and disk reserve required')
    if hashlib.sha256(catalog_path.read_bytes()).hexdigest() != CATALOG_SHA256:
        raise ValueError('frozen source catalog selection changed')
    catalog = json.loads(catalog_path.read_text())
    if (catalog['source_git_blob'] != 'c1ce147ecdd0eac37648a4b0473f1589bf411c1f'
            or catalog['source_sha256'] != '631ae6453fba8950e1f369d5fbd1199a4252c932c8ffa42372fe9d84d12e6304'):
        raise ValueError('author source catalog identity changed')
    rows = [row for row in catalog['selected'] if row['experiment'] == 'ssp585']
    keys = {(row['variable'], row['ensemble']) for row in rows}
    if keys != {(var, member) for var in ('pr', 'tas')
                for member in ('r1i1p1f1', 'r2i1p1f1')} or len(rows) != 4:
        raise ValueError('not exactly four source-matched stores')
    out_dir.mkdir(parents=True)
    records = []
    context = ssl.create_default_context(cafile=certifi.where())
    for row in sorted(rows, key=lambda item: (item['variable'], item['ensemble'])):
        store = row['zstore']
        prefix = 'gs://cmip6/CMIP6/ScenarioMIP/'
        if not store.startswith(prefix) or not store.endswith('/') or '/MPI-ESM1-2-HR/ssp585/' not in store:
            raise ValueError('unexpected GCS store identity')
        url = 'https://storage.googleapis.com/cmip6/' + store[len('gs://cmip6/'):] + '.zmetadata'
        request = urllib.request.Request(url, headers={'User-Agent': 'GIVE-precipitation-research/1.0',
                                                       'Accept-Encoding': 'identity'})
        with urllib.request.urlopen(request, context=context, timeout=60) as response:
            if response.status != 200 or response.headers.get('Content-Encoding'):
                raise ValueError('unexpected metadata HTTP response')
            payload = response.read(MAX_META + 1)
            if len(payload) > MAX_META:
                raise ValueError('metadata exceeds 2 MiB cap')
            server_hash = ','.join(response.headers.get_all('x-goog-hash', []))
        md5s = [part.strip()[4:] for part in server_hash.split(',') if part.strip().startswith('md5=')]
        if md5s and md5s != [base64.b64encode(hashlib.md5(payload).digest()).decode()]:
            raise ValueError('GCS metadata MD5 disagrees')
        document = json.loads(payload)
        contract = checked_metadata(document, row)
        name = f"{row['variable']}_{row['ensemble']}.zmetadata.json"
        (out_dir / name).write_bytes(payload)
        records.append({'source': row, 'metadata_url': url, 'metadata_file': name,
                        'metadata_bytes': len(payload), 'metadata_sha256': hashlib.sha256(payload).hexdigest(),
                        'server_md5_verified': bool(md5s), **contract})
    result = {'status': 'four_source_matched_mpi_store_metadata_validated_no_climate_payload',
              'catalog_sha256': CATALOG_SHA256, 'records': records,
              'climate_payload_read': False, 'yield_damage_scc_estimated': False}
    (out_dir / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'status': result['status'], 'stores':
                      [{k: item[k] for k in ('variable', 'member_id', 'shape', 'chunks',
                                             'uncompressed_chunk_bytes', 'calendar', 'server_md5_verified')}
                       for item in records]}))


if __name__ == '__main__':
    main()
