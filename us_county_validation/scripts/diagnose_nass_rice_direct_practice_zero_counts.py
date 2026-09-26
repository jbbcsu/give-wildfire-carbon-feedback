#!/usr/bin/env python3
"""Disambiguate exact-series rice zero counts using three broad count requests."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from datetime import UTC, datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DOWNLOADER = ROOT / "us_county_validation/scripts/download_nass_quickstats_api.py"
PROTOCOL = ROOT / "US_RICE_DIRECT_PRACTICE_ZERO_COUNT_DIAGNOSTIC_20260925.md"
PRACTICES = (None, "IRRIGATED", "NON-IRRIGATED")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(2**20), b""):
            digest.update(block)
    return digest.hexdigest()


def load_downloader():
    spec = importlib.util.spec_from_file_location("nass_rice_count_diagnostic", DOWNLOADER)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load credential-safe NASS downloader")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def parameters(practice: str | None) -> dict[str, str]:
    query = {
        "source_desc": "SURVEY", "sector_desc": "CROPS",
        "commodity_desc": "RICE", "statisticcat_desc": "YIELD",
        "agg_level_desc": "COUNTY", "freq_desc": "ANNUAL",
        "reference_period_desc": "YEAR", "format": "JSON",
    }
    if practice is not None:
        query["prodn_practice_desc"] = practice
    return query


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
    for practice in PRACTICES:
        query = parameters(practice)
        count = base.count_records(query, key)
        rows.append({
            "practice": practice or "UNFILTERED",
            "count": count,
            "query_parameters_excluding_key": query,
        })
    counts = {row["practice"]: row["count"] for row in rows}
    if counts["UNFILTERED"] > 0 and counts["IRRIGATED"] == counts["NON-IRRIGATED"] == 0:
        conclusion = "county_rice_yield_exists_but_no_direct_practice_labels"
    elif counts["IRRIGATED"] > 0 or counts["NON-IRRIGATED"] > 0:
        conclusion = "primary_exact_series_descriptor_requires_separate_audit"
    else:
        conclusion = "broad_count_inconclusive_or_county_survey_rice_yield_absent"
    result = {
        "schema": "nass_rice_direct_practice_zero_count_diagnostic_v1",
        "status": "completed_count_only_no_values_downloaded",
        "retrieved_utc": datetime.now(UTC).isoformat(),
        "official_count_endpoint": base.COUNT_ENDPOINT,
        "protocol": {"path": str(PROTOCOL.relative_to(ROOT)), "sha256": sha256(PROTOCOL)},
        "implementation": {
            "path": str(Path(__file__).resolve().relative_to(ROOT)),
            "sha256": sha256(Path(__file__).resolve()),
        },
        "queries": rows,
        "conclusion": conclusion,
        "api_data_endpoint_called": False,
        "yield_values_downloaded": False,
        "response_estimated": False,
        "damage_or_scc_estimated": False,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"counts": counts, "conclusion": conclusion}, sort_keys=True))


if __name__ == "__main__":
    main()
