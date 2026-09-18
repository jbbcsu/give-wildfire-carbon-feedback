#!/usr/bin/env python3
"""Stream one author PEEPS December pattern or paired GMST file.

This pilot uses a bounded HTTP prefix of Zenodo record 7557622. It does not
verify the whole archive MD5; the selected NetCDF is still research input,
not a validated climate response or GIVE result.
"""
import argparse
import hashlib
import json
from pathlib import Path
import os
import ssl
import sys
import tarfile
from urllib.request import Request, urlopen

import certifi
from run_bounded_job import run


URL = 'https://zenodo.org/api/records/7557622/files/outputs.tar.gz/content'
RECORD = 'https://doi.org/10.5281/zenodo.7557622'
OUTER_SIZE = 3244457764
OUTER_MD5 = 'eed1a0e8a43bf915c78ec68d0f37e357'
RANGE_END = 283115519
INNER_NAME = 'outputs/dec_patterns.tar.gz'
GMST_INNER_NAME = 'outputs/global_temp.tar.gz'
ALLOWED_MODELS = ('MPI-ESM1-2-HR', 'MRI-ESM2-0', 'UKESM1-0-LL')
ALLOWED_SCENARIOS = ('historical', 'ssp126', 'ssp370', 'ssp585')
MAX_MEMBER_BYTES = 8 * 1024 * 1024


def extract_member(stream, target_name, destination, inner_name=INNER_NAME):
    """Read nested streaming tars and write exactly one basename match."""
    destination = Path(destination)
    partial = destination.with_name(destination.name + '.partial')
    if destination.exists() or partial.exists():
        raise FileExistsError('selected destination already exists')
    with tarfile.open(fileobj=stream, mode='r|gz') as outer:
        for outer_member in outer:
            if outer_member.name != inner_name:
                continue
            if not outer_member.isfile() or outer_member.size <= 0:
                raise ValueError('invalid nested monthly archive')
            nested_stream = outer.extractfile(outer_member)
            if nested_stream is None:
                raise ValueError('nested monthly archive unreadable')
            with tarfile.open(fileobj=nested_stream, mode='r|gz') as inner:
                for member in inner:
                    if member.name != target_name:
                        continue
                    if not member.isfile() or not (0 < member.size <= MAX_MEMBER_BYTES):
                        raise ValueError('selected member exceeds pilot cap')
                    selected_stream = inner.extractfile(member)
                    if selected_stream is None:
                        raise ValueError('selected member unreadable')
                    digest = hashlib.sha256()
                    remaining = member.size
                    try:
                        with partial.open('xb') as output:
                            while remaining:
                                block = selected_stream.read(min(1024 * 1024, remaining))
                                if not block:
                                    raise EOFError('selected member incomplete')
                                output.write(block)
                                digest.update(block)
                                remaining -= len(block)
                        if partial.stat().st_size != member.size:
                            raise ValueError('selected member size mismatch')
                        with partial.open('rb') as check:
                            magic = check.read(8)
                        if not (magic.startswith(b'CDF') or magic == b'\x89HDF\r\n\x1a\n'):
                            raise ValueError('selected member is not NetCDF')
                        os.replace(partial, destination)
                    except BaseException:
                        partial.unlink(missing_ok=True)
                        raise
                    return {'member_name': target_name, 'member_bytes': member.size,
                            'member_sha256': digest.hexdigest(),
                            'outer_month_archive_bytes': outer_member.size,
                            'netcdf_magic': magic.hex()}
            raise LookupError('selected member missing from nested archive')
    raise LookupError('selected nested archive missing from outer bundle')


def worker(model, scenario, kind, output_dir):
    output_dir = Path(output_dir)
    if kind == 'pr_dec':
        target_name = f'{model}_{scenario}_pr_monthly_patterns_dec.nc'
        inner_name, range_end = INNER_NAME, RANGE_END
        variable, month = 'pr', 'dec'
    elif kind == 'tgav':
        target_name = f'{model}_{scenario}_ensemble_avg_tgav.nc'
        inner_name, range_end = GMST_INNER_NAME, 1048575
        variable, month = 'tas_global_mean', None
    else:
        raise ValueError('unsupported published PEEPS member kind')
    destination = output_dir / target_name
    request = Request(URL, headers={'Range': f'bytes=0-{range_end}',
                                    'User-Agent': 'GIVE-precipitation-SCC-research/1.0'})
    # Python.org macOS Python may not have a populated system CA store.
    # Use certifi's public CA bundle; do not disable TLS verification.
    context = ssl.create_default_context(cafile=certifi.where())
    with urlopen(request, timeout=45, context=context) as response:
        expected_range = f'bytes 0-{range_end}/{OUTER_SIZE}'
        if response.status != 206 or response.headers.get('Content-Range') != expected_range:
            raise ValueError('server did not honor exact bounded range')
        if int(response.headers.get('Content-Length', '-1')) != range_end + 1:
            raise ValueError('unexpected response byte count')
        details = extract_member(response, target_name, destination, inner_name)
    receipt = {
        'status': 'selected_author_file_acquired_not_climate_validated',
        'source_record': RECORD, 'source_url': URL, 'source_license': 'CC-BY-4.0',
        'outer_archive_size_bytes': OUTER_SIZE, 'outer_archive_md5_expected_unverified': OUTER_MD5,
        'partial_http_range': f'bytes=0-{range_end}',
        'whole_outer_archive_checksum_verified': False,
        'model': model, 'scenario': scenario, 'variable': variable, 'month': month,
        'output_relative_to_project': str(destination.relative_to(Path(__file__).resolve().parents[1])),
        **details,
    }
    (output_dir / 'selected_member_receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', choices=ALLOWED_MODELS, required=True)
    parser.add_argument('--scenario', choices=ALLOWED_SCENARIOS, required=True)
    parser.add_argument('--kind', choices=('pr_dec', 'tgav'), default='pr_dec')
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--worker', action='store_true')
    args = parser.parse_args()
    project = Path(__file__).resolve().parents[1]
    output_dir = args.output_dir.resolve()
    if not output_dir.is_relative_to(project / 'data/interim') or output_dir == project / 'data/interim':
        parser.error('output must be a specific ignored data/interim child')
    if args.worker:
        worker(args.model, args.scenario, args.kind, output_dir)
        return
    if output_dir.exists():
        parser.error('fresh output directory required')
    output_dir.mkdir(parents=True)
    command = [sys.executable, str(Path(__file__).resolve()), '--worker',
               '--model', args.model, '--scenario', args.scenario,
               '--kind', args.kind,
               '--output-dir', str(output_dir)]
    result = run(command, output_dir / 'monitor_receipt.json',
                 output_dir / 'run.log', max_mib=512, min_free_gib=130,
                 max_log_mib=2, interval=0.2, write_paths=[output_dir],
                 max_new_disk_mib=64)
    print(json.dumps(result))
    if result['status'] != 'completed':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
