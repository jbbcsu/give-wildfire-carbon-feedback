#!/usr/bin/env python3
"""Aggregate MapSPAM 2000 maize production to the Hultgren half-degree grid."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
FIELDS = [
    "maize_total_mt",
    "maize_rainfed_high_mt",
    "maize_rainfed_low_mt",
    "maize_irrigated_mt",
    "maize_rainfed_subsistence_mt",
]


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def halfdegree_key(latitude: float, longitude: float) -> tuple[int, int]:
    require(math.isfinite(latitude) and math.isfinite(longitude), "nonfinite coordinate")
    require(-90.0 < latitude < 90.0 and -180.0 < longitude < 180.0, "coordinate outside cell centers")
    row = math.floor((90.0 - latitude) / 0.5)
    column = math.floor((longitude + 180.0) / 0.5)
    require(0 <= row < 360 and 0 <= column < 720, "half-degree key outside grid")
    return row, column


def aggregate(path: Path) -> tuple[dict[tuple[int, int], list[float]], dict[str, float | int]]:
    cells: dict[tuple[int, int], list[float]] = defaultdict(lambda: [0.0] * len(FIELDS))
    totals = [0.0] * len(FIELDS)
    rows = 0
    positive_rows = 0
    with path.open("r", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        required = {"latitude", "longitude", *FIELDS}
        require(reader.fieldnames is not None and required <= set(reader.fieldnames), "MapSPAM columns differ")
        for row_number, record in enumerate(reader, start=2):
            rows += 1
            values = [float(record[field]) for field in FIELDS]
            require(all(math.isfinite(value) and value >= 0.0 for value in values), f"invalid production at row {row_number}")
            if values[0] <= 0.0:
                continue
            positive_rows += 1
            key = halfdegree_key(float(record["latitude"]), float(record["longitude"]))
            target = cells[key]
            for index, value in enumerate(values):
                target[index] += value
                totals[index] += value
    require(rows > 0 and totals[0] > 0.0, "empty MapSPAM production input")
    component_sum = sum(totals[1:])
    component_difference = component_sum - totals[0]
    component_relative_difference = component_difference / totals[0]
    # The distributed MapSPAM values are rounded to 0.1 mt.  Across millions
    # of records that produces a small source-level residual, so enforce and
    # report a tight relative tolerance rather than pretending exact identity.
    require(abs(component_relative_difference) <= 1e-6, "MapSPAM maize systems differ materially from total")
    return dict(cells), {
        "source_rows": rows,
        "positive_maize_rows": positive_rows,
        "positive_halfdegree_cells": len(cells),
        "system_component_sum_mt": component_sum,
        "system_component_minus_total_mt": component_difference,
        "system_component_relative_difference": component_relative_difference,
        **{f"source_{field}": total for field, total in zip(FIELDS, totals, strict=True)},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mapspam", type=Path, required=True)
    parser.add_argument("--moderators", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists() and not args.receipt.exists(), "fresh outputs required")

    cells, audit = aggregate(args.mapspam)
    moderators = pd.read_parquet(args.moderators, columns=["native_lat_index", "native_lon_index", "income_available"])
    require(len(moderators) == len(moderators.drop_duplicates(["native_lat_index", "native_lon_index"])), "duplicate moderator cells")
    eligible = set(zip(moderators.native_lat_index.astype(int), moderators.native_lon_index.astype(int), strict=True))
    income = set(zip(
        moderators.loc[moderators.income_available, "native_lat_index"].astype(int),
        moderators.loc[moderators.income_available, "native_lon_index"].astype(int),
        strict=True,
    ))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["native_lat_index", "native_lon_index", "latitude", "longitude", *FIELDS])
        for (row, column), values in sorted(cells.items()):
            writer.writerow([row, column, 89.75 - 0.5 * row, -179.75 + 0.5 * column, *[format(value, ".12g") for value in values]])

    total = float(audit["source_maize_total_mt"])
    eligible_total = sum(values[0] for key, values in cells.items() if key in eligible)
    income_total = sum(values[0] for key, values in cells.items() if key in income)
    result = {
        "schema": "mapspam_halfdegree_maize_production_weights/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "production_weight_basis_complete_not_value_welfare_damage_or_scc",
        "source": {"path": str(args.mapspam), "bytes": args.mapspam.stat().st_size, "sha256": digest(args.mapspam), "doi": "10.7910/DVN/A50I2T"},
        "moderators": {"path": str(args.moderators), "sha256": digest(args.moderators)},
        "aggregation": "sum 5-arcminute MapSPAM production points within native 0.5-degree ISIMIP/GGCMI cells",
        "audit": {
            **audit,
            "eligible_hultgren_maize_production_mt": eligible_total,
            "eligible_hultgren_maize_production_fraction": eligible_total / total,
            "income_matched_hultgren_maize_production_mt": income_total,
            "income_matched_hultgren_maize_production_fraction": income_total / total,
        },
        "output": {"path": str(args.output), "bytes": args.output.stat().st_size, "sha256": digest(args.output)},
        "claim_gates": {"production_weight_basis": True, "value_weight": False, "welfare": False, "damage_or_scc": False},
        "implementation": {"path": str(Path(__file__).resolve().relative_to(ROOT)), "sha256": digest(Path(__file__).resolve())},
    }
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "audit": result["audit"], "output": result["output"]}, indent=2))


if __name__ == "__main__":
    main()
