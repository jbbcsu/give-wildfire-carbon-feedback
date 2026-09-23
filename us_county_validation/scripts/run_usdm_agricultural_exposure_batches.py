#!/usr/bin/env python3
"""Run isolated USDM-map batches and merge exact annual exposures."""
from __future__ import annotations

import argparse
from datetime import UTC, datetime
import hashlib
import json
import math
import subprocess
import sys
import time
import tomllib
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq


HERE = Path(__file__).resolve().parent
BUILDER = HERE / "build_usdm_agricultural_exposure.py"
MEASURE = HERE.parent.parent / "scripts/run_command_with_resource_receipt.py"
CATEGORIES = ("none", "d0", "d1", "d2", "d3", "d4")


def sha512(path: Path) -> str:
    digest = hashlib.sha512()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--prepared-grid", type=Path, required=True)
    parser.add_argument("--prepared-grid-audit", type=Path, required=True)
    parser.add_argument("--shape-dir", type=Path, required=True)
    parser.add_argument("--batch-dir", type=Path, required=True)
    parser.add_argument("--batch-size", type=int, default=10)
    parser.add_argument("--memory-cap-bytes", type=int, default=640 * 1024 * 1024)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--audit-out", type=Path, required=True)
    parser.add_argument("--resource-out", type=Path, required=True)
    arguments = parser.parse_args()
    if arguments.batch_size <= 0:
        raise ValueError("batch size must be positive")
    contract = tomllib.loads(arguments.config.read_text(encoding="utf-8"))
    map_count = int(contract["expected_archives"])
    arguments.batch_dir.mkdir(parents=True, exist_ok=True)
    started = datetime.now(UTC)
    before = time.perf_counter()
    batch_records = []
    all_map_audits = []
    frames = []
    peak_rss = 0
    maximum_attempted_peak_rss = 0
    rejected_batches = []

    def accept_batch(start: int, count: int) -> None:
        nonlocal peak_rss, maximum_attempted_peak_rss
        stem = f"maps_{start:04d}_{start + count - 1:04d}"
        exposure = arguments.batch_dir / f"{stem}.parquet"
        audit_path = arguments.batch_dir / f"{stem}.audit.json"
        resource_path = arguments.batch_dir / f"{stem}.resource.json"
        reusable = exposure.is_file() and audit_path.is_file() and resource_path.is_file()
        if not reusable:
            command = [
                sys.executable, str(MEASURE), "--metrics-out", str(resource_path), "--",
                sys.executable, str(BUILDER), "--config", str(arguments.config),
                "--prepared-grid", str(arguments.prepared_grid),
                "--prepared-grid-audit", str(arguments.prepared_grid_audit),
                "--shape-dir", str(arguments.shape_dir), "--out", str(exposure),
                "--audit-out", str(audit_path), "--start-index", str(start),
                "--limit", str(count),
            ]
            subprocess.run(command, check=True)
        resource = json.loads(resource_path.read_text(encoding="utf-8"))
        if resource["status"] != "command_completed" or int(resource["returncode"]) != 0:
            raise ValueError(f"batch {stem} did not complete successfully")
        batch_peak = int(resource["peak_rss_bytes"])
        maximum_attempted_peak_rss = max(maximum_attempted_peak_rss, batch_peak)
        if batch_peak > arguments.memory_cap_bytes:
            rejected_batches.append({
                "start_index": start,
                "end_index_inclusive": start + count - 1,
                "maps": count,
                "peak_rss_bytes": batch_peak,
                "resource": str(resource_path),
                "reason": "measured RSS exceeded cap; output excluded and interval split",
            })
            if count == 1:
                raise ValueError(f"single-map batch {stem} exceeded memory cap: {batch_peak}")
            print(f"rejecting {stem} at {batch_peak} bytes; splitting to single maps", flush=True)
            for index in range(start, start + count):
                accept_batch(index, 1)
            return
        peak_rss = max(peak_rss, batch_peak)
        audit = json.loads(audit_path.read_text(encoding="utf-8"))
        if int(audit["map_index_start"]) != start or int(audit["maps_processed"]) != count:
            raise ValueError(f"batch audit index mismatch for {stem}")
        if sha512(exposure) != audit["output_sha512"]:
            raise ValueError(f"batch exposure checksum differs from audit for {stem}")
        all_map_audits.extend(audit["map_audits"])
        frame = pd.read_parquet(exposure)
        frames.append(frame)
        batch_records.append({
            "start_index": start, "end_index_inclusive": start + count - 1,
            "maps": count, "exposure": str(exposure), "exposure_sha512": sha512(exposure),
            "audit": str(audit_path), "resource": str(resource_path),
            "peak_rss_bytes": batch_peak, "wall_seconds": resource["wall_seconds"],
        })
        action = "reused" if reusable else "accepted"
        print(f"{action} {stem}: peak_rss={batch_peak}", flush=True)

    for start in range(0, map_count, arguments.batch_size):
        accept_batch(start, min(arguments.batch_size, map_count - start))

    if len(all_map_audits) != map_count:
        raise ValueError("merged batch map count differs from contract")
    dates = [row["map_date"] for row in all_map_audits]
    if len(set(dates)) != map_count or dates != sorted(dates):
        raise ValueError("batch map dates are duplicate or out of order")
    if any(sum(map(int, row["exclusive_class_overlap_points"].values())) for row in all_map_audits):
        raise ValueError("batch map audit contains an exclusive-class overlap")

    combined = pd.concat(frames, ignore_index=True)
    keys = ["county_geoid", "mask_id", "harvest_year"]
    numeric = ["represented_days", "total_equivalent_weeks", *[f"weeks_{name}" for name in CATEGORIES]]
    result = combined.groupby(keys, as_index=False, observed=True)[numeric].sum()
    result["analysis_role"] = "historical_agricultural_area_validation_only"
    result["scc_authorized"] = False
    result = result[[
        "county_geoid", "mask_id", "harvest_year", "represented_days",
        "total_equivalent_weeks", "analysis_role", "scc_authorized",
        *[f"weeks_{name}" for name in CATEGORIES],
    ]].sort_values(keys).reset_index(drop=True)
    if result.duplicated(keys).any():
        raise ValueError("merged exposure contains duplicate county-mask-year keys")
    for year, part in result.groupby("harvest_year", observed=True):
        expected_days = 366 if pd.Timestamp(int(year), 1, 1).is_leap_year else 365
        if not part.represented_days.eq(expected_days).all():
            raise ValueError(f"merged represented-day coverage failed for {year}")
        weeks = part[[f"weeks_{name}" for name in CATEGORIES]].sum(axis=1)
        if not (weeks - expected_days / 7).abs().le(1e-9).all():
            raise ValueError(f"merged category accounting failed for {year}")
    arguments.out.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.Table.from_pandas(result, preserve_index=False), arguments.out, compression="zstd")
    finished = datetime.now(UTC)
    wall = time.perf_counter() - before
    audit = {
        "schema": "usdm_agricultural_area_exposure_audit_v1",
        "config": str(arguments.config),
        "grid": str(arguments.prepared_grid),
        "grid_rows": int(json.loads(arguments.prepared_grid_audit.read_text())["rows"]),
        "unique_grid_cells": int(json.loads(arguments.prepared_grid_audit.read_text())["unique_cells"]),
        "county_mask_groups": int(result.groupby(["county_geoid", "mask_id"]).ngroups),
        "maps_processed": map_count,
        "full_configured_run": True,
        "harvest_years": sorted(map(int, result.harvest_year.unique())),
        "output": str(arguments.out),
        "output_rows": len(result),
        "output_sha512": sha512(arguments.out),
        "map_audits": all_map_audits,
        "batches": batch_records,
        "rejected_batches": rejected_batches,
        "claim_boundary": "historical spatial-fidelity sensitivity only; not future drought, damage, or SCC",
    }
    arguments.audit_out.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    resource = {
        "schema_version": 1,
        "status": "command_completed",
        "started_utc": started.isoformat(),
        "finished_utc": finished.isoformat(),
        "wall_seconds": wall,
        "peak_rss_bytes": peak_rss,
        "maximum_attempted_peak_rss_bytes": maximum_attempted_peak_rss,
        "returncode": 0,
        "measurement_scope": "maximum independently measured RSS across isolated map batches",
        "batches": len(batch_records),
        "rejected_batches": rejected_batches,
    }
    arguments.resource_out.write_text(json.dumps(resource, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"merged {map_count} maps into {len(result)} county-mask-year rows; peak batch RSS={peak_rss}")


if __name__ == "__main__":
    main()
