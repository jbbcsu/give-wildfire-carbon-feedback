#!/usr/bin/env python3
"""Build full-calendar-year county USDM exposure weeks, state by state."""
from __future__ import annotations

import argparse
import hashlib
import json
import tomllib
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.dataset as ds
import pyarrow.parquet as pq


CATEGORIES = ["none_pct", "d0_pct", "d1_pct", "d2_pct", "d3_pct", "d4_pct"]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def aggregate_state_year(
    weeks: pd.DataFrame, state: str, year: int, crops: tuple[str, ...]
) -> pd.DataFrame:
    start = pd.Timestamp(year, 1, 1)
    end = pd.Timestamp(year, 12, 31)
    overlap = weeks.loc[weeks.valid_end.ge(start) & weeks.valid_start.le(end)].copy()
    if overlap.empty:
        raise ValueError(f"no USDM intervals overlap {state} {year}")
    overlap["clip_start"] = overlap.valid_start.clip(lower=start)
    overlap["clip_end"] = overlap.valid_end.clip(upper=end)
    overlap["days"] = (overlap.clip_end - overlap.clip_start).dt.days + 1
    if (overlap.days <= 0).any():
        raise ValueError(f"nonpositive clipped interval in {state} {year}")
    ordered = overlap.sort_values(["county_geoid", "clip_start", "clip_end"])
    previous_end = ordered.groupby("county_geoid", observed=True).clip_end.shift()
    has_previous = previous_end.notna()
    expected_start = previous_end + pd.Timedelta(days=1)
    if ordered.loc[has_previous, "clip_start"].ne(expected_start.loc[has_previous]).any():
        raise ValueError(f"gapped or overlapping intervals in {state} {year}")
    boundaries = ordered.groupby("county_geoid", observed=True).agg(
        first_start=("clip_start", "min"),
        last_end=("clip_end", "max"),
        covered_days=("days", "sum"),
        county_name=("county_name", "first"),
    )
    expected_days = (end - start).days + 1
    if (
        boundaries.first_start.ne(start).any()
        or boundaries.last_end.ne(end).any()
        or boundaries.covered_days.ne(expected_days).any()
    ):
        raise ValueError(f"incomplete daily coverage in {state} {year}")
    weighted = ordered[CATEGORIES].multiply(ordered.days / 700, axis=0)
    weighted["county_geoid"] = ordered.county_geoid.to_numpy()
    sums = weighted.groupby("county_geoid", observed=True)[CATEGORIES].sum()
    sums = sums.rename(columns={name: name.removesuffix("_pct") + "_weeks" for name in CATEGORIES})
    sums = sums.join(boundaries[["county_name"]], how="left")
    week_columns = [name.removesuffix("_pct") + "_weeks" for name in CATEGORIES]
    sums["all_category_weeks"] = sums[week_columns].sum(axis=1)
    expected_weeks = expected_days / 7
    # Official category percentages are rounded to two decimals. The raw panel
    # already enforces a per-week sum tolerance of 0.15 percentage points, so
    # its conservative annual accumulation bound is <0.08 week.
    if not np.allclose(sums.all_category_weeks, expected_weeks, rtol=0, atol=0.08):
        raise ValueError(f"category weeks do not reconcile in {state} {year}")
    sums["d1plus_weeks"] = sums[["d1_weeks", "d2_weeks", "d3_weeks", "d4_weeks"]].sum(axis=1)
    sums["d2plus_weeks"] = sums[["d2_weeks", "d3_weeks", "d4_weeks"]].sum(axis=1)
    sums["drought_weighted_index_weeks"] = (
        sums.d0_weeks + 2 * sums.d1_weeks + 3 * sums.d2_weeks
        + 4 * sums.d3_weeks + 5 * sums.d4_weeks
    )
    base = sums.reset_index()
    outputs = []
    for crop in crops:
        part = base.copy()
        part.insert(1, "state", state)
        part.insert(2, "outcome_crop", crop)
        part.insert(3, "harvest_year", year)
        part.insert(4, "exposure_period", "calendar_year")
        part["source_area_basis"] = "county_area"
        part["published_area_basis"] = "agricultural_area"
        part["exact_published_exposure_replication"] = False
        part["analysis_role"] = "historical_external_validation_only"
        part["scc_authorized"] = False
        outputs.append(part)
    return pd.concat(outputs, ignore_index=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--weeks", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--audit-out", type=Path, required=True)
    arguments = parser.parse_args()
    contract = tomllib.loads(arguments.config.read_text(encoding="utf-8"))
    states = tuple(str(value) for value in contract["states"])
    years = range(int(contract["year_min"]), int(contract["year_max"]) + 1)
    crops = ("corn_grain", "soybeans")
    source = ds.dataset(arguments.weeks, format="parquet")
    required = {"county_geoid", "state", "county_name", "map_date", "valid_start", "valid_end", *CATEGORIES}
    if missing := required - set(source.schema.names):
        raise ValueError(f"USDM panel lacks fields {sorted(missing)}")
    arguments.out.parent.mkdir(parents=True, exist_ok=True)
    writer: pq.ParquetWriter | None = None
    total_rows = 0
    state_audit: list[dict[str, Any]] = []
    try:
        for state in states:
            table = source.to_table(filter=ds.field("state") == state, columns=sorted(required))
            frame = table.to_pandas()
            for column in ("map_date", "valid_start", "valid_end"):
                frame[column] = pd.to_datetime(frame[column], errors="raise")
            state_rows = 0
            state_counties: set[str] = set()
            for year in years:
                result = aggregate_state_year(frame, state, year, crops)
                output = pa.Table.from_pandas(result, preserve_index=False)
                if writer is None:
                    writer = pq.ParquetWriter(arguments.out, output.schema, compression="zstd")
                elif output.schema != writer.schema:
                    raise ValueError(f"output schema drift for {state} {year}")
                writer.write_table(output)
                total_rows += len(result)
                state_rows += len(result)
                state_counties.update(map(str, result.county_geoid.unique()))
            state_audit.append({
                "state": state, "rows": state_rows, "counties": len(state_counties)
            })
    finally:
        if writer is not None:
            writer.close()
    if writer is None:
        raise RuntimeError("no annual exposures written")
    metadata = pq.ParquetFile(arguments.out).metadata
    if metadata.num_rows != total_rows:
        raise RuntimeError("annual exposure Parquet row count mismatch")
    audit = {
        "schema": "usdm_calendar_year_county_exposure_v1",
        "input": {"path": str(arguments.weeks), "sha256": sha256(arguments.weeks)},
        "config": {"path": str(arguments.config), "sha256": sha256(arguments.config)},
        "output": {"path": str(arguments.out), "sha256": sha256(arguments.out), "rows": total_rows},
        "states": state_audit,
        "crops": list(crops),
        "year_start": min(years),
        "year_end": max(years),
        "exposure_definition": "sum of county-area category fraction times covered days divided by seven",
        "annual_category_reconciliation_tolerance_weeks": 0.08,
        "published_difference": "county-area REST shares replace published agricultural-area intersection",
        "role": "historical_external_validation_only_not_future_projection_damage_or_scc",
    }
    arguments.audit_out.parent.mkdir(parents=True, exist_ok=True)
    arguments.audit_out.write_text(
        json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"wrote {total_rows} crop-county-year exposure rows")


if __name__ == "__main__":
    main()
