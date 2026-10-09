"""Small public aggregates with raw climate, NASS rows and covariance omitted."""
import argparse
import json
from pathlib import Path
import re
import shutil
from summarize_contiguous_climate_contrasts import ROOT, sha256


def read(path):
    p = ROOT/path
    return dict(path=path, sha256=sha256(p), content=json.loads(p.read_text()))


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--out', type=Path, required=True)
    args = p.parse_args()
    if args.out.exists():
        raise ValueError('fresh export required')
    regional = 'data/interim/us_regional_county_climate_20260908'
    response = 'data/interim/us_source_matched_response_20260908'
    climate, comparison = read(regional+'/receipt.json'), read(regional+'/comparison.json')
    result, validation = read(response+'/result.json'), read(response+'/numerical_validation_explicit_reductions.json')
    if climate['content']['status'] != 'us_regional_county_climate_inputs_validated' or comparison['content']['status'] != 'us_regional_county_climate_comparison_validated':
        raise ValueError('regional evidence not validated')
    if validation['content']['status'] != 'us_source_matched_numerical_checks_complete' or validation['content']['result']['sha256'] != result['sha256']:
        raise ValueError('response numerical validation differs')
    if validation['content']['code_sha256'] != sha256(ROOT/'scripts/validate_us_source_matched_response.py'):
        raise ValueError('numerical validator changed')
    for field in ('county_weights', 'area_audits'):
        climate['content'][field+'_record_count'] = len(climate['content'].pop(field))
    for crop in comparison['content']['comparisons']:
        for contrast in crop['contrasts']:
            for kind in ('core', 'shape'):
                if contrast[kind] is not None:
                    del contrast[kind]['annual_equal_county_means']
    for estimate in result['content']['estimates']:
        if estimate['status'] == 'estimated':
            del estimate['result']['covariance_county_cluster']
    dirs = [ROOT/regional, ROOT/response, ROOT/'data/interim/us_paired_regional_requests_20260908']
    acquisitions = []
    for band in ('south', 'central', 'north'):
        for scenario in ('obsclim', 'counterclim'):
            for var in ('pr', 'tas', 'tasmax'):
                for year in (1981, 1991, 2001):
                    path = f'data/interim/us_{band}_{scenario}_{var}_{year}_20260908'
                    dirs.append(ROOT/path)
                    source = read(path+'/receipt.json')
                    r = source['content']
                    if r['status'] != 'regional_paired_climate_content_validated' or r['content_validation']['valid_domain_missing_values'] != 0:
                        raise ValueError('regional acquisition not validated')
                    acquisitions.append(dict(path=source['path'], sha256=source['sha256'],
                        band=band, scenario=scenario, variable=var, first_year=year,
                        resource_doi=r['source_contract']['resource_doi'],
                        climate_sha256=r['climate_sha256'], validated_missing_values=0))
    patterns = [r'us_(south|central|north)_(obsclim|counterclim)_(pr|tas|tasmax)_(1981|1991|2001)_(request|acquisition)_20260908(_v\d+)?_resource.json',
                r'us_(regional|source_matched|paired_regional).*20260908(_v\d+)?_resource.json']
    jobs = []
    for path in sorted((ROOT/'outputs').glob('*resource.json')):
        if any(re.fullmatch(pattern, path.name) for pattern in patterns):
            item = read(str(path.relative_to(ROOT)))
            log = path.with_name(path.name.replace('_resource.json', '.log'))
            item['log_sha256'] = sha256(log) if log.exists() else None
            jobs.append(item)
    payloads = {f for d in dirs for f in d.rglob('*') if f.is_file()}
    special = ROOT/'data/interim/us_paired_county_climate_20260908/central_counterclim_pr_1981_request.json'
    payloads.add(special)
    content = dict(role='regional_climate_and_exploratory_source_matched_response', causal_or_scc_result=False,
        national_representativeness_claimed=False, climate=climate, comparison=comparison,
        response=result, numerical_validation=validation,
        first_numerical_warning_run_preserved=read(response+'/numerical_validation.json'),
        input_manifest=read(response+'/input_manifest.json'), acquisitions=acquisitions, jobs=jobs,
        sampled_peak_job_rss_bytes=max(j['content']['sampled_peak_group_rss_bytes'] for j in jobs),
        cumulative_regional_acquisition_and_response_retained_bytes_before_export=sum(f.stat().st_size for f in payloads),
        storage_scope='54 regional acquisition directories, regional request records, regional features and source-response outputs; excludes previous pilots and resource logs',
        free_bytes_at_export=shutil.disk_usage(ROOT).free,
        projection='Original hash-bound artifacts retain county weights, annual climate series and coefficient covariances; this public aggregate omits those fields.',
        code_sha256=sha256(Path(__file__)))
    args.out.write_text(json.dumps(content, indent=2, allow_nan=False)+'\n')
    print('Acquisitions', len(acquisitions), 'jobs', len(jobs), 'peak_MiB', content['sampled_peak_job_rss_bytes']/2**20,
          'retained_MiB', content['cumulative_regional_acquisition_and_response_retained_bytes_before_export']/2**20,
          'aggregate_bytes', args.out.stat().st_size, 'free_GiB', content['free_bytes_at_export']/2**30)


if __name__ == '__main__':
    main()
