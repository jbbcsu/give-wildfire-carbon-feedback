#!/usr/bin/env python3
"""Run one command and write portable wall-time/peak-RSS measurements."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import resource
import subprocess
import sys
import time


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--metrics-out", required=True)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = list(args.command)
    if command[:1] == ["--"]:
        command = command[1:]
    if not command:
        raise ValueError("A measured command is required")

    started = datetime.now(timezone.utc)
    before = time.perf_counter()
    completed = subprocess.run(command, check=False)
    wall_seconds = time.perf_counter() - before
    finished = datetime.now(timezone.utc)
    maximum = int(resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss)
    # Darwin reports bytes; Linux and the BSDs supported by CPython report KiB.
    peak_rss_bytes = maximum if sys.platform == "darwin" else maximum * 1024
    payload = {
        "schema_version": 1,
        "status": "command_completed" if completed.returncode == 0 else "command_failed",
        "started_utc": started.isoformat(),
        "finished_utc": finished.isoformat(),
        "wall_seconds": wall_seconds,
        "peak_rss_bytes": peak_rss_bytes,
        "returncode": int(completed.returncode),
    }
    output = Path(args.metrics_out)
    output.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    raise SystemExit(completed.returncode)


if __name__ == "__main__":
    main()
