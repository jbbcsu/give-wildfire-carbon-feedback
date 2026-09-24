#!/usr/bin/env python3
"""Build current-USD maize weights rebased to a common 2014--2016 level.

This is a registered alternative to the failed constant-dollar baseline. It
requires complete 1999--2001 FAOSTAT current-USD observations and uses the
pinned U.S. GDP implicit price deflator as an explicit approximation.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import tomllib
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from audit_mapspam_faostat_welfare_crosswalk import parse_unsd_m49
from build_hultgren_country_maize_value_weights import allocate_country_cells

ROOT = Path(__file__).resolve().parents[1]
CURRENT = "gross_production_value_current_1000_us_usd"
OUTPUT_VALUE = "maize_gross_production_value_current_usd_rebased_2014_2016_usd"
YEARS = (1999, 2000, 2001)


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mapspam", type=Path, required=True)
    parser.add_argument("--gec-audit", type=Path, required=True)
    parser.add_argument("--faostat", type=Path, required=True)
    parser.add_argument("--unsd", type=Path, required=True)
    parser.add_argument("--price-registry", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.receipt.exists():
        raise ValueError("fresh outputs required")
    registry = tomllib.loads(args.price_registry.read_text(encoding="utf-8"))
    indices = registry["annual_indices"]
    annual_index = {year: float(indices[f"y{year}"]) for year in YEARS}
    target = sum(float(indices[f"y{year}"]) for year in (2014, 2015, 2016)) / 3.0
    rule = registry["current_usd_baseline_rebase"]
    if rule["input_years"] != list(YEARS) or "mean_t" not in rule["formula"]:
        raise ValueError("price rebase registry differs")

    iso_to_m49, _ = parse_unsd_m49(args.unsd)
    m49_to_iso = {m49: iso for iso, m49 in iso_to_m49.items()}
    values: dict[str, dict[int, float]] = defaultdict(dict)
    flags: dict[str, set[str]] = defaultdict(set)
    with args.faostat.open(newline="", encoding="utf-8") as stream:
        for row_number, row in enumerate(csv.DictReader(stream), start=2):
            year = int(row["year"])
            if int(row["item_code"]) != 56 or year not in YEARS or not row[CURRENT]:
                continue
            iso = m49_to_iso.get(row["m49_code"].zfill(3))
            if not iso:
                continue
            if year in values[iso]:
                raise ValueError(f"duplicate country-year at row {row_number}")
            values[iso][year] = float(row[CURRENT])
            flags[iso].add(row[CURRENT + "_flag"])
    rebased_thousand = {
        iso: sum(by_year[year] * target / annual_index[year] for year in YEARS) / len(YEARS)
        for iso, by_year in values.items()
        if set(by_year) == set(YEARS)
    }
    gec = json.loads(args.gec_audit.read_text(encoding="utf-8"))
    stat_to_iso = {row["stat_code"]: row["resolved_iso3"] for row in gec["per_stat_code"]}
    frame, audit = allocate_country_cells(args.mapspam, stat_to_iso, rebased_thousand)
    audit["allocated_current_usd_rebased_2014_2016_usd"] = audit.pop(
        "allocated_constant_2014_2016_usd"
    )
    frame = frame.rename(columns={
        "maize_gross_production_value_constant_2014_2016_usd": OUTPUT_VALUE
    })
    args.output.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(args.output, index=False)
    country_totals = frame.groupby("iso3")[OUTPUT_VALUE].sum()
    result = {
        "schema": "hultgren_country_cell_maize_value_weights_current_rebased/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "alternative_current_usd_rebased_country_cell_weights_not_welfare_damage_or_scc",
        "value_column": OUTPUT_VALUE,
        "units": "US dollars rebased from annual current USD to mean 2014-2016 GDP-deflator level",
        "price_basis": {"annual_indices": annual_index, "target_index": target, "formula": rule["formula"], "price_concept_equivalence_claimed": False},
        "sources": {
            "mapspam": {"path": str(args.mapspam), "sha256": digest(args.mapspam)},
            "gec_audit": {"path": str(args.gec_audit), "sha256": digest(args.gec_audit)},
            "faostat": {"path": str(args.faostat), "sha256": digest(args.faostat), "license": "CC-BY-4.0"},
            "unsd": {"path": str(args.unsd), "sha256": digest(args.unsd)},
            "price_registry": {"path": str(args.price_registry), "sha256": digest(args.price_registry), "underlying_source_sha256": registry["source_sha256"]},
        },
        "audit": {**audit, "complete_current_usd_country_count_before_mapspam": len(rebased_thousand), "venezuela_rebased_value_usd": float(country_totals.get("VEN", 0.0)), "venezuela_share": float(country_totals.get("VEN", 0.0) / country_totals.sum())},
        "source_flags": {iso: sorted(flags[iso]) for iso in sorted(rebased_thousand)},
        "output": {"path": str(args.output), "sha256": digest(args.output), "bytes": args.output.stat().st_size},
        "limitations": [
            "The U.S. GDP-wide deflator is an explicit approximation to a farm-gate price concept.",
            "Countries lacking any of the three current-USD observations remain missing without imputation.",
            "This builds weights only; it does not authorize welfare, damage, or SCC calculation.",
        ],
        "claim_gates": {"alternative_weight_input": True, "welfare": False, "damage_or_scc": False},
        "implementation": {"path": "scripts/build_hultgren_country_maize_value_weights_current_rebased.py", "sha256": digest(Path(__file__).resolve())},
    }
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "audit": result["audit"], "output": result["output"]}, indent=2))


if __name__ == "__main__":
    main()
