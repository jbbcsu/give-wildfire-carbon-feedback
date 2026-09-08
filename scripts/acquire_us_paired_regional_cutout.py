"""Acquire one registered regional subset under standing data authorization."""
import argparse
import json
from pathlib import Path
import shutil
import urllib.request
import zipfile
from prepare_us_paired_regional_cutout import ROOT, PROTOCOL, sha256, parent_and_payload, json_request
from acquire_registered_heat_cutout import check_archive_identity
from run_authorized_heat_subset_pilot import stream_copy, inspect_archive, NoRedirect
from validate_us_paired_regional_cutout import validate

BUDGET = 64*2**20


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--request-receipt', type=Path, required=True)
    parser.add_argument('--out-dir', type=Path, required=True)
    args = parser.parse_args()
    path, out = args.config.resolve(), args.out_dir.resolve()
    if not path.is_relative_to(ROOT/'config') or not out.is_relative_to(ROOT/'data/interim') or out.exists():
        raise ValueError('registered config and fresh ignored output required')
    config, request = json.loads(path.read_text()), json.loads(args.request_receipt.read_text())
    parent, _ = parent_and_payload(config)
    if request['config_sha256'] != sha256(path) or request['source_checks_passed'] is not True:
        raise ValueError('regional request identity differs')
    dataset, dataset_hash = json_request(f'https://data.isimip.org/api/v1/datasets/{parent["dataset_id"]}/')
    _, payload = parent_and_payload(config, dataset)
    if payload != request['payload'] or parent != request['source']:
        raise ValueError('regional source/payload changed')
    job_id = request['service_response']['id']
    job_url = request['service_response']['job_url']
    if job_url != f'https://files.isimip.org/api/v2/{job_id}':
        raise ValueError('regional job URL differs')
    job, job_hash = json_request(job_url)
    if job['id'] != job_id:
        raise ValueError('regional job identity differs')
    if job['status'] != 'finished':
        print('Registered job is not ready:', job['status'], '; no download performed')
        return
    url = job['file_url']
    check_archive_identity(url, job_id, 1, 'preflight')
    opener = urllib.request.build_opener(NoRedirect)
    with opener.open(urllib.request.Request(url, method='HEAD', headers={'Accept-Encoding': 'identity'}), timeout=30) as response:
        if response.status != 200:
            raise ValueError('archive HEAD status differs')
        size, etag = int(response.headers.get('Content-Length', '0')), response.headers.get('ETag')
    check_archive_identity(url, job_id, size, etag)
    if shutil.disk_usage(ROOT).free-BUDGET < 130*2**30:
        raise ValueError('protected free-space floor would be breached')
    out.mkdir()
    result = dict(status='registered_not_downloaded', authorization='standing user project-data authorization',
        config_path=str(path.relative_to(ROOT)), config_sha256=sha256(path), source_contract=parent, regional_contract=config,
        request_receipt_sha256=sha256(args.request_receipt), catalogue_response_sha256=dataset_hash,
        job_id=job_id, job_response_sha256=job_hash, archive_url=url, archive_bytes=size, archive_etag=etag,
        initial_free_bytes=shutil.disk_usage(ROOT).free, additional_disk_budget_bytes=BUDGET,
        protocol_sha256=sha256(ROOT/PROTOCOL), code_sha256=sha256(Path(__file__)), causal_or_scc_result=False,
        helper_hashes={n: sha256(ROOT/'scripts'/n) for n in ['prepare_us_paired_regional_cutout.py',
            'validate_us_paired_regional_cutout.py', 'run_authorized_heat_subset_pilot.py', 'acquire_registered_heat_cutout.py']})
    def budget(incoming=0):
        used = sum(p.stat().st_size for p in out.iterdir() if p.is_file())
        if used+incoming > BUDGET-128*1024 or shutil.disk_usage(ROOT).free-incoming < 130*2**30:
            raise ValueError('regional disk budget exceeded')
    def save():
        budget()
        (out/'receipt.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    save()
    try:
        with opener.open(urllib.request.Request(url, headers={'Accept-Encoding':'identity'}), timeout=30) as response:
            if response.status != 200 or int(response.headers.get('Content-Length', '0')) != size or response.headers.get('ETag') != etag:
                raise ValueError('archive GET differs from HEAD')
            result['archive_sha256'] = stream_copy(response, out/'cutout.zip', size, budget)
        variable = parent['specifiers']['climate_variable']
        climate = out/f'{variable}_cutout.nc'
        with zipfile.ZipFile(out/'cutout.zip') as archive:
            member = inspect_archive(archive, size)
            result['archive_member'] = member.filename
            with archive.open(member) as stream:
                result['climate_sha256'] = stream_copy(stream, climate, member.file_size, budget)
        result['content_validation'] = validate(climate, config)
        result.update(status='regional_paired_climate_content_validated',
                      retained_bytes_before_final_receipt=sum(p.stat().st_size for p in out.iterdir() if p.is_file()))
        save()
        print('Regional climate content validated:', config['band'], variable, parent['expected_start_year'], size, 'archive bytes')
    except Exception as error:
        result.update(status='failed_preserved', error_type=type(error).__name__, error=str(error))
        (out/'failure.json').write_text(json.dumps(result, indent=2)+'\n')
        raise


if __name__ == '__main__':
    main()
