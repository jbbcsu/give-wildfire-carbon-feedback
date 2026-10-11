#!/usr/bin/env python3
"""Build crop-season monthly precipitation climatologies for timing analysis.

This extends the validated Hultgren precipitation-basis input without altering
the existing quantity benchmark.  It preserves each rainfed/irrigated crop
calendar separately and stores mean monthly rainfall by crop-season offset.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from build_hultgren_grid_weather_basis import crop_month_keys, load_support
from build_hultgren_precip_basis_climatology import EXPECTED, digest, require, stream_monthly

ROOT = Path(__file__).resolve().parents[1]
MAX_MONTHS = 10
RAIN_COLUMNS = [f"crop_month_offset_{index:02d}_precip_mm" for index in range(1, MAX_MONTHS + 1)]
CALENDAR_COLUMNS = [f"crop_month_offset_{index:02d}_calendar_month" for index in range(1, MAX_MONTHS + 1)]


def sha256(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def offset_climatology(
    monthly_rain: np.ndarray,
    month_lookup: dict[tuple[int, int], int],
    plant_month: int,
    harvest_month: int,
    harvest_years: range = range(1982, 2011),
) -> tuple[np.ndarray, np.ndarray]:
    """Return mean rainfall and calendar month for each crop-season offset."""
    sequences = []
    calendar_months = None
    for harvest_year in harvest_years:
        keys = crop_month_keys(harvest_year, plant_month, harvest_month)
        require(4 <= len(keys) <= MAX_MONTHS, "crop season outside supported 4-10 months")
        this_calendar = np.asarray([month for _, month in keys], dtype=np.int16)
        if calendar_months is None:
            calendar_months = this_calendar
        else:
            require(np.array_equal(calendar_months, this_calendar), "calendar-month sequence changed across harvest years")
        sequences.append(monthly_rain[[month_lookup[key] for key in keys]])
    matrix = np.stack(sequences)
    require(np.isfinite(matrix).all() and np.all(matrix >= 0), "invalid crop-season monthly rainfall")
    return matrix.mean(axis=0, dtype=np.float64), calendar_months


def summarize_regime(
    regime: str,
    support: pd.DataFrame,
    union_lookup: dict[tuple[int, int], int],
    months: pd.DatetimeIndex,
    rain: np.ndarray,
) -> pd.DataFrame:
    month_lookup = {(int(value.year), int(value.month)): index for index, value in enumerate(months)}
    records = []
    for row in support.itertuples(index=False):
        union_index = union_lookup[(int(row.native_lat_index), int(row.native_lon_index))]
        values, calendar_months = offset_climatology(
            rain[:, union_index], month_lookup, int(row.plant_month), int(row.harvest_month)
        )
        record = {
            "regime": regime,
            "native_lat_index": int(row.native_lat_index),
            "native_lon_index": int(row.native_lon_index),
            "latitude": float(row.latitude),
            "longitude": float(row.longitude),
            "plant_month": int(row.plant_month),
            "harvest_month": int(row.harvest_month),
            "season_months": int(row.season_months),
            "mirca_area_ha": float(row.mirca_area_ha),
            "complete_harvest_years": 29,
        }
        for index in range(MAX_MONTHS):
            active = index < len(values)
            record[RAIN_COLUMNS[index]] = float(values[index]) if active else 0.0
            record[CALENDAR_COLUMNS[index]] = int(calendar_months[index]) if active else 0
        records.append(record)
    output = pd.DataFrame(records)
    require(len(output) == len(support), f"{regime} output rows differ")
    require(np.isfinite(output[RAIN_COLUMNS].to_numpy()).all(), f"{regime} rainfall invalid")
    require((output[RAIN_COLUMNS] >= 0).all().all(), f"{regime} rainfall negative")
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pr", action="append", type=Path, required=True)
    parser.add_argument("--rainfed-calendar", type=Path, required=True)
    parser.add_argument("--rainfed-area", type=Path, required=True)
    parser.add_argument("--irrigated-calendar", type=Path, required=True)
    parser.add_argument("--irrigated-area", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists() and not args.receipt.exists(), "fresh outputs required")
    require(len(args.pr) == 3 and {path.name for path in args.pr} == set(EXPECTED), "three frozen precipitation decades required")
    for path in args.pr:
        require(digest(path, "sha512") == EXPECTED[path.name], f"precipitation source hash differs: {path.name}")

    rainfed, rainfed_audit = load_support(args.rainfed_calendar, args.rainfed_area)
    irrigated, irrigated_audit = load_support(args.irrigated_calendar, args.irrigated_area)
    union = pd.concat([rainfed[["native_lat_index", "native_lon_index"]], irrigated[["native_lat_index", "native_lon_index"]]])
    union = union.drop_duplicates().sort_values(["native_lat_index", "native_lon_index"]).reset_index(drop=True)
    months, rain, stream_audit = stream_monthly(args.pr, union)
    lookup = {(int(row.native_lat_index), int(row.native_lon_index)): index for index, row in union.iterrows()}
    output = pd.concat([
        summarize_regime("rainfed", rainfed, lookup, months, rain),
        summarize_regime("irrigated", irrigated, lookup, months, rain),
    ], ignore_index=True)
    require(not output.duplicated(["regime", "native_lat_index", "native_lon_index"]).any(), "duplicate regime-cell output")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    output.to_parquet(args.output, index=False, compression="zstd")
    require(args.output.stat().st_size < 64 * 2**20, "output exceeds 64 MiB owned-output budget")

    result = {
        "schema": "hultgren_monthly_precip_climatology/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "complete_historical_monthly_precipitation_input_not_response_damage_or_scc",
        "source_period": [1981, 2010],
        "harvest_years": [1982, 2010],
        "definition": "mean monthly precipitation across 29 complete crop harvest years, indexed from planting through harvest and kept separate by irrigation regime",
        "columns": {"rainfall_mm": RAIN_COLUMNS, "calendar_month": CALENDAR_COLUMNS},
        "sources": [{"path": str(path), "bytes": path.stat().st_size, "sha512": digest(path, "sha512")} for path in sorted(args.pr)],
        "support_sources": {
            "rainfed_calendar": {"path": str(args.rainfed_calendar), "sha256": sha256(args.rainfed_calendar)},
            "rainfed_area": {"path": str(args.rainfed_area), "sha256": sha256(args.rainfed_area)},
            "irrigated_calendar": {"path": str(args.irrigated_calendar), "sha256": sha256(args.irrigated_calendar)},
            "irrigated_area": {"path": str(args.irrigated_area), "sha256": sha256(args.irrigated_area)},
        },
        "support": {"union_cells": int(len(union)), "rainfed_cells": int(len(rainfed)), "irrigated_cells": int(len(irrigated)), "output_rows": int(len(output)), "rainfed": rainfed_audit, "irrigated": irrigated_audit, **stream_audit},
        "output": {"path": str(args.output), "bytes": args.output.stat().st_size, "sha256": sha256(args.output)},
        "limitations": [
            "This is a historical climatology, not a climate-change projection.",
            "Monthly timing cannot identify daily dry spells, drought indices, or precipitation extremes.",
            "Rainfed and irrigated calendars remain separate; no response or welfare aggregation is performed.",
            "No damage or SCC gate is opened.",
        ],
        "claim_gates": {"monthly_precipitation_input": True, "response": False, "damage": False, "scc": False},
        "implementation": {"path": str(Path(__file__).resolve().relative_to(ROOT)), "sha256": sha256(Path(__file__).resolve())},
    }
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "support": result["support"], "output": result["output"]}, indent=2))


if __name__ == "__main__":
    main()
