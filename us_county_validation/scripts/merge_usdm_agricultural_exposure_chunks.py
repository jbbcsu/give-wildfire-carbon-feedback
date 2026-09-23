#!/usr/bin/env python3
"""Merge independently validated whole-county USDM exposure chunks."""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq


def sha512(path: Path) -> str:
    digest = hashlib.sha512()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--chunk-audit", type=Path, required=True)
    parser.add_argument("--chunk-root", type=Path, required=True)
    parser.add_argument("--memory-cap-bytes", type=int, default=640 * 1024 * 1024)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--audit-out", type=Path, required=True)
    parser.add_argument("--resource-out", type=Path, required=True)
    arguments = parser.parse_args()
    split = json.loads(arguments.chunk_audit.read_text(encoding="utf-8"))
    if split.get("schema") != "cdl_agricultural_grid_county_chunks_v1":
        raise ValueError("unexpected grid-chunk audit schema")
    frames = []
    map_rows: dict[str, dict[str, object]] = {}
    overlap_sums: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    maximum_peak = 0
    wall_seconds = 0.0
    input_records = []
    observed_counties: set[str] = set()
    for record in split["chunks"]:
        index = int(record["chunk"])
        directory = arguments.chunk_root / f"chunk_{index:03d}"
        exposure = directory / "exposure_990m.parquet"
        audit_path = directory / "exposure_990m.audit.json"
        resource_path = directory / "exposure_990m.resource.json"
        validation_path = directory / "exposure_990m.validation.json"
        if not all(path.is_file() for path in (
            exposure, audit_path, resource_path, validation_path,
        )):
            raise FileNotFoundError(f"chunk {index} exposure is incomplete")
        validation = json.loads(validation_path.read_text(encoding="utf-8"))
        if not validation.get("passed") or validation.get("exposure_sha512") != sha512(exposure):
            raise ValueError(f"chunk {index} did not retain validated identity")
        resource = json.loads(resource_path.read_text(encoding="utf-8"))
        peak = int(resource["peak_rss_bytes"])
        if resource.get("status") != "command_completed" or peak > arguments.memory_cap_bytes:
            raise ValueError(f"chunk {index} resource gate failed")
        maximum_peak = max(maximum_peak, peak)
        wall_seconds += float(resource["wall_seconds"])
        audit = json.loads(audit_path.read_text(encoding="utf-8"))
        frame = pd.read_parquet(exposure)
        frame["county_geoid"] = frame.county_geoid.astype(str).str.zfill(5)
        expected_counties = set(map(str, record["counties"]))
        actual_counties = set(frame.county_geoid)
        if actual_counties != expected_counties or observed_counties & actual_counties:
            raise ValueError(f"chunk {index} county support differs or overlaps")
        observed_counties |= actual_counties
        frames.append(frame)
        for row in audit["map_audits"]:
            date = str(row["map_date"])
            if date not in map_rows:
                map_rows[date] = dict(row)
            else:
                for key in ("archive", "archive_sha512", "represented_days"):
                    if map_rows[date].get(key) != row.get(key):
                        raise ValueError(f"chunk map metadata differs for {date} {key}")
            for category, value in row["exclusive_class_overlap_points"].items():
                overlap_sums[date][str(category)] += int(value)
        input_records.append({
            "chunk": index,
            "counties": len(actual_counties),
            "rows": len(frame),
            "sha512": sha512(exposure),
            "peak_rss_bytes": peak,
        })
    result = pd.concat(frames, ignore_index=True)
    keys = ["county_geoid", "mask_id", "harvest_year"]
    if result.duplicated(keys).any():
        raise ValueError("merged chunk exposure contains duplicate keys")
    result = result.sort_values(keys).reset_index(drop=True)
    arguments.out.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.Table.from_pandas(result, preserve_index=False), arguments.out, compression="zstd")
    map_audits = []
    for date in sorted(map_rows):
        row = map_rows[date]
        row["exclusive_class_overlap_points"] = dict(sorted(overlap_sums[date].items()))
        map_audits.append(row)
    if len(map_audits) != 679:
        raise ValueError("merged chunks do not contain all 679 maps")
    audit = {
        "schema": "usdm_agricultural_area_exposure_audit_v1",
        "config": "unchanged chunk-level frozen contract",
        "grid": str(arguments.chunk_audit),
        "grid_rows": int(split["source"]["rows"]),
        "county_mask_groups": int(result.groupby(["county_geoid", "mask_id"]).ngroups),
        "maps_processed": len(map_audits),
        "full_configured_run": True,
        "harvest_years": sorted(map(int, result.harvest_year.unique())),
        "output": str(arguments.out),
        "output_rows": len(result),
        "output_sha512": sha512(arguments.out),
        "map_audits": map_audits,
        "chunks": input_records,
        "claim_boundary": "historical spatial-fidelity sensitivity only; not future drought, damage, or SCC",
    }
    arguments.audit_out.write_text(
        json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    resource = {
        "schema_version": 1,
        "status": "command_completed",
        "wall_seconds": wall_seconds,
        "peak_rss_bytes": maximum_peak,
        "returncode": 0,
        "measurement_scope": "maximum independently measured RSS across county chunks and isolated map batches",
        "chunks": len(input_records),
    }
    arguments.resource_out.write_text(
        json.dumps(resource, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps({
        "chunks": len(input_records), "counties": len(observed_counties),
        "rows": len(result), "maximum_peak_rss_bytes": maximum_peak,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
