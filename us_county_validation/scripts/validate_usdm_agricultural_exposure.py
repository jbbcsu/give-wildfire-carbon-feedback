#!/usr/bin/env python3
"""Independent accounting validation for CDL-weighted USDM exposures."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

import pyarrow.parquet as pq


CATEGORIES = ("none", "d0", "d1", "d2", "d3", "d4")


def sha512_file(path: Path) -> str:
    digest = hashlib.sha512()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--exposure", type=Path, required=True)
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--resource", type=Path)
    parser.add_argument("--memory-cap-bytes", type=int, default=640 * 1024 * 1024)
    parser.add_argument("--out", type=Path, required=True)
    arguments = parser.parse_args()

    audit = json.loads(arguments.audit.read_text(encoding="utf-8"))
    parquet = pq.ParquetFile(arguments.exposure)
    exposure_columns = [f"weeks_{name}" for name in CATEGORIES]
    required = {
        "county_geoid", "mask_id", "harvest_year", "represented_days",
        "total_equivalent_weeks", "scc_authorized", *exposure_columns,
    }
    if missing := required - set(parquet.schema_arrow.names):
        raise ValueError(f"exposure file lacks {sorted(missing)}")

    keys: set[tuple[str, str, int]] = set()
    years: Counter[int] = Counter()
    groups_by_year: dict[int, set[tuple[str, str]]] = defaultdict(set)
    maximum_sum_error = 0.0
    rows = 0
    for batch in parquet.iter_batches(batch_size=65536, columns=sorted(required)):
        values = batch.to_pydict()
        for position in range(batch.num_rows):
            geoid = str(values["county_geoid"][position]).zfill(5)
            mask = str(values["mask_id"][position])
            year = int(values["harvest_year"][position])
            key = (geoid, mask, year)
            if key in keys:
                raise ValueError(f"duplicate county-mask-year row {key}")
            keys.add(key)
            weeks = [float(values[column][position]) for column in exposure_columns]
            if any(not math.isfinite(value) or value < -1e-12 for value in weeks):
                raise ValueError(f"nonfinite or negative exposure at {key}")
            total = float(values["total_equivalent_weeks"][position])
            represented = int(values["represented_days"][position])
            error = abs(sum(weeks) - total)
            maximum_sum_error = max(maximum_sum_error, error)
            if error > 1e-9 or not math.isclose(total, represented / 7, rel_tol=0, abs_tol=1e-9):
                raise ValueError(f"weekly/day accounting mismatch at {key}")
            if values["scc_authorized"][position] is not False:
                raise ValueError(f"SCC authorization flag is not false at {key}")
            years[year] += 1
            groups_by_year[year].add((geoid, mask))
            rows += 1
    if rows != parquet.metadata.num_rows or rows != int(audit["output_rows"]):
        raise ValueError("exposure row count differs from metadata or audit")
    if set(years) != set(map(int, audit["harvest_years"])):
        raise ValueError("harvest-year support differs from audit")
    group_sets = list(groups_by_year.values())
    if any(value != group_sets[0] for value in group_sets[1:]):
        raise ValueError("county-mask support differs across harvest years")

    overlap_total = 0
    map_dates = set()
    for row in audit["map_audits"]:
        map_date = str(row["map_date"])
        if map_date in map_dates:
            raise ValueError(f"duplicate map audit {map_date}")
        map_dates.add(map_date)
        overlap_total += sum(int(value) for value in row["exclusive_class_overlap_points"].values())
    if overlap_total:
        raise ValueError("one or more maps contain exclusive-class overlaps at support points")
    if len(map_dates) != int(audit["maps_processed"]):
        raise ValueError("map audit count differs from declared count")

    sha512 = sha512_file(arguments.exposure)
    if sha512 != audit["output_sha512"]:
        raise ValueError("exposure checksum differs from audit")
    resource = None
    if arguments.resource is not None:
        resource = json.loads(arguments.resource.read_text(encoding="utf-8"))
        if resource["status"] != "command_completed" or int(resource["returncode"]) != 0:
            raise ValueError("resource receipt does not record success")
        if int(resource["peak_rss_bytes"]) > arguments.memory_cap_bytes:
            raise ValueError("resource receipt exceeds memory cap")

    result = {
        "schema": "usdm_agricultural_area_exposure_independent_validation_v1",
        "passed": True,
        "exposure": str(arguments.exposure),
        "exposure_sha512": sha512,
        "rows": rows,
        "maps": len(map_dates),
        "harvest_years": sorted(years),
        "county_mask_groups": len(group_sets[0]),
        "maximum_category_sum_error_weeks": maximum_sum_error,
        "exclusive_class_overlap_points": overlap_total,
        "resource": resource,
        "claim_boundary": "validates spatial-temporal accounting, not causal, global, or SCC interpretation",
    }
    arguments.out.parent.mkdir(parents=True, exist_ok=True)
    arguments.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
