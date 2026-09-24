#!/usr/bin/env python3
"""Build conditional half-degree maize gross-production-value weights.

National 1999--2001 FAOSTAT constant-dollar maize values are allocated within
country in proportion to fixed MapSPAM 2000 maize production. Countries
without a baseline value remain missing. This is a baseline value-weight
sensitivity, not a market-welfare, damage, or SCC calculation.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from audit_mapspam_faostat_welfare_crosswalk import parse_unsd_m49, read_faostat_baseline
from build_mapspam_halfdegree_maize_weights import halfdegree_key

ROOT = Path(__file__).resolve().parents[1]
MAIZE_ITEM = 56


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def allocate(
    mapspam: Path, stat_to_iso: dict[str, str | None], iso_value_thousand_usd: dict[str, float]
) -> tuple[dict[tuple[int, int], tuple[float, float]], dict[str, float | int]]:
    country_production: dict[str, float] = defaultdict(float)
    source_total = 0.0
    matched_total = 0.0
    rows = 0
    with mapspam.open("r", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        required = {"stat_code", "latitude", "longitude", "maize_total_mt"}
        require(reader.fieldnames is not None and required <= set(reader.fieldnames), "MapSPAM columns differ")
        for row_number, record in enumerate(reader, start=2):
            rows += 1
            production = float(record["maize_total_mt"])
            require(math.isfinite(production) and production >= 0.0, f"invalid production at row {row_number}")
            source_total += production
            iso = stat_to_iso.get(record["stat_code"])
            if production > 0.0 and iso in iso_value_thousand_usd:
                country_production[iso] += production
                matched_total += production
    require(rows > 0 and source_total > 0.0 and matched_total > 0.0, "empty matched production")
    require(all(value > 0.0 for value in country_production.values()), "nonpositive matched country production")

    cells: dict[tuple[int, int], list[float]] = defaultdict(lambda: [0.0, 0.0])
    allocated_by_country: dict[str, float] = defaultdict(float)
    with mapspam.open("r", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        for row_number, record in enumerate(reader, start=2):
            production = float(record["maize_total_mt"])
            if production <= 0.0:
                continue
            iso = stat_to_iso.get(record["stat_code"])
            if iso not in iso_value_thousand_usd:
                continue
            value_usd = (
                production / country_production[iso]
                * iso_value_thousand_usd[iso]
                * 1000.0
            )
            require(math.isfinite(value_usd) and value_usd >= 0.0, f"invalid allocation at row {row_number}")
            key = halfdegree_key(float(record["latitude"]), float(record["longitude"]))
            cells[key][0] += production
            cells[key][1] += value_usd
            allocated_by_country[iso] += value_usd
    for iso, allocated in allocated_by_country.items():
        expected = iso_value_thousand_usd[iso] * 1000.0
        require(abs(allocated - expected) <= 1e-10 * max(1.0, expected), f"national allocation differs for {iso}")
    total_value = sum(value * 1000.0 for iso, value in iso_value_thousand_usd.items() if iso in country_production)
    require(abs(sum(value[1] for value in cells.values()) - total_value) <= 1e-10 * total_value, "global value allocation differs")
    return {key: (value[0], value[1]) for key, value in cells.items()}, {
        "source_rows": rows,
        "source_maize_production_mt": source_total,
        "matched_maize_production_mt": matched_total,
        "matched_maize_production_fraction": matched_total / source_total,
        "matched_country_count": len(country_production),
        "positive_halfdegree_cells": len(cells),
        "allocated_constant_2014_2016_usd": total_value,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mapspam", type=Path, required=True)
    parser.add_argument("--gec-audit", type=Path, required=True)
    parser.add_argument("--faostat", type=Path, required=True)
    parser.add_argument("--unsd", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists() and not args.receipt.exists(), "fresh outputs required")

    gec = json.loads(args.gec_audit.read_text(encoding="utf-8"))
    require(gec["unresolved_rows"] == 0 and gec["gate"]["four_character_country_mapping_resolved"], "GEC resolution audit failed")
    stat_to_iso = {row["stat_code"]: row["resolved_iso3"] for row in gec["per_stat_code"]}
    iso_to_m49, _ = parse_unsd_m49(args.unsd)
    faostat = read_faostat_baseline(args.faostat)
    iso_values = {
        iso: float(faostat[(MAIZE_ITEM, m49)]["mean_constant_2014_2016_thousand_usd"])
        for iso, m49 in iso_to_m49.items()
        if (MAIZE_ITEM, m49) in faostat
    }
    cells, audit = allocate(args.mapspam, stat_to_iso, iso_values)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["native_lat_index", "native_lon_index", "latitude", "longitude", "matched_maize_production_mt", "maize_gross_production_value_constant_2014_2016_usd"])
        for (row, column), (production, value) in sorted(cells.items()):
            writer.writerow([row, column, 89.75 - 0.5 * row, -179.75 + 0.5 * column, format(production, ".12g"), format(value, ".12g")])
    result = {
        "schema": "mapspam_faostat_halfdegree_maize_value_weights/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "conditional_baseline_gross_production_value_weights_not_welfare_damage_or_scc",
        "method": "allocate each matched country's mean 1999-2001 FAOSTAT maize gross production value across MapSPAM cells in proportion to fixed MapSPAM 2000 maize production; exclude countries without value and do not impute",
        "units": "constant 2014-2016 US dollars",
        "sources": {
            "mapspam": {"path": str(args.mapspam), "sha256": digest(args.mapspam), "doi": "10.7910/DVN/A50I2T"},
            "gec_audit": {"path": str(args.gec_audit), "sha256": digest(args.gec_audit)},
            "faostat": {"path": str(args.faostat), "sha256": digest(args.faostat), "license": "CC-BY-4.0"},
            "unsd": {"path": str(args.unsd), "sha256": digest(args.unsd)},
        },
        "audit": audit,
        "output": {"path": str(args.output), "bytes": args.output.stat().st_size, "sha256": digest(args.output)},
        "limitations": [
            "FAOSTAT supplies national crop value, so within-country spatial value is proportional to modeled MapSPAM production.",
            "Countries without a 1999-2001 baseline value are excluded without imputation.",
            "Gross production value is not producer surplus, consumer surplus, trade-adjusted welfare, or a damage estimate.",
        ],
        "claim_gates": {"conditional_baseline_value_weight": True, "global_complete_value_weight": False, "welfare": False, "damage_or_scc": False},
        "implementation": {"path": str(Path(__file__).resolve().relative_to(ROOT)), "sha256": digest(Path(__file__).resolve())},
    }
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "audit": audit, "output": result["output"]}, indent=2))


if __name__ == "__main__":
    main()
