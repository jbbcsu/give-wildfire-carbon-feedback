#!/usr/bin/env python3
"""Count-only audit for Census county practice-specific production and area."""
from __future__ import annotations

import argparse
import importlib.util
import json
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOWNLOADER = ROOT / "us_county_validation/scripts/download_nass_quickstats_api.py"
PROTOCOL = ROOT / "US_CENSUS_DIRECT_PRACTICE_OUTCOME_SUPPORT_PROTOCOL_20260921.md"
CROPS = {"corn": ("CORN", "GRAIN"), "soybean": ("SOYBEANS", "BEANS")}
PRACTICES = ("IRRIGATED", "NON-IRRIGATED")
YEARS = (2012, 2017, 2022)
STATISTICS = {"area": ("AREA HARVESTED", "ACRES"), "production": ("PRODUCTION", "BU")}


def sha(path: Path) -> str:
    import hashlib
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(2**20), b""):
            digest.update(block)
    return digest.hexdigest()


def load_downloader():
    spec = importlib.util.spec_from_file_location("nass_census_outcome_support", DOWNLOADER)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load credential-safe NASS downloader")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def parameters(crop: str, practice: str, year: int, statistic: str) -> dict[str, str]:
    if crop not in CROPS or practice not in PRACTICES or year not in YEARS or statistic not in STATISTICS:
        raise ValueError("unsupported Census support query")
    commodity, utilization = CROPS[crop]
    statistic_name, unit = STATISTICS[statistic]
    return {
        "source_desc": "CENSUS",
        "sector_desc": "CROPS",
        "commodity_desc": commodity,
        "class_desc": "ALL CLASSES",
        "statisticcat_desc": statistic_name,
        "agg_level_desc": "COUNTY",
        "freq_desc": "ANNUAL",
        "reference_period_desc": "YEAR",
        "domain_desc": "TOTAL",
        "prodn_practice_desc": practice,
        "util_practice_desc": utilization,
        "unit_desc": unit,
        "year": str(year),
        "format": "JSON",
    }


def summarize(rows: list[dict]) -> dict:
    expected = {(crop, practice, year, statistic) for crop in CROPS for practice in PRACTICES
                for year in YEARS for statistic in STATISTICS}
    keys = {(row["crop"], row["practice"], int(row["year"]), row["statistic"]) for row in rows}
    if keys != expected or len(rows) != len(expected) or any(type(row["count"]) is not int or row["count"] < 0 for row in rows):
        raise ValueError("Census count matrix incomplete or invalid")
    cells = []
    for crop in CROPS:
        for practice in PRACTICES:
            for year in YEARS:
                counts = {row["statistic"]: row["count"] for row in rows
                          if row["crop"] == crop and row["practice"] == practice and row["year"] == year}
                cells.append({"crop": crop, "practice": practice, "year": year,
                              "area_count": counts["area"], "production_count": counts["production"],
                              "count_feasible": min(counts.values()) >= 100})
    return {"query_count": len(rows), "cells": cells,
            "feasible_cells": sum(row["count_feasible"] for row in cells)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--secrets-file", type=Path, default=ROOT / ".secrets/nass.env")
    args = parser.parse_args()
    out = args.out.resolve()
    if out.exists() or not out.is_relative_to(ROOT / "data/interim") or out.suffix != ".json":
        raise ValueError("fresh ignored interim JSON output required")
    base = load_downloader()
    key = base.read_key(args.secrets_file)
    rows = []
    for crop in CROPS:
        for practice in PRACTICES:
            for year in YEARS:
                for statistic in STATISTICS:
                    query = parameters(crop, practice, year, statistic)
                    rows.append({"crop": crop, "practice": practice, "year": year,
                                 "statistic": statistic, "count": base.count_records(query, key),
                                 "query_parameters_excluding_key": query})
    summary = summarize(rows)
    result = {
        "status": "nass_census_direct_practice_outcome_count_support_audited_not_yields",
        "retrieved_utc": datetime.now(UTC).isoformat(),
        "official_count_endpoint": base.COUNT_ENDPOINT,
        "protocol_sha256": sha(PROTOCOL),
        "code_sha256": sha(Path(__file__)),
        "queries": rows,
        **summary,
        "values_downloaded": False,
        "yield_ratios_calculated": False,
        "response_estimated": False,
        "damage_or_scc_estimated": False,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": result["status"], **summary}))


if __name__ == "__main__":
    main()
