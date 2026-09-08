"""New regional request contract, reusing genuine parent source identity checks."""
import argparse
import json
from pathlib import Path

from prepare_heat_subset_pilot import json_request, validate_and_prepare, SERVICE
from summarize_contiguous_climate_contrasts import ROOT, sha256

PROTOCOL = 'US_PAIRED_REGIONAL_ACQUISITION_PROTOCOL_20260908.md'
BANDS = {'south': [-109.5, -74.5, 25.5, 33.5], 'central': [-109.5, -74.5, 33.5, 41.5],
         'north': [-109.5, -74.5, 41.5, 49.5]}
SOURCE_IDS = {'obsclim': {'pr': 'ce7b96db-96cf-4d8e-a406-704338415eaa',
    'tas': 'ae8ab033-cea9-4fca-a275-5c46533ec970', 'tasmax': '3e990c11-804c-4113-9fb7-2f8af30bf90c'},
    'counterclim': {'pr': '0cf6af1f-14c6-4625-b89a-68352da58765',
    'tas': 'efcda79c-cf3f-428f-9ca2-45481cd13631', 'tasmax': 'db109b0d-5f70-489d-9ae9-36a0c343279f'}}


def parent_and_payload(config, dataset=None):
    if config.get('role') != 'registered_us_paired_regional_climate_request' or config.get('protocol_sha256') != sha256(ROOT/PROTOCOL):
        raise ValueError('regional request protocol differs')
    band = config['band']
    if band not in BANDS or config['bbox_west_east_south_north'] != BANDS[band]:
        raise ValueError('unregistered regional bounds')
    path = (ROOT/config['parent_source_config']).resolve()
    if not path.is_relative_to(ROOT/'config') or sha256(path) != config['parent_source_config_sha256']:
        raise ValueError('parent source config identity differs')
    parent = json.loads(path.read_text())
    scenario = parent['specifiers']['climate_scenario']
    if parent['specifiers']['climate_forcing'] != 'gswp3-w5e5' or scenario not in ('obsclim', 'counterclim'):
        raise ValueError('regional forcing differs')
    variable = parent['specifiers']['climate_variable']
    if parent['dataset_id'] != SOURCE_IDS[scenario].get(variable) or parent['dataset_version'] != ('20211021' if scenario == 'obsclim' else '20220506'):
        raise ValueError('regional dataset identity/version differs')
    if parent['expected_start_year'] not in (1981, 1991, 2001) or parent['expected_end_year'] != parent['expected_start_year']+9:
        raise ValueError('regional source period differs')
    for flag in ('source_averaging_authorized', 'damage_or_scc_authorized'):
        if config.get(flag) is not False:
            raise ValueError('regional scientific gate differs')
    if dataset is not None:
        # The real, unchanged parent is checked only for catalog/source identity.
        # Its old spatial payload is deliberately NOT submitted or relabeled.
        validate_and_prepare(parent, dataset)
    return parent, dict(paths=[parent['source_path']], operations=[dict(operation='select_bbox',
        bbox=BANDS[band], compute_mean=False, output_csv=False)])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--submit', action='store_true')
    args = parser.parse_args()
    path = args.config.resolve()
    if not path.is_relative_to(ROOT/'config') or args.out.exists() or args.out.with_suffix('.partial').exists():
        raise ValueError('registered config and fresh request receipt required')
    config = json.loads(path.read_text())
    parent, _ = parent_and_payload(config)
    dataset, digest = json_request(f'https://data.isimip.org/api/v1/datasets/{parent["dataset_id"]}/')
    _, payload = parent_and_payload(config, dataset)
    result = dict(role='registered_us_paired_regional_source_request', config_path=str(path.relative_to(ROOT)),
        config_sha256=sha256(path), protocol_sha256=sha256(ROOT/PROTOCOL), code_sha256=sha256(Path(__file__)),
        parent_source_config=config['parent_source_config'], parent_source_config_sha256=config['parent_source_config_sha256'],
        parent_catalogue_check_not_parent_bbox_submission=True, source_checks_passed=True,
        catalogue_response_sha256=digest, payload=payload, source=parent,
        status='prepared_not_submitted', climate_bytes_downloaded=0, causal_or_scc_result=False)
    partial = args.out.with_suffix('.partial')
    partial.write_text(json.dumps(result, indent=2)+'\n')
    if args.submit:
        response, digest = json_request(SERVICE, payload)
        result.update(status='server_request_returned', service_response=response, service_response_sha256=digest)
    partial.write_text(json.dumps(result, indent=2)+'\n')
    partial.replace(args.out)
    print(result['status'], result.get('service_response'))


if __name__ == '__main__':
    main()
