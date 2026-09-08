"""Compact support evidence with reproducibility hashes; no crop-year rows."""
import argparse
import json
from pathlib import Path
import shutil
from summarize_contiguous_climate_contrasts import ROOT, sha256


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise ValueError('new output required')
    path = ROOT / 'data/interim/paired_weather_support_20260908/result.json'
    result = json.loads(path.read_text())
    if result['status'] != 'paired_weather_support_diagnostic_validated':
        raise ValueError('support diagnostic incomplete')
    if result['code_sha256'] != sha256(ROOT / 'scripts/diagnose_paired_weather_support.py'):
        raise ValueError('diagnostic code changed after run')
    if result['protocol_sha256'] != sha256(ROOT / 'PAIRED_WEATHER_SUPPORT_PROTOCOL_20260908.md'):
        raise ValueError('protocol changed after run')
    result['full_result'] = dict(path=str(path.relative_to(ROOT)), sha256=sha256(path), bytes=path.stat().st_size)
    for crop in result['crops']:
        for family in crop['families'].values():
            del family['cell_diagnostics']
    result['jobs'] = []
    for stem in ['paired_weather_support_tests_20260908', 'paired_weather_support_20260908']:
        resource = ROOT / f'outputs/{stem}_resource.json'
        log = ROOT / f'outputs/{stem}.log'
        receipt = json.loads(resource.read_text())
        if receipt['status'] != 'completed':
            raise ValueError('support job did not complete')
        result['jobs'].append(dict(resource=dict(path=str(resource.relative_to(ROOT)), sha256=sha256(resource), content=receipt),
                                   log=dict(path=str(log.relative_to(ROOT)), sha256=sha256(log))))
    result['test_script_sha256'] = sha256(ROOT / 'scripts/test_paired_weather_support.py')
    result['export_script_sha256'] = sha256(Path(__file__))
    result['free_bytes_at_export'] = shutil.disk_usage(ROOT).free
    args.out.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    for crop in result['crops']:
        print(crop['crop'])
        for name, value in crop['families'].items():
            print(name, value['rows'], value['cells'], {k: v['rows'] for k, v in value['flags'].items()},
                  'constant cells', value['all_constant_cells'], 'zero thresholds', value['zero_distance_threshold_cells'])


if __name__ == '__main__':
    main()
