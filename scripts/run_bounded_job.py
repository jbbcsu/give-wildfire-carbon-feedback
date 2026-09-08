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
        max_log_mib=10, interval=0.2, write_paths=None, max_new_disk_mib=None,
        scratch_dir=None):
    if min(max_mib, max_log_mib, interval) <= 0 or min_free_gib < 0:
        raise ValueError('invalid resource budget')
    # Fail before launching if process visibility is unavailable.
    group_rss(os.getpgrp())
    if shutil.disk_usage(receipt.parent).free < min_free_gib * 2**30:
        raise RuntimeError('free disk below reserve; job not started')
    # Optional owned-path accounting separates this job's additions from other
    # applications' writes on the same filesystem. The global floor stays active.
    if (write_paths is None)!=(max_new_disk_mib is None):
        raise ValueError('owned write paths and incremental disk cap must be supplied together')
    if scratch_dir is not None and write_paths is None:raise ValueError('scratch requires owned disk accounting')
    if max_new_disk_mib is not None and max_new_disk_mib<=0:raise ValueError('positive incremental disk cap required')
    project=Path(__file__).resolve().parents[1]
    watched=[]
    for path in list(write_paths or [])+([scratch_dir] if scratch_dir is not None else []):
        path=Path(path).resolve()
        if not (path.is_relative_to(project/'data/interim') and path!=project/'data/interim'):
            raise ValueError('owned data paths must be specific ignored interim children')
        watched.append(path)
    if scratch_dir is not None:
        scratch_dir=Path(scratch_dir).resolve()
        if scratch_dir.exists():raise ValueError('new job scratch directory required')
        scratch_dir.mkdir(parents=True)
    def size(path):
        if not path.exists():return 0
        if path.is_symlink():raise ValueError('owned write path cannot be a symlink')
        if path.is_file():return path.stat().st_size
        total=0
        for entry in path.rglob('*'):
            if entry.is_symlink():raise ValueError('owned output contains a symlink')
            try:
                if entry.is_file():total+=entry.stat().st_size
            except FileNotFoundError:
                pass  # A concurrently removed scratch file no longer occupies disk.
        return total
    watched=list(dict.fromkeys(watched))
    if any(a!=b and a.is_relative_to(b) for a in watched for b in watched):
        raise ValueError('owned write paths must not overlap')
    initial_sizes={p:size(p) for p in watched};initial_log_bytes=size(log)
    peak_new_disk=0
    started = time.monotonic()
    peak = 0
    status = 'completed'
    env = dict(os.environ)
    for name in ['OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS',
                 'VECLIB_MAXIMUM_THREADS', 'NUMEXPR_NUM_THREADS']:
        env[name] = '1'
    env['PYTHONDONTWRITEBYTECODE']='1'
    if scratch_dir is not None:env['TMPDIR']=str(scratch_dir)
    with log.open('xb') as stream:
        process = subprocess.Popen(command, stdout=stream, stderr=subprocess.STDOUT,
                                   start_new_session=True, env=env)
        try:
            while True:
                rss = group_rss(process.pid)
                peak = max(peak, rss)
                added=sum(max(0,size(p)-initial_sizes[p]) for p in watched)+max(0,size(log)-initial_log_bytes)
                peak_new_disk=max(peak_new_disk,added)
                if rss > max_mib * 2**20:
                    status = 'memory_budget_exceeded'
                elif log.stat().st_size > max_log_mib * 2**20:
                    status = 'log_budget_exceeded'
                elif shutil.disk_usage(receipt.parent).free < min_free_gib * 2**30:
                    status = 'disk_reserve_breached'
                elif max_new_disk_mib is not None and added>max_new_disk_mib*2**20-128*1024:
                    status = 'owned_disk_budget_exceeded'
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
            if max_new_disk_mib is not None:
                result.update(sampled_peak_new_disk_bytes=peak_new_disk,max_new_disk_mib=max_new_disk_mib,
                    write_paths=[str(p.relative_to(project)) for p in watched],
                    disk_accounting='sampled_owned_paths_plus_log_with_128KiB_receipt_reserve',
                    scratch_dir=(str(scratch_dir.relative_to(project)) if scratch_dir is not None else None))
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
