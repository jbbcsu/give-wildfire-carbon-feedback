"""Publish small, source-bound county feasibility/climate evidence, not raw data."""
import argparse
import json
from pathlib import Path
import shutil
from summarize_contiguous_climate_contrasts import ROOT, sha256


def read(path):
    p = ROOT/path
    return dict(path=path, sha256=sha256(p), content=json.loads(p.read_text()))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise ValueError('fresh export required')
    inventory = read('data/interim/us_paired_overlap_20260908/result.json')
    r = inventory['content']
    geo = r.pop('county_geography')
    r['county_bounds_inventory'] = dict(west=min(g['bounds_lonlat'][0] for g in geo),
        east=max(g['bounds_lonlat'][2] for g in geo), south=min(g['bounds_lonlat'][1] for g in geo),
        north=max(g['bounds_lonlat'][3] for g in geo),
        counties_by_state_fips={s: sum(g['county_geoid'][:2] == s for g in geo) for s in sorted({g['county_geoid'][:2] for g in geo})})
    climate = read('data/interim/us_paired_county_climate_20260908/receipt.json')
    c = climate['content']
    weights = c.pop('county_weights')
    c['weight_rows'] = len(weights)
    comparison = read('data/interim/us_paired_county_climate_20260908/comparison.json')
    for crop in comparison['content']['comparisons']:
        for contrast in crop['contrasts']:
            for family in ('core', 'shape'):
                if contrast[family] is not None:
                    del contrast[family]['annual_equal_county_means']
    comparison['publication_projection'] = 'Annual series remain in the hash-bound ignored original; aggregate contrasts retained here.'
    for record, expected, code in [(inventory, 'existing_us_paired_climate_overlap_inventoried', 'inventory_us_paired_climate_overlap.py'),
                                    (climate, 'us_paired_county_climate_inputs_validated', 'build_us_paired_county_climate.py'),
                                    (comparison, 'us_paired_county_climate_comparison_validated', 'compare_us_paired_county_climate.py')]:
        if record['content']['status'] != expected or record['content']['code_sha256'] != sha256(ROOT/'scripts'/code):
            raise ValueError('result status/code binding differs')
    jobs = []
    for stem in ['us_paired_overlap_tests_20260908', 'us_paired_overlap_20260908',
                 'us_paired_county_climate_tests_20260908', 'us_paired_county_climate_20260908',
                 'us_county_climate_comparison_tests_20260908', 'us_county_climate_comparison_20260908']:
        job = read(f'outputs/{stem}_resource.json')
        if job['content']['status'] != 'completed':
            raise ValueError('unsuccessful analysis job')
        job['log_sha256'] = sha256(ROOT/f'outputs/{stem}.log')
        jobs.append(job)
    directories = ['data/interim/us_paired_overlap_20260908', 'data/interim/us_paired_county_climate_20260908']
    retained = sum(p.stat().st_size for d in directories for p in (ROOT/d).rglob('*') if p.is_file())
    result = dict(role='county_calendar_climate_source_and_detrending_benchmark', causal_or_scc_result=False,
                  inventory=inventory, climate=climate, comparison=comparison, jobs=jobs,
                  test_scripts={n: sha256(ROOT/'scripts'/n) for n in ['test_us_paired_climate_overlap.py',
                      'test_us_paired_county_climate.py', 'test_us_county_climate_comparison.py']},
                  retained_new_analysis_bytes_before_export=retained, free_bytes_at_export=shutil.disk_usage(ROOT).free,
                  code_sha256=sha256(Path(__file__)))
    args.out.write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print('Bounds', r['county_bounds_inventory'])
    print('Retained', retained, 'bytes; new aggregate', args.out.stat().st_size)
    for crop in comparison['content']['comparisons']:
        threshold = 29 if crop['crop'] == 'corn_grain' else 30
        for contrast in crop['contrasts']:
            print(crop['crop'], contrast['name'], 'heat', contrast['core']['differences'][f'stage2_tmax_exceedance_{threshold}c_c_days'], 'zero shape rows', crop['shape_excluded_county_years'])


if __name__ == '__main__':
    main()
