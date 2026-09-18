#!/usr/bin/env python3
"""Stream hash-pinned author PEEPS catalog; retain only MPI source rows."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import shutil
import ssl
import urllib.request

import certifi


COMMIT = 'd4ed4c479f5399015708135558daa382bbbc2da0'
SIZE = 22_939_452
GIT_BLOB = 'c1ce147ecdd0eac37648a4b0473f1589bf411c1f'
URL = f'https://raw.githubusercontent.com/JGCRI/linear_pattern_scaling/{COMMIT}/pangeo_table.csv'


def selected_row(row):
    return (row['model'] == 'MPI-ESM1-2-HR'
            and row['experiment'] in ('historical', 'ssp585')
            and row['variable'] in ('pr', 'tas')
            and row['domain'] == 'Amon')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    project = Path(__file__).resolve().parents[1]
    output = args.output.resolve()
    if (not output.is_relative_to(project / 'data/interim') or output.exists()
            or shutil.disk_usage(project).free < 130 * 2**30):
        parser.error('fresh ignored output and >=130 GiB free disk required')
    source_sha = hashlib.sha256()
    blob_sha = hashlib.sha1(b'blob ' + str(SIZE).encode() + b'\0')
    read_bytes = 0
    selected = []
    rows = 0
    request = urllib.request.Request(URL, headers={'User-Agent': 'GIVE-precipitation-research/1.0',
                                                    'Accept-Encoding': 'identity'})
    with urllib.request.urlopen(request, context=ssl.create_default_context(cafile=certifi.where()),
                                timeout=60) as response:
        if response.status != 200 or response.headers.get('Content-Encoding'):
            raise ValueError('unexpected source HTTP response')
        def decoded_lines():
            nonlocal read_bytes
            while True:
                line = response.readline(32_769)
                if not line:
                    break
                read_bytes += len(line)
                if len(line) > 32_768 or read_bytes > SIZE:
                    raise ValueError('catalog line or size bound exceeded')
                source_sha.update(line)
                blob_sha.update(line)
                yield line.decode('utf-8')
        reader = csv.DictReader(decoded_lines())
        if not {'model', 'experiment', 'ensemble', 'variable', 'domain', 'zstore'}.issubset(reader.fieldnames):
            raise ValueError('unexpected author catalog schema')
        for row in reader:
            rows += 1
            if selected_row(row):
                if len(selected) >= 2_000 or not row['zstore'].startswith('gs://cmip6/'):
                    raise ValueError('selected source row bound or host failed')
                selected.append({key: row[key] for key in
                                 ('model', 'experiment', 'ensemble', 'variable', 'domain', 'zstore')})
    if read_bytes != SIZE or blob_sha.hexdigest() != GIT_BLOB or not selected:
        raise ValueError('frozen author catalog size/hash or selection failed')
    counts = []
    for experiment in ('historical', 'ssp585'):
        for variable in ('pr', 'tas'):
            subset = [x for x in selected if x['experiment'] == experiment and x['variable'] == variable]
            counts.append({'experiment': experiment, 'variable': variable, 'rows': len(subset),
                           'ensembles': sorted({x['ensemble'] for x in subset}),
                           'stores': sorted({x['zstore'] for x in subset})})
    result = {'status': 'author_catalog_mpi_source_inventory_only',
              'source_url': URL, 'source_bytes': read_bytes,
              'source_sha256': source_sha.hexdigest(), 'source_git_blob': GIT_BLOB,
              'catalog_rows': rows, 'selection': 'MPI-ESM1-2-HR; historical/ssp585; pr/tas; Amon; all ensemble rows',
              'selected_rows': len(selected), 'counts': counts, 'selected': selected,
              'climate_payload_read': False, 'yield_damage_scc_estimated': False}
    payload = json.dumps(result, indent=2) + '\n'
    if len(payload.encode()) > 2 * 2**20:
        raise ValueError('selected metadata exceeds cap')
    output.write_text(payload)
    print(json.dumps({'status': result['status'], 'catalog_rows': rows,
                      'selected_rows': len(selected), 'counts':
                      [{k: v for k, v in item.items() if k != 'stores'} for item in counts]}))


if __name__ == '__main__':
    main()
