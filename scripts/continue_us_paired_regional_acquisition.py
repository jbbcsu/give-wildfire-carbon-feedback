"""Resume the registered regional queue; one bounded child at a time.

At most two unfinished server requests. No resubmission of uncertain POSTs,
no automatic retry of failed acquisitions, and no unmonitored analysis child.
"""
import argparse
import fcntl
import json
from pathlib import Path
import re
import sys
import time

from run_bounded_job import run

ROOT = Path(__file__).resolve().parents[1]
PATTERN = re.compile(r'isimip3a_us_(south|central|north)_(obsclim|counterclim)_(pr|tas|tasmax)_(1981|1991|2001)_20260908\.json')


def fresh_job(stem):
    version = 1
    while True:
        name = stem + ('' if version == 1 else f'_v{version}')
        receipt, log = ROOT/f'outputs/{name}_resource.json', ROOT/f'outputs/{name}.log'
        scratch = ROOT/f'data/interim/job_scratch/{name}'
        if not any(p.exists() for p in (receipt, log, scratch)):
            return receipt, log, scratch
        version += 1


def job(command, stem, writes):
    receipt, log, scratch = fresh_job(stem)
    result = run([sys.executable]+command, receipt, log, 1024, 130,
                 write_paths=writes, max_new_disk_mib=64, scratch_dir=scratch)
    tail = log.read_text()[-500:]
    if 'Registered job is not ready:' not in tail or result['status'] != 'completed':
        print(stem, result['status'], tail, flush=True)
    if result['status'] != 'completed':
        raise RuntimeError('bounded regional step failed; inspect preserved '+str(receipt))
    return receipt


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--max-actions', type=int, default=12)
    parser.add_argument('--max-seconds', type=int, default=180)
    args = parser.parse_args()
    if not 1 <= args.max_actions <= 108 or not 1 <= args.max_seconds <= 600:
        raise ValueError('bounded queue slice required')
    requests = ROOT/'data/interim/us_paired_regional_requests_20260908'
    requests.mkdir(exist_ok=True)
    with (requests/'driver.lock').open('a') as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        configs = sorted((ROOT/'config').glob('isimip3a_us_*_20260908.json'))
        if len(configs) != 54 or any(PATTERN.fullmatch(p.name) is None for p in configs):
            raise ValueError('regional queue config inventory differs')
        started, actions = time.monotonic(), 0
        last_attempt, cooldown = {}, {}
        while actions < args.max_actions and time.monotonic()-started < args.max_seconds:
            pending, unrequested, completed = [], [], []
            for config in configs:
                band, scenario, var, year = PATTERN.fullmatch(config.name).groups()
                stem = f'us_{band}_{scenario}_{var}_{year}'
                out = ROOT/f'data/interim/{stem}_20260908'
                req = requests/f'{band}_{scenario}_{var}_{year}.json'
                if stem == 'us_central_counterclim_pr_1981':
                    req = ROOT/'data/interim/us_paired_county_climate_20260908/central_counterclim_pr_1981_request.json'
                if out.exists():
                    receipt = out/'receipt.json'
                    if (out/'failure.json').exists() or not receipt.exists() or json.loads(receipt.read_text()).get('status') != 'regional_paired_climate_content_validated':
                        raise RuntimeError('inspect incomplete regional output: '+str(out))
                    completed.append(stem)
                    continue
                if req.with_suffix('.partial').exists():
                    raise RuntimeError('uncertain POST preserved; do not resubmit: '+str(req))
                item = (config, stem, out, req)
                (pending if req.exists() else unrequested).append(item)
            if len(completed) == 54:
                print('ALL 54 regional cutouts validated; proceed to county finite-area coverage and feature construction.', flush=True)
                break
            ready = [p for p in pending if time.monotonic()-last_attempt.get(p[1], -1000) >= cooldown.get(p[1], 30)]
            if ready:
                config, stem, out, req = ready[0]
                job(['scripts/acquire_us_paired_regional_cutout.py', '--config', str(config),
                     '--request-receipt', str(req), '--out-dir', str(out)], stem+'_acquisition_20260908', [out])
                last_attempt[stem] = time.monotonic()
                if not out.exists():
                    cooldown[stem] = min(120, 2*cooldown.get(stem, 15))
            elif len(pending) < 2 and unrequested:
                config, stem, out, req = unrequested[0]
                job(['scripts/prepare_us_paired_regional_cutout.py', '--config', str(config),
                     '--out', str(req), '--submit'], stem+'_request_20260908', [req, req.with_suffix('.partial')])
                last_attempt[stem] = time.monotonic()-30
            else:
                time.sleep(2)
                continue
            actions += 1
        statuses = []
        retained = 0
        for config in configs:
            band, scenario, var, year = PATTERN.fullmatch(config.name).groups()
            directory = ROOT/f'data/interim/us_{band}_{scenario}_{var}_{year}_20260908'
            receipt = directory/'receipt.json'
            if receipt.exists() and json.loads(receipt.read_text()).get('status') == 'regional_paired_climate_content_validated':
                statuses.append(config.name)
                retained += sum(p.stat().st_size for p in directory.iterdir() if p.is_file())
        print('QUEUE SLICE:', len(statuses), '/54 validated;', retained, 'regional retained bytes;', actions, 'bounded actions.', flush=True)


if __name__ == '__main__':
    main()
