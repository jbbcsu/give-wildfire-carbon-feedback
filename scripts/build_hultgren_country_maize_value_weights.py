#!/usr/bin/env python3
"""Build country-by-half-degree maize baseline-value weights.

National 1999--2001 FAOSTAT maize gross production values are allocated over
MapSPAM rows in proportion to fixed production, retaining country identity.
The output is a market-input proxy, not welfare, damage, or SCC.
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

import pandas as pd

from audit_mapspam_faostat_welfare_crosswalk import parse_unsd_m49, read_faostat_baseline
from build_mapspam_halfdegree_maize_weights import halfdegree_key

ROOT = Path(__file__).resolve().parents[1]
MAIZE_ITEM = 56


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def allocate_country_cells(
    mapspam: Path, stat_to_iso: dict[str, str | None], iso_values_thousand_usd: dict[str, float]
) -> tuple[pd.DataFrame, dict[str, object]]:
    country_production: dict[str, float] = defaultdict(float)
    source_total = 0.0
    with mapspam.open("r", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        required = {"stat_code", "latitude", "longitude", "maize_total_mt"}
        require(reader.fieldnames is not None and required <= set(reader.fieldnames), "MapSPAM columns differ")
        for row_number, record in enumerate(reader, start=2):
            production = float(record["maize_total_mt"])
            require(math.isfinite(production) and production >= 0.0, f"invalid production at row {row_number}")
            source_total += production
            iso = stat_to_iso.get(record["stat_code"])
            if production > 0.0 and iso in iso_values_thousand_usd:
                country_production[str(iso)] += production
    require(source_total > 0.0 and country_production, "empty matched production")

    cells: dict[tuple[str, int, int], list[float]] = defaultdict(lambda: [0.0, 0.0])
    with mapspam.open("r", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        for row_number, record in enumerate(reader, start=2):
            production = float(record["maize_total_mt"])
            iso = stat_to_iso.get(record["stat_code"])
            if production <= 0.0 or iso not in iso_values_thousand_usd:
                continue
            key = (str(iso), *halfdegree_key(float(record["latitude"]), float(record["longitude"])))
            value = production / country_production[str(iso)] * iso_values_thousand_usd[str(iso)] * 1000.0
            require(math.isfinite(value) and value >= 0.0, f"invalid value at row {row_number}")
            cells[key][0] += production
            cells[key][1] += value
    rows = [
        {
            "iso3": iso,
            "native_lat_index": lat,
            "native_lon_index": lon,
            "matched_maize_production_mt": values[0],
            "maize_gross_production_value_constant_2014_2016_usd": values[1],
        }
        for (iso, lat, lon), values in sorted(cells.items())
    ]
    frame = pd.DataFrame(rows)
    require(not frame.empty and not frame.duplicated(["iso3", "native_lat_index", "native_lon_index"]).any(), "invalid cell keys")
    expected = {iso: value * 1000.0 for iso, value in iso_values_thousand_usd.items() if iso in country_production}
    observed = frame.groupby("iso3")["maize_gross_production_value_constant_2014_2016_usd"].sum().to_dict()
    for iso, value in expected.items():
        require(math.isclose(observed[iso], value, rel_tol=1e-10, abs_tol=1e-4), f"national value differs: {iso}")
    return frame, {
        "source_maize_production_mt": source_total,
        "matched_maize_production_mt": sum(country_production.values()),
        "matched_maize_production_fraction": sum(country_production.values()) / source_total,
        "matched_country_count": len(country_production),
        "country_cell_rows": len(frame),
        "allocated_constant_2014_2016_usd": float(frame["maize_gross_production_value_constant_2014_2016_usd"].sum()),
        "cells_shared_by_multiple_countries": int((frame.groupby(["native_lat_index", "native_lon_index"]).size() > 1).sum()),
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
    require(gec["unresolved_rows"] == 0 and gec["gate"]["four_character_country_mapping_resolved"], "GEC audit failed")
    stat_to_iso = {row["stat_code"]: row["resolved_iso3"] for row in gec["per_stat_code"]}
    iso_to_m49, _ = parse_unsd_m49(args.unsd)
    faostat = read_faostat_baseline(args.faostat)
    iso_values = {
        iso: float(faostat[(MAIZE_ITEM, m49)]["mean_constant_2014_2016_thousand_usd"])
        for iso, m49 in iso_to_m49.items()
        if (MAIZE_ITEM, m49) in faostat
    }
    frame, audit = allocate_country_cells(args.mapspam, stat_to_iso, iso_values)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(args.output, index=False)
    result = {
        "schema": "hultgren_country_cell_maize_value_weights/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "conditional_country_cell_baseline_value_weights_not_welfare_damage_or_scc",
        "sources": {
            "mapspam": {"path": str(args.mapspam), "sha256": digest(args.mapspam), "doi": "10.7910/DVN/A50I2T"},
            "gec_audit": {"path": str(args.gec_audit), "sha256": digest(args.gec_audit)},
            "faostat": {"path": str(args.faostat), "sha256": digest(args.faostat), "license": "CC-BY-4.0"},
            "unsd": {"path": str(args.unsd), "sha256": digest(args.unsd)},
        },
        "audit": audit,
        "output": {"path": str(args.output), "sha256": digest(args.output), "bytes": args.output.stat().st_size},
        "method": "allocate each matched country's mean 1999-2001 FAOSTAT maize gross production value across its MapSPAM rows and retain country-by-half-degree-cell identity",
        "limitations": [
            "National gross production value is allocated within country in proportion to modeled MapSPAM production.",
            "Half-degree cells crossing borders retain separate country rows but share the same cell weather response.",
            "Gross production value is a market baseline proxy, not welfare, damage, or SCC.",
        ],
        "claim_gates": {"country_market_input": True, "welfare": False, "damage_or_scc": False},
        "implementation": {"path": str(Path(__file__).resolve().relative_to(ROOT)), "sha256": digest(Path(__file__).resolve())},
    }
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "audit": audit, "output": result["output"]}, indent=2))


if __name__ == "__main__":
    main()
