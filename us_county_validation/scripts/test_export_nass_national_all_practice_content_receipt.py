#!/usr/bin/env python3
"""Offline adversarial tests for the national NASS content receipt."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory

import export_nass_national_all_practice_content_receipt as module


def raw_row(commodity: str, year: int) -> dict[str, object]:
    return {
        "year": year, "commodity_desc": commodity, "unit_desc": "BU / ACRE",
        "prodn_practice_desc": "ALL PRODUCTION PRACTICES",
        "util_practice_desc": module.SERIES[commodity]["util"], "source_desc": "SURVEY",
        "sector_desc": "CROPS", "statisticcat_desc": "YIELD", "agg_level_desc": "COUNTY",
        "freq_desc": "ANNUAL", "reference_period_desc": "YEAR", "domain_desc": "TOTAL",
        "domaincat_desc": "NOT SPECIFIED", "Value": "100", "state_ansi": "31",
        "county_ansi": "039",
    }


with TemporaryDirectory() as temporary:
    root = Path(temporary)
    manifest = root / "MANIFEST.jsonl"
    records = []
    for commodity in ("CORN", "SOYBEANS"):
        for year in (1981, 1982):
            name = module._expected_name(commodity, year)
            payload = json.dumps({"data": [raw_row(commodity, year)]}).encode("utf-8")
            (root / name).write_bytes(payload)
            records.append(
                {
                    "license": "USDA public data; preserve disclosure/suppression flags and source attribution",
                    "official_count_endpoint": "https://quickstats.nass.usda.gov/api/get_counts/",
                    "official_data_endpoint": "https://quickstats.nass.usda.gov/api/api_GET/",
                    "preflight_count": 1,
                    "query_parameters_excluding_key": module._expected_query(commodity, year),
                    "raw_bytes": len(payload), "raw_file": str(root / name),
                    "raw_sha512": hashlib.sha512(payload).hexdigest(),
                    "retrieved_utc": "2026-08-26T20:00:00+00:00",
                    "role": "US county crop-yield validation outcome; not an SCC input",
                    "source": "USDA NASS Quick Stats API",
                }
            )
    manifest.write_text("".join(json.dumps(value, sort_keys=True) + "\n" for value in records))
    source = manifest.read_bytes()
    module.EXPECTED_OBJECTS = 4
    module.EXPECTED_TOTAL_BYTES = sum(value["raw_bytes"] for value in records)
    module.EXPECTED_TOTAL_RECORDS = 4
    module.REVIEWED_MANIFEST_SIZE_BYTES = len(source)
    module.REVIEWED_MANIFEST_SHA512 = hashlib.sha512(source).hexdigest()
    original_expected_query = module._expected_query
    module._expected_query = lambda commodity, year: original_expected_query(commodity, year)
    # Narrow the chronological scope for this synthetic fixture only.
    original_range = range
    module.range = lambda start, stop: original_range(1981, 1983) if (start, stop) == (1981, 2020) else original_range(start, stop)

    receipt = module.build_receipt(manifest, root)
    module.validate_receipt(receipt)
    assert receipt["scope"]["object_count"] == 4
    assert "/users/" not in module.serialize(receipt).decode("utf-8").lower()

    tampered = copy.deepcopy(receipt)
    tampered["objects"][0]["raw_sha512"] = "0" * 128
    try:
        module.validate_receipt(tampered)
    except RuntimeError as error:
        assert "object envelope" in str(error)
    else:
        raise AssertionError("expected receipt-tampering failure")

    source_records = [json.loads(line) for line in manifest.read_text().splitlines()]
    source_records[0]["query_parameters_excluding_key"]["api_key"] = "forbidden"
    manifest.write_text("".join(json.dumps(value, sort_keys=True) + "\n" for value in source_records))
    changed = manifest.read_bytes()
    module.REVIEWED_MANIFEST_SIZE_BYTES = len(changed)
    module.REVIEWED_MANIFEST_SHA512 = hashlib.sha512(changed).hexdigest()
    try:
        module.build_receipt(manifest, root)
    except RuntimeError as error:
        assert "fields differ" in str(error) or "credential" in str(error)
    else:
        raise AssertionError("expected credential-field failure")

print("national NASS content receipt tests passed")
