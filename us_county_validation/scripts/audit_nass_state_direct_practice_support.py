#!/usr/bin/env python3
"""Count-only NASS audit for a newer state direct-practice validation panel."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOWNLOADER = ROOT / "us_county_validation/scripts/download_nass_quickstats_api.py"
PROTOCOL = ROOT / "US_STATE_DIRECT_PRACTICE_TERMINAL_SUPPORT_PROTOCOL_20260921.md"
CROPS = {
    "corn": ("CORN", "GRAIN"),
    "soybean": ("SOYBEANS", "BEANS"),
}
PRACTICES = ("IRRIGATED", "NON-IRRIGATED")
YEARS = tuple(range(2012, 2026))
TERMINAL_YEARS = tuple(range(2020, 2026))


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(2**20), b""):
            digest.update(block)
    return digest.hexdigest()


def load_downloader():
    spec = importlib.util.spec_from_file_location("nass_quickstats_state_audit", DOWNLOADER)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load credential-safe NASS downloader")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def parameters(crop: str, practice: str, year: int) -> dict[str, str]:
    if crop not in CROPS or practice not in PRACTICES or year not in YEARS:
        raise ValueError("unsupported state support query")
    commodity, utilization = CROPS[crop]
    return {
        "source_desc": "SURVEY",
        "sector_desc": "CROPS",
        "commodity_desc": commodity,
        "class_desc": "ALL CLASSES",
        "statisticcat_desc": "YIELD",
        "agg_level_desc": "STATE",
        "freq_desc": "ANNUAL",
        "reference_period_desc": "YEAR",
        "domain_desc": "TOTAL",
        "prodn_practice_desc": practice,
        "util_practice_desc": utilization,
        "unit_desc": "BU / ACRE",
        "year": str(year),
        "format": "JSON",
    }


def summarize(rows: list[dict]) -> dict:
    expected = {(crop, practice, year) for crop in CROPS for practice in PRACTICES for year in YEARS}
    keys = {(row["crop"], row["practice"], int(row["year"])) for row in rows}
    if keys != expected or len(rows) != len(expected) or any(type(row["count"]) is not int or row["count"] < 0 for row in rows):
        raise ValueError("state support count matrix incomplete or invalid")
    series = []
    for crop in CROPS:
        for practice in PRACTICES:
            chosen = [row for row in rows if row["crop"] == crop and row["practice"] == practice]
            terminal = [row["count"] for row in chosen if row["year"] in TERMINAL_YEARS]
            series.append({
                "crop": crop,
                "practice": practice,
                "development_years": [2012, 2019],
                "terminal_years": [2020, 2025],
                "minimum_annual_count_all_years": min(row["count"] for row in chosen),
                "minimum_terminal_annual_count": min(terminal),
                "terminal_state_year_count": sum(terminal),
                "state_panel_feasible": min(terminal) >= 8 and sum(terminal) >= 60,
            })
    return {"query_count": len(rows), "series": series}


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
                query = parameters(crop, practice, year)
                count = base.count_records(query, key)
                rows.append({"crop": crop, "practice": practice, "year": year,
                             "count": count, "query_parameters_excluding_key": query})
    summary = summarize(rows)
    result = {
        "status": "nass_state_direct_practice_count_support_audited_not_yield_response",
        "retrieved_utc": datetime.now(UTC).isoformat(),
        "official_count_endpoint": base.COUNT_ENDPOINT,
        "protocol_sha256": sha(PROTOCOL),
        "code_sha256": sha(Path(__file__)),
        "queries": rows,
        **summary,
        "yield_values_downloaded": False,
        "weather_aligned": False,
        "response_estimated": False,
        "damage_or_scc_estimated": False,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": result["status"], **summary}))


if __name__ == "__main__":
    main()
