#!/usr/bin/env python3
"""Run outcome-blind sentinel scoring in isolated memory-bounded batches."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tomllib
from pathlib import Path

from build_usdm_agricultural_exposure import configured_dates


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--shape-config", type=Path, required=True)
    parser.add_argument("--grid", type=Path, required=True)
    parser.add_argument("--prepared-grid", type=Path)
    parser.add_argument("--prepared-grid-audit", type=Path)
    parser.add_argument("--grid-audit", type=Path)
    parser.add_argument("--shape-dir", type=Path, required=True)
    parser.add_argument("--score-dir", type=Path, required=True)
    parser.add_argument("--batch-size", type=int, default=25)
    arguments = parser.parse_args()
    if arguments.batch_size <= 0:
        raise ValueError("--batch-size must be positive")
    dates = configured_dates(tomllib.loads(arguments.shape_config.read_text(encoding="utf-8")))
    script = Path(__file__).with_name("select_usdm_multiresolution_sentinels.py")
    arguments.score_dir.mkdir(parents=True, exist_ok=True)
    completed = []

    def run_batch(start: int, limit: int) -> None:
        score = arguments.score_dir / f"scores_{start:04d}_{start + limit - 1:04d}.npz"
        audit = score.with_suffix(".audit.json")
        if score.is_file() and audit.is_file():
            receipt = json.loads(audit.read_text(encoding="utf-8"))
            if (
                receipt.get("schema") == "usdm_multiresolution_sentinel_score_batch_v1"
                and int(receipt["maps_scored"]) == limit
                and int(receipt["map_index_start"]) == start
                and int(receipt["map_index_end_inclusive"]) == start + limit - 1
            ):
                completed.append(receipt)
                print(f"reuse {start:04d}-{start + limit - 1:04d}", flush=True)
                return
        command = [
            sys.executable, "-B", str(script),
            "--config", str(arguments.config),
            "--shape-config", str(arguments.shape_config),
            "--grid", str(arguments.grid),
            "--shape-dir", str(arguments.shape_dir),
            "--out", str(arguments.score_dir / "unused_selection.json"),
            "--inventory-out", str(arguments.score_dir / "unused_inventory.csv"),
            "--start-index", str(start), "--limit", str(limit),
            "--score-out", str(score), "--score-audit-out", str(audit),
        ]
        if arguments.prepared_grid is not None:
            if arguments.prepared_grid_audit is None or arguments.grid_audit is None:
                raise ValueError("prepared scoring requires both audit arguments")
            command.extend([
                "--prepared-grid", str(arguments.prepared_grid),
                "--prepared-grid-audit", str(arguments.prepared_grid_audit),
                "--grid-audit", str(arguments.grid_audit),
            ])
        result = subprocess.run(command, text=True, capture_output=True)
        if result.returncode:
            if limit == 1:
                raise RuntimeError(
                    f"single-map score batch {start} failed\n{result.stdout[-2000:]}\n{result.stderr[-4000:]}"
                )
            left = limit // 2
            print(f"split {start:04d}-{start + limit - 1:04d} after bounded failure", flush=True)
            run_batch(start, left)
            run_batch(start + left, limit - left)
            return
        receipt = json.loads(audit.read_text(encoding="utf-8"))
        if int(receipt["resource"]["peak_rss_bytes"]) > int(receipt["resource"]["ceiling_bytes"]):
            raise MemoryError(f"score batch {start}:{start + limit} exceeded ceiling")
        completed.append(receipt)
        print(
            f"batch {start:04d}-{start + limit - 1:04d} peak={receipt['resource']['peak_rss_bytes']}",
            flush=True,
        )

    for start in range(0, len(dates), arguments.batch_size):
        limit = min(arguments.batch_size, len(dates) - start)
        run_batch(start, limit)
    print(json.dumps({"batches": len(completed), "maps": len(dates), "maximum_peak_rss_bytes": max(x["resource"]["peak_rss_bytes"] for x in completed)}, indent=2))


if __name__ == "__main__":
    main()
