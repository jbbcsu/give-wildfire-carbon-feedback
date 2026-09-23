#!/usr/bin/env python3
"""Bounded full-source audit of the Hultgren maize month calendar."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.hultgren_crop_calendar import (
    calendar_months_for_report_year,
    month_of_season,
    normalized_plant_month,
    season_months,
    source_month_from_day,
)

DEFAULT_DATA = ROOT / "data/raw/hultgren_response/historical_git/dae5fe8d0d4a260328e4baa45b547368bd6790b3/corn_gmfd_v1_ready.dta"
DEFAULT_OUTPUT = ROOT / "data/provenance/hultgren_maize_calendar_validation_20260923.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--chunk-size", type=int, default=50_000)
    args = parser.parse_args()
    if not args.data.exists():
        raise FileNotFoundError(args.data)
    if args.chunk_size <= 0:
        raise ValueError("chunk size must be positive")

    columns = [
        "iso", "median_plant_date", "median_harvest_date",
        "median_plant_month", "median_harvest_month", "season_length",
    ]
    observations = 0
    missing_rows = 0
    valid_rows = 0
    plant_month_mismatches = 0
    harvest_month_mismatches = 0
    season_length_mismatches = 0
    phase_partition_mismatches = 0
    calendar_counts: Counter[str] = Counter()
    regime_counts: Counter[str] = Counter()
    country_counts: Counter[str] = Counter()
    source_year_configurations: set[tuple[str, int, int]] = set()

    with pd.read_stata(args.data, columns=columns, iterator=True, convert_categoricals=False) as reader:
        while True:
            try:
                chunk = reader.read(args.chunk_size)
            except StopIteration:
                break
            if chunk.empty:
                break
            observations += len(chunk)
            complete = chunk.dropna(subset=columns[1:])
            missing_rows += len(chunk) - len(complete)
            for row in complete.itertuples(index=False):
                valid_rows += 1
                derived_plant_raw = source_month_from_day(row.median_plant_date)
                derived_harvest = source_month_from_day(row.median_harvest_date)
                derived_plant = normalized_plant_month(derived_plant_raw, derived_harvest)
                stored_plant = int(row.median_plant_month)
                stored_harvest = int(row.median_harvest_month)
                stored_length = int(row.season_length)
                plant_month_mismatches += derived_plant != stored_plant
                harvest_month_mismatches += derived_harvest != stored_harvest
                months = season_months(stored_plant, stored_harvest)
                season_length_mismatches += len(months) != stored_length
                indices = tuple(month_of_season(month, stored_plant, stored_harvest) for month in months)
                phase_counts = (
                    sum(index == 1 for index in indices),
                    sum(2 <= index <= 4 for index in indices),
                    sum(index >= 5 for index in indices),
                )
                phase_partition_mismatches += phase_counts != (1, 3, stored_length - 4)
                calendar_counts[f"{stored_plant:02d}-{stored_harvest:02d}-{stored_length}"] += 1
                regime_counts["cross_year" if stored_plant >= stored_harvest else "same_year"] += 1
                country_counts[str(row.iso)] += 1
                source_year_configurations.add((str(row.iso), stored_plant, stored_harvest))

    source_year_mismatches = 0
    for iso, plant, harvest in source_year_configurations:
        pairs = calendar_months_for_report_year(2000, plant, harvest, iso)
        expected_months = season_months(plant, harvest)
        if tuple(month for _, month in pairs) != expected_months:
            source_year_mismatches += 1

    gates = {
        "source_observation_count": observations == 412_282,
        "complete_calendar_count": valid_rows == 377_973 and missing_rows == 34_309,
        "plant_day_to_month_exact": plant_month_mismatches == 0,
        "harvest_day_to_month_exact": harvest_month_mismatches == 0,
        "inclusive_season_length_exact": season_length_mismatches == 0,
        "three_phase_partition_exact": phase_partition_mismatches == 0,
        "report_year_mapping_internally_exact": source_year_mismatches == 0,
    }
    if not all(gates.values()):
        raise AssertionError(f"Hultgren maize calendar gate failed: {gates}")

    payload = {
        "schema": "hultgren_maize_calendar_validation/v1",
        "validated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": {
            "dataset_path": str(args.data.relative_to(ROOT)),
            "dataset_sha256": sha256(args.data),
            "source_code": "collapse_clim.do pinned at 3ccdffcd4e4ff6e55566ce76e2aac130ee86349a",
        },
        "execution": {"chunk_size": args.chunk_size, "columns_read": columns},
        "counts": {
            "observations": observations,
            "valid_calendar_rows": valid_rows,
            "missing_calendar_rows": missing_rows,
            "unique_calendar_configurations": len(calendar_counts),
            "calendar_configurations": dict(sorted(calendar_counts.items())),
            "year_regimes": dict(sorted(regime_counts.items())),
            "india_valid_rows": country_counts.get("IND", 0),
            "unique_country_calendar_year_configurations": len(source_year_configurations),
        },
        "mismatches": {
            "plant_month": int(plant_month_mismatches),
            "harvest_month": int(harvest_month_mismatches),
            "season_length": int(season_length_mismatches),
            "phase_partition": int(phase_partition_mismatches),
            "report_year_mapping": int(source_year_mismatches),
        },
        "validation_gates": gates,
        "claim_gates": {
            "source_calendar_month_arithmetic_reproduced": True,
            "primitive_daily_weather_reproduced": False,
            "administrative_grid_aggregation_validated": False,
            "future_climate_projection_validated": False,
            "damage_estimate_validated": False,
            "scc_estimate_validated": False,
        },
        "interpretation": (
            "The source day-to-month, inclusive season, month-of-season and three-phase calendar "
            "arithmetic are reproduced for every complete historical maize row. This validates "
            "calendar bookkeeping, not daily weather, spatial aggregation, future response, damage, or SCC."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": "ok", "gates": gates, "counts": payload["counts"]}, indent=2))


if __name__ == "__main__":
    main()
