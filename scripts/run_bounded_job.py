#!/usr/bin/env python3
"""Monitor a POSIX job group; stop on sampled RSS, log, or disk budget breach.

Sampling is not a kernel allocation limit. Descendants must not detach from
the job's session. This controls analysis subprocesses, not the Codex app.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import time


def group_rss(pgid):
    result = subprocess.run(['ps', '-axo', 'pgid=,rss='], check=True,
                            capture_output=True, text=True, timeout=5)
    return sum(int(row.split()[1]) * 1024 for row in result.stdout.splitlines()
               if len(row.split()) == 2 and int(row.split()[0]) == pgid)


def run(command, receipt, log, max_mib=1024, min_free_gib=150,
        max_log_mib=10, interval=0.2):
    if min(max_mib, max_log_mib, interval) <= 0 or min_free_gib < 0:
        raise ValueError('invalid resource budget')
    # Fail before launching if process visibility is unavailable.
    group_rss(os.getpgrp())
    if shutil.disk_usage(receipt.parent).free < min_free_gib * 2**30:
        raise RuntimeError('free disk below reserve; job not started')
    started = time.monotonic()
    peak = 0
    status = 'completed'
    env = dict(os.environ)
    for name in ['OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS',
                 'VECLIB_MAXIMUM_THREADS', 'NUMEXPR_NUM_THREADS']:
        env[name] = '1'
    with log.open('xb') as stream:
        process = subprocess.Popen(command, stdout=stream, stderr=subprocess.STDOUT,
                                   start_new_session=True, env=env)
        try:
            while True:
                rss = group_rss(process.pid)
                peak = max(peak, rss)
                if rss > max_mib * 2**20:
                    status = 'memory_budget_exceeded'
                elif log.stat().st_size > max_log_mib * 2**20:
                    status = 'log_budget_exceeded'
                elif shutil.disk_usage(receipt.parent).free < min_free_gib * 2**30:
                    status = 'disk_reserve_breached'
                if status != 'completed':
                    break
                if process.poll() is not None and rss == 0:
                    break
                time.sleep(interval)
        except BaseException:
            status = 'monitor_interrupted_or_failed'
            raise
        finally:
            # Only the session created by this launcher is targeted.
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            returncode = process.wait()
            if status == 'completed' and returncode:
                status = 'command_failed'
            result = dict(status=status, returncode=returncode,
                          sampled_peak_group_rss_bytes=peak,
                          max_mib=max_mib, min_free_gib=min_free_gib,
                          sampling_interval_seconds=interval,
                          wall_seconds=time.monotonic()-started,
                          limit_kind='sampled_process_group_not_kernel_limit')
            receipt.write_text(json.dumps(result, indent=2)+'\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--receipt', type=Path, required=True)
    parser.add_argument('--log', type=Path, required=True)
    parser.add_argument('--max-mib', type=float, default=1024)
    parser.add_argument('--min-free-gib', type=float, default=150)
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ['--'] else args.command
    if not command or args.receipt.exists():
        parser.error('command required and receipt must be new')
    result = run(command, args.receipt, args.log, args.max_mib, args.min_free_gib)
    print(json.dumps(result))
    raise SystemExit(0 if result['status'] == 'completed' else 1)
