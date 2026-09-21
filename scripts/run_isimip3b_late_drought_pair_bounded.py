#!/usr/bin/env python3
"""Launch one late-drought pair with the shared sampled resource guard."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from run_bounded_job import run


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--esm", required=True)
    parser.add_argument("--scenario", choices=("ssp126", "ssp370", "ssp585"), required=True)
    parser.add_argument("--raw-root", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--log", type=Path, required=True)
    args = parser.parse_args()
    paths = [args.out_dir, args.receipt, args.log]
    paths = [path if path.is_absolute() else ROOT/path for path in paths]
    out_dir, receipt, log = paths
    if any(path.exists() for path in paths):
        raise ValueError("fresh output, receipt and log paths required")
    command = [sys.executable, str(ROOT/"scripts/build_isimip3b_late_drought_pair.py"),
               "--esm", args.esm, "--scenario", args.scenario,
               "--raw-root", str(args.raw_root.resolve()), "--out-dir", str(out_dir)]
    result = run(command, receipt, log, max_mib=512, min_free_gib=130,
                 max_log_mib=2, write_paths=[out_dir], max_new_disk_mib=128)
    print(json.dumps(result))
    raise SystemExit(0 if result["status"] == "completed" else 1)


if __name__ == "__main__":
    main()
