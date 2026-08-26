#!/usr/bin/env python3
"""Combine a complete set of validated crop-stage scPDSI partitions."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from scpdsi_partition_provenance import (
    COMBINED_CONTRACT_ID,
    manifest_path_for,
    sha256_file,
    write_manifest,
)
from validate_stage_scpdsi_partition import validate_frame, validate_partition


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--expected-partitions", type=int, required=True)
    parser.add_argument("--expected-stages", type=int, default=3)
    parser.add_argument("--threshold", type=float, required=True)
    parser.add_argument("--scpdsi", required=True)
    parser.add_argument("--calendar", required=True)
    parser.add_argument("--crop", required=True)
    parser.add_argument("--irrigation", required=True)
    parser.add_argument("--year-start", type=int, required=True)
    parser.add_argument("--year-end", type=int, required=True)
    parser.add_argument("--lat-start", type=int, default=0)
    parser.add_argument("--lat-stop", type=int, required=True)
    parser.add_argument("--stage-fractions", default="0,0.3,0.7,1")
    parser.add_argument("--manifest-out")
    args = parser.parse_args()
    paths = sorted(Path(args.directory).glob("*.parquet"))
    if len(paths) != args.expected_partitions:
        raise ValueError(f"Expected {args.expected_partitions} partitions, found {len(paths)}")
    scpdsi_path = Path(args.scpdsi)
    calendar_path = Path(args.calendar)
    scpdsi_sha256 = sha256_file(scpdsi_path)
    calendar_sha256 = sha256_file(calendar_path)
    frames: list[pd.DataFrame] = []
    manifests: list[dict[str, object]] = []
    for path in paths:
        manifest = json.loads(manifest_path_for(path).read_text(encoding="utf-8"))
        lat_start = int(manifest.get("lat_start", -1))
        lat_stop = int(manifest.get("lat_stop", -1))
        frame, checked = validate_partition(
            path, manifest_path_for(path), threshold=args.threshold,
            expected_stages=args.expected_stages, expected_crop=args.crop,
            expected_irrigation=args.irrigation,
            expected_year_start=args.year_start, expected_year_end=args.year_end,
            expected_lat_start=lat_start, expected_lat_stop=lat_stop,
            expected_stage_fractions=args.stage_fractions,
            expected_scpdsi_sha256=scpdsi_sha256,
            expected_calendar_sha256=calendar_sha256,
        )
        frames.append(frame)
        manifests.append(checked)
    intervals = sorted((int(item["lat_start"]), int(item["lat_stop"])) for item in manifests)
    cursor = args.lat_start
    for start, stop in intervals:
        if start != cursor or stop <= start:
            raise ValueError("Stage-scPDSI latitude partitions overlap or leave a gap")
        cursor = stop
    if cursor != args.lat_stop:
        raise ValueError("Stage-scPDSI latitude partitions do not cover the declared range")
    nonempty = [frame for frame in frames if not frame.empty]
    if not nonempty:
        raise ValueError("No stage-scPDSI rows to combine")
    combined = pd.concat(nonempty, ignore_index=True)
    validate_frame(combined, args.threshold, args.expected_stages)
    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    combined.to_parquet(output, index=False)
    combined_manifest = Path(args.manifest_out) if args.manifest_out else manifest_path_for(output)
    write_manifest(
        combined_manifest,
        {
            "schema_version": 1,
            "contract_id": COMBINED_CONTRACT_ID,
            "output_file": str(output.resolve()),
            "output_sha256": sha256_file(output),
            "output_rows": int(len(combined)),
            "scpdsi_source_file": str(scpdsi_path.resolve()),
            "scpdsi_source_sha256": scpdsi_sha256,
            "calendar_source_file": str(calendar_path.resolve()),
            "calendar_source_sha256": calendar_sha256,
            "crop": args.crop,
            "irrigation": args.irrigation,
            "year_start": int(args.year_start),
            "year_end": int(args.year_end),
            "lat_start": int(args.lat_start),
            "lat_stop": int(args.lat_stop),
            "threshold": float(args.threshold),
            "stage_fractions": args.stage_fractions,
            "expected_stages": int(args.expected_stages),
            "expected_partitions": int(args.expected_partitions),
            "partition_source_manifests_validated": True,
            "complete_latitude_partition_coverage": True,
            "partitions": [
                {
                    "file": str(path.resolve()),
                    "sha256": sha256_file(path),
                    "manifest_file": str(manifest_path_for(path).resolve()),
                    "manifest_sha256": sha256_file(manifest_path_for(path)),
                    "lat_start": int(manifest["lat_start"]),
                    "lat_stop": int(manifest["lat_stop"]),
                    "rows": int(manifest["output_rows"]),
                }
                for path, manifest in zip(paths, manifests)
            ],
            "drought_source_role": "historical_benchmark_not_future_scc_input",
        },
    )
    print(f"wrote {len(combined)} stage-scPDSI rows from {len(paths)} partitions")


if __name__ == "__main__":
    main()
