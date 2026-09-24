#!/usr/bin/env python3
"""Audit national maize value controls before monetary promotion.

The checks are review triggers, not replacements for source values. They flag
large constant-dollar value per MapSPAM tonne and large divergence from the
same FAOSTAT record's current-dollar value.
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

from audit_mapspam_faostat_welfare_crosswalk import parse_unsd_m49

CONSTANT = "gross_production_value_constant_20142016_1000_us_usd"
CURRENT = "gross_production_value_current_1000_us_usd"
YEARS = {1999, 2000, 2001}


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
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("fresh output required")
    gec = json.loads(args.gec_audit.read_text(encoding="utf-8"))
    mapping = {row["stat_code"]: row["resolved_iso3"] for row in gec["per_stat_code"]}
    production: dict[str, float] = defaultdict(float)
    with args.mapspam.open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            iso = mapping.get(row["stat_code"])
            if iso:
                production[str(iso)] += float(row["maize_total_mt"])
    iso_to_m49, _ = parse_unsd_m49(args.unsd)
    m49_to_iso = {m49: iso for iso, m49 in iso_to_m49.items()}
    values: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    flags: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    with args.faostat.open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            if int(row["item_code"]) != 56 or int(row["year"]) not in YEARS:
                continue
            iso = m49_to_iso.get(row["m49_code"].zfill(3))
            if not iso:
                continue
            for field in (CONSTANT, CURRENT):
                if row[field]:
                    values[iso][field].append(float(row[field]) * 1000.0)
                    flags[iso][field].add(row[field + "_flag"])
    records = []
    for iso in sorted(production):
        constant = values[iso][CONSTANT]
        if not constant or production[iso] <= 0.0:
            continue
        current = values[iso][CURRENT]
        constant_mean = sum(constant) / len(constant)
        current_mean = sum(current) / len(current) if current else None
        records.append({
            "iso3": iso,
            "mapspam_maize_production_mt": production[iso],
            "constant_2014_2016_usd_mean": constant_mean,
            "constant_year_count": len(constant),
            "constant_flags": sorted(flags[iso][CONSTANT]),
            "constant_usd_per_mapspam_tonne": constant_mean / production[iso],
            "current_usd_mean": current_mean,
            "current_year_count": len(current),
            "current_flags": sorted(flags[iso][CURRENT]),
            "constant_to_current_ratio": constant_mean / current_mean if current_mean and current_mean > 0 else None,
        })
    global_constant = sum(row["constant_2014_2016_usd_mean"] for row in records)
    for row in records:
        row["share_of_matched_constant_value"] = row["constant_2014_2016_usd_mean"] / global_constant
        row["review_flag_value_per_tonne_above_2000"] = row["constant_usd_per_mapspam_tonne"] > 2000.0
        ratio = row["constant_to_current_ratio"]
        row["review_flag_constant_current_ratio_above_10"] = ratio is not None and ratio > 10.0
    triggered = [row for row in records if row["review_flag_value_per_tonne_above_2000"] or row["review_flag_constant_current_ratio_above_10"]]
    venezuela = next(row for row in records if row["iso3"] == "VEN")
    result = {
        "schema": "faostat_maize_value_plausibility_audit/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "monetary_promotion_blocked_pending_price_basis_resolution",
        "sources": {
            "mapspam": {"path": str(args.mapspam), "sha256": digest(args.mapspam)},
            "gec_audit": {"path": str(args.gec_audit), "sha256": digest(args.gec_audit)},
            "faostat": {"path": str(args.faostat), "sha256": digest(args.faostat), "license": "CC-BY-4.0"},
            "unsd": {"path": str(args.unsd), "sha256": digest(args.unsd)},
        },
        "review_thresholds": {"constant_usd_per_mapspam_tonne": 2000.0, "constant_to_current_ratio": 10.0, "role": "diagnostic review triggers, not winsorization or replacement rules"},
        "coverage": {"countries_with_constant_value": len(records), "countries_with_three_current_usd_years": sum(row["current_year_count"] == 3 for row in records), "matched_constant_value": global_constant},
        "triggered_countries": [row["iso3"] for row in triggered],
        "venezuela_diagnostic": venezuela,
        "records": records,
        "decision": {
            "production_weighted_yield_results_affected": False,
            "value_weighted_and_monetary_results_publication_ready": False,
            "required_next_step": "verify FAOSTAT constant-dollar construction for flagged countries and run a preregistered alternative baseline, such as complete 1999-2001 current-USD values converted to a common price year, without outcome-based country deletion",
            "do_not": "do not silently delete Venezuela, cap its value, or reinterpret the current conditional monetary sensitivities as damages or SCC",
        },
        "interpretation": "The source field is reproduced exactly; this audit does not assert a FAOSTAT error. It shows that its use as a cross-country maize market baseline fails the project's plausibility review pending price-basis resolution.",
        "claim_gates": {"monetary_promotion": False, "damage_or_scc": False},
        "implementation": {"path": "scripts/audit_faostat_maize_value_plausibility.py", "sha256": digest(Path(__file__).resolve())},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "triggered_countries": result["triggered_countries"], "venezuela_diagnostic": venezuela}, indent=2))


if __name__ == "__main__":
    main()
