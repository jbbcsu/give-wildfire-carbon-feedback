#!/usr/bin/env python3
"""Synthetic tests for the four-vintage all-cropland classifier."""
from __future__ import annotations

import importlib.util
import hashlib
import json
import tempfile
from pathlib import Path


SCRIPT = Path(__file__).with_name("prepare_nass_cropland_irrigation_classifier.py")
SPEC = importlib.util.spec_from_file_location("prepare_classifier", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load classifier preparer")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def row(year: int, county: str, practice: str, value: str) -> dict[str, str]:
    irrigated = practice == "IRRIGATED"
    return {
        **MODULE.EXPECTED,
        "prodn_practice_desc": practice,
        "unit_desc": "ACRES",
        "year": str(year),
        "state_ansi": "01",
        "county_ansi": county,
        "state_alpha": "AL",
        "state_name": "ALABAMA",
        "county_name": f"COUNTY {county}",
        "Value": value,
        "short_desc": (
            "AG LAND, CROPLAND, HARVESTED, IRRIGATED - ACRES"
            if irrigated else "AG LAND, CROPLAND, HARVESTED - ACRES"
        ),
    }


with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    paths = {}
    for year in MODULE.YEARS:
        rows = [
            row(year, "001", "ALL PRODUCTION PRACTICES", "1,000"),
            row(year, "001", "IRRIGATED", "100" if year != 2007 else "200"),
            row(year, "003", "ALL PRODUCTION PRACTICES", "1,000"),
            row(year, "003", "IRRIGATED", "150"),
            row(year, "005", "ALL PRODUCTION PRACTICES", "1,000"),
            row(year, "005", "IRRIGATED", "(D)"),
        ]
        path = root / f"{year}.json"
        path.write_text(json.dumps({"data": rows}), encoding="utf-8")
        paths[year] = path
    manifest = root / "MANIFEST.jsonl"
    with manifest.open("w", encoding="utf-8") as stream:
        for year, path in paths.items():
            stream.write(json.dumps({
                "raw_file": str(path),
                "raw_bytes": path.stat().st_size,
                "raw_sha512": hashlib.sha512(path.read_bytes()).hexdigest(),
                "retrieved_utc": "2026-09-22T00:00:00+00:00",
                "source": "USDA NASS Quick Stats API",
                "license": "USDA public data",
                "official_count_endpoint": "https://quickstats.nass.usda.gov/api/get_counts/",
                "official_data_endpoint": "https://quickstats.nass.usda.gov/api/api_GET/",
                "preflight_count": 6,
                "query_parameters_excluding_key": {"year": str(year)},
            }, sort_keys=True) + "\n")
    output, audit = MODULE.prepare(paths, manifest)
    indexed = output.set_index("county_geoid")
    assert indexed.loc["01001", "irrigation_class"] == "irrigated"
    assert abs(indexed.loc["01001", "maximum_irrigation_share"] - 0.2) < 1e-12
    assert indexed.loc["01003", "irrigation_class"] == "dryland"
    assert indexed.loc["01005", "irrigation_class"] == "missing"
    assert indexed.loc["01005", "eligible_vintage_count"] == 0
    assert audit["exact_equality_count"] == 1
    assert audit["eligible_counties"] == 2
    assert len(audit["source_receipts"]) == 4
    assert all("key" not in receipt["query_parameters_excluding_key"] for receipt in audit["source_receipts"])

print("four-vintage all-cropland classifier tests passed")
