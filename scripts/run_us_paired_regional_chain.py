"""Finite persistent acquisition -> validated climate construction -> comparison.

This advances climate inputs only, not empirical crop damages/SCC. Errors stop
the chain with preserved artifacts. No Git operation or background detachment.
"""
import argparse
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from continue_us_paired_regional_acquisition import ROOT, fresh_job
from run_bounded_job import run


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--max-hours', type=float, default=6)
    args = parser.parse_args()
    if not 0 < args.max_hours <= 12:
        raise ValueError('finite local chain duration required')
    state_dir = ROOT/'data/interim/us_paired_regional_chain_20260908'
    state_dir.mkdir(exist_ok=True)
    state_path = state_dir/'state.json'
    with (state_dir/'chain.lock').open('a') as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        started = time.monotonic()
        state = dict(scope='regional_climate_inputs_and_comparison_only', crop_yield_estimated=False,
                     causal_or_scc_result=False, stage='starting', max_hours=args.max_hours,
                     pid=os.getpid(), started_at=datetime.now(timezone.utc).isoformat())
        def save(stage, **fields):
            state.update(stage=stage, updated_at=datetime.now(timezone.utc).isoformat(), **fields)
            state_path.write_text(json.dumps(state, indent=2)+'\n')
        def bounded(command, stem, paths):
            receipt, log, scratch = fresh_job(stem)
            r = run([sys.executable]+command, receipt, log, 1024, 130, write_paths=paths,
                    max_new_disk_mib=64, scratch_dir=scratch)
            if r['status'] != 'completed':
                raise RuntimeError('bounded chain step failed: '+str(receipt))
        try:
            while True:
                validated = 0
                for band in ('south', 'central', 'north'):
                    for scenario in ('obsclim', 'counterclim'):
                        for var in ('pr', 'tas', 'tasmax'):
                            for first in (1981, 1991, 2001):
                                rp = ROOT/f'data/interim/us_{band}_{scenario}_{var}_{first}_20260908/receipt.json'
                                if rp.exists() and json.loads(rp.read_text()).get('status') == 'regional_paired_climate_content_validated':
                                    validated += 1
                if validated == 54:
                    break
                if time.monotonic()-started >= args.max_hours*3600:
                    save('duration_reached_resume_same_queue', validated_cutouts=validated)
                    return
                save('acquisition_running', validated_cutouts=validated)
                subprocess.run([sys.executable, 'scripts/continue_us_paired_regional_acquisition.py',
                                '--max-actions', '108', '--max-seconds', '600'], cwd=ROOT, check=True)
            output = ROOT/'data/interim/us_regional_county_climate_20260908'
            receipt = output/'receipt.json'
            if output.exists() and (not receipt.exists() or json.loads(receipt.read_text()).get('status') != 'us_regional_county_climate_inputs_validated'):
                raise RuntimeError('existing incomplete regional feature output needs inspection')
            if not output.exists():
                save('feature_tests_running', validated_cutouts=54)
                bounded(['scripts/test_us_regional_county_features.py'], 'us_regional_chain_feature_tests_20260908', [])
                save('feature_construction_running')
                bounded(['scripts/build_us_regional_county_climate.py', '--outdir', str(output)],
                        'us_regional_county_climate_20260908', [output])
            comparison = output/'comparison.json'
            if comparison.exists() and json.loads(comparison.read_text()).get('status') != 'us_regional_county_climate_comparison_validated':
                raise RuntimeError('existing regional comparison needs inspection')
            if not comparison.exists():
                save('comparison_tests_running')
                bounded(['scripts/test_us_county_climate_comparison.py'], 'us_regional_chain_comparison_tests_20260908', [])
                save('climate_comparison_running')
                bounded(['scripts/compare_us_regional_county_climate.py', '--out', str(comparison)],
                        'us_regional_county_comparison_20260908', [comparison])
            save('climate_inputs_and_comparison_complete_review_required', validated_cutouts=54,
                 comparison_path=str(comparison.relative_to(ROOT)))
        except BaseException as error:
            save('stopped_preserved_for_review', error_type=type(error).__name__, error=str(error))
            raise


if __name__ == '__main__':
    main()
