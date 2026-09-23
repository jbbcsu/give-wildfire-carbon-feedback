#!/usr/bin/env python3
"""Merge independently validated state 990 m exposure partitions."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from build_cdl_2008_agricultural_grid import CONTIGUOUS_STATE_FIPS


CATEGORIES = ("none", "d0", "d1", "d2", "d3", "d4")


def hashes(path: Path) -> tuple[str, str]:
    sha256 = hashlib.sha256()
    sha512 = hashlib.sha512()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            sha256.update(block)
            sha512.update(block)
    return sha256.hexdigest(), sha512.hexdigest()


def expected_states_and_counties(path: Path) -> tuple[list[str], set[str]]:
    counties = set()
    with path.open("r", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        for row in reader:
            geoid = str(row["county_geoid"]).zfill(5)
            if (
                geoid[:2] in CONTIGUOUS_STATE_FIPS
                and str(row.get("classifier_eligible", "")).strip().lower() in {"true", "1", "yes"}
            ):
                counties.add(geoid)
    if not counties:
        raise ValueError("county inventory has no eligible continental counties")
    return sorted({value[:2] for value in counties}), counties


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--partition-dir", type=Path, required=True)
    parser.add_argument("--county-inventory", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--audit-out", type=Path, required=True)
    parser.add_argument("--memory-cap-bytes", type=int, default=640 * 1024 * 1024)
    arguments = parser.parse_args()
    states, expected_counties = expected_states_and_counties(arguments.county_inventory)
    frames = []
    receipts = []
    for state in states:
        directory = arguments.partition_dir / f"state_{state}"
        exposure = directory / "exposure_990m.parquet"
        exposure_check_path = directory / "exposure_990m.validation.json"
        grid_check_path = directory / "grid_990m.validation.json"
        if not all(path.is_file() for path in (exposure, exposure_check_path, grid_check_path)):
            raise FileNotFoundError(f"state {state} partition is incomplete")
        exposure_check = json.loads(exposure_check_path.read_text(encoding="utf-8"))
        grid_check = json.loads(grid_check_path.read_text(encoding="utf-8"))
        if not exposure_check.get("passed") or not grid_check.get("passed"):
            raise ValueError(f"state {state} validator did not pass")
        for check in (exposure_check, grid_check):
            if int(check["resource"]["peak_rss_bytes"]) > arguments.memory_cap_bytes:
                raise ValueError(f"state {state} resource ceiling failed")
        _, exposure_sha512 = hashes(exposure)
        if exposure_sha512 != exposure_check["exposure_sha512"]:
            raise ValueError(f"state {state} exposure identity differs from validation")
        frame = pd.read_parquet(exposure)
        frame["county_geoid"] = frame.county_geoid.astype(str).str.zfill(5)
        if not frame.county_geoid.str.startswith(state).all():
            raise ValueError(f"state {state} partition contains another state")
        frames.append(frame)
        receipts.append({
            "state_fips": state,
            "counties": int(grid_check["counties"]),
            "grid_rows": int(grid_check["rows"]),
            "grid_sha512": str(grid_check["grid_sha512"]),
            "exposure_rows": int(exposure_check["rows"]),
            "exposure_sha512": exposure_sha512,
            "grid_peak_rss_bytes": int(grid_check["resource"]["peak_rss_bytes"]),
            "exposure_peak_rss_bytes": int(exposure_check["resource"]["peak_rss_bytes"]),
        })
    result = pd.concat(frames, ignore_index=True)
    keys = ["county_geoid", "mask_id", "harvest_year"]
    if result.duplicated(keys).any():
        raise ValueError("merged state partitions contain duplicate county-mask-year keys")
    actual_counties = set(result.county_geoid)
    if actual_counties != expected_counties:
        raise ValueError(
            f"merged counties differ from inventory: missing={len(expected_counties - actual_counties)} "
            f"extra={len(actual_counties - expected_counties)}"
        )
    if set(result.mask_id) != {"cultivated_agriculture", "broad_agriculture"}:
        raise ValueError("merged mask support differs")
    if set(map(int, result.harvest_year.unique())) != set(range(2001, 2014)):
        raise ValueError("merged harvest-year support differs")
    expected_rows = len(expected_counties) * 2 * 13
    if len(result) != expected_rows:
        raise ValueError(f"merged row count {len(result)} differs from {expected_rows}")
    if result.scc_authorized.any():
        raise ValueError("merged exposure authorizes SCC use")
    maximum_error = 0.0
    for year, part in result.groupby("harvest_year", observed=True):
        expected_days = 366 if pd.Timestamp(int(year), 1, 1).is_leap_year else 365
        if not part.represented_days.eq(expected_days).all():
            raise ValueError(f"represented days differ for harvest year {year}")
        total = part[[f"weeks_{name}" for name in CATEGORIES]].sum(axis=1)
        error = (total - expected_days / 7).abs()
        maximum_error = max(maximum_error, float(error.max()))
        if not error.le(1e-9).all():
            raise ValueError(f"annual category accounting differs for {year}")
    result = result.sort_values(keys).reset_index(drop=True)
    arguments.out.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.Table.from_pandas(result, preserve_index=False), arguments.out, compression="zstd")
    output_sha256, output_sha512 = hashes(arguments.out)
    audit = {
        "schema": "usdm_national_990m_merged_validation_v1",
        "passed": True,
        "state_count": len(states),
        "counties": len(actual_counties),
        "masks": 2,
        "harvest_years": list(range(2001, 2014)),
        "rows": len(result),
        "maximum_category_sum_error_weeks": maximum_error,
        "output": {
            "path": str(arguments.out), "sha256": output_sha256,
            "sha512": output_sha512, "bytes": arguments.out.stat().st_size,
        },
        "maximum_grid_peak_rss_bytes": max(row["grid_peak_rss_bytes"] for row in receipts),
        "maximum_exposure_peak_rss_bytes": max(row["exposure_peak_rss_bytes"] for row in receipts),
        "partitions": receipts,
        "claim_boundary": "validates national 990 m historical exposure accounting only; not causal, future, damage, global-transfer, or SCC evidence",
    }
    arguments.audit_out.parent.mkdir(parents=True, exist_ok=True)
    arguments.audit_out.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({key: audit[key] for key in (
        "passed", "state_count", "counties", "rows", "maximum_category_sum_error_weeks",
        "maximum_grid_peak_rss_bytes", "maximum_exposure_peak_rss_bytes",
    )}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
