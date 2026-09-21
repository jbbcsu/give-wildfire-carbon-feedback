#!/usr/bin/env python3
"""Run one local analysis job under sampled RSS and free-disk safeguards."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import time


def group_rss(pgid: int) -> int:
    result = subprocess.run(["ps", "-axo", "pgid=,rss="], check=True,
                            capture_output=True, text=True, timeout=5)
    return sum(int(row.split()[1]) * 1024 for row in result.stdout.splitlines()
               if len(row.split()) == 2 and int(row.split()[0]) == pgid)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--max-mib", type=float, default=512)
    parser.add_argument("--min-free-gib", type=float, default=130)
    parser.add_argument("--max-log-mib", type=float, default=64)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if (not command or args.receipt.exists() or args.log.exists() or
            min(args.max_mib, args.max_log_mib) <= 0 or args.min_free_gib < 0):
        parser.error("valid command, budgets, and fresh receipt/log required")
    root = Path(__file__).resolve().parents[1]
    receipt = args.receipt.resolve()
    log = args.log.resolve()
    if (not receipt.is_relative_to(root / "data/interim") or
            not log.is_relative_to(root / "data/interim")):
        parser.error("receipt and log must be isolated ignored interim files")
    receipt.parent.mkdir(parents=True, exist_ok=True)
    log.parent.mkdir(parents=True, exist_ok=True)
    args.receipt, args.log = receipt, log
    group_rss(os.getpgrp())
    if shutil.disk_usage(args.receipt.parent).free < args.min_free_gib * 2**30:
        raise RuntimeError("free disk below reserve; job not started")
    env = dict(os.environ)
    for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
                 "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS"):
        env[name] = "1"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    started = time.monotonic()
    peak = 0
    status = "completed"
    with args.log.open("xb") as stream:
        process = subprocess.Popen(command, stdout=stream, stderr=subprocess.STDOUT,
                                   start_new_session=True, env=env)
        try:
            while True:
                rss = group_rss(process.pid)
                peak = max(peak, rss)
                if rss > args.max_mib * 2**20:
                    status = "memory_budget_exceeded"
                elif args.log.stat().st_size > args.max_log_mib * 2**20:
                    status = "log_budget_exceeded"
                elif shutil.disk_usage(args.receipt.parent).free < args.min_free_gib * 2**30:
                    status = "disk_reserve_breached"
                if status != "completed" or (process.poll() is not None and rss == 0):
                    break
                time.sleep(0.2)
        finally:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            returncode = process.wait()
    if status == "completed" and returncode:
        status = "command_failed"
    result = {"status": status, "returncode": returncode,
              "sampled_peak_group_rss_bytes": peak, "max_mib": args.max_mib,
              "min_free_gib": args.min_free_gib, "max_log_mib": args.max_log_mib,
              "wall_seconds": time.monotonic() - started,
              "limit_kind": "sampled_process_group_not_kernel_limit"}
    args.receipt.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))
    raise SystemExit(0 if status == "completed" else 1)


if __name__ == "__main__":
    main()
