#!/usr/bin/env python3
"""Independently validate a streamed CDL county/agricultural support grid."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import tomllib
from collections import defaultdict
from pathlib import Path

import pyarrow.parquet as pq


def file_hashes(path: Path) -> tuple[str, str]:
    sha256 = hashlib.sha256()
    sha512 = hashlib.sha512()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            sha256.update(block)
            sha512.update(block)
    return sha256.hexdigest(), sha512.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--grid", type=Path, required=True)
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--resource", type=Path)
    parser.add_argument("--memory-cap-bytes", type=int, default=640 * 1024 * 1024)
    parser.add_argument("--out", type=Path, required=True)
    arguments = parser.parse_args()

    audit = json.loads(arguments.audit.read_text(encoding="utf-8"))
    contract = tomllib.loads(arguments.config.read_text(encoding="utf-8"))
    masks = set(contract["masks"])
    if masks != {"cultivated_agriculture", "broad_agriculture"}:
        raise ValueError("unexpected mask contract")
    expected_columns = {
        "county_geoid", "mask_id", "coarse_row", "coarse_col",
        "agricultural_pixel_count", "spatial_weight", "scc_authorized",
    }
    parquet = pq.ParquetFile(arguments.grid)
    if missing := expected_columns - set(parquet.schema_arrow.names):
        raise ValueError(f"grid lacks {sorted(missing)}")

    sums: dict[tuple[str, str], float] = defaultdict(float)
    pixels: dict[tuple[str, str], int] = defaultdict(int)
    cells: dict[tuple[str, str], int] = defaultdict(int)
    rows = 0
    for batch in parquet.iter_batches(
        batch_size=65536,
        columns=["county_geoid", "mask_id", "agricultural_pixel_count", "spatial_weight", "scc_authorized"],
    ):
        values = batch.to_pydict()
        for geoid, mask, count, weight, authorized in zip(
            values["county_geoid"], values["mask_id"], values["agricultural_pixel_count"],
            values["spatial_weight"], values["scc_authorized"], strict=True,
        ):
            if str(mask) not in masks:
                raise ValueError(f"unknown mask {mask}")
            if authorized is not False or int(count) <= 0 or not math.isfinite(float(weight)) or float(weight) <= 0:
                raise ValueError("invalid row authorization, pixel count, or weight")
            key = (str(geoid).zfill(5), str(mask))
            sums[key] += float(weight)
            pixels[key] += int(count)
            cells[key] += 1
            rows += 1
    if rows != parquet.metadata.num_rows or rows != int(audit["output_rows"]):
        raise ValueError("row count differs across grid, metadata, and audit")
    if any(not math.isclose(value, 1.0, rel_tol=0, abs_tol=1e-10) for value in sums.values()):
        raise ValueError("one or more county-mask weight sums differ from one")

    audit_rows = audit["counties"]
    audit_lookup = {
        (str(row["county_geoid"]).zfill(5), str(row["mask_id"])): row
        for row in audit_rows
    }
    if len(audit_lookup) != len(audit_rows):
        raise ValueError("duplicate county-mask record in audit")
    if set(audit_lookup) != set(sums):
        zero_support = {
            key for key, row in audit_lookup.items() if int(row["agricultural_pixels"]) == 0
        }
        if set(audit_lookup) - zero_support != set(sums):
            raise ValueError("grid county-mask support differs from audit")
    for key, value in sums.items():
        row = audit_lookup[key]
        if pixels[key] != int(row["agricultural_pixels"]) or cells[key] != int(row["positive_coarse_cells"]):
            raise ValueError(f"pixel/cell total differs from audit for {key}")

    counties = sorted({key[0] for key in audit_lookup})
    strict_broad = 0
    for geoid in counties:
        cultivated = int(audit_lookup[(geoid, "cultivated_agriculture")]["agricultural_pixels"])
        broad = int(audit_lookup[(geoid, "broad_agriculture")]["agricultural_pixels"])
        if broad < cultivated:
            raise ValueError(f"broad support is smaller than cultivated support in {geoid}")
        strict_broad += broad > cultivated
    if strict_broad == 0:
        raise ValueError("broad mask never adds support")

    sha256, sha512 = file_hashes(arguments.grid)
    if "output_sha256" in audit and sha256 != audit["output_sha256"]:
        raise ValueError("grid SHA-256 differs from audit")
    if "output_sha512" in audit and sha512 != audit["output_sha512"]:
        raise ValueError("grid SHA-512 differs from audit")
    resource = None
    if arguments.resource is not None:
        resource = json.loads(arguments.resource.read_text(encoding="utf-8"))
        if resource["status"] != "command_completed" or int(resource["returncode"]) != 0:
            raise ValueError("resource receipt does not record successful completion")
        if int(resource["peak_rss_bytes"]) > arguments.memory_cap_bytes:
            raise ValueError("resource receipt exceeds memory cap")

    result = {
        "schema": "cdl_2008_agricultural_grid_independent_validation_v1",
        "passed": True,
        "grid": str(arguments.grid),
        "grid_sha256": sha256,
        "grid_sha512": sha512,
        "rows": rows,
        "counties": len(counties),
        "county_mask_groups_with_positive_support": len(sums),
        "counties_where_broad_strictly_exceeds_cultivated": strict_broad,
        "maximum_absolute_weight_sum_error": max(abs(value - 1) for value in sums.values()),
        "resource": resource,
        "claim_boundary": "validates construction and resource constraints, not causal, global, or SCC interpretation",
    }
    arguments.out.parent.mkdir(parents=True, exist_ok=True)
    arguments.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
