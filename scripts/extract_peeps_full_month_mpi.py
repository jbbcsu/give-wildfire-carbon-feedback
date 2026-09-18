#!/usr/bin/env python3
"""Stream all twelve author-released MPI SSP585 monthly pr coefficients.

The 3.2 GB source is never saved. The whole received stream must match the
author archive MD5 before the selected member receipt is marked complete.
"""
import argparse
import certifi
import hashlib
import json
import os
from pathlib import Path
import ssl
import sys
import tarfile
from urllib.request import Request, urlopen

from run_bounded_job import run
from extract_peeps_december_pilot import URL, RECORD, OUTER_SIZE, OUTER_MD5, MAX_MEMBER_BYTES


MODEL = 'MPI-ESM1-2-HR'
SCENARIO = 'ssp585'
MONTHS = ('jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec')
MAX_SELECTED_BYTES = 48 * 1024 * 1024


class HashingReader:
    def __init__(self, source):
        self.source = source
        self.digest = hashlib.md5()
        self.bytes_read = 0

    def read(self, size=-1):
        data = self.source.read(size)
        self.digest.update(data)
        self.bytes_read += len(data)
        return data


def save_member(inner, target_name, destination):
    for member in inner:
        if member.name != target_name:
            continue
        if not member.isfile() or not (0 < member.size <= MAX_MEMBER_BYTES):
            raise ValueError('selected PEEPS member outside size/type bound')
        if destination.exists():
            raise FileExistsError('duplicate selected monthly member')
        selected = inner.extractfile(member)
        if selected is None:
            raise ValueError('selected PEEPS member unreadable')
        digest = hashlib.sha256()
        remaining = member.size
        partial = destination.with_name(destination.name + '.partial')
        if partial.exists():
            raise FileExistsError('stale partial selected file')
        try:
            with partial.open('xb') as output:
                while remaining:
                    block = selected.read(min(1024 * 1024, remaining))
                    if not block:
                        raise EOFError('selected PEEPS member truncated')
                    output.write(block)
                    digest.update(block)
                    remaining -= len(block)
            with partial.open('rb') as check:
                magic = check.read(8)
            if not (magic.startswith(b'CDF') or magic == b'\x89HDF\r\n\x1a\n'):
                raise ValueError('selected member is not NetCDF')
            os.replace(partial, destination)
        except BaseException:
            partial.unlink(missing_ok=True)
            raise
        return {'name': target_name, 'bytes': member.size, 'sha256': digest.hexdigest()}
    raise LookupError(f'author month archive lacks {target_name}')


def extract_stream(source, output_dir, months=MONTHS, expected_size=OUTER_SIZE, expected_md5=OUTER_MD5):
    output_dir = Path(output_dir)
    reader = HashingReader(source)
    wanted = {f'outputs/{m}_patterns.tar.gz': m for m in months}
    seen = {}
    total = 0
    with tarfile.open(fileobj=reader, mode='r|gz') as outer:
        for nested_member in outer:
            month = wanted.get(nested_member.name)
            if month is None:
                continue
            if month in seen or not nested_member.isfile() or nested_member.size <= 0:
                raise ValueError('duplicate or invalid PEEPS month archive')
            nested_stream = outer.extractfile(nested_member)
            if nested_stream is None:
                raise ValueError('PEEPS nested month archive unreadable')
            target = f'{MODEL}_{SCENARIO}_pr_monthly_patterns_{month}.nc'
            with tarfile.open(fileobj=nested_stream, mode='r|gz') as inner:
                selected = save_member(inner, target, output_dir / target)
            total += selected['bytes']
            if total > MAX_SELECTED_BYTES:
                raise ValueError('selected monthly files exceed 48 MiB internal cap')
            seen[month] = selected
    # Ensure MD5 covers all bytes, including any source footer/trailing bytes
    # not requested by tarfile's end-of-archive detection.
    while reader.read(1024 * 1024):
        pass
    if set(seen) != set(months):
        raise ValueError('missing one or more published month archives')
    if reader.bytes_read != expected_size or reader.digest.hexdigest() != expected_md5:
        raise ValueError('published outer archive byte count or MD5 mismatch')
    return {'status': 'whole_author_archive_md5_verified_selected_members_acquired',
            'source_record': RECORD, 'source_url': URL, 'source_license': 'CC-BY-4.0',
            'outer_archive_bytes': reader.bytes_read, 'outer_archive_md5': reader.digest.hexdigest(),
            'model': MODEL, 'scenario': SCENARIO, 'variable': 'pr',
            'selected_months': list(months), 'selected_total_bytes': total,
            'selected_members': [seen[m] for m in months],
            'yield_damage_scc_estimated': False}


def worker(output_dir):
    request = Request(URL, headers={'User-Agent': 'GIVE-precipitation-SCC-research/1.0'})
    context = ssl.create_default_context(cafile=certifi.where())
    with urlopen(request, timeout=90, context=context) as response:
        if response.status != 200 or int(response.headers.get('Content-Length', '-1')) != OUTER_SIZE:
            raise ValueError('unexpected PEEPS complete archive response')
        result = extract_stream(response, output_dir)
    receipt = Path(output_dir) / 'selected_months_receipt.json'
    receipt.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'status': result['status'], 'selected_months': result['selected_months'],
                      'selected_total_bytes': result['selected_total_bytes']}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', required=True, type=Path)
    parser.add_argument('--worker', action='store_true')
    args = parser.parse_args()
    project = Path(__file__).resolve().parents[1]
    output_dir = args.output_dir.resolve()
    if not output_dir.is_relative_to(project / 'data/interim') or output_dir == project / 'data/interim':
        parser.error('output must be a specific ignored project interim child')
    if args.worker:
        worker(output_dir)
        return
    if output_dir.exists():
        parser.error('fresh output directory required')
    output_dir.mkdir(parents=True)
    result = run([sys.executable, str(Path(__file__).resolve()), '--worker',
                  '--output-dir', str(output_dir)],
                 output_dir / 'monitor_receipt.json', output_dir / 'run.log',
                 max_mib=512, min_free_gib=130, max_log_mib=2,
                 interval=0.2, write_paths=[output_dir], max_new_disk_mib=64)
    print(json.dumps(result))
    if result['status'] != 'completed':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
